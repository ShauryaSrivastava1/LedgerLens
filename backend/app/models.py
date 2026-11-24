"""
ORM models for Milestone 1.

Scope of this milestone: company master data, per-period financial metrics,
and shareholding pattern. Document ingestion, embeddings, and AI-generated
scores are intentionally deferred to Milestone 2+ so this schema can be
reviewed and stabilized first — later milestones will add tables (documents,
ai_reports, moat_scores, red_flags, etc.) as foreign-keyed extensions rather
than reshaping this core.
"""

import enum
import uuid

from sqlalchemy import (
    Column,
    String,
    Numeric,
    Integer,
    Date,
    DateTime,
    ForeignKey,
    Enum,
    JSON,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class PeriodType(str, enum.Enum):
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # NSE/BSE symbol, e.g. "TCS", "DMART"
    symbol = Column(String(32), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    sector = Column(String(128), nullable=True)
    industry = Column(String(128), nullable=True)
    isin = Column(String(16), unique=True, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    financial_metrics = relationship(
        "FinancialMetric", back_populates="company", cascade="all, delete-orphan"
    )
    shareholding_records = relationship(
        "ShareholdingPattern", back_populates="company", cascade="all, delete-orphan"
    )
    documents = relationship(
        "Document", back_populates="company", cascade="all, delete-orphan"
    )
    ai_reports = relationship(
        "AIReport", back_populates="company", cascade="all, delete-orphan"
    )
    risk_alerts = relationship(
        "RiskAlert", back_populates="company", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Company {self.symbol}>"


class FinancialMetric(Base):
    """
    One row = one company's full metric set for one reporting period
    (a quarter or a full year). Storing metrics wide (one row per period)
    rather than fully normalized (one row per metric) keeps trend queries
    ("show ROCE over 12 quarters") a single indexed range scan instead of
    a pivot, which matters once the AI report generator is querying this
    table on every request.
    """

    __tablename__ = "financial_metrics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )

    period_type = Column(Enum(PeriodType), nullable=False)
    period_end_date = Column(Date, nullable=False)  # e.g. 2026-03-31
    fiscal_year = Column(String(9), nullable=False)  # e.g. "FY2025-26"

    # --- P&L ---
    revenue = Column(Numeric(20, 2), nullable=True)
    ebitda = Column(Numeric(20, 2), nullable=True)
    ebitda_margin = Column(Numeric(6, 3), nullable=True)  # percentage
    operating_margin = Column(Numeric(6, 3), nullable=True)
    net_margin = Column(Numeric(6, 3), nullable=True)
    pat = Column(Numeric(20, 2), nullable=True)
    eps = Column(Numeric(10, 2), nullable=True)

    # --- Returns ---
    roe = Column(Numeric(6, 3), nullable=True)
    roce = Column(Numeric(6, 3), nullable=True)

    # --- Balance sheet / leverage ---
    debt_equity = Column(Numeric(6, 3), nullable=True)
    interest_coverage = Column(Numeric(8, 3), nullable=True)
    current_ratio = Column(Numeric(6, 3), nullable=True)
    quick_ratio = Column(Numeric(6, 3), nullable=True)
    working_capital = Column(Numeric(20, 2), nullable=True)

    # --- Cash flow ---
    operating_cash_flow = Column(Numeric(20, 2), nullable=True)
    free_cash_flow = Column(Numeric(20, 2), nullable=True)
    capex = Column(Numeric(20, 2), nullable=True)

    # --- Working capital efficiency ---
    inventory_days = Column(Numeric(8, 2), nullable=True)
    receivable_days = Column(Numeric(8, 2), nullable=True)
    payable_days = Column(Numeric(8, 2), nullable=True)

    # --- Shareholder returns ---
    dividend_per_share = Column(Numeric(10, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="financial_metrics")

    __table_args__ = (
        # A company can't have two rows for the same period type + end date.
        UniqueConstraint(
            "company_id", "period_type", "period_end_date", name="uq_company_period"
        ),
    )


class ShareholdingPattern(Base):
    """
    Quarterly shareholding disclosure. Tracked separately from
    FinancialMetric because it's sourced from a different filing
    (shareholding pattern disclosure vs. financial results) and updates
    on a different cadence in practice.
    """

    __tablename__ = "shareholding_patterns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )

    period_end_date = Column(Date, nullable=False)

    promoter_holding_pct = Column(Numeric(6, 3), nullable=True)
    institution_holding_pct = Column(Numeric(6, 3), nullable=True)
    fii_holding_pct = Column(Numeric(6, 3), nullable=True)
    dii_holding_pct = Column(Numeric(6, 3), nullable=True)
    public_holding_pct = Column(Numeric(6, 3), nullable=True)
    pledge_pct = Column(Numeric(6, 3), nullable=True)  # % of promoter shares pledged

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="shareholding_records")

    __table_args__ = (
        UniqueConstraint("company_id", "period_end_date", name="uq_company_shareholding_period"),
    )


# ============================================================
# Milestone 2: Document ingestion
# ============================================================

class DocumentType(str, enum.Enum):
    ANNUAL_REPORT = "ANNUAL_REPORT"
    QUARTERLY_RESULT = "QUARTERLY_RESULT"
    INVESTOR_PRESENTATION = "INVESTOR_PRESENTATION"
    EARNINGS_CALL_TRANSCRIPT = "EARNINGS_CALL_TRANSCRIPT"
    CORPORATE_ANNOUNCEMENT = "CORPORATE_ANNOUNCEMENT"
    OTHER = "OTHER"


class DocumentStatus(str, enum.Enum):
    PENDING = "PENDING"        # uploaded, not yet processed
    PROCESSING = "PROCESSING"  # extraction/embedding in progress
    PROCESSED = "PROCESSED"    # done successfully
    FAILED = "FAILED"          # processing raised an error; see error_message


class Document(Base):
    """
    A single uploaded source file (annual report, transcript, etc.) and the
    status of its processing pipeline. The file itself lives on disk (or
    object storage in production) — this row tracks metadata + lifecycle.
    """

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )

    document_type = Column(Enum(DocumentType), nullable=False)
    original_filename = Column(String(512), nullable=False)
    storage_path = Column(String(1024), nullable=False)

    # Optional: which reporting period this document covers. Nullable
    # because some documents (e.g. a corporate announcement) don't map to
    # one specific period.
    period_end_date = Column(Date, nullable=True)

    status = Column(Enum(DocumentStatus), nullable=False, default=DocumentStatus.PENDING)
    error_message = Column(String(2048), nullable=True)

    page_count = Column(Integer, nullable=True)
    char_count = Column(Integer, nullable=True)

    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    company = relationship("Company", back_populates="documents")
    chunks = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
    metric_candidates = relationship(
        "ExtractedMetricCandidate", back_populates="document", cascade="all, delete-orphan"
    )


class DocumentChunk(Base):
    """
    One chunk of extracted text from a Document, with enough metadata
    (page number, char offsets) to cite back to the source when the AI
    layer quotes it. The embedding vector itself lives in ChromaDB —
    `vector_id` is the join key between the two stores. Keeping chunk
    text in Postgres too (not only in Chroma) means we can render
    citations and audit extraction quality without a round trip to the
    vector DB.
    """

    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    company_id = Column(UUID(as_uuid=True), nullable=False)  # denormalized for query filtering

    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    text = Column(String, nullable=False)
    vector_id = Column(String(64), nullable=False)  # id of the matching vector in ChromaDB

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )


class MetricCandidateStatus(str, enum.Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class ExtractedMetricCandidate(Base):
    """
    A financial figure the extraction pipeline *thinks* it found in a
    document, held for human review before it's allowed anywhere near the
    FinancialMetric table. This exists specifically to honor "no
    hallucinations" / "no black-box decisions": a regex or LLM guessing a
    number from unstructured text is not the same as a verified metric,
    and the two must never be conflated. Accepting a candidate is a
    separate, explicit, auditable action (see MetricCandidateStatus).
    """

    __tablename__ = "extracted_metric_candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    company_id = Column(UUID(as_uuid=True), nullable=False)

    # Matches a FinancialMetric column name where possible (e.g. "revenue",
    # "roce") so an accepted candidate can be mapped straight across.
    metric_name = Column(String(64), nullable=False)
    extracted_value = Column(Numeric(20, 4), nullable=True)
    unit_note = Column(String(64), nullable=True)  # e.g. "₹ crore", "%", as stated in source
    raw_text_snippet = Column(String(512), nullable=False)  # evidence — required, never blank
    page_number = Column(Integer, nullable=True)
    confidence = Column(Numeric(4, 3), nullable=False)  # 0.000 - 1.000, heuristic

    status = Column(
        Enum(MetricCandidateStatus), nullable=False, default=MetricCandidateStatus.PENDING_REVIEW
    )
    # Set when a human promotes this candidate into a verified FinancialMetric
    # row (Milestone 3). Non-null == this candidate's value is now live in
    # the trusted table; kept as an explicit lineage link for audit purposes.
    promoted_financial_metric_id = Column(
        UUID(as_uuid=True), ForeignKey("financial_metrics.id", ondelete="SET NULL"), nullable=True
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    document = relationship("Document", back_populates="metric_candidates")


# ============================================================
# Milestone 3: AI report generation
# ============================================================

class AIReport(Base):
    """
    One generated analysis run for a company. Stores the LLM's scores and
    flagged items, PLUS `context_snapshot` — exactly which document IDs,
    pages, and financial periods were fed to the model for this run. That
    snapshot is what makes a report reproducible/auditable: given the same
    context snapshot and the same model, the analysis can be re-run and
    checked, rather than trusting a black-box score with no paper trail.
    """

    __tablename__ = "ai_reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )

    llm_provider = Column(String(32), nullable=False)
    llm_model = Column(String(128), nullable=False)

    overall_score = Column(Numeric(5, 2), nullable=True)
    financial_health_score = Column(Numeric(5, 2), nullable=True)
    growth_score = Column(Numeric(5, 2), nullable=True)
    profitability_score = Column(Numeric(5, 2), nullable=True)
    governance_score = Column(Numeric(5, 2), nullable=True)
    moat_score = Column(Numeric(5, 2), nullable=True)
    valuation_score = Column(Numeric(5, 2), nullable=True)
    risk_score = Column(Numeric(5, 2), nullable=True)
    confidence_score = Column(Numeric(4, 3), nullable=False)

    summary = Column(String(2048), nullable=False)

    # Lists of {statement, evidence, source_type, document_id, page_number,
    # period, confidence, citation_verified} — see report_schema.py
    green_flags = Column(JSON, nullable=False, default=list)
    red_flags = Column(JSON, nullable=False, default=list)
    questions_investors_should_ask = Column(JSON, nullable=False, default=list)
    things_to_verify = Column(JSON, nullable=False, default=list)
    potential_risks = Column(JSON, nullable=False, default=list)

    # {"document_ids": [...], "periods": [...], "topics_queried": [...]}
    context_snapshot = Column(JSON, nullable=False, default=dict)

    generated_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="ai_reports")


# ============================================================
# Milestone 5: Auth, portfolio, watchlist, risk alerts
# ============================================================

class User(Base):
    """
    Portfolio and watchlist data is personal in a way company research
    isn't — this is the first milestone that needs to know who's asking.
    Company/document/report endpoints stay open; only the endpoints added
    in this milestone require a logged-in user (see routers/portfolio.py,
    watchlist.py, alerts.py).
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    holdings = relationship("Holding", back_populates="user", cascade="all, delete-orphan")
    watchlist_items = relationship(
        "WatchlistItem", back_populates="user", cascade="all, delete-orphan"
    )
    alert_acknowledgments = relationship(
        "AlertAcknowledgment", back_populates="user", cascade="all, delete-orphan"
    )


class Holding(Base):
    """
    One position in a user's portfolio. Tracks cost basis (quantity +
    average buy price) and an optional target allocation, NOT current
    market value — this platform has no live price feed (that's the
    "Historical Price Data" source from the original spec, not yet
    ingested), so "current allocation" here is computed from invested
    cost, not mark-to-market value. Flagged explicitly in the API rather
    than presented as something it isn't.
    """

    __tablename__ = "holdings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    quantity = Column(Numeric(18, 4), nullable=False)
    average_buy_price = Column(Numeric(14, 4), nullable=False)
    target_allocation_pct = Column(Numeric(5, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="holdings")
    company = relationship("Company")

    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company_holding"),
    )


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    note = Column(String(512), nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="watchlist_items")
    company = relationship("Company")

    __table_args__ = (
        UniqueConstraint("user_id", "company_id", name="uq_user_company_watchlist"),
    )


class RiskAlertType(str, enum.Enum):
    PLEDGE_INCREASE = "PLEDGE_INCREASE"
    PROMOTER_HOLDING_DECREASE = "PROMOTER_HOLDING_DECREASE"
    GOVERNANCE_SCORE_DROP = "GOVERNANCE_SCORE_DROP"
    OVERALL_SCORE_DROP = "OVERALL_SCORE_DROP"


class RiskAlertSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskAlert(Base):
    """
    Company-scoped, not user-scoped — an alert reflects something that
    changed in a company's data, independent of who happens to be
    tracking it. Generated automatically right after the data that
    triggers it is saved (see services/risk_alerts.py, called from the
    shareholding and AI-report endpoints) rather than on a polling
    schedule, so alerts appear the moment the underlying evidence exists.
    """

    __tablename__ = "risk_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    alert_type = Column(Enum(RiskAlertType), nullable=False)
    severity = Column(Enum(RiskAlertSeverity), nullable=False)
    message = Column(String(512), nullable=False)
    evidence = Column(String(512), nullable=False)  # e.g. "Pledge rose from 2.1% to 5.4%"

    triggered_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="risk_alerts")


class AlertAcknowledgment(Base):
    """
    Per-user acknowledgment of a RiskAlert. Kept separate from RiskAlert
    itself so two users tracking the same company can independently mark
    an alert as seen without affecting each other's view.
    """

    __tablename__ = "alert_acknowledgments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("risk_alerts.id", ondelete="CASCADE"), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="alert_acknowledgments")

    __table_args__ = (
        UniqueConstraint("user_id", "alert_id", name="uq_user_alert_ack"),
    )


# ============================================================
# Milestone 6: Historical price data + true portfolio valuation
# ============================================================

class PriceHistory(Base):
    """
    Daily close price for a company. This platform has no live market
    data connection — no external price API is reachable from here, by
    design of what this environment can access — so prices only exist
    for a company once someone ingests them (single point or CSV bulk
    upload; see routers/prices.py). Portfolio valuation and AI-report
    valuation context are only ever as current as the last ingested
    price, and every place that uses this data says so explicitly
    (see PortfolioSummaryOut.price_data_note and HoldingRowOut's
    price_as_of/price_staleness_days) rather than presenting a stale
    number as if it were live.
    """

    __tablename__ = "price_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)

    price_date = Column(Date, nullable=False)
    close_price = Column(Numeric(14, 4), nullable=False)
    source = Column(String(64), nullable=True)  # e.g. "manual_upload", "csv:nse_history_2025.csv"

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company")

    __table_args__ = (
        UniqueConstraint("company_id", "price_date", name="uq_company_price_date"),
    )
