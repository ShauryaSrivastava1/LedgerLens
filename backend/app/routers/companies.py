import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("", response_model=schemas.CompanyOut, status_code=201)
def create_company(company: schemas.CompanyCreate, db: Session = Depends(get_db)):
    existing = crud.get_company_by_symbol(db, company.symbol)
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Company with symbol '{company.symbol}' already exists"
        )
    try:
        return crud.create_company(db, company)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=list[schemas.CompanyOut])
def list_companies(
    skip: int = 0,
    limit: int = Query(default=50, le=200),
    sector: Optional[str] = None,
    db: Session = Depends(get_db),
):
    return crud.list_companies(db, skip=skip, limit=limit, sector=sector)


@router.get("/{company_id}", response_model=schemas.CompanyDetail)
def get_company(company_id: uuid.UUID, db: Session = Depends(get_db)):
    company = crud.get_company_detail(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


@router.get("/symbol/{symbol}", response_model=schemas.CompanyOut)
def get_company_by_symbol(symbol: str, db: Session = Depends(get_db)):
    company = crud.get_company_by_symbol(db, symbol)
    if not company:
        raise HTTPException(status_code=404, detail=f"No company with symbol '{symbol}'")
    return company


@router.patch("/{company_id}", response_model=schemas.CompanyOut)
def update_company(
    company_id: uuid.UUID, updates: schemas.CompanyUpdate, db: Session = Depends(get_db)
):
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return crud.update_company(db, company, updates)


@router.delete("/{company_id}", status_code=204)
def delete_company(company_id: uuid.UUID, db: Session = Depends(get_db)):
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    crud.delete_company(db, company)
    return None
