import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db
from app.services.embeddings import EmbeddingService, get_embedding_service
from app.services.vector_store import VectorStore, get_persistent_vector_store

router = APIRouter(prefix="/companies/{company_id}/search", tags=["search"])


@router.get("", response_model=schemas.SearchResponse)
def search_company_documents(
    company_id: uuid.UUID,
    q: str = Query(..., min_length=2, description="Natural language search query"),
    n_results: int = Query(default=5, le=20),
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_store: VectorStore = Depends(get_persistent_vector_store),
):
    """
    Semantic search over a company's ingested document chunks. This is the
    retrieval half of retrieval-augmented generation — the AI assistant
    milestone will call the same path, then hand the returned chunks to
    an LLM with instructions to answer only from what's retrieved and
    cite page numbers, in keeping with the "no hallucinations" principle.
    """
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    query_embedding = embedding_service.embed_texts([q])[0]
    matches = vector_store.query(
        query_embedding=query_embedding,
        n_results=n_results,
        where={"company_id": str(company_id)},
    )

    results = []
    for match in matches:
        document = crud.get_document(db, uuid.UUID(match.metadata["document_id"]))
        if document is None:
            continue
        results.append(
            schemas.SearchResult(
                document_id=document.id,
                document_filename=document.original_filename,
                document_type=document.document_type.value,
                page_number=match.metadata.get("page_number"),
                text=match.text,
                # Chroma returns cosine distance (lower = more similar);
                # convert to an intuitive 0-1 relevance score.
                relevance_score=round(1 - match.distance, 4),
            )
        )

    return schemas.SearchResponse(query=q, results=results)
