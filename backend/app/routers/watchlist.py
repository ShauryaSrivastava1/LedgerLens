import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.services.auth import get_current_user
from app.services.csv_export import generate_watchlist_csv

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.post("", response_model=schemas.WatchlistItemOut, status_code=201)
def add_to_watchlist(
    payload: schemas.WatchlistItemCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    company = crud.get_company(db, payload.company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        return crud.create_watchlist_item(db, current_user.id, payload.company_id, payload.note)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("", response_model=list[schemas.WatchlistItemOut])
def list_my_watchlist(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    return crud.list_watchlist(db, current_user.id)


@router.delete("/{item_id}", status_code=204)
def remove_from_watchlist(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    item = crud.get_watchlist_item(db, item_id)
    if not item or item.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Watchlist item not found")
    crud.delete_watchlist_item(db, item)
    return None


@router.get("/export.csv")
def export_watchlist_csv(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    items = crud.list_watchlist(db, current_user.id)
    companies = {c.id: c for c in (crud.get_company(db, i.company_id) for i in items) if c}
    csv_content = generate_watchlist_csv(items, companies)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="watchlist.csv"'},
    )
