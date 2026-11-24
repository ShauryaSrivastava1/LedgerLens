"""
Orchestrates AI report generation: build grounded context -> construct a
prompt that constrains the model to that context -> call the LLM -> parse
and validate the JSON response -> cross-check citations -> return a dict
ready to persist as an AIReport row.
"""

import json
import re

from sqlalchemy.orm import Session

from app import crud, models
from app.services.embeddings import EmbeddingService
from app.services.llm.base import LLMClient
from app.services.report_context import ReportContext, build_context
from app.services.report_schema import LLMReportOutput, verify_and_annotate_flags
from app.services.vector_store import VectorStore

SYSTEM_PROMPT = """You are a rigorous, evidence-based equity research assistant analyzing an \
Indian listed company for a retail investor. Your purpose is to help the investor think \
critically and reduce emotional bias — NOT to predict stock prices and NOT to tell them to \
buy or sell.

Rules you must follow exactly:
1. Every item in green_flags and red_flags MUST cite specific evidence: either a document \
excerpt (using its exact document_id and page_number as given to you) or a specific financial \
metric and period from the data provided (using the exact period label as given to you).
2. Never invent numbers, quotes, document IDs, or facts that are not present in the context \
you were given. If you did not see it in the context below, you do not know it.
3. If there is not enough evidence for a section, leave that list empty rather than guessing \
or padding it with generic statements.
4. Do not recommend buying or selling. State what the evidence shows and let the investor draw \
their own conclusion.
5. Respond with ONLY a single valid JSON object matching the schema below. No prose, no \
markdown code fences, no text outside the JSON.

JSON schema:
{
  "scores": {
    "overall": <0-100>, "financial_health": <0-100>, "growth": <0-100>,
    "profitability": <0-100>, "governance": <0-100>, "moat": <0-100>,
    "valuation": <0-100>, "risk": <0-100>, "confidence": <0-1>
  },
  "green_flags": [
    {"statement": "...", "evidence": "...", "source_type": "document"|"financial_metric",
     "document_id": "<id or null>", "page_number": <int or null>,
     "period": "<period label or null>", "confidence": <0-1>}
  ],
  "red_flags": [ same shape as green_flags ],
  "questions_investors_should_ask": ["..."],
  "things_to_verify": ["..."],
  "potential_risks": ["..."],
  "summary": "2-4 sentence neutral summary"
}"""


def _build_user_prompt(context: ReportContext) -> str:
    excerpt_blocks = []
    for e in context.excerpts:
        excerpt_blocks.append(
            f"[document_id={e.document_id} | file={e.document_filename} | "
            f"page={e.page_number} | topic={e.topic}]\n{e.text}"
        )
    excerpts_text = "\n\n".join(excerpt_blocks) if excerpt_blocks else "No document excerpts available."

    return f"""Company: {context.company.name} ({context.company.symbol})
Sector: {context.company.sector or 'unknown'}

=== FINANCIAL METRICS (most recent first) ===
{context.financial_summary}

=== SHAREHOLDING PATTERN (most recent first) ===
{context.shareholding_summary}

=== PRICE DATA ===
{context.price_summary}
(This is historical/current price context only, for describing valuation
relative to where the stock has traded — NOT a request to predict future
price movement. Never forecast a price target.)

=== DOCUMENT EXCERPTS ===
{excerpts_text}

Using ONLY the information above, produce the JSON report described in your instructions."""


def _extract_json(raw_text: str) -> dict:
    """Strips markdown code fences if the model added them despite
    instructions not to, then parses JSON. Raises with the raw text
    included so a parsing failure is debuggable, not a silent guess."""
    cleaned = raw_text.strip()
    fence_match = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM did not return valid JSON: {exc}. Raw output: {raw_text[:1000]}")


def _insufficient_evidence_report(company: models.Company) -> dict:
    """No LLM call needed (or wanted) when there's nothing to analyze —
    this is a deterministic response, not a guess, matching the "if data
    is unavailable, say I don't have enough evidence" principle."""
    return {
        "llm_provider": "none",
        "llm_model": "none",
        "overall_score": None,
        "financial_health_score": None,
        "growth_score": None,
        "profitability_score": None,
        "governance_score": None,
        "moat_score": None,
        "valuation_score": None,
        "risk_score": None,
        "confidence_score": 0.0,
        "summary": (
            f"I don't have enough evidence to analyze {company.name}. No financial metrics "
            "or ingested documents were found for this company. Upload annual reports, "
            "quarterly results, or add financial metrics to enable analysis."
        ),
        "green_flags": [],
        "red_flags": [],
        "questions_investors_should_ask": [],
        "things_to_verify": [
            "No data has been ingested for this company yet — verify documents were uploaded and processed successfully."
        ],
        "potential_risks": [],
        "context_snapshot": {"document_ids": [], "periods": [], "topics_queried": []},
    }


def generate_report(
    db: Session,
    company_id,
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    llm_client: LLMClient,
) -> dict:
    company = crud.get_company(db, company_id)
    if company is None:
        raise ValueError(f"Company {company_id} not found")

    financial_metrics = crud.list_financial_metrics(db, company_id)
    shareholding_records = crud.list_shareholding_records(db, company_id)
    price_history = crud.list_prices(db, company_id)
    documents = {str(d.id): d for d in crud.list_documents(db, company_id)}

    context = build_context(
        company=company,
        financial_metrics=financial_metrics,
        shareholding_records=shareholding_records,
        price_history=price_history,
        embedding_service=embedding_service,
        vector_store=vector_store,
        document_lookup=documents,
    )

    if not context.has_any_evidence:
        return _insufficient_evidence_report(company)

    user_prompt = _build_user_prompt(context)
    raw_output = llm_client.complete(SYSTEM_PROMPT, user_prompt)
    parsed_json = _extract_json(raw_output)
    llm_output = LLMReportOutput.model_validate(parsed_json)

    green_flags = verify_and_annotate_flags(
        llm_output.green_flags, context.known_document_ids, context.known_periods
    )
    red_flags = verify_and_annotate_flags(
        llm_output.red_flags, context.known_document_ids, context.known_periods
    )

    return {
        "llm_provider": llm_client.provider_name,
        "llm_model": llm_client.model_name,
        "overall_score": llm_output.scores.overall,
        "financial_health_score": llm_output.scores.financial_health,
        "growth_score": llm_output.scores.growth,
        "profitability_score": llm_output.scores.profitability,
        "governance_score": llm_output.scores.governance,
        "moat_score": llm_output.scores.moat,
        "valuation_score": llm_output.scores.valuation,
        "risk_score": llm_output.scores.risk,
        "confidence_score": llm_output.scores.confidence,
        "summary": llm_output.summary,
        "green_flags": green_flags,
        "red_flags": red_flags,
        "questions_investors_should_ask": llm_output.questions_investors_should_ask,
        "things_to_verify": llm_output.things_to_verify,
        "potential_risks": llm_output.potential_risks,
        "context_snapshot": {
            "document_ids": sorted(context.known_document_ids),
            "periods": sorted(context.known_periods),
            "topics_queried": list(context.excerpts and {e.topic for e in context.excerpts} or []),
        },
    }
