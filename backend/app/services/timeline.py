"""
Merges a company's key events — documents uploaded, AI reports generated,
risk alerts triggered — into one chronological timeline. Deliberately
narrow: financial metric additions and shareholding updates aren't
included as events, since they're data points (already visible in their
own trend charts) rather than something that "happened" in a narrative
sense. This is the "what's the story of this company on the platform"
view, not a full audit log.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from sqlalchemy.orm import Session

from app import models


class TimelineEventType(str, Enum):
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    AI_REPORT_GENERATED = "AI_REPORT_GENERATED"
    RISK_ALERT = "RISK_ALERT"


@dataclass
class TimelineEvent:
    event_type: TimelineEventType
    occurred_at: datetime
    title: str
    description: str
    related_id: str


def build_company_timeline(db: Session, company_id) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []

    documents = (
        db.query(models.Document).filter(models.Document.company_id == company_id).all()
    )
    for doc in documents:
        events.append(
            TimelineEvent(
                event_type=TimelineEventType.DOCUMENT_UPLOADED,
                occurred_at=doc.uploaded_at,
                title=f"{doc.document_type.value.replace('_', ' ').title()} uploaded",
                description=doc.original_filename,
                related_id=str(doc.id),
            )
        )

    reports = (
        db.query(models.AIReport).filter(models.AIReport.company_id == company_id).all()
    )
    for report in reports:
        score_text = (
            f"Overall score: {report.overall_score}" if report.overall_score is not None else "Insufficient evidence"
        )
        events.append(
            TimelineEvent(
                event_type=TimelineEventType.AI_REPORT_GENERATED,
                occurred_at=report.generated_at,
                title="AI report generated",
                description=score_text,
                related_id=str(report.id),
            )
        )

    alerts = (
        db.query(models.RiskAlert).filter(models.RiskAlert.company_id == company_id).all()
    )
    for alert in alerts:
        events.append(
            TimelineEvent(
                event_type=TimelineEventType.RISK_ALERT,
                occurred_at=alert.triggered_at,
                title=alert.message,
                description=alert.evidence,
                related_id=str(alert.id),
            )
        )

    events.sort(key=lambda e: e.occurred_at, reverse=True)
    return events
