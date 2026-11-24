from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.services.comparison import build_comparison_row

router = APIRouter(prefix="/compare", tags=["compare"])

MAX_COMPARISON_SIZE = 10


@router.get("", response_model=schemas.ComparisonResponse)
def compare_companies(
    symbols: str = Query(..., description="Comma-separated company symbols, e.g. DMART,TRENT"),
    db: Session = Depends(get_db),
):
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    if len(symbol_list) < 2:
        raise HTTPException(status_code=400, detail="Provide at least 2 symbols to compare")
    if len(symbol_list) > MAX_COMPARISON_SIZE:
        raise HTTPException(status_code=400, detail=f"Cannot compare more than {MAX_COMPARISON_SIZE} companies at once")
    if len(set(symbol_list)) != len(symbol_list):
        raise HTTPException(status_code=400, detail="Duplicate symbols in comparison request")

    rows = []
    for symbol in symbol_list:
        company = crud.get_company_by_symbol(db, symbol)
        if not company:
            raise HTTPException(status_code=404, detail=f"No company with symbol '{symbol}'")
        rows.append(build_comparison_row(db, company))

    return schemas.ComparisonResponse(
        symbols=symbol_list,
        rows=[schemas.ComparisonRowOut(**row.__dict__) for row in rows],
    )
