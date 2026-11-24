import datetime
import json
from decimal import Decimal

from app import models
from app.services.assistant import answer_question
from app.services.document_processor import DocumentProcessor
from tests.fake_llm import FakeLLMClient
from tests.pdf_fixtures import make_pdf_bytes


def _create_company(db_session, symbol="ASSISTUNIT"):
    company = models.Company(symbol=symbol, name="Assistant Unit Test Co")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def test_answer_question_insufficient_evidence_skips_llm_call(
    db_session, fake_embedding_service, ephemeral_vector_store
):
    company = _create_company(db_session)
    llm = FakeLLMClient()

    result = answer_question(
        db_session, company.id, "Is this company a good investment?",
        fake_embedding_service, ephemeral_vector_store, llm,
    )

    assert result["insufficient_evidence"] is True
    assert result["citations"] == []
    assert result["confidence"] == 0.0
    assert llm.last_user_prompt is None  # no LLM call for a company with nothing ingested


def test_answer_question_retrieval_is_driven_by_the_question_not_fixed_topics(
    db_session, fake_embedding_service, ephemeral_vector_store, tmp_path
):
    """The prompt sent to the LLM should contain the user's actual
    question text, not one of report generation's five fixed topic
    queries — this is the core behavioral difference for Milestone 9."""
    company = _create_company(db_session)

    pdf_path = tmp_path / "report.pdf"
    pdf_path.write_bytes(
        make_pdf_bytes(["The company has a strong distribution network moat across India."])
    )
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

    processor = DocumentProcessor(
        db=db_session, vector_store=ephemeral_vector_store, embedding_service=fake_embedding_service
    )
    processor.process(document.id)

    llm = FakeLLMClient()
    question = "What gives this company its competitive edge?"
    result = answer_question(
        db_session, company.id, question, fake_embedding_service, ephemeral_vector_store, llm
    )

    assert llm.last_user_prompt is not None
    assert question in llm.last_user_prompt
    # None of report generation's fixed topic query text should be what
    # drove retrieval here.
    assert "competitive moat brand distribution switching costs" not in llm.last_user_prompt

    document_citations = [c for c in result["citations"] if c["source_type"] == "document"]
    assert len(document_citations) == 1
    assert document_citations[0]["citation_verified"] is True
    assert document_citations[0]["document_id"] == str(document.id)
    assert result["insufficient_evidence"] is False


def test_answer_question_financial_metric_citation_verifies(
    db_session, fake_embedding_service, ephemeral_vector_store
):
    company = _create_company(db_session)
    metric = models.FinancialMetric(
        company_id=company.id,
        period_type=models.PeriodType.ANNUAL,
        period_end_date=datetime.date(2025, 3, 31),
        fiscal_year="FY2024-25",
        roce=22.5,
    )
    db_session.add(metric)
    db_session.commit()

    llm = FakeLLMClient()
    result = answer_question(
        db_session, company.id, "How is the company's return on capital?",
        fake_embedding_service, ephemeral_vector_store, llm,
    )

    metric_citations = [c for c in result["citations"] if c["source_type"] == "financial_metric"]
    assert len(metric_citations) == 1
    assert metric_citations[0]["citation_verified"] is True
    assert "FY2024-25" in metric_citations[0]["period"]


def test_answer_question_forces_insufficient_evidence_when_nothing_verifies(
    db_session, fake_embedding_service, ephemeral_vector_store
):
    """Evidence exists for the company overall, but the LLM's returned
    citation doesn't match anything actually retrieved — the answer must
    not be trusted as-is."""
    company = _create_company(db_session)
    metric = models.FinancialMetric(
        company_id=company.id,
        period_type=models.PeriodType.ANNUAL,
        period_end_date=datetime.date(2025, 3, 31),
        fiscal_year="FY2024-25",
        roce=22.5,
    )
    db_session.add(metric)
    db_session.commit()

    fabricated = json.dumps(
        {
            "answer": "Everything here looks great.",
            "citations": [
                {
                    "source_type": "financial_metric",
                    "document_id": None,
                    "page_number": None,
                    "period": "a period that was never in context",
                    "reference": "fabricated",
                    "confidence": 0.9,
                }
            ],
            "confidence": 0.9,
            "insufficient_evidence": False,
        }
    )
    llm = FakeLLMClient(canned_response=fabricated)
    result = answer_question(
        db_session, company.id, "Should I invest?", fake_embedding_service, ephemeral_vector_store, llm
    )

    assert result["insufficient_evidence"] is True
    assert result["citations"] == []


def test_answer_question_respects_model_declared_insufficient_evidence(
    db_session, fake_embedding_service, ephemeral_vector_store
):
    company = _create_company(db_session)
    metric = models.FinancialMetric(
        company_id=company.id,
        period_type=models.PeriodType.ANNUAL,
        period_end_date=datetime.date(2025, 3, 31),
        fiscal_year="FY2024-25",
        roce=22.5,
    )
    db_session.add(metric)
    db_session.commit()

    declared_insufficient = json.dumps(
        {
            "answer": "I don't have evidence on that specific topic.",
            "citations": [],
            "confidence": 0.1,
            "insufficient_evidence": True,
        }
    )
    llm = FakeLLMClient(canned_response=declared_insufficient)
    result = answer_question(
        db_session, company.id, "What is management's succession plan?",
        fake_embedding_service, ephemeral_vector_store, llm,
    )

    assert result["insufficient_evidence"] is True
    assert result["citations"] == []


def test_answer_question_raises_on_invalid_json(
    db_session, fake_embedding_service, ephemeral_vector_store
):
    company = _create_company(db_session)
    metric = models.FinancialMetric(
        company_id=company.id,
        period_type=models.PeriodType.ANNUAL,
        period_end_date=datetime.date(2025, 3, 31),
        fiscal_year="FY2024-25",
    )
    db_session.add(metric)
    db_session.commit()

    llm = FakeLLMClient(canned_response="not valid json")
    try:
        answer_question(
            db_session, company.id, "Anything?", fake_embedding_service, ephemeral_vector_store, llm
        )
        assert False, "expected ValueError"
    except ValueError as e:
        assert "did not return valid JSON" in str(e)


def test_answer_question_includes_price_data_in_prompt(
    db_session, fake_embedding_service, ephemeral_vector_store
):
    company = _create_company(db_session)
    metric = models.FinancialMetric(
        company_id=company.id,
        period_type=models.PeriodType.ANNUAL,
        period_end_date=datetime.date(2025, 3, 31),
        fiscal_year="FY2024-25",
    )
    db_session.add(metric)
    db_session.add(
        models.PriceHistory(
            company_id=company.id, price_date=datetime.date(2025, 6, 1), close_price=Decimal("999.25")
        )
    )
    db_session.commit()

    llm = FakeLLMClient()
    answer_question(
        db_session, company.id, "Where does the price stand today?",
        fake_embedding_service, ephemeral_vector_store, llm,
    )

    assert "999.25" in llm.last_user_prompt
    assert "NOT a request to predict" in llm.last_user_prompt


def test_answer_question_missing_company_raises(
    db_session, fake_embedding_service, ephemeral_vector_store
):
    import uuid

    llm = FakeLLMClient()
    try:
        answer_question(
            db_session, uuid.UUID("00000000-0000-0000-0000-000000000000"), "Anything?",
            fake_embedding_service, ephemeral_vector_store, llm,
        )
        assert False, "expected ValueError"
    except ValueError as e:
        assert "not found" in str(e)
