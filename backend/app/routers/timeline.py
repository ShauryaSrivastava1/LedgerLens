import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.services.timeline import build_company_timeline

router = APIRouter(tags=["timeline"])


@router.get("/companies/{company_id}/timeline", response_model=list[schemas.TimelineEventOut])
def get_company_timeline(company_id: uuid.UUID, db: Session = Depends(get_db)):
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return build_company_timeline(db, company_id)
