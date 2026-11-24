"""
Pydantic schemas — the API's request/response contracts.

Kept separate from ORM models on purpose: it lets us evolve the DB schema
and the public API independently, and stops internal columns from leaking
into responses by accident.
"""

import uuid
import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict, EmailStr


class PeriodType(str, Enum):
    QUARTERLY = "QUARTERLY"
    ANNUAL = "ANNUAL"


# ---------- Company ----------

class CompanyBase(BaseModel):
    symbol: str = Field(..., max_length=32, examples=["DMART"])
    name: str = Field(..., max_length=255, examples=["Avenue Supermarts Ltd"])
    sector: Optional[str] = None
    industry: Optional[str] = None
    isin: Optional[str] = Field(None, max_length=16)


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    isin: Optional[str] = None


class CompanyOut(CompanyBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime.datetime
    updated_at: datetime.datetime


# ---------- Financial Metrics ----------

class FinancialMetricBase(BaseModel):
    period_type: PeriodType
    period_end_date: datetime.date
    fiscal_year: str = Field(..., max_length=9, examples=["FY2025-26"])

    revenue: Optional[Decimal] = None
    ebitda: Optional[Decimal] = None
    ebitda_margin: Optional[Decimal] = None
    operating_margin: Optional[Decimal] = None
    net_margin: Optional[Decimal] = None
    pat: Optional[Decimal] = None
    eps: Optional[Decimal] = None

    roe: Optional[Decimal] = None
    roce: Optional[Decimal] = None

    debt_equity: Optional[Decimal] = None
    interest_coverage: Optional[Decimal] = None
    current_ratio: Optional[Decimal] = None
    quick_ratio: Optional[Decimal] = None
    working_capital: Optional[Decimal] = None

    operating_cash_flow: Optional[Decimal] = None
    free_cash_flow: Optional[Decimal] = None
    capex: Optional[Decimal] = None

    inventory_days: Optional[Decimal] = None
    receivable_days: Optional[Decimal] = None
    payable_days: Optional[Decimal] = None

    dividend_per_share: Optional[Decimal] = None


class FinancialMetricCreate(FinancialMetricBase):
    pass


class FinancialMetricOut(FinancialMetricBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company_id: uuid.UUID
    created_at: datetime.datetime


# ---------- Shareholding ----------

class ShareholdingPatternBase(BaseModel):
    period_end_date: datetime.date
    promoter_holding_pct: Optional[Decimal] = None
    institution_holding_pct: Optional[Decimal] = None
    fii_holding_pct: Optional[Decimal] = None
    dii_holding_pct: Optional[Decimal] = None
    public_holding_pct: Optional[Decimal] = None
    pledge_pct: Optional[Decimal] = None


class ShareholdingPatternCreate(ShareholdingPatternBase):
    pass


class ShareholdingPatternOut(ShareholdingPatternBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company_id: uuid.UUID
    created_at: datetime.datetime


# ---------- Composite ----------

class CompanyDetail(CompanyOut):
    """Company plus its full metric and shareholding history, most recent first."""
    financial_metrics: list[FinancialMetricOut] = []
    shareholding_records: list[ShareholdingPatternOut] = []


# ============================================================
# Milestone 2: Document ingestion
# ============================================================

class DocumentType(str, Enum):
    ANNUAL_REPORT = "ANNUAL_REPORT"
    QUARTERLY_RESULT = "QUARTERLY_RESULT"
    INVESTOR_PRESENTATION = "INVESTOR_PRESENTATION"
    EARNINGS_CALL_TRANSCRIPT = "EARNINGS_CALL_TRANSCRIPT"
    CORPORATE_ANNOUNCEMENT = "CORPORATE_ANNOUNCEMENT"
    OTHER = "OTHER"


class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company_id: uuid.UUID
    document_type: DocumentType
    original_filename: str
    period_end_date: Optional[datetime.date]
    status: DocumentStatus
    error_message: Optional[str]
    page_count: Optional[int]
    char_count: Optional[int]
    uploaded_at: datetime.datetime
    processed_at: Optional[datetime.datetime]


class DocumentChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    page_number: Optional[int]
    text: str


class MetricCandidateStatus(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class MetricCandidateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    document_id: uuid.UUID
    metric_name: str
    extracted_value: Optional[Decimal]
    unit_note: Optional[str]
    raw_text_snippet: str
    page_number: Optional[int]
    confidence: Decimal
    status: MetricCandidateStatus
    promoted_financial_metric_id: Optional[uuid.UUID] = None
    created_at: datetime.datetime
    reviewed_at: Optional[datetime.datetime]


class SearchResult(BaseModel):
    """One retrieved chunk, with everything needed to cite it."""
    document_id: uuid.UUID
    document_filename: str
    document_type: DocumentType
    page_number: Optional[int]
    text: str
    relevance_score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]


# ============================================================
# Milestone 3: AI report generation
# ============================================================

class FlagSourceType(str, Enum):
    DOCUMENT = "document"
    FINANCIAL_METRIC = "financial_metric"


class FlagOut(BaseModel):
    statement: str
    evidence: str
    source_type: FlagSourceType
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    period: Optional[str] = None
    confidence: float
    citation_verified: bool


class ContextSnapshot(BaseModel):
    document_ids: list[str]
    periods: list[str]
    topics_queried: list[str]


class AIReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company_id: uuid.UUID
    llm_provider: str
    llm_model: str

    overall_score: Optional[Decimal]
    financial_health_score: Optional[Decimal]
    growth_score: Optional[Decimal]
    profitability_score: Optional[Decimal]
    governance_score: Optional[Decimal]
    moat_score: Optional[Decimal]
    valuation_score: Optional[Decimal]
    risk_score: Optional[Decimal]
    confidence_score: Decimal

    summary: str
    green_flags: list[FlagOut]
    red_flags: list[FlagOut]
    questions_investors_should_ask: list[str]
    things_to_verify: list[str]
    potential_risks: list[str]
    context_snapshot: ContextSnapshot

    generated_at: datetime.datetime


class PromoteMetricCandidateRequest(BaseModel):
    """
    What period this candidate's value should be written to in
    FinancialMetric. Not inferred silently from the document, because the
    document's own period (or lack of one) may not match what this
    specific figure describes — e.g. an annual report showing a 5-year
    comparison table contains figures for periods other than the report's
    own. Requiring this explicitly is part of keeping promotion an
    intentional, auditable human decision rather than a guess.
    """
    period_type: PeriodType
    period_end_date: datetime.date
    fiscal_year: str = Field(..., max_length=9)


# ============================================================
# Milestone 4: Company comparison
# ============================================================

class ComparisonRowOut(BaseModel):
    company_id: str
    symbol: str
    name: str
    sector: Optional[str]

    latest_period_label: Optional[str]
    revenue: Optional[Decimal]
    revenue_growth_pct: Optional[float]
    pat: Optional[Decimal]
    pat_growth_pct: Optional[float]
    roce: Optional[Decimal]
    roe: Optional[Decimal]
    ebitda_margin: Optional[Decimal]
    net_margin: Optional[Decimal]
    debt_equity: Optional[Decimal]
    free_cash_flow: Optional[Decimal]

    promoter_holding_pct: Optional[Decimal]
    pledge_pct: Optional[Decimal]

    latest_report_id: Optional[str]
    overall_score: Optional[Decimal]
    moat_score: Optional[Decimal]
    governance_score: Optional[Decimal]
    valuation_score: Optional[Decimal]
    risk_score: Optional[Decimal]
    report_confidence: Optional[Decimal]


class ComparisonResponse(BaseModel):
    symbols: list[str]
    rows: list[ComparisonRowOut]


# ============================================================
# Milestone 5: Auth
# ============================================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: str
    full_name: Optional[str]
    created_at: datetime.datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ============================================================
# Milestone 5: Portfolio (holdings)
# ============================================================

class HoldingCreate(BaseModel):
    company_id: uuid.UUID
    quantity: Decimal = Field(..., gt=0)
    average_buy_price: Decimal = Field(..., gt=0)
    target_allocation_pct: Optional[Decimal] = Field(None, ge=0, le=100)


class HoldingUpdate(BaseModel):
    quantity: Optional[Decimal] = Field(None, gt=0)
    average_buy_price: Optional[Decimal] = Field(None, gt=0)
    target_allocation_pct: Optional[Decimal] = Field(None, ge=0, le=100)


class HoldingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID
    quantity: Decimal
    average_buy_price: Decimal
    target_allocation_pct: Optional[Decimal]
    created_at: datetime.datetime
    updated_at: datetime.datetime


class HoldingRowOut(BaseModel):
    holding_id: str
    company_id: str
    symbol: str
    name: str
    sector: Optional[str]
    quantity: Decimal
    average_buy_price: Decimal
    invested_amount: Decimal
    target_allocation_pct: Optional[Decimal]
    actual_allocation_pct: Optional[Decimal]

    # Mark-to-market fields — all null if no price data has been ingested
    # for this company (see PriceHistory). Never backfilled from cost
    # basis; a null here means "unknown," not "zero."
    current_price: Optional[Decimal] = None
    price_as_of: Optional[datetime.date] = None
    price_staleness_days: Optional[int] = None
    current_value: Optional[Decimal] = None
    unrealized_pnl: Optional[Decimal] = None
    unrealized_pnl_pct: Optional[float] = None
    down_significantly_from_buy: bool = False  # unrealized_pnl_pct <= -15%


class SectorAllocationOut(BaseModel):
    sector: str
    invested_amount: Decimal
    actual_allocation_pct: Decimal


class PortfolioSummaryOut(BaseModel):
    total_invested: Decimal
    total_current_value: Optional[Decimal] = None
    total_unrealized_pnl: Optional[Decimal] = None
    total_unrealized_pnl_pct: Optional[float] = None
    all_holdings_priced: bool = False

    holdings: list[HoldingRowOut]
    sector_allocation: list[SectorAllocationOut]
    note: str = (
        "Allocation figures are based on invested cost (quantity x average buy price). "
        "See total_current_value/current_value fields for mark-to-market figures, which "
        "are only as current as the last price ingested for each company (no live feed)."
    )
    price_data_note: str = (
        "current_value/unrealized_pnl fields use the most recently ingested price for each "
        "company, which may be stale — check each holding's price_as_of and "
        "price_staleness_days rather than assuming it's today's price."
    )


# ============================================================
# Milestone 5: Watchlist
# ============================================================

class WatchlistItemCreate(BaseModel):
    company_id: uuid.UUID
    note: Optional[str] = Field(None, max_length=512)


class WatchlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    user_id: uuid.UUID
    company_id: uuid.UUID
    note: Optional[str]
    added_at: datetime.datetime


# ============================================================
# Milestone 5: Risk alerts
# ============================================================

class RiskAlertType(str, Enum):
    PLEDGE_INCREASE = "PLEDGE_INCREASE"
    PROMOTER_HOLDING_DECREASE = "PROMOTER_HOLDING_DECREASE"
    GOVERNANCE_SCORE_DROP = "GOVERNANCE_SCORE_DROP"
    OVERALL_SCORE_DROP = "OVERALL_SCORE_DROP"


class RiskAlertSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskAlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company_id: uuid.UUID
    alert_type: RiskAlertType
    severity: RiskAlertSeverity
    message: str
    evidence: str
    triggered_at: datetime.datetime
    acknowledged: bool = False


# ============================================================
# Milestone 6: Historical price data + true portfolio valuation
# ============================================================

class PriceHistoryCreate(BaseModel):
    price_date: datetime.date
    close_price: Decimal = Field(..., gt=0)


class PriceHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    company_id: uuid.UUID
    price_date: datetime.date
    close_price: Decimal
    source: Optional[str]
    created_at: datetime.datetime


class PriceBulkUploadResult(BaseModel):
    rows_added: int
    rows_skipped_duplicate: int
    rows_with_errors: int
    errors: list[str]  # capped list of human-readable parse errors, see routers/prices.py


# ============================================================
# Milestone 9: AI Assistant
# ============================================================

class AssistantAskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        examples=["Why is promoter pledging a concern for this company?"],
    )


class AssistantCitationOut(BaseModel):
    source_type: FlagSourceType
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    period: Optional[str] = None
    reference: str
    confidence: float
    citation_verified: bool


class AssistantContextSnapshot(BaseModel):
    document_ids: list[str]
    periods: list[str]
    chunks_retrieved: int


class AssistantAnswerOut(BaseModel):
    company_id: uuid.UUID
    question: str
    answer: str
    citations: list[AssistantCitationOut]
    confidence: float
    insufficient_evidence: bool
    context_snapshot: AssistantContextSnapshot


# ============================================================
# Milestone 7: Company timeline
# ============================================================

class TimelineEventType(str, Enum):
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    AI_REPORT_GENERATED = "AI_REPORT_GENERATED"
    RISK_ALERT = "RISK_ALERT"


class TimelineEventOut(BaseModel):
    event_type: TimelineEventType
    occurred_at: datetime.datetime
    title: str
    description: str
    related_id: str
