"""
Generates RiskAlert rows by comparing newly-saved data against the
immediately preceding record for the same company. Called synchronously
right after the triggering save (see routers/financials.py and
routers/ai_reports.py) — deliberately not a scheduled job, so an alert
exists the moment its evidence does, with no polling delay.

Thresholds here are simple and conservative on purpose: this is meant to
surface "something changed, go look" rather than make a judgment call the
investor should be making themselves. A false negative (missing a subtle
shift) is a lesser problem than crying wolf on noise.
"""

from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app import models

PLEDGE_INCREASE_THRESHOLD = Decimal("0.5")  # percentage points
PROMOTER_HOLDING_DROP_THRESHOLD = Decimal("1.0")  # percentage points
GOVERNANCE_SCORE_DROP_THRESHOLD = Decimal("10")  # points, on a 0-100 scale
OVERALL_SCORE_DROP_THRESHOLD = Decimal("10")


def _create_alert(
    db: Session,
    company_id,
    alert_type: models.RiskAlertType,
    severity: models.RiskAlertSeverity,
    message: str,
    evidence: str,
) -> models.RiskAlert:
    alert = models.RiskAlert(
        company_id=company_id,
        alert_type=alert_type,
        severity=severity,
        message=message,
        evidence=evidence,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def check_shareholding_alerts(
    db: Session,
    company: models.Company,
    new_record: models.ShareholdingPattern,
    previous_record: Optional[models.ShareholdingPattern],
) -> list[models.RiskAlert]:
    if previous_record is None:
        return []

    alerts = []

    if new_record.pledge_pct is not None and previous_record.pledge_pct is not None:
        delta = new_record.pledge_pct - previous_record.pledge_pct
        if delta >= PLEDGE_INCREASE_THRESHOLD:
            severity = models.RiskAlertSeverity.HIGH if delta >= 5 else models.RiskAlertSeverity.MEDIUM
            alerts.append(
                _create_alert(
                    db,
                    company.id,
                    models.RiskAlertType.PLEDGE_INCREASE,
                    severity,
                    f"Promoter pledge percentage increased for {company.symbol}.",
                    f"Pledge rose from {previous_record.pledge_pct}% to {new_record.pledge_pct}% "
                    f"(as of {new_record.period_end_date}).",
                )
            )

    if new_record.promoter_holding_pct is not None and previous_record.promoter_holding_pct is not None:
        delta = previous_record.promoter_holding_pct - new_record.promoter_holding_pct
        if delta >= PROMOTER_HOLDING_DROP_THRESHOLD:
            alerts.append(
                _create_alert(
                    db,
                    company.id,
                    models.RiskAlertType.PROMOTER_HOLDING_DECREASE,
                    models.RiskAlertSeverity.MEDIUM,
                    f"Promoter holding decreased for {company.symbol}.",
                    f"Promoter holding fell from {previous_record.promoter_holding_pct}% to "
                    f"{new_record.promoter_holding_pct}% (as of {new_record.period_end_date}).",
                )
            )

    return alerts


def check_report_alerts(
    db: Session,
    company: models.Company,
    new_report: models.AIReport,
    previous_report: Optional[models.AIReport],
) -> list[models.RiskAlert]:
    if previous_report is None:
        return []

    alerts = []

    if new_report.governance_score is not None and previous_report.governance_score is not None:
        delta = previous_report.governance_score - new_report.governance_score
        if delta >= GOVERNANCE_SCORE_DROP_THRESHOLD:
            alerts.append(
                _create_alert(
                    db,
                    company.id,
                    models.RiskAlertType.GOVERNANCE_SCORE_DROP,
                    models.RiskAlertSeverity.HIGH if delta >= 20 else models.RiskAlertSeverity.MEDIUM,
                    f"Governance score dropped for {company.symbol}.",
                    f"Governance score fell from {previous_report.governance_score} to "
                    f"{new_report.governance_score} between AI reports generated "
                    f"{previous_report.generated_at} and {new_report.generated_at}.",
                )
            )

    if new_report.overall_score is not None and previous_report.overall_score is not None:
        delta = previous_report.overall_score - new_report.overall_score
        if delta >= OVERALL_SCORE_DROP_THRESHOLD:
            alerts.append(
                _create_alert(
                    db,
                    company.id,
                    models.RiskAlertType.OVERALL_SCORE_DROP,
                    models.RiskAlertSeverity.MEDIUM,
                    f"Overall score dropped for {company.symbol}.",
                    f"Overall score fell from {previous_report.overall_score} to "
                    f"{new_report.overall_score} between AI reports generated "
                    f"{previous_report.generated_at} and {new_report.generated_at}.",
                )
            )

    return alerts
