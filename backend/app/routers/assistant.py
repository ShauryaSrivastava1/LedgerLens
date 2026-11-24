import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.services.assistant import answer_question
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.llm.base import LLMClient
from app.services.llm.factory import get_llm_client
from app.services.vector_store import VectorStore, get_persistent_vector_store

router = APIRouter(prefix="/companies/{company_id}/assistant", tags=["assistant"])


@router.post("/ask", response_model=schemas.AssistantAnswerOut)
def ask_assistant(
    company_id: uuid.UUID,
    request: schemas.AssistantAskRequest,
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStore = Depends(get_persistent_vector_store),
    llm_client: LLMClient = Depends(get_llm_client),
):
    """
    Grounded question answering, scoped to a single company. Retrieval is
    driven by an embedding of the question itself — not the fixed
    analysis-topic queries AI report generation runs — but reuses the
    exact same EmbeddingService, VectorStore, LLM infrastructure, and
    citation-verification machinery Milestones 2 and 3 built.

    Stateless: no conversation history is kept server-side or accepted in
    the request. Every call is answered fresh from retrieved evidence only,
    same as report generation — there's no chat session to poison with a
    bad prior turn.

    No auth required, same as every other company-research endpoint —
    company research (including asking questions about it) is public on
    this platform.
    """
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    try:
        answer_data = answer_question(
            db, company_id, request.question, embedding_service, vector_store, llm_client
        )
    except ValueError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return schemas.AssistantAnswerOut(company_id=company_id, **answer_data)
