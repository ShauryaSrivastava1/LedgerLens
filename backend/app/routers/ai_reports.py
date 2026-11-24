import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.llm.base import LLMClient
from app.services.llm.factory import get_llm_client
from app.services.pdf_export import generate_ai_report_pdf
from app.services.report_generator import generate_report
from app.services.risk_alerts import check_report_alerts
from app.services.vector_store import VectorStore, get_persistent_vector_store

router = APIRouter(prefix="/companies/{company_id}/ai-reports", tags=["ai-reports"])


@router.post("", response_model=schemas.AIReportOut, status_code=201)
def create_report(
    company_id: uuid.UUID,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStore = Depends(get_persistent_vector_store),
    llm_client: LLMClient = Depends(get_llm_client),
):
    """
    Generates a new AI report synchronously and stores it. Runs in the
    request/response cycle (not a background task) since it's a single
    on-demand LLM call, not a multi-document batch job — the tradeoff is
    the caller waits for the LLM round trip.
    """
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    previous_reports = crud.list_ai_reports(db, company_id)  # desc by generated_at
    previous_report = previous_reports[0] if previous_reports else None

    try:
        report_data = generate_report(db, company_id, embedding_service, vector_store, llm_client)
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    new_report = crud.create_ai_report(db, company_id, report_data)
    check_report_alerts(db, company, new_report, previous_report)
    return new_report


@router.get("", response_model=list[schemas.AIReportOut])
def list_reports(company_id: uuid.UUID, db: Session = Depends(get_db)):
    """Historical scores for this company, most recent first — the data
    behind the "Historical Score" / "Company Timeline" features."""
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return crud.list_ai_reports(db, company_id)


@router.get("/{report_id}", response_model=schemas.AIReportOut)
def get_report(company_id: uuid.UUID, report_id: uuid.UUID, db: Session = Depends(get_db)):
    report = crud.get_ai_report(db, report_id)
    if not report or report.company_id != company_id:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/{report_id}/pdf")
def download_report_pdf(company_id: uuid.UUID, report_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Renders the same data as GET /{report_id} into a downloadable PDF —
    for saving or sharing outside the platform. No auth required, same
    as the JSON version, since company research (including its AI
    reports) is public on this platform.
    """
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    report = crud.get_ai_report(db, report_id)
    if not report or report.company_id != company_id:
        raise HTTPException(status_code=404, detail="Report not found")

    pdf_bytes = generate_ai_report_pdf(report, company)
    filename = f"{company.symbol}-ai-report-{report.generated_at:%Y-%m-%d}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
