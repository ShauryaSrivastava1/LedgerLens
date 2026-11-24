from tests.pdf_fixtures import make_pdf_bytes


def _create_company(client, symbol="TIMELINECO"):
    return client.post("/companies", json={"symbol": symbol, "name": f"{symbol} Ltd"}).json()["id"]


def test_timeline_missing_company_404(client):
    resp = client.get("/companies/00000000-0000-0000-0000-000000000000/timeline")
    assert resp.status_code == 404


def test_timeline_empty_for_new_company(client):
    company_id = _create_company(client)
    resp = client.get(f"/companies/{company_id}/timeline")
    assert resp.status_code == 200
    assert resp.json() == []


def test_timeline_includes_document_upload(client):
    company_id = _create_company(client)
    client.post(
        f"/companies/{company_id}/documents",
        files={"file": ("report.pdf", make_pdf_bytes(["Some content."]), "application/pdf")},
        data={"document_type": "ANNUAL_REPORT"},
    )
    resp = client.get(f"/companies/{company_id}/timeline")
    events = resp.json()
    assert len(events) == 1
    assert events[0]["event_type"] == "DOCUMENT_UPLOADED"
    assert events[0]["description"] == "report.pdf"


def test_timeline_includes_ai_report(client):
    company_id = _create_company(client)
    client.post(
        f"/companies/{company_id}/financial-metrics",
        json={"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25", "roce": "20"},
    )
    client.post(f"/companies/{company_id}/ai-reports")

    resp = client.get(f"/companies/{company_id}/timeline")
    events = resp.json()
    report_events = [e for e in events if e["event_type"] == "AI_REPORT_GENERATED"]
    assert len(report_events) == 1


def test_timeline_includes_risk_alert(client):
    company_id = _create_company(client)
    client.post(f"/companies/{company_id}/shareholding", json={"period_end_date": "2024-03-31", "pledge_pct": "1.0"})
    client.post(f"/companies/{company_id}/shareholding", json={"period_end_date": "2025-03-31", "pledge_pct": "9.0"})

    resp = client.get(f"/companies/{company_id}/timeline")
    events = resp.json()
    alert_events = [e for e in events if e["event_type"] == "RISK_ALERT"]
    assert len(alert_events) == 1


def test_timeline_sorted_most_recent_first(client):
    company_id = _create_company(client)
    # Document upload happens first
    client.post(
        f"/companies/{company_id}/documents",
        files={"file": ("old.pdf", make_pdf_bytes(["x"]), "application/pdf")},
        data={"document_type": "ANNUAL_REPORT"},
    )
    # AI report generated after (later timestamp, since generated after the upload call returns)
    client.post(
        f"/companies/{company_id}/financial-metrics",
        json={"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25"},
    )
    client.post(f"/companies/{company_id}/ai-reports")

    resp = client.get(f"/companies/{company_id}/timeline")
    events = resp.json()
    assert len(events) == 2
    timestamps = [e["occurred_at"] for e in events]
    assert timestamps == sorted(timestamps, reverse=True)


def test_timeline_combines_all_event_types(client):
    company_id = _create_company(client)

    client.post(
        f"/companies/{company_id}/documents",
        files={"file": ("report.pdf", make_pdf_bytes(["x"]), "application/pdf")},
        data={"document_type": "ANNUAL_REPORT"},
    )
    client.post(
        f"/companies/{company_id}/financial-metrics",
        json={"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25"},
    )
    client.post(f"/companies/{company_id}/ai-reports")
    client.post(f"/companies/{company_id}/shareholding", json={"period_end_date": "2024-03-31", "pledge_pct": "1.0"})
    client.post(f"/companies/{company_id}/shareholding", json={"period_end_date": "2025-03-31", "pledge_pct": "9.0"})

    resp = client.get(f"/companies/{company_id}/timeline")
    events = resp.json()
    types = {e["event_type"] for e in events}
    assert types == {"DOCUMENT_UPLOADED", "AI_REPORT_GENERATED", "RISK_ALERT"}
