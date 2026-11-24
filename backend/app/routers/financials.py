import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.services.risk_alerts import check_shareholding_alerts

router = APIRouter(prefix="/companies/{company_id}", tags=["financials"])


def _require_company(db: Session, company_id: uuid.UUID):
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


# ---------- Financial Metrics ----------

@router.post(
    "/financial-metrics", response_model=schemas.FinancialMetricOut, status_code=201
)
def add_financial_metric(
    company_id: uuid.UUID,
    metric: schemas.FinancialMetricCreate,
    db: Session = Depends(get_db),
):
    _require_company(db, company_id)
    try:
        return crud.add_financial_metric(db, company_id, metric)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/financial-metrics", response_model=list[schemas.FinancialMetricOut])
def list_financial_metrics(
    company_id: uuid.UUID,
    period_type: Optional[schemas.PeriodType] = None,
    db: Session = Depends(get_db),
):
    _require_company(db, company_id)
    return crud.list_financial_metrics(db, company_id, period_type)


# ---------- Shareholding ----------

@router.post(
    "/shareholding", response_model=schemas.ShareholdingPatternOut, status_code=201
)
def add_shareholding_record(
    company_id: uuid.UUID,
    record: schemas.ShareholdingPatternCreate,
    db: Session = Depends(get_db),
):
    company = _require_company(db, company_id)

    try:
        new_record = crud.add_shareholding_record(db, company_id, record)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    # Find the record immediately preceding the new one by period_end_date
    # (not just "whatever was latest before this insert"), so backfilling
    # an older record doesn't get compared against a newer one.
    all_records = crud.list_shareholding_records(db, company_id)  # desc by period_end_date
    new_index = next(i for i, r in enumerate(all_records) if r.id == new_record.id)
    previous_record = all_records[new_index + 1] if new_index + 1 < len(all_records) else None

    check_shareholding_alerts(db, company, new_record, previous_record)
    return new_record


@router.get("/shareholding", response_model=list[schemas.ShareholdingPatternOut])
def list_shareholding_records(company_id: uuid.UUID, db: Session = Depends(get_db)):
    _require_company(db, company_id)
    return crud.list_shareholding_records(db, company_id)
