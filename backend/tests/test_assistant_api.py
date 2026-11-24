from tests.pdf_fixtures import make_pdf_bytes


def _create_company(client, symbol="ASKTEST"):
    return client.post("/companies", json={"symbol": symbol, "name": "Ask Test Co"}).json()["id"]


def _upload_pdf(client, company_id, pages_text, document_type="ANNUAL_REPORT"):
    return client.post(
        f"/companies/{company_id}/documents",
        files={"file": ("r.pdf", make_pdf_bytes(pages_text), "application/pdf")},
        data={"document_type": document_type},
    )


def test_ask_insufficient_evidence_when_company_has_no_data(client):
    """A company with nothing ingested at all gets the deterministic
    response, no LLM call needed."""
    company_id = _create_company(client)
    resp = client.post(
        f"/companies/{company_id}/assistant/ask",
        json={"question": "What is the promoter pledge situation here?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["insufficient_evidence"] is True
    assert body["citations"] == []
    assert body["confidence"] == 0.0
    assert "don't have enough" in body["answer"]
    assert body["context_snapshot"]["chunks_retrieved"] == 0


def test_ask_with_document_evidence_returns_verified_citation(client):
    company_id = _create_company(client)
    upload = _upload_pdf(
        client,
        company_id,
        ["The company has a strong distribution moat across rural and urban markets."],
    )
    assert upload.status_code == 201

    resp = client.post(
        f"/companies/{company_id}/assistant/ask",
        json={"question": "Does this company have a competitive moat?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["insufficient_evidence"] is False
    assert body["question"] == "Does this company have a competitive moat?"
    assert len(body["citations"]) >= 1
    doc_citation = next(c for c in body["citations"] if c["source_type"] == "document")
    assert doc_citation["citation_verified"] is True
    assert doc_citation["document_id"] is not None
    assert body["context_snapshot"]["chunks_retrieved"] >= 1


def test_ask_with_financial_metric_evidence_returns_verified_citation(client):
    company_id = _create_company(client)
    client.post(
        f"/companies/{company_id}/financial-metrics",
        json={
            "period_type": "ANNUAL",
            "period_end_date": "2025-03-31",
            "fiscal_year": "FY2024-25",
            "roce": "23.1",
        },
    )
    # Give the company some non-financial evidence too so the "nothing
    # ingested at all" short-circuit doesn't apply — but here the citation
    # should come back tied to the financial-metric period specifically.
    resp = client.post(
        f"/companies/{company_id}/assistant/ask",
        json={"question": "How healthy are this company's returns on capital?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["insufficient_evidence"] is False
    metric_citation = next(c for c in body["citations"] if c["source_type"] == "financial_metric")
    assert metric_citation["citation_verified"] is True
    assert metric_citation["period"] in body["context_snapshot"]["periods"]


def test_ask_is_stateless_repeated_questions_dont_share_state(client):
    """No conversation memory: two different questions in a row don't
    influence each other, and each response only reflects its own
    question/citations."""
    company_id = _create_company(client)
    client.post(
        f"/companies/{company_id}/financial-metrics",
        json={
            "period_type": "ANNUAL",
            "period_end_date": "2025-03-31",
            "fiscal_year": "FY2024-25",
            "roce": "23.1",
        },
    )

    first = client.post(
        f"/companies/{company_id}/assistant/ask", json={"question": "What is the ROCE trend?"}
    ).json()
    second = client.post(
        f"/companies/{company_id}/assistant/ask", json={"question": "What is the ROCE trend?"}
    ).json()

    assert first["question"] == second["question"] == "What is the ROCE trend?"
    # Independently regenerated, not reused from a stored session.
    assert first["citations"] == second["citations"]


def test_ask_for_missing_company_404(client):
    resp = client.post(
        "/companies/00000000-0000-0000-0000-000000000000/assistant/ask",
        json={"question": "Is this company financially healthy?"},
    )
    assert resp.status_code == 404


def test_ask_rejects_too_short_question(client):
    company_id = _create_company(client)
    resp = client.post(f"/companies/{company_id}/assistant/ask", json={"question": "hi"})
    assert resp.status_code == 422


def test_ask_rejects_missing_question(client):
    company_id = _create_company(client)
    resp = client.post(f"/companies/{company_id}/assistant/ask", json={})
    assert resp.status_code == 422


def test_ask_rejects_too_long_question(client):
    company_id = _create_company(client)
    resp = client.post(
        f"/companies/{company_id}/assistant/ask", json={"question": "x" * 5000}
    )
    assert resp.status_code == 422


def test_ask_no_auth_required(client):
    """Company research (including asking the assistant) is public on
    this platform, same as every other research endpoint."""
    company_id = _create_company(client)
    resp = client.post(
        f"/companies/{company_id}/assistant/ask", json={"question": "Tell me about this company."}
    )
    assert resp.status_code == 200


def test_ask_forces_insufficient_evidence_when_llm_output_uncited(client, monkeypatch):
    """If the model claims to have answered but none of its citations
    verify against what was actually retrieved, the response must be
    downgraded to the deterministic insufficient-evidence answer rather
    than trusting the model's prose."""
    import json

    from app.services.llm.factory import get_llm_client
    from app.main import app

    class UnverifiedCitationLLM:
        provider_name = "fake"
        model_name = "fake-model-v1"

        def complete(self, system_prompt, user_prompt, max_tokens=4096):
            return json.dumps(
                {
                    "answer": "This company looks great, buy it.",
                    "citations": [
                        {
                            "source_type": "document",
                            "document_id": "totally-made-up-id",
                            "page_number": 1,
                            "period": None,
                            "reference": "fabricated",
                            "confidence": 0.9,
                        }
                    ],
                    "confidence": 0.9,
                    "insufficient_evidence": False,
                }
            )

    company_id = _create_company(client)
    _upload_pdf(client, company_id, ["Some real excerpt about the business."])

    app.dependency_overrides[get_llm_client] = lambda: UnverifiedCitationLLM()
    try:
        resp = client.post(
            f"/companies/{company_id}/assistant/ask",
            json={"question": "Should I invest in this company?"},
        )
    finally:
        # restore the fixture-provided override for any subsequent calls
        from tests.fake_llm import FakeLLMClient

        app.dependency_overrides[get_llm_client] = lambda: FakeLLMClient()

    assert resp.status_code == 200
    body = resp.json()
    assert body["insufficient_evidence"] is True
    assert body["citations"] == []
