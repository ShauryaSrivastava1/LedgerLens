from tests.pdf_fixtures import make_pdf_bytes


def _create_company(client, symbol="APITEST"):
    return client.post("/companies", json={"symbol": symbol, "name": "API Test Co"}).json()["id"]


def test_create_report_insufficient_evidence(client):
    company_id = _create_company(client)
    resp = client.post(f"/companies/{company_id}/ai-reports")
    assert resp.status_code == 201
    body = resp.json()
    assert body["llm_provider"] == "none"
    assert "don't have enough evidence" in body["summary"]


def test_create_report_with_data(client):
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
    resp = client.post(f"/companies/{company_id}/ai-reports")
    assert resp.status_code == 201
    body = resp.json()
    assert body["llm_provider"] == "fake"
    assert body["overall_score"] is not None
    assert len(body["green_flags"]) >= 1
    assert body["context_snapshot"]["periods"]


def test_list_and_get_reports(client):
    company_id = _create_company(client)
    client.post(f"/companies/{company_id}/ai-reports")
    client.post(f"/companies/{company_id}/ai-reports")

    list_resp = client.get(f"/companies/{company_id}/ai-reports")
    assert list_resp.status_code == 200
    reports = list_resp.json()
    assert len(reports) == 2

    detail_resp = client.get(f"/companies/{company_id}/ai-reports/{reports[0]['id']}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["id"] == reports[0]["id"]


def test_create_report_for_missing_company_404(client):
    resp = client.post("/companies/00000000-0000-0000-0000-000000000000/ai-reports")
    assert resp.status_code == 404


# ---------- Metric candidate promotion ----------

def _upload_and_get_candidate(client, company_id):
    upload = client.post(
        f"/companies/{company_id}/documents",
        files={"file": ("r.pdf", make_pdf_bytes(["Total Revenue from Operations stood at 4,500.00 crore."]), "application/pdf")},
        data={"document_type": "ANNUAL_REPORT"},
    )
    document_id = upload.json()["id"]
    candidates = client.get(f"/companies/{company_id}/documents/{document_id}/metric-candidates").json()
    return document_id, candidates[0]


def test_promote_requires_accepted_candidate_first(client):
    company_id = _create_company(client)
    document_id, candidate = _upload_and_get_candidate(client, company_id)

    resp = client.post(
        f"/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate['id']}/promote",
        json={"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25"},
    )
    assert resp.status_code == 409


def test_promote_creates_new_financial_metric(client):
    company_id = _create_company(client)
    document_id, candidate = _upload_and_get_candidate(client, company_id)

    client.post(
        f"/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate['id']}/accept"
    )
    resp = client.post(
        f"/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate['id']}/promote",
        json={"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25"},
    )
    assert resp.status_code == 200
    metric = resp.json()
    assert metric["revenue"] == "4500.00"
    assert metric["fiscal_year"] == "FY2024-25"

    # Company's financial metrics should now include this
    company_detail = client.get(f"/companies/{company_id}").json()
    assert len(company_detail["financial_metrics"]) == 1


def test_promote_updates_existing_financial_metric(client):
    company_id = _create_company(client)
    # Pre-existing metric row for the same period with a different field set
    client.post(
        f"/companies/{company_id}/financial-metrics",
        json={"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25", "roce": "20.0"},
    )
    document_id, candidate = _upload_and_get_candidate(client, company_id)
    client.post(f"/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate['id']}/accept")

    resp = client.post(
        f"/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate['id']}/promote",
        json={"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25"},
    )
    assert resp.status_code == 200
    metric = resp.json()
    assert metric["revenue"] == "4500.00"
    assert metric["roce"] == "20.000"  # untouched field preserved

    company_detail = client.get(f"/companies/{company_id}").json()
    assert len(company_detail["financial_metrics"]) == 1  # updated in place, not duplicated


def test_promote_twice_rejected(client):
    company_id = _create_company(client)
    document_id, candidate = _upload_and_get_candidate(client, company_id)
    client.post(f"/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate['id']}/accept")
    client.post(
        f"/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate['id']}/promote",
        json={"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25"},
    )
    second = client.post(
        f"/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate['id']}/promote",
        json={"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25"},
    )
    assert second.status_code == 409
