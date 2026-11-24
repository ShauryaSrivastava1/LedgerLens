"""
Builds one comparison row per company: latest-period ratios plus
period-over-period growth (computed from the two most recent rows of the
same period_type, so an ANNUAL comparison isn't accidentally diluted by a
QUARTERLY row in between). Pulls the latest AI report's scores too, if one
exists, so comparison covers both the numbers and the model's read on
moat/governance/valuation in one place — as your spec's "Compare
Companies" feature calls for.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app import crud, models
from sqlalchemy.orm import Session


def _pct_growth(current: Optional[Decimal], previous: Optional[Decimal]) -> Optional[float]:
    if current is None or previous is None or previous == 0:
        return None
    return float((current - previous) / abs(previous) * 100)


def _latest_pair_by_period_type(
    metrics: list[models.FinancialMetric], period_type: models.PeriodType
) -> tuple[Optional[models.FinancialMetric], Optional[models.FinancialMetric]]:
    """metrics is assumed sorted period_end_date desc (as crud.list_financial_metrics returns)."""
    matching = [m for m in metrics if m.period_type == period_type]
    latest = matching[0] if len(matching) >= 1 else None
    previous = matching[1] if len(matching) >= 2 else None
    return latest, previous


@dataclass
class ComparisonRow:
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


def build_comparison_row(db: Session, company: models.Company) -> ComparisonRow:
    metrics = crud.list_financial_metrics(db, company.id)  # desc by period_end_date

    # Prefer ANNUAL for growth comparisons (matches how a retail investor
    # usually thinks about "revenue growth"); fall back to QUARTERLY if a
    # company has no annual data yet.
    latest, previous = _latest_pair_by_period_type(metrics, models.PeriodType.ANNUAL)
    if latest is None:
        latest, previous = _latest_pair_by_period_type(metrics, models.PeriodType.QUARTERLY)

    shareholding = crud.list_shareholding_records(db, company.id)
    latest_shareholding = shareholding[0] if shareholding else None

    reports = crud.list_ai_reports(db, company.id)
    latest_report = reports[0] if reports else None

    return ComparisonRow(
        company_id=str(company.id),
        symbol=company.symbol,
        name=company.name,
        sector=company.sector,
        latest_period_label=(
            f"{latest.fiscal_year} ({latest.period_type.value})" if latest else None
        ),
        revenue=latest.revenue if latest else None,
        revenue_growth_pct=_pct_growth(latest.revenue if latest else None, previous.revenue if previous else None),
        pat=latest.pat if latest else None,
        pat_growth_pct=_pct_growth(latest.pat if latest else None, previous.pat if previous else None),
        roce=latest.roce if latest else None,
        roe=latest.roe if latest else None,
        ebitda_margin=latest.ebitda_margin if latest else None,
        net_margin=latest.net_margin if latest else None,
        debt_equity=latest.debt_equity if latest else None,
        free_cash_flow=latest.free_cash_flow if latest else None,
        promoter_holding_pct=latest_shareholding.promoter_holding_pct if latest_shareholding else None,
        pledge_pct=latest_shareholding.pledge_pct if latest_shareholding else None,
        latest_report_id=str(latest_report.id) if latest_report else None,
        overall_score=latest_report.overall_score if latest_report else None,
        moat_score=latest_report.moat_score if latest_report else None,
        governance_score=latest_report.governance_score if latest_report else None,
        valuation_score=latest_report.valuation_score if latest_report else None,
        risk_score=latest_report.risk_score if latest_report else None,
        report_confidence=latest_report.confidence_score if latest_report else None,
    )
