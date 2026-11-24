"""
Data access layer. Routers call these functions instead of touching the
ORM/session directly — keeps HTTP concerns (status codes, request parsing)
out of the persistence logic, and makes this layer independently testable.
"""

import uuid
from typing import Optional

from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError

from app import models, schemas


# ---------- Company ----------

def get_company(db: Session, company_id: uuid.UUID) -> Optional[models.Company]:
    return db.query(models.Company).filter(models.Company.id == company_id).first()


def get_company_by_symbol(db: Session, symbol: str) -> Optional[models.Company]:
    return (
        db.query(models.Company)
        .filter(models.Company.symbol == symbol.upper())
        .first()
    )


def get_company_detail(db: Session, company_id: uuid.UUID) -> Optional[models.Company]:
    """Fetch a company with metrics/shareholding eager-loaded, newest first."""
    return (
        db.query(models.Company)
        .options(
            joinedload(models.Company.financial_metrics),
            joinedload(models.Company.shareholding_records),
        )
        .filter(models.Company.id == company_id)
        .first()
    )


def list_companies(
    db: Session, skip: int = 0, limit: int = 50, sector: Optional[str] = None
) -> list[models.Company]:
    query = db.query(models.Company)
    if sector:
        query = query.filter(models.Company.sector == sector)
    return query.order_by(models.Company.symbol).offset(skip).limit(limit).all()


def create_company(db: Session, company: schemas.CompanyCreate) -> models.Company:
    db_company = models.Company(
        symbol=company.symbol.upper(),
        name=company.name,
        sector=company.sector,
        industry=company.industry,
        isin=company.isin,
    )
    db.add(db_company)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Company with symbol '{company.symbol}' already exists")
    db.refresh(db_company)
    return db_company


def update_company(
    db: Session, db_company: models.Company, updates: schemas.CompanyUpdate
) -> models.Company:
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(db_company, field, value)
    db.commit()
    db.refresh(db_company)
    return db_company


def delete_company(db: Session, db_company: models.Company) -> None:
    db.delete(db_company)
    db.commit()


# ---------- Financial Metrics ----------

def add_financial_metric(
    db: Session, company_id: uuid.UUID, metric: schemas.FinancialMetricCreate
) -> models.FinancialMetric:
    db_metric = models.FinancialMetric(company_id=company_id, **metric.model_dump())
    db.add(db_metric)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "A financial metric row already exists for this company, "
            "period_type, and period_end_date"
        )
    db.refresh(db_metric)
    return db_metric


def list_financial_metrics(
    db: Session, company_id: uuid.UUID, period_type: Optional[str] = None
) -> list[models.FinancialMetric]:
    query = db.query(models.FinancialMetric).filter(
        models.FinancialMetric.company_id == company_id
    )
    if period_type:
        query = query.filter(models.FinancialMetric.period_type == period_type)
    return query.order_by(models.FinancialMetric.period_end_date.desc()).all()


# ---------- Shareholding ----------

def add_shareholding_record(
    db: Session, company_id: uuid.UUID, record: schemas.ShareholdingPatternCreate
) -> models.ShareholdingPattern:
    db_record = models.ShareholdingPattern(company_id=company_id, **record.model_dump())
    db.add(db_record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(
            "A shareholding record already exists for this company and period_end_date"
        )
    db.refresh(db_record)
    return db_record


def list_shareholding_records(
    db: Session, company_id: uuid.UUID
) -> list[models.ShareholdingPattern]:
    return (
        db.query(models.ShareholdingPattern)
        .filter(models.ShareholdingPattern.company_id == company_id)
        .order_by(models.ShareholdingPattern.period_end_date.desc())
        .all()
    )


# ============================================================
# Milestone 2: Documents
# ============================================================

def create_document(
    db: Session,
    company_id: uuid.UUID,
    document_type: models.DocumentType,
    original_filename: str,
    storage_path: str,
    period_end_date=None,
) -> models.Document:
    doc = models.Document(
        company_id=company_id,
        document_type=document_type,
        original_filename=original_filename,
        storage_path=storage_path,
        period_end_date=period_end_date,
        status=models.DocumentStatus.PENDING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document(db: Session, document_id: uuid.UUID) -> Optional[models.Document]:
    return db.query(models.Document).filter(models.Document.id == document_id).first()


def list_documents(db: Session, company_id: uuid.UUID) -> list[models.Document]:
    return (
        db.query(models.Document)
        .filter(models.Document.company_id == company_id)
        .order_by(models.Document.uploaded_at.desc())
        .all()
    )


def list_document_chunks(db: Session, document_id: uuid.UUID) -> list[models.DocumentChunk]:
    return (
        db.query(models.DocumentChunk)
        .filter(models.DocumentChunk.document_id == document_id)
        .order_by(models.DocumentChunk.chunk_index)
        .all()
    )


def list_metric_candidates(
    db: Session, document_id: uuid.UUID, status: Optional[str] = None
) -> list[models.ExtractedMetricCandidate]:
    query = db.query(models.ExtractedMetricCandidate).filter(
        models.ExtractedMetricCandidate.document_id == document_id
    )
    if status:
        query = query.filter(models.ExtractedMetricCandidate.status == status)
    return query.order_by(models.ExtractedMetricCandidate.confidence.desc()).all()


def get_metric_candidate(
    db: Session, candidate_id: uuid.UUID
) -> Optional[models.ExtractedMetricCandidate]:
    return (
        db.query(models.ExtractedMetricCandidate)
        .filter(models.ExtractedMetricCandidate.id == candidate_id)
        .first()
    )


def set_metric_candidate_status(
    db: Session, candidate: models.ExtractedMetricCandidate, status: models.MetricCandidateStatus
) -> models.ExtractedMetricCandidate:
    import datetime

    candidate.status = status
    candidate.reviewed_at = datetime.datetime.now(datetime.timezone.utc)
    db.commit()
    db.refresh(candidate)
    return candidate


def promote_metric_candidate(
    db: Session,
    candidate: models.ExtractedMetricCandidate,
    period_type: models.PeriodType,
    period_end_date,
    fiscal_year: str,
) -> models.FinancialMetric:
    """
    Writes an accepted candidate's value into the verified FinancialMetric
    table: updates the matching (company, period_type, period_end_date)
    row if one exists, else creates a new one with just this field set.
    Links the candidate to the resulting row via promoted_financial_metric_id
    so the lineage from "regex guess" to "verified metric" stays traceable.
    """
    existing = (
        db.query(models.FinancialMetric)
        .filter(
            models.FinancialMetric.company_id == candidate.company_id,
            models.FinancialMetric.period_type == period_type,
            models.FinancialMetric.period_end_date == period_end_date,
        )
        .first()
    )

    if existing:
        setattr(existing, candidate.metric_name, candidate.extracted_value)
        metric_row = existing
    else:
        metric_row = models.FinancialMetric(
            company_id=candidate.company_id,
            period_type=period_type,
            period_end_date=period_end_date,
            fiscal_year=fiscal_year,
        )
        setattr(metric_row, candidate.metric_name, candidate.extracted_value)
        db.add(metric_row)

    db.commit()
    db.refresh(metric_row)

    candidate.promoted_financial_metric_id = metric_row.id
    db.commit()
    db.refresh(candidate)

    return metric_row


# ============================================================
# Milestone 3: AI Reports
# ============================================================

def create_ai_report(db: Session, company_id: uuid.UUID, report_data: dict) -> models.AIReport:
    report = models.AIReport(company_id=company_id, **report_data)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def list_ai_reports(db: Session, company_id: uuid.UUID) -> list[models.AIReport]:
    return (
        db.query(models.AIReport)
        .filter(models.AIReport.company_id == company_id)
        .order_by(models.AIReport.generated_at.desc())
        .all()
    )


def get_ai_report(db: Session, report_id: uuid.UUID) -> Optional[models.AIReport]:
    return db.query(models.AIReport).filter(models.AIReport.id == report_id).first()


# ============================================================
# Milestone 5: Users
# ============================================================

def create_user(db: Session, email: str, hashed_password: str, full_name: Optional[str] = None) -> models.User:
    user = models.User(email=email.lower(), hashed_password=hashed_password, full_name=full_name)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"An account with email '{email}' already exists")
    db.refresh(user)
    return user


def get_user(db: Session, user_id: uuid.UUID) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email.lower()).first()


# ============================================================
# Milestone 5: Holdings (portfolio)
# ============================================================

def create_holding(
    db: Session,
    user_id: uuid.UUID,
    company_id: uuid.UUID,
    quantity,
    average_buy_price,
    target_allocation_pct=None,
) -> models.Holding:
    holding = models.Holding(
        user_id=user_id,
        company_id=company_id,
        quantity=quantity,
        average_buy_price=average_buy_price,
        target_allocation_pct=target_allocation_pct,
    )
    db.add(holding)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("A holding for this company already exists — update it instead")
    db.refresh(holding)
    return holding


def list_holdings(db: Session, user_id: uuid.UUID) -> list[models.Holding]:
    return db.query(models.Holding).filter(models.Holding.user_id == user_id).all()


def get_holding(db: Session, holding_id: uuid.UUID) -> Optional[models.Holding]:
    return db.query(models.Holding).filter(models.Holding.id == holding_id).first()


def update_holding(db: Session, holding: models.Holding, updates: dict) -> models.Holding:
    for field, value in updates.items():
        if value is not None:
            setattr(holding, field, value)
    db.commit()
    db.refresh(holding)
    return holding


def delete_holding(db: Session, holding: models.Holding) -> None:
    db.delete(holding)
    db.commit()


# ============================================================
# Milestone 5: Watchlist
# ============================================================

def create_watchlist_item(
    db: Session, user_id: uuid.UUID, company_id: uuid.UUID, note: Optional[str] = None
) -> models.WatchlistItem:
    item = models.WatchlistItem(user_id=user_id, company_id=company_id, note=note)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("This company is already on your watchlist")
    db.refresh(item)
    return item


def list_watchlist(db: Session, user_id: uuid.UUID) -> list[models.WatchlistItem]:
    return (
        db.query(models.WatchlistItem)
        .filter(models.WatchlistItem.user_id == user_id)
        .order_by(models.WatchlistItem.added_at.desc())
        .all()
    )


def get_watchlist_item(db: Session, item_id: uuid.UUID) -> Optional[models.WatchlistItem]:
    return db.query(models.WatchlistItem).filter(models.WatchlistItem.id == item_id).first()


def delete_watchlist_item(db: Session, item: models.WatchlistItem) -> None:
    db.delete(item)
    db.commit()


# ============================================================
# Milestone 5: Risk alerts
# ============================================================

def list_alerts_for_company(db: Session, company_id: uuid.UUID) -> list[models.RiskAlert]:
    return (
        db.query(models.RiskAlert)
        .filter(models.RiskAlert.company_id == company_id)
        .order_by(models.RiskAlert.triggered_at.desc())
        .all()
    )


def list_alerts_for_companies(db: Session, company_ids: list[uuid.UUID]) -> list[models.RiskAlert]:
    if not company_ids:
        return []
    return (
        db.query(models.RiskAlert)
        .filter(models.RiskAlert.company_id.in_(company_ids))
        .order_by(models.RiskAlert.triggered_at.desc())
        .all()
    )


def get_risk_alert(db: Session, alert_id: uuid.UUID) -> Optional[models.RiskAlert]:
    return db.query(models.RiskAlert).filter(models.RiskAlert.id == alert_id).first()


def get_acknowledgment(
    db: Session, user_id: uuid.UUID, alert_id: uuid.UUID
) -> Optional[models.AlertAcknowledgment]:
    return (
        db.query(models.AlertAcknowledgment)
        .filter(
            models.AlertAcknowledgment.user_id == user_id,
            models.AlertAcknowledgment.alert_id == alert_id,
        )
        .first()
    )


def acknowledge_alert(db: Session, user_id: uuid.UUID, alert_id: uuid.UUID) -> models.AlertAcknowledgment:
    existing = get_acknowledgment(db, user_id, alert_id)
    if existing:
        return existing
    ack = models.AlertAcknowledgment(user_id=user_id, alert_id=alert_id)
    db.add(ack)
    db.commit()
    db.refresh(ack)
    return ack


def list_acknowledged_alert_ids(db: Session, user_id: uuid.UUID) -> set:
    rows = (
        db.query(models.AlertAcknowledgment.alert_id)
        .filter(models.AlertAcknowledgment.user_id == user_id)
        .all()
    )
    return {r[0] for r in rows}


# ============================================================
# Milestone 6: Price history
# ============================================================

def add_price(
    db: Session, company_id: uuid.UUID, price_date, close_price, source: Optional[str] = None
) -> models.PriceHistory:
    price = models.PriceHistory(
        company_id=company_id, price_date=price_date, close_price=close_price, source=source
    )
    db.add(price)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError(f"A price for {price_date} already exists for this company")
    db.refresh(price)
    return price


def bulk_add_prices(
    db: Session, company_id: uuid.UUID, rows: list, source: Optional[str] = None
) -> tuple[int, int]:
    """
    Inserts (price_date, close_price) pairs, skipping any date that
    already has a price on file rather than failing the whole batch —
    re-uploading an overlapping export is a normal workflow, not an error.
    Returns (rows_added, rows_skipped_duplicate).
    """
    existing_dates = {
        d for (d,) in db.query(models.PriceHistory.price_date).filter(
            models.PriceHistory.company_id == company_id
        ).all()
    }

    added = 0
    skipped = 0
    for row in rows:
        if row.price_date in existing_dates:
            skipped += 1
            continue
        db.add(
            models.PriceHistory(
                company_id=company_id,
                price_date=row.price_date,
                close_price=row.close_price,
                source=source,
            )
        )
        existing_dates.add(row.price_date)
        added += 1

    db.commit()
    return added, skipped


def list_prices(
    db: Session, company_id: uuid.UUID, start=None, end=None
) -> list[models.PriceHistory]:
    query = db.query(models.PriceHistory).filter(models.PriceHistory.company_id == company_id)
    if start:
        query = query.filter(models.PriceHistory.price_date >= start)
    if end:
        query = query.filter(models.PriceHistory.price_date <= end)
    return query.order_by(models.PriceHistory.price_date.desc()).all()


def get_latest_price(db: Session, company_id: uuid.UUID) -> Optional[models.PriceHistory]:
    return (
        db.query(models.PriceHistory)
        .filter(models.PriceHistory.company_id == company_id)
        .order_by(models.PriceHistory.price_date.desc())
        .first()
    )


def get_latest_prices_for_companies(db: Session, company_ids: list[uuid.UUID]) -> dict:
    """Returns {company_id: PriceHistory} for the latest price of each given company."""
    if not company_ids:
        return {}
    result = {}
    for company_id in company_ids:
        latest = get_latest_price(db, company_id)
        if latest:
            result[company_id] = latest
    return result
