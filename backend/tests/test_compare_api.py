def _create_company_with_metrics(client, symbol, revenues, roce="20.0"):
    company_id = client.post("/companies", json={"symbol": symbol, "name": f"{symbol} Ltd"}).json()["id"]
    dates = ["2024-03-31", "2025-03-31"]
    fys = ["FY2023-24", "FY2024-25"]
    for date, fy, revenue in zip(dates, fys, revenues):
        client.post(
            f"/companies/{company_id}/financial-metrics",
            json={
                "period_type": "ANNUAL",
                "period_end_date": date,
                "fiscal_year": fy,
                "revenue": str(revenue),
                "roce": roce,
            },
        )
    return company_id


def test_compare_requires_at_least_two_symbols(client):
    resp = client.get("/compare", params={"symbols": "ONLYONE"})
    assert resp.status_code == 400


def test_compare_rejects_too_many_symbols(client):
    resp = client.get("/compare", params={"symbols": ",".join(f"S{i}" for i in range(11))})
    assert resp.status_code == 400


def test_compare_rejects_duplicate_symbols(client):
    _create_company_with_metrics(client, "DUP", [100, 200])
    resp = client.get("/compare", params={"symbols": "DUP,DUP"})
    assert resp.status_code == 400


def test_compare_missing_company_404(client):
    _create_company_with_metrics(client, "REAL", [100, 200])
    resp = client.get("/compare", params={"symbols": "REAL,GHOST"})
    assert resp.status_code == 404


def test_compare_computes_growth_correctly(client):
    _create_company_with_metrics(client, "GROWCO", [1000, 1200])  # 20% growth
    _create_company_with_metrics(client, "FLATCO", [1000, 1000])  # 0% growth

    resp = client.get("/compare", params={"symbols": "GROWCO,FLATCO"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbols"] == ["GROWCO", "FLATCO"]

    rows_by_symbol = {r["symbol"]: r for r in body["rows"]}
    assert rows_by_symbol["GROWCO"]["revenue_growth_pct"] == 20.0
    assert rows_by_symbol["FLATCO"]["revenue_growth_pct"] == 0.0
    assert rows_by_symbol["GROWCO"]["revenue"] == "1200.00"


def test_compare_handles_company_with_single_period_no_growth(client):
    company_id = client.post("/companies", json={"symbol": "SOLO", "name": "Solo Ltd"}).json()["id"]
    client.post(
        f"/companies/{company_id}/financial-metrics",
        json={"period_type": "ANNUAL", "period_end_date": "2025-03-31", "fiscal_year": "FY2024-25", "revenue": "500"},
    )
    another_id = client.post("/companies", json={"symbol": "OTHER", "name": "Other Ltd"}).json()["id"]

    resp = client.get("/compare", params={"symbols": "SOLO,OTHER"})
    assert resp.status_code == 200
    rows_by_symbol = {r["symbol"]: r for r in resp.json()["rows"]}
    assert rows_by_symbol["SOLO"]["revenue_growth_pct"] is None
    assert rows_by_symbol["SOLO"]["revenue"] == "500.00"
    assert rows_by_symbol["OTHER"]["revenue"] is None


def test_compare_includes_latest_ai_report_scores(client):
    company_id = _create_company_with_metrics(client, "SCORED", [100, 150])
    client.post(f"/companies/{company_id}/ai-reports")

    other_id = client.post("/companies", json={"symbol": "NOREPORT", "name": "No Report Ltd"}).json()["id"]

    resp = client.get("/compare", params={"symbols": "SCORED,NOREPORT"})
    rows_by_symbol = {r["symbol"]: r for r in resp.json()["rows"]}
    assert rows_by_symbol["SCORED"]["overall_score"] is not None
    assert rows_by_symbol["SCORED"]["latest_report_id"] is not None
    assert rows_by_symbol["NOREPORT"]["overall_score"] is None
    assert rows_by_symbol["NOREPORT"]["latest_report_id"] is None
