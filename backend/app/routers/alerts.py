import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.services.auth import get_current_user

router = APIRouter(tags=["risk-alerts"])


@router.get("/companies/{company_id}/risk-alerts", response_model=list[schemas.RiskAlertOut])
def list_company_alerts(company_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Public — a company's alert history is part of its research record,
    same as its documents or financial metrics. No acknowledgment state
    here since that's per-user; see /me/alerts for the authenticated,
    ack-aware view.
    """
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return crud.list_alerts_for_company(db, company_id)


@router.get("/me/alerts", response_model=list[schemas.RiskAlertOut])
def list_my_alerts(
    db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Alerts for every company in the current user's portfolio or watchlist, annotated
    with whether *this user* has acknowledged each one."""
    holding_company_ids = {h.company_id for h in crud.list_holdings(db, current_user.id)}
    watchlist_company_ids = {w.company_id for w in crud.list_watchlist(db, current_user.id)}
    company_ids = list(holding_company_ids | watchlist_company_ids)

    alerts = crud.list_alerts_for_companies(db, company_ids)
    acknowledged_ids = crud.list_acknowledged_alert_ids(db, current_user.id)

    results = []
    for alert in alerts:
        out = schemas.RiskAlertOut.model_validate(alert)
        out.acknowledged = alert.id in acknowledged_ids
        results.append(out)
    return results


@router.post("/alerts/{alert_id}/acknowledge", status_code=204)
def acknowledge_alert(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    alert = crud.get_risk_alert(db, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    crud.acknowledge_alert(db, current_user.id, alert_id)
    return None
