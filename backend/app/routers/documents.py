import datetime
import uuid
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.database import get_db
from app.services import storage
from app.services.document_processor import DocumentProcessor
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.vector_store import VectorStore, get_persistent_vector_store

router = APIRouter(prefix="/companies/{company_id}/documents", tags=["documents"])


def _require_company(db: Session, company_id: uuid.UUID) -> models.Company:
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company


def _run_processing_job(
    document_id: uuid.UUID,
    db: Session,
    embedding_service: EmbeddingService,
    vector_store: VectorStore,
) -> None:
    import logging

    logger = logging.getLogger(__name__)

    logger.info("STARTING document processing: %s", document_id)

    try:
        processor = DocumentProcessor(
            db=db,
            vector_store=vector_store,
            embedding_service=embedding_service,
        )

        processor.process(document_id)

        logger.info("FINISHED document processing: %s", document_id)

    except Exception:
        logger.exception(
            "DOCUMENT PROCESSING FAILED: %s",
            document_id,
        )
        raise

@router.post("", response_model=schemas.DocumentOut, status_code=201)
async def upload_document(
    company_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: schemas.DocumentType = Form(...),
    period_end_date: Optional[datetime.date] = Form(None),
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStore = Depends(get_persistent_vector_store),
):
    _require_company(db, company_id)

    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=415, detail="Only PDF files are supported in this milestone")

    document_id = uuid.uuid4()
    content = await file.read()
    storage_path = storage.save_upload(company_id, document_id, file.filename, content)

    document = models.Document(
        id=document_id,
        company_id=company_id,
        document_type=models.DocumentType(document_type.value),
        original_filename=file.filename,
        storage_path=storage_path,
        period_end_date=period_end_date,
        status=models.DocumentStatus.PENDING,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    background_tasks.add_task(_run_processing_job, document.id, db, embedding_service, vector_store)

    return document


@router.get("", response_model=list[schemas.DocumentOut])
def list_documents(company_id: uuid.UUID, db: Session = Depends(get_db)):
    _require_company(db, company_id)
    return crud.list_documents(db, company_id)


@router.get("/{document_id}", response_model=schemas.DocumentOut)
def get_document(company_id: uuid.UUID, document_id: uuid.UUID, db: Session = Depends(get_db)):
    _require_company(db, company_id)
    document = crud.get_document(db, document_id)
    if not document or document.company_id != company_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.get("/{document_id}/chunks", response_model=list[schemas.DocumentChunkOut])
def list_chunks(company_id: uuid.UUID, document_id: uuid.UUID, db: Session = Depends(get_db)):
    _require_company(db, company_id)
    document = crud.get_document(db, document_id)
    if not document or document.company_id != company_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return crud.list_document_chunks(db, document_id)


@router.get(
    "/{document_id}/metric-candidates", response_model=list[schemas.MetricCandidateOut]
)
def list_metric_candidates(
    company_id: uuid.UUID,
    document_id: uuid.UUID,
    status: Optional[schemas.MetricCandidateStatus] = None,
    db: Session = Depends(get_db),
):
    _require_company(db, company_id)
    document = crud.get_document(db, document_id)
    if not document or document.company_id != company_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return crud.list_metric_candidates(db, document_id, status.value if status else None)


@router.post(
    "/{document_id}/metric-candidates/{candidate_id}/accept",
    response_model=schemas.MetricCandidateOut,
)
def accept_metric_candidate(
    company_id: uuid.UUID,
    document_id: uuid.UUID,
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Marks a candidate ACCEPTED. This does NOT write into FinancialMetric —
    that's a deliberate separation (see ExtractedMetricCandidate docstring
    in models.py). Promoting accepted candidates into FinancialMetric via
    the Milestone 1 endpoint is a manual step for now; automating that
    with a confirmation step is a candidate for a later milestone.
    """
    candidate = crud.get_metric_candidate(db, candidate_id)
    if not candidate or candidate.document_id != document_id or candidate.company_id != company_id:
        raise HTTPException(status_code=404, detail="Metric candidate not found")
    return crud.set_metric_candidate_status(db, candidate, models.MetricCandidateStatus.ACCEPTED)


@router.post(
    "/{document_id}/metric-candidates/{candidate_id}/reject",
    response_model=schemas.MetricCandidateOut,
)
def reject_metric_candidate(
    company_id: uuid.UUID,
    document_id: uuid.UUID,
    candidate_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    candidate = crud.get_metric_candidate(db, candidate_id)
    if not candidate or candidate.document_id != document_id or candidate.company_id != company_id:
        raise HTTPException(status_code=404, detail="Metric candidate not found")
    return crud.set_metric_candidate_status(db, candidate, models.MetricCandidateStatus.REJECTED)


@router.post(
    "/{document_id}/metric-candidates/{candidate_id}/promote",
    response_model=schemas.FinancialMetricOut,
)
def promote_metric_candidate(
    company_id: uuid.UUID,
    document_id: uuid.UUID,
    candidate_id: uuid.UUID,
    request: schemas.PromoteMetricCandidateRequest,
    db: Session = Depends(get_db),
):
    """
    Writes an accepted candidate's value into the verified FinancialMetric
    table (Milestone 1 schema). Requires the candidate to already be
    ACCEPTED — promotion is a second, deliberate step after review, not a
    side effect of acceptance.
    """
    candidate = crud.get_metric_candidate(db, candidate_id)
    if not candidate or candidate.document_id != document_id or candidate.company_id != company_id:
        raise HTTPException(status_code=404, detail="Metric candidate not found")

    if candidate.status != models.MetricCandidateStatus.ACCEPTED:
        raise HTTPException(
            status_code=409,
            detail="Candidate must be ACCEPTED before it can be promoted to a financial metric",
        )
    if candidate.promoted_financial_metric_id is not None:
        raise HTTPException(status_code=409, detail="Candidate has already been promoted")

    return crud.promote_metric_candidate(
        db,
        candidate,
        period_type=models.PeriodType(request.period_type.value),
        period_end_date=request.period_end_date,
        fiscal_year=request.fiscal_year,
    )
