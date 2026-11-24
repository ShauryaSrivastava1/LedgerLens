import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.services.auth import get_current_user
from app.services.csv_export import generate_portfolio_csv
from app.services.portfolio import build_portfolio_summary

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.post("/holdings", response_model=schemas.HoldingOut, status_code=201)
def add_holding(
    payload: schemas.HoldingCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    company = crud.get_company(db, payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        return crud.create_holding(
            db,
            current_user.id,
            payload.company_id,
            payload.quantity,
            payload.average_buy_price,
            payload.target_allocation_pct,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/holdings", response_model=list[schemas.HoldingOut])
def list_my_holdings(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    return crud.list_holdings(db, current_user.id)


@router.patch("/holdings/{holding_id}", response_model=schemas.HoldingOut)
def update_holding(
    holding_id: uuid.UUID,
    payload: schemas.HoldingUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    holding = crud.get_holding(db, holding_id)
    if not holding or holding.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Holding not found")
    return crud.update_holding(db, holding, payload.model_dump())


@router.delete("/holdings/{holding_id}", status_code=204)
def delete_holding(
    holding_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    holding = crud.get_holding(db, holding_id)
    if not holding or holding.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Holding not found")
    crud.delete_holding(db, holding)
    return None


@router.get("/summary", response_model=schemas.PortfolioSummaryOut)
def get_portfolio_summary(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    summary = build_portfolio_summary(db, current_user.id)
    return schemas.PortfolioSummaryOut(
        total_invested=summary.total_invested,
        total_current_value=summary.total_current_value,
        total_unrealized_pnl=summary.total_unrealized_pnl,
        total_unrealized_pnl_pct=summary.total_unrealized_pnl_pct,
        all_holdings_priced=summary.all_holdings_priced,
        holdings=[schemas.HoldingRowOut(**h.__dict__) for h in summary.holdings],
        sector_allocation=[schemas.SectorAllocationOut(**s.__dict__) for s in summary.sector_allocation],
    )


@router.get("/export.csv")
def export_portfolio_csv(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    summary = build_portfolio_summary(db, current_user.id)
    csv_content = generate_portfolio_csv(summary)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="portfolio.csv"'},
    )
