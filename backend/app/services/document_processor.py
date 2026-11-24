"""
Orchestrates the full ingestion pipeline for one document:

  extract text -> chunk -> embed -> store vectors -> store chunk rows
  -> extract metric candidates -> store candidate rows -> mark PROCESSED

Every step's failure is caught at the top level and recorded on the
Document row (status=FAILED, error_message set) rather than raised past
the background task boundary, where FastAPI would otherwise just log and
swallow it — leaving the document silently stuck at PROCESSING forever.
"""

import datetime
import uuid

from sqlalchemy.orm import Session

from app import models
from app.services import chunking, metric_extraction, storage, text_extraction
from app.services.embeddings import EmbeddingService
from app.services.vector_store import VectorStore


class DocumentProcessor:
    def __init__(self, db: Session, vector_store: VectorStore, embedding_service: EmbeddingService):
        self.db = db
        self.vector_store = vector_store
        self.embedding_service = embedding_service

    def process(self, document_id: uuid.UUID) -> None:
        document = self.db.query(models.Document).filter(models.Document.id == document_id).first()
        if document is None:
            raise ValueError(f"Document {document_id} not found")

        document.status = models.DocumentStatus.PROCESSING
        self.db.commit()

        try:
            self._run_pipeline(document)
            document.status = models.DocumentStatus.PROCESSED
            document.processed_at = datetime.datetime.now(datetime.timezone.utc)
            document.error_message = None
        except Exception as exc:  # noqa: BLE001 - intentionally broad; see module docstring
            document.status = models.DocumentStatus.FAILED
            document.error_message = str(exc)[:2048]

        self.db.commit()

    def _run_pipeline(self, document: models.Document) -> None:
        pdf_bytes_path = document.storage_path

        pages = text_extraction.extract_pages(pdf_bytes_path)
        document.page_count = len(pages)
        document.char_count = sum(len(p.text) for p in pages)

        chunks = chunking.chunk_pages(pages)
        if not chunks:
            # Not an error — e.g. a scanned/image-only PDF with no
            # extractable text. Recorded as processed-but-empty rather
            # than failed, since the extraction itself didn't error.
            return

        embeddings = self.embedding_service.embed_texts([c.text for c in chunks])

        metadatas = [
            {
                "document_id": str(document.id),
                "company_id": str(document.company_id),
                "page_number": c.page_number,
                "chunk_index": c.chunk_index,
            }
            for c in chunks
        ]
        vector_ids = self.vector_store.add_chunks(
            texts=[c.text for c in chunks], embeddings=embeddings, metadatas=metadatas
        )

        for chunk, vector_id in zip(chunks, vector_ids):
            self.db.add(
                models.DocumentChunk(
                    document_id=document.id,
                    company_id=document.company_id,
                    chunk_index=chunk.chunk_index,
                    page_number=chunk.page_number,
                    text=chunk.text,
                    vector_id=vector_id,
                )
            )

        candidates = metric_extraction.extract_candidates(pages)
        for candidate in candidates:
            self.db.add(
                models.ExtractedMetricCandidate(
                    document_id=document.id,
                    company_id=document.company_id,
                    metric_name=candidate.metric_name,
                    extracted_value=candidate.extracted_value,
                    unit_note=candidate.unit_note,
                    raw_text_snippet=candidate.raw_text_snippet,
                    page_number=candidate.page_number,
                    confidence=candidate.confidence,
                )
            )

        self.db.flush()
