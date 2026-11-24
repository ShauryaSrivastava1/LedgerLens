"""
Assembles the grounded context for report generation: recent financial
metrics, shareholding trend, and semantically-retrieved document excerpts
across a fixed set of analysis topics. This is the only place in the
pipeline allowed to decide what the LLM gets to see — the LLM is expected
to work only from what's assembled here.
"""

from dataclasses import dataclass, field
import datetime

from app import models
from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStore

# Fixed topic queries run against the vector store for every report.
# Deliberately not driven by user input — a consistent, spec-derived set
# of angles (moat, governance, capital allocation, red flags, guidance)
# is what makes two reports on the same document set reproducible.
TOPIC_QUERIES: dict[str, str] = {
    "moat": "competitive moat brand distribution switching costs network effects pricing power",
    "governance": "corporate governance related party transactions auditor qualified opinion contingent liabilities",
    "capital_allocation": "capital allocation capex debt reduction dividend policy buyback free cash flow",
    "red_flags": "promoter pledging insider selling receivables inventory increase margin decline goodwill",
    "management_guidance": "management guidance outlook commentary earnings call capacity expansion",
}

MAX_METRIC_PERIODS = 8
CHUNKS_PER_TOPIC = 3


@dataclass
class Excerpt:
    document_id: str
    document_filename: str
    page_number: int | None
    text: str
    topic: str


@dataclass
class ReportContext:
    company: models.Company
    financial_summary: str
    shareholding_summary: str
    price_summary: str = ""
    excerpts: list[Excerpt] = field(default_factory=list)

    @property
    def known_document_ids(self) -> set[str]:
        return {e.document_id for e in self.excerpts}

    @property
    def known_periods(self) -> set[str]:
        # Extracted from financial_summary lines; see _format_financial_summary.
        return self._periods

    _periods: set[str] = field(default_factory=set)

    @property
    def has_any_evidence(self) -> bool:
        return bool(self.excerpts) or bool(self._periods)


def _format_financial_summary(metrics: list[models.FinancialMetric]) -> tuple[str, set[str]]:
    if not metrics:
        return "No financial metrics on file for this company.", set()

    lines = []
    periods = set()
    for m in metrics[:MAX_METRIC_PERIODS]:
        period_label = f"{m.fiscal_year} ({m.period_type.value}, ending {m.period_end_date})"
        periods.add(period_label)
        parts = [f"Period: {period_label}"]
        for label, value in [
            ("Revenue", m.revenue), ("PAT", m.pat), ("EBITDA margin %", m.ebitda_margin),
            ("ROCE %", m.roce), ("ROE %", m.roe), ("Debt/Equity", m.debt_equity),
            ("Receivable days", m.receivable_days), ("Free cash flow", m.free_cash_flow),
        ]:
            if value is not None:
                parts.append(f"{label}={value}")
        lines.append(" | ".join(parts))
    return "\n".join(lines), periods


def _format_shareholding_summary(records: list[models.ShareholdingPattern]) -> str:
    if not records:
        return "No shareholding pattern data on file for this company."
    lines = []
    for r in records[:MAX_METRIC_PERIODS]:
        lines.append(
            f"As of {r.period_end_date}: promoter={r.promoter_holding_pct}%, "
            f"pledge={r.pledge_pct}%, institutions={r.institution_holding_pct}%, "
            f"public={r.public_holding_pct}%"
        )
    return "\n".join(lines)


def _format_price_summary(prices: list[models.PriceHistory]) -> str:
    """
    Gives the model the latest price plus a simple 52-week range as
    factual context for the valuation score — NOT a request to predict
    where the price goes next. This platform is explicitly not a price
    predictor; the instruction in the system prompt reinforces that this
    data is for describing where the stock sits today, not forecasting.
    """
    if not prices:
        return "No price data on file for this company."

    latest = prices[0]  # prices is desc by price_date
    cutoff = latest.price_date - datetime.timedelta(days=365)
    window = [p for p in prices if p.price_date >= cutoff]
    high = max(p.close_price for p in window)
    low = min(p.close_price for p in window)

    return (
        f"Latest close: {latest.close_price} as of {latest.price_date}. "
        f"52-week range (from data on file): low {low}, high {high}."
    )


def build_context(
    company: models.Company,
    financial_metrics: list[models.FinancialMetric],
    shareholding_records: list[models.ShareholdingPattern],
    price_history: list[models.PriceHistory],
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    document_lookup: dict[str, models.Document],
) -> ReportContext:
    financial_summary, periods = _format_financial_summary(financial_metrics)
    shareholding_summary = _format_shareholding_summary(shareholding_records)
    price_summary = _format_price_summary(price_history)

    excerpts: list[Excerpt] = []
    seen_vector_ids: set[str] = set()

    for topic, query_text in TOPIC_QUERIES.items():
        query_embedding = embedding_service.embed_texts([query_text])[0]
        matches = vector_store.query(
            query_embedding=query_embedding,
            n_results=CHUNKS_PER_TOPIC,
            where={"company_id": str(company.id)},
        )
        for match in matches:
            if match.vector_id in seen_vector_ids:
                continue
            seen_vector_ids.add(match.vector_id)

            document_id = match.metadata.get("document_id")
            document = document_lookup.get(document_id)
            if document is None:
                continue

            excerpts.append(
                Excerpt(
                    document_id=document_id,
                    document_filename=document.original_filename,
                    page_number=match.metadata.get("page_number"),
                    text=match.text,
                    topic=topic,
                )
            )

    context = ReportContext(
        company=company,
        financial_summary=financial_summary,
        shareholding_summary=shareholding_summary,
        price_summary=price_summary,
        excerpts=excerpts,
    )
    context._periods = periods
    return context


# ============================================================
# Milestone 9: AI Assistant — question-driven retrieval
# ============================================================
#
# The assistant needs the exact same kind of grounded context as report
# generation (financial/shareholding/price summaries + citeable document
# excerpts), so it reuses ReportContext and the financial/shareholding/
# price formatters unchanged. The only thing that differs is *what* gets
# retrieved from the vector store: one query embedding of the user's own
# question, instead of report generation's five fixed analysis-topic
# queries. This is deliberately a separate function rather than a branch
# inside build_context() — the retrieval strategies are conceptually
# different enough (fixed topics vs. free-text question) that forcing them
# through one function would mean threading a "mode" flag through it.

DEFAULT_ASSISTANT_CHUNKS = 8


def build_assistant_context(
    company: models.Company,
    financial_metrics: list[models.FinancialMetric],
    shareholding_records: list[models.ShareholdingPattern],
    price_history: list[models.PriceHistory],
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
    document_lookup: dict[str, models.Document],
    question: str,
    n_results: int = DEFAULT_ASSISTANT_CHUNKS,
) -> ReportContext:
    financial_summary, periods = _format_financial_summary(financial_metrics)
    shareholding_summary = _format_shareholding_summary(shareholding_records)
    price_summary = _format_price_summary(price_history)

    query_embedding = embedding_service.embed_texts([question])[0]
    matches = vector_store.query(
        query_embedding=query_embedding,
        n_results=n_results,
        where={"company_id": str(company.id)},
    )

    excerpts: list[Excerpt] = []
    for match in matches:
        document_id = match.metadata.get("document_id")
        document = document_lookup.get(document_id)
        if document is None:
            continue
        excerpts.append(
            Excerpt(
                document_id=document_id,
                document_filename=document.original_filename,
                page_number=match.metadata.get("page_number"),
                text=match.text,
                topic="user_question",  # not one of report generation's fixed topics
            )
        )

    context = ReportContext(
        company=company,
        financial_summary=financial_summary,
        shareholding_summary=shareholding_summary,
        price_summary=price_summary,
        excerpts=excerpts,
    )
    context._periods = periods
    return context
