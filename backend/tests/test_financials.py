def _create_company(client, symbol="DMART"):
    resp = client.post("/companies", json={"symbol": symbol, "name": "Test Co"})
    return resp.json()["id"]


def test_add_financial_metric(client):
    company_id = _create_company(client)
    payload = {
        "period_type": "QUARTERLY",
        "period_end_date": "2026-03-31",
        "fiscal_year": "FY2025-26",
        "revenue": "12500000000.00",
        "pat": "980000000.00",
        "roce": "22.5",
        "receivable_days": "18.4",
    }
    resp = client.post(f"/companies/{company_id}/financial-metrics", json=payload)
    assert resp.status_code == 201
    assert resp.json()["roce"] == "22.500"


def test_duplicate_period_rejected(client):
    company_id = _create_company(client)
    payload = {
        "period_type": "ANNUAL",
        "period_end_date": "2025-03-31",
        "fiscal_year": "FY2024-25",
    }
    r1 = client.post(f"/companies/{company_id}/financial-metrics", json=payload)
    assert r1.status_code == 201
    r2 = client.post(f"/companies/{company_id}/financial-metrics", json=payload)
    assert r2.status_code == 409


def test_list_financial_metrics_ordered_desc(client):
    company_id = _create_company(client)
    for date, fy in [("2024-03-31", "FY2023-24"), ("2025-03-31", "FY2024-25")]:
        client.post(
            f"/companies/{company_id}/financial-metrics",
            json={"period_type": "ANNUAL", "period_end_date": date, "fiscal_year": fy},
        )
    resp = client.get(f"/companies/{company_id}/financial-metrics")
    dates = [m["period_end_date"] for m in resp.json()]
    assert dates == sorted(dates, reverse=True)


def test_metrics_for_missing_company_404(client):
    resp = client.get("/companies/00000000-0000-0000-0000-000000000000/financial-metrics")
    assert resp.status_code == 404


def test_add_shareholding_record(client):
    company_id = _create_company(client)
    payload = {
        "period_end_date": "2026-03-31",
        "promoter_holding_pct": "74.9",
        "pledge_pct": "0.0",
    }
    resp = client.post(f"/companies/{company_id}/shareholding", json=payload)
    assert resp.status_code == 201
    assert resp.json()["pledge_pct"] == "0.000"


def test_company_detail_includes_history(client):
    company_id = _create_company(client)
    client.post(
        f"/companies/{company_id}/financial-metrics",
        json={
            "period_type": "ANNUAL",
            "period_end_date": "2025-03-31",
            "fiscal_year": "FY2024-25",
        },
    )
    client.post(
        f"/companies/{company_id}/shareholding",
        json={"period_end_date": "2025-03-31", "promoter_holding_pct": "70.0"},
    )
    resp = client.get(f"/companies/{company_id}")
    body = resp.json()
    assert len(body["financial_metrics"]) == 1
    assert len(body["shareholding_records"]) == 1
