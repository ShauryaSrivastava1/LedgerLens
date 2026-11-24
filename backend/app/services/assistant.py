"""
Orchestrates the grounded AI Assistant: build a question-driven retrieval
context -> construct a prompt constrained to that context -> call the LLM
-> parse and validate the JSON response -> cross-check citations -> return
a dict ready for the API response.

Deliberately mirrors report_generator.py's shape (retrieval -> LLM ->
validate -> verify citations) since it's the same grounded-answer pattern
applied to a single ad-hoc question instead of a fixed report. Every piece
of infrastructure — EmbeddingService, VectorStore, the financial/
shareholding/price summarizers, the provider-agnostic LLMClient, JSON
extraction, and citation verification — is reused from Milestones 2/3, not
reimplemented here.

Single-company, stateless: this module has no concept of conversation
history. Every call answers exactly one question about exactly one
company from freshly retrieved evidence — nothing is carried over from a
previous call, and nothing here accepts or stores prior turns.
"""

from sqlalchemy.orm import Session

from app import crud, models
from app.services.embeddings import EmbeddingService
from app.services.llm.base import LLMClient
from app.services.report_context import DEFAULT_ASSISTANT_CHUNKS, ReportContext, build_assistant_context
from app.services.report_generator import _extract_json
from app.services.report_schema import AssistantAnswerOutput, verify_and_annotate_citations
from app.services.vector_store import VectorStore

SYSTEM_PROMPT = """You are a rigorous, evidence-based equity research assistant answering a \
retail investor's question about ONE specific Indian listed company. Your purpose is to help \
the investor think critically and reduce emotional bias — NOT to predict stock prices and NOT \
to tell them to buy or sell.

Rules you must follow exactly:
1. Answer ONLY using the context given to you below (financial metrics, shareholding pattern, \
price data, and document excerpts). If you did not see it in the context, you do not know it.
2. Every substantive claim in your answer MUST be backed by at least one citation: either a \
document excerpt (using its exact document_id and page_number as given to you) or a specific \
financial metric and period from the data provided (using the exact period label as given to \
you). Never invent a document_id, page_number, period, number, or quote that is not present in \
the context below.
3. If the context provided does not contain enough evidence to answer the question, set \
"insufficient_evidence" to true, leave "citations" empty, and briefly say in "answer" that you \
don't have enough evidence on this platform to answer — do not guess, pad with generic \
statements, or answer from general knowledge about the company or the sector.
4. This question is about a single company only. Do not compare it to other companies, even if \
asked — say that comparison isn't something you can do here and stick to what the evidence says \
about this company.
5. Do not recommend buying or selling, and do not predict future prices. State what the evidence \
shows and let the investor draw their own conclusion.
6. Respond with ONLY a single valid JSON object matching the schema below. No prose, no markdown \
code fences, no text outside the JSON.

JSON schema:
{
  "answer": "2-6 sentence answer, grounded only in the context below",
  "citations": [
    {"source_type": "document"|"financial_metric", "document_id": "<id or null>",
     "page_number": <int or null>, "period": "<period label or null>",
     "reference": "short description of what this citation supports", "confidence": <0-1>}
  ],
  "confidence": <0-1>,
  "insufficient_evidence": <true or false>
}"""


def _build_user_prompt(context: ReportContext, question: str) -> str:
    excerpt_blocks = []
    for e in context.excerpts:
        excerpt_blocks.append(
            f"[document_id={e.document_id} | file={e.document_filename} | "
            f"page={e.page_number}]\n{e.text}"
        )
    excerpts_text = (
        "\n\n".join(excerpt_blocks) if excerpt_blocks else "No relevant document excerpts were retrieved."
    )

    return f"""Company: {context.company.name} ({context.company.symbol})
Sector: {context.company.sector or 'unknown'}

=== FINANCIAL METRICS (most recent first) ===
{context.financial_summary}

=== SHAREHOLDING PATTERN (most recent first) ===
{context.shareholding_summary}

=== PRICE DATA ===
{context.price_summary}
(Historical/current price context only — NOT a request to predict future price movement.)

=== DOCUMENT EXCERPTS RETRIEVED FOR THIS QUESTION ===
{excerpts_text}

=== QUESTION ===
{question}

Using ONLY the information above, produce the JSON answer described in your instructions."""


def _insufficient_evidence_answer(company: models.Company, question: str, reason: str) -> dict:
    """
    No LLM call needed (or wanted) when a company has nothing ingested at
    all, and no trustworthy answer possible when a question's retrieved
    context turns out to support nothing — either way, this is a fixed,
    deterministic response rather than freeform LLM prose, so there is
    nothing here for a model to hallucinate.
    """
    return {
        "question": question,
        "answer": (
            f"I don't have enough verified evidence to answer that about {company.name}. {reason}"
        ),
        "citations": [],
        "confidence": 0.0,
        "insufficient_evidence": True,
        "context_snapshot": {"document_ids": [], "periods": [], "chunks_retrieved": 0},
    }


def answer_question(
    db: Session,
    company_id,
    question: str,
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    llm_client: LLMClient,
    n_results: int = DEFAULT_ASSISTANT_CHUNKS,
) -> dict:
    company = crud.get_company(db, company_id)
    if company is None:
        raise ValueError(f"Company {company_id} not found")

    financial_metrics = crud.list_financial_metrics(db, company_id)
    shareholding_records = crud.list_shareholding_records(db, company_id)
    price_history = crud.list_prices(db, company_id)
    documents = {str(d.id): d for d in crud.list_documents(db, company_id)}

    # Mirrors report_generator's short-circuit: a company with nothing
    # ingested at all (no metrics, no shareholding, no documents) has
    # nothing to ground an answer in, so skip the LLM call entirely.
    if not financial_metrics and not shareholding_records and not documents:
        return _insufficient_evidence_answer(
            company,
            question,
            "No financial metrics, shareholding data, or documents have been ingested for "
            "this company yet.",
        )

    context = build_assistant_context(
        company=company,
        financial_metrics=financial_metrics,
        shareholding_records=shareholding_records,
        price_history=price_history,
        embedding_service=embedding_service,
        vector_store=vector_store,
        document_lookup=documents,
        question=question,
        n_results=n_results,
    )

    user_prompt = _build_user_prompt(context, question)
    raw_output = llm_client.complete(SYSTEM_PROMPT, user_prompt)
    parsed_json = _extract_json(raw_output)
    llm_output = AssistantAnswerOutput.model_validate(parsed_json)

    citations = verify_and_annotate_citations(
        llm_output.citations, context.known_document_ids, context.known_periods
    )
    verified_count = sum(1 for c in citations if c["citation_verified"])

    context_snapshot = {
        "document_ids": sorted(context.known_document_ids),
        "periods": sorted(context.known_periods),
        "chunks_retrieved": len(context.excerpts),
    }

    # Every answer must be evidence-based and carry verified citations —
    # a prompt instruction asking for that is not a guarantee. If the
    # model claims to have evidence but none of its citations actually
    # verify against what was retrieved, the answer is untrustworthy
    # regardless of what insufficient_evidence says, so it's replaced
    # with the same deterministic response used when nothing was
    # ingested at all, rather than returned to the user as-is.
    if llm_output.insufficient_evidence or verified_count == 0:
        result = _insufficient_evidence_answer(
            company,
            question,
            "The evidence retrieved for this question didn't provide verifiable support for an "
            "answer — try rephrasing, or ask about a topic covered in this company's ingested "
            "documents or financial metrics.",
        )
        result["context_snapshot"] = context_snapshot
        return result

    return {
        "question": question,
        "answer": llm_output.answer,
        "citations": citations,
        "confidence": llm_output.confidence,
        "insufficient_evidence": False,
        "context_snapshot": context_snapshot,
    }
