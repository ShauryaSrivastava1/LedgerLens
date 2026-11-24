from app.services import metric_extraction
from app.services.text_extraction import PageText


def test_extracts_revenue_candidate():
    pages = [PageText(page_number=5, text="Total Revenue from Operations stood at 1,234.56 crore this quarter.")]
    candidates = metric_extraction.extract_candidates(pages)

    revenue_candidates = [c for c in candidates if c.metric_name == "revenue"]
    assert len(revenue_candidates) == 1
    assert revenue_candidates[0].extracted_value == 1234.56
    assert revenue_candidates[0].page_number == 5
    assert "1,234.56" in revenue_candidates[0].raw_text_snippet


def test_extracts_roce_percentage_with_higher_confidence():
    pages = [PageText(page_number=2, text="ROCE for FY26 was 24.3%, up from last year.")]
    candidates = metric_extraction.extract_candidates(pages)

    roce_candidates = [c for c in candidates if c.metric_name == "roce"]
    assert len(roce_candidates) == 1
    assert roce_candidates[0].extracted_value == 24.3
    assert roce_candidates[0].confidence == 0.75


def test_no_candidates_for_irrelevant_text():
    pages = [PageText(page_number=1, text="This page discusses our sustainability initiatives and CSR programs.")]
    candidates = metric_extraction.extract_candidates(pages)
    assert candidates == []


def test_handles_empty_pages_gracefully():
    pages = [PageText(page_number=1, text="")]
    candidates = metric_extraction.extract_candidates(pages)
    assert candidates == []


def test_snippet_is_evidence_not_blank():
    pages = [PageText(page_number=1, text="Profit After Tax came in at 500.25 crore for the quarter.")]
    candidates = metric_extraction.extract_candidates(pages)
    pat_candidates = [c for c in candidates if c.metric_name == "pat"]
    assert len(pat_candidates) == 1
    assert len(pat_candidates[0].raw_text_snippet) > 0
