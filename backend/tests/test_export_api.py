def _create_company(client, symbol="EXPORTCO", sector="Retail"):
    return client.post("/companies", json={"symbol": symbol, "name": f"{symbol} Ltd", "sector": sector}).json()["id"]


# ---------- AI report PDF export ----------

def test_download_report_pdf(client):
    company_id = _create_company(client)
    client.post(
        f"/companies/{company_id}/financial-metrics",
        json={"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25", "roce": "20"},
    )
    report = client.post(f"/companies/{company_id}/ai-reports").json()

    resp = client.get(f"/companies/{company_id}/ai-reports/{report['id']}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content[:5] == b"%PDF-"
    assert len(resp.content) > 500  # not a trivially empty/broken PDF


def test_download_pdf_missing_report_404(client):
    company_id = _create_company(client)
    resp = client.get(
        f"/companies/{company_id}/ai-reports/00000000-0000-0000-0000-000000000000/pdf"
    )
    assert resp.status_code == 404


def test_download_pdf_missing_company_404(client):
    resp = client.get(
        "/companies/00000000-0000-0000-0000-000000000000/ai-reports/"
        "00000000-0000-0000-0000-000000000000/pdf"
    )
    assert resp.status_code == 404


def test_download_pdf_for_insufficient_evidence_report(client):
    """A report with null scores (no data on file) should still render a valid PDF, not crash."""
    company_id = _create_company(client)
    report = client.post(f"/companies/{company_id}/ai-reports").json()
    assert report["llm_provider"] == "none"  # confirm this is the insufficient-evidence path

    resp = client.get(f"/companies/{company_id}/ai-reports/{report['id']}/pdf")
    assert resp.status_code == 200
    assert resp.content[:5] == b"%PDF-"


# ---------- Portfolio CSV export ----------

def test_export_portfolio_csv_requires_auth(client):
    resp = client.get("/portfolio/export.csv")
    assert resp.status_code == 401


def test_export_portfolio_csv(client, auth_headers):
    company_id = _create_company(client, "CSVCO", sector="Retail")
    client.post(
        "/portfolio/holdings",
        json={"company_id": company_id, "quantity": "10", "average_buy_price": "100"},
        headers=auth_headers,
    )

    resp = client.get("/portfolio/export.csv", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]

    text = resp.content.decode()
    lines = text.strip().split("\n")
    assert lines[0].startswith("symbol,name,sector")
    assert "CSVCO" in lines[1]


def test_export_empty_portfolio_csv_has_header_only(client, auth_headers):
    resp = client.get("/portfolio/export.csv", headers=auth_headers)
    assert resp.status_code == 200
    lines = resp.content.decode().strip().split("\n")
    assert len(lines) == 1  # header row only


# ---------- Watchlist CSV export ----------

def test_export_watchlist_csv_requires_auth(client):
    resp = client.get("/watchlist/export.csv")
    assert resp.status_code == 401


def test_export_watchlist_csv(client, auth_headers):
    company_id = _create_company(client, "WATCHCSV")
    client.post(
        "/watchlist", json={"company_id": company_id, "note": "keep an eye on this"}, headers=auth_headers
    )

    resp = client.get("/watchlist/export.csv", headers=auth_headers)
    assert resp.status_code == 200
    text = resp.content.decode()
    lines = text.strip().replace("\r\n", "\n").split("\n")
    assert lines[0] == "symbol,name,sector,note,added_at"
    assert "WATCHCSV" in lines[1]
    assert "keep an eye on this" in lines[1]
