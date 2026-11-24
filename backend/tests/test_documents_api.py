from tests.pdf_fixtures import make_pdf_bytes


def _create_company(client, symbol="DOCTEST"):
    resp = client.post("/companies", json={"symbol": symbol, "name": "Doc Test Co"})
    return resp.json()["id"]


def _upload_pdf(client, company_id, pages_text, document_type="ANNUAL_REPORT"):
    pdf_bytes = make_pdf_bytes(pages_text)
    return client.post(
        f"/companies/{company_id}/documents",
        files={"file": ("report.pdf", pdf_bytes, "application/pdf")},
        data={"document_type": document_type},
    )


def test_upload_document_processes_synchronously_in_test_client(client):
    company_id = _create_company(client)
    resp = _upload_pdf(
        client,
        company_id,
        ["Total Revenue from Operations stood at 2,000.00 crore this year."],
    )
    assert resp.status_code == 201
    document = resp.json()
    assert document["original_filename"] == "report.pdf"

    detail = client.get(f"/companies/{company_id}/documents/{document['id']}").json()
    assert detail["status"] == "PROCESSED"
    assert detail["page_count"] == 1


def test_upload_rejects_non_pdf_content_type(client):
    company_id = _create_company(client)
    resp = client.post(
        f"/companies/{company_id}/documents",
        files={"file": ("notes.txt", b"just text", "text/plain")},
        data={"document_type": "OTHER"},
    )
    assert resp.status_code == 415


def test_upload_for_missing_company_404(client):
    resp = client.post(
        "/companies/00000000-0000-0000-0000-000000000000/documents",
        files={"file": ("r.pdf", make_pdf_bytes(["x"]), "application/pdf")},
        data={"document_type": "ANNUAL_REPORT"},
    )
    assert resp.status_code == 404


def test_list_documents(client):
    company_id = _create_company(client)
    _upload_pdf(client, company_id, ["Page text"])
    resp = client.get(f"/companies/{company_id}/documents")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_list_chunks_after_processing(client):
    company_id = _create_company(client)
    upload = _upload_pdf(client, company_id, ["Some meaningful content about the business."])
    document_id = upload.json()["id"]

    resp = client.get(f"/companies/{company_id}/documents/{document_id}/chunks")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


def test_metric_candidates_generated_and_reviewable(client):
    company_id = _create_company(client)
    upload = _upload_pdf(
        client, company_id, ["Total Revenue from Operations stood at 3,300.00 crore this quarter."]
    )
    document_id = upload.json()["id"]

    candidates_resp = client.get(f"/companies/{company_id}/documents/{document_id}/metric-candidates")
    assert candidates_resp.status_code == 200
    candidates = candidates_resp.json()
    assert len(candidates) >= 1
    assert all(c["status"] == "PENDING_REVIEW" for c in candidates)

    candidate_id = candidates[0]["id"]
    accept_resp = client.post(
        f"/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate_id}/accept"
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "ACCEPTED"
    assert accept_resp.json()["reviewed_at"] is not None


def test_reject_metric_candidate(client):
    company_id = _create_company(client)
    upload = _upload_pdf(
        client, company_id, ["ROCE for FY26 was 19.9%, an improvement year on year."]
    )
    document_id = upload.json()["id"]

    candidates = client.get(
        f"/companies/{company_id}/documents/{document_id}/metric-candidates"
    ).json()
    candidate_id = candidates[0]["id"]

    resp = client.post(
        f"/companies/{company_id}/documents/{document_id}/metric-candidates/{candidate_id}/reject"
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"


def test_semantic_search_returns_relevant_chunk(client):
    company_id = _create_company(client)
    _upload_pdf(
        client,
        company_id,
        ["The company enjoys a strong distribution network moat across rural India."],
    )

    resp = client.get(f"/companies/{company_id}/search", params={"q": "distribution network moat"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["query"] == "distribution network moat"
    assert len(body["results"]) >= 1
    assert "moat" in body["results"][0]["text"].lower()


def test_search_for_missing_company_404(client):
    resp = client.get(
        "/companies/00000000-0000-0000-0000-000000000000/search", params={"q": "anything"}
    )
    assert resp.status_code == 404
