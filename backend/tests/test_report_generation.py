import datetime
import json
from decimal import Decimal

from app import models
from app.services.report_generator import generate_report
from tests.fake_llm import FakeLLMClient
from tests.pdf_fixtures import make_pdf_bytes
from app.services.document_processor import DocumentProcessor


def _create_company(db_session, symbol="REPTEST"):
    company = models.Company(symbol=symbol, name="Report Test Co")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


def test_generate_report_insufficient_evidence_skips_llm_call(
    db_session, fake_embedding_service, ephemeral_vector_store
):
    company = _create_company(db_session)
    llm = FakeLLMClient()

    result = generate_report(db_session, company.id, fake_embedding_service, ephemeral_vector_store, llm)

    assert result["llm_provider"] == "none"
    assert "don't have enough evidence" in result["summary"]
    assert result["green_flags"] == []
    assert llm.last_user_prompt is None  # LLM was never called


def test_generate_report_with_financial_metrics_only(
    db_session, fake_embedding_service, ephemeral_vector_store
):
    company = _create_company(db_session)
    metric = models.FinancialMetric(
        company_id=company.id,
        period_type=models.PeriodType.ANNUAL,
        period_end_date=datetime.date(2025, 3, 31),
        fiscal_year="FY2024-25",
        roce=22.5,
        revenue=5000,
    )
    db_session.add(metric)
    db_session.commit()

    llm = FakeLLMClient()
    result = generate_report(db_session, company.id, fake_embedding_service, ephemeral_vector_store, llm)

    assert result["llm_provider"] == "fake"
    assert llm.last_user_prompt is not None
    assert "FY2024-25" in llm.last_user_prompt
    # A financial_metric-sourced green flag should be citation-verified
    financial_flags = [f for f in result["green_flags"] if f["source_type"] == "financial_metric"]
    assert len(financial_flags) == 1
    assert financial_flags[0]["citation_verified"] is True


def test_generate_report_with_documents_verifies_and_flags_bad_citations(
    db_session, fake_embedding_service, ephemeral_vector_store, tmp_path
):
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
    result = generate_report(db_session, company.id, fake_embedding_service, ephemeral_vector_store, llm)

    document_flags = [f for f in result["green_flags"] if f["source_type"] == "document"]
    assert len(document_flags) == 1
    assert document_flags[0]["citation_verified"] is True
    assert document_flags[0]["document_id"] == str(document.id)

    # The fake LLM always emits one red flag citing a fabricated document_id
    assert len(result["red_flags"]) == 1
    assert result["red_flags"][0]["citation_verified"] is False


def test_generate_report_raises_on_invalid_json(
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

    llm = FakeLLMClient(canned_response="this is not json")
    try:
        generate_report(db_session, company.id, fake_embedding_service, ephemeral_vector_store, llm)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "did not return valid JSON" in str(e)


def test_generate_report_strips_markdown_fences(
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

    fenced = "```json\n" + json.dumps({
        "scores": {"overall": 50, "financial_health": 50, "growth": 50, "profitability": 50,
                   "governance": 50, "moat": 50, "valuation": 50, "risk": 50, "confidence": 0.5},
        "green_flags": [], "red_flags": [], "questions_investors_should_ask": [],
        "things_to_verify": [], "potential_risks": [], "summary": "fenced response",
    }) + "\n```"

    llm = FakeLLMClient(canned_response=fenced)
    result = generate_report(db_session, company.id, fake_embedding_service, ephemeral_vector_store, llm)
    assert result["summary"] == "fenced response"


def test_generate_report_includes_price_data_in_prompt(
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
            company_id=company.id, price_date=datetime.date(2025, 6, 1), close_price=Decimal("1234.50")
        )
    )
    db_session.commit()

    llm = FakeLLMClient()
    generate_report(db_session, company.id, fake_embedding_service, ephemeral_vector_store, llm)

    assert "1234.50" in llm.last_user_prompt
    assert "52-week range" in llm.last_user_prompt
    assert "NOT a request to predict" in llm.last_user_prompt
