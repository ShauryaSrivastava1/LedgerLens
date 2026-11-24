import uuid

from app import models
from app.services.document_processor import DocumentProcessor
from tests.pdf_fixtures import make_pdf_bytes


def _create_company_and_document(db_session, tmp_path, pages_text):
    company = models.Company(symbol="TESTCO", name="Test Company")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(make_pdf_bytes(pages_text))

    document = models.Document(
        company_id=company.id,
        document_type=models.DocumentType.ANNUAL_REPORT,
        original_filename="report.pdf",
        storage_path=str(pdf_path),
        status=models.DocumentStatus.PENDING,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    return company, document


def test_pipeline_processes_document_end_to_end(
    db_session, fake_embedding_service, ephemeral_vector_store, tmp_path
):
    company, document = _create_company_and_document(
        db_session,
        tmp_path,
        pages_text=[
            "Total Revenue from Operations stood at 5,000.00 crore.",
            "ROCE for the year was 21.5%. Profit After Tax was 800.00 crore.",
        ],
    )

    processor = DocumentProcessor(
        db=db_session, vector_store=ephemeral_vector_store, embedding_service=fake_embedding_service
    )
    processor.process(document.id)

    db_session.refresh(document)
    assert document.status == models.DocumentStatus.PROCESSED
    assert document.page_count == 2
    assert document.char_count > 0
    assert document.processed_at is not None

    chunks = (
        db_session.query(models.DocumentChunk)
        .filter(models.DocumentChunk.document_id == document.id)
        .all()
    )
    assert len(chunks) >= 2
    assert all(c.vector_id for c in chunks)

    candidates = (
        db_session.query(models.ExtractedMetricCandidate)
        .filter(models.ExtractedMetricCandidate.document_id == document.id)
        .all()
    )
    metric_names = {c.metric_name for c in candidates}
    assert "revenue" in metric_names
    assert "roce" in metric_names
    assert "pat" in metric_names
    assert all(c.status == models.MetricCandidateStatus.PENDING_REVIEW for c in candidates)


def test_pipeline_vectors_are_queryable(
    db_session, fake_embedding_service, ephemeral_vector_store, tmp_path
):
    company, document = _create_company_and_document(
        db_session, tmp_path, pages_text=["The company has a strong distribution moat across India."]
    )

    processor = DocumentProcessor(
        db=db_session, vector_store=ephemeral_vector_store, embedding_service=fake_embedding_service
    )
    processor.process(document.id)

    chunk = db_session.query(models.DocumentChunk).filter(
        models.DocumentChunk.document_id == document.id
    ).first()

    # Querying with the embedding of the exact same chunk text should surface it.
    query_embedding = fake_embedding_service.embed_texts([chunk.text])[0]
    results = ephemeral_vector_store.query(
        query_embedding=query_embedding, n_results=1, where={"company_id": str(company.id)}
    )
    assert len(results) == 1
    assert results[0].vector_id == chunk.vector_id


def test_pipeline_handles_missing_document_gracefully(db_session, fake_embedding_service, ephemeral_vector_store):
    processor = DocumentProcessor(
        db=db_session, vector_store=ephemeral_vector_store, embedding_service=fake_embedding_service
    )
    try:
        processor.process(uuid.uuid4())
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_pipeline_marks_failed_on_bad_storage_path(db_session, fake_embedding_service, ephemeral_vector_store, tmp_path):
    company = models.Company(symbol="BADPATH", name="Bad Path Co")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    document = models.Document(
        company_id=company.id,
        document_type=models.DocumentType.ANNUAL_REPORT,
        original_filename="missing.pdf",
        storage_path=str(tmp_path / "does-not-exist.pdf"),
        status=models.DocumentStatus.PENDING,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)

    processor = DocumentProcessor(
        db=db_session, vector_store=ephemeral_vector_store, embedding_service=fake_embedding_service
    )
    processor.process(document.id)

    db_session.refresh(document)
    assert document.status == models.DocumentStatus.FAILED
    assert document.error_message
