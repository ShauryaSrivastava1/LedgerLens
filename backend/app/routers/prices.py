import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.services.price_ingestion import parse_price_csv

router = APIRouter(prefix="/companies/{company_id}/prices", tags=["prices"])

MAX_ERRORS_RETURNED = 20


def _require_company(db: Session, company_id: uuid.UUID):
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.post("", response_model=schemas.PriceHistoryOut, status_code=201)
def add_price(
    company_id: uuid.UUID,
    payload: schemas.PriceHistoryCreate,
    db: Session = Depends(get_db),
):
    _require_company(db, company_id)
    try:
        return crud.add_price(
            db, company_id, payload.price_date, payload.close_price, source="manual_entry"
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/bulk", response_model=schemas.PriceBulkUploadResult, status_code=201)
async def bulk_upload_prices(
    company_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Accepts a CSV with a date column and a close-price column (flexible
    naming — see services/price_ingestion.py). Rows with an already-priced
    date are skipped, not treated as an error, since re-uploading an
    overlapping export is a normal workflow.
    """
    _require_company(db, company_id)

    content = await file.read()
    parse_result = parse_price_csv(content)

    added, skipped = crud.bulk_add_prices(
        db, company_id, parse_result.rows, source=f"csv:{file.filename}"
    )

    return schemas.PriceBulkUploadResult(
        rows_added=added,
        rows_skipped_duplicate=skipped,
        rows_with_errors=len(parse_result.errors),
        errors=parse_result.errors[:MAX_ERRORS_RETURNED],
    )


@router.get("", response_model=list[schemas.PriceHistoryOut])
def list_prices(
    company_id: uuid.UUID,
    start: Optional[str] = Query(None, description="YYYY-MM-DD"),
    end: Optional[str] = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    _require_company(db, company_id)
    return crud.list_prices(db, company_id, start=start, end=end)


@router.get("/latest", response_model=schemas.PriceHistoryOut)
def get_latest_price(company_id: uuid.UUID, db: Session = Depends(get_db)):
    _require_company(db, company_id)
    price = crud.get_latest_price(db, company_id)
    if not price:
        raise HTTPException(status_code=404, detail="No price data on file for this company")
    return price
