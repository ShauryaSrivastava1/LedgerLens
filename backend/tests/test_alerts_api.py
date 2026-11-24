def _create_company(client, symbol="ALERTAPI"):
    return client.post("/companies", json={"symbol": symbol, "name": f"{symbol} Ltd"}).json()["id"]


def test_shareholding_endpoint_triggers_alert_on_pledge_increase(client):
    company_id = _create_company(client)
    client.post(
        f"/companies/{company_id}/shareholding",
        json={"period_end_date": "2024-03-31", "pledge_pct": "1.0", "promoter_holding_pct": "70.0"},
    )
    client.post(
        f"/companies/{company_id}/shareholding",
        json={"period_end_date": "2025-03-31", "pledge_pct": "8.0", "promoter_holding_pct": "70.0"},
    )

    resp = client.get(f"/companies/{company_id}/risk-alerts")
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "PLEDGE_INCREASE"


def test_no_alert_on_first_shareholding_record(client):
    company_id = _create_company(client)
    client.post(
        f"/companies/{company_id}/shareholding",
        json={"period_end_date": "2025-03-31", "pledge_pct": "8.0"},
    )
    resp = client.get(f"/companies/{company_id}/risk-alerts")
    assert resp.json() == []


def test_company_alerts_for_missing_company_404(client):
    resp = client.get("/companies/00000000-0000-0000-0000-000000000000/risk-alerts")
    assert resp.status_code == 404


def test_me_alerts_requires_auth(client):
    resp = client.get("/me/alerts")
    assert resp.status_code == 401


def test_me_alerts_aggregates_watchlist_and_portfolio_companies(client, auth_headers):
    watched_id = _create_company(client, "WATCHEDCO")
    held_id = _create_company(client, "HELDCO")
    unrelated_id = _create_company(client, "UNRELATEDCO")

    # Trigger an alert on each of the two tracked companies
    for cid in (watched_id, held_id, unrelated_id):
        client.post(f"/companies/{cid}/shareholding", json={"period_end_date": "2024-03-31", "pledge_pct": "1.0"})
        client.post(f"/companies/{cid}/shareholding", json={"period_end_date": "2025-03-31", "pledge_pct": "9.0"})

    client.post("/watchlist", json={"company_id": watched_id}, headers=auth_headers)
    client.post(
        "/portfolio/holdings",
        json={"company_id": held_id, "quantity": "1", "average_buy_price": "1"},
        headers=auth_headers,
    )

    resp = client.get("/me/alerts", headers=auth_headers)
    assert resp.status_code == 200
    alerted_companies = {a["company_id"] for a in resp.json()}
    assert watched_id in alerted_companies
    assert held_id in alerted_companies
    assert unrelated_id not in alerted_companies  # not tracked by this user


def test_acknowledge_alert_flow(client, auth_headers):
    company_id = _create_company(client)
    client.post(f"/companies/{company_id}/shareholding", json={"period_end_date": "2024-03-31", "pledge_pct": "1.0"})
    client.post(f"/companies/{company_id}/shareholding", json={"period_end_date": "2025-03-31", "pledge_pct": "9.0"})
    client.post("/watchlist", json={"company_id": company_id}, headers=auth_headers)

    alerts = client.get("/me/alerts", headers=auth_headers).json()
    assert len(alerts) == 1
    assert alerts[0]["acknowledged"] is False

    ack_resp = client.post(f"/alerts/{alerts[0]['id']}/acknowledge", headers=auth_headers)
    assert ack_resp.status_code == 204

    alerts_after = client.get("/me/alerts", headers=auth_headers).json()
    assert alerts_after[0]["acknowledged"] is True


def test_acknowledge_missing_alert_404(client, auth_headers):
    resp = client.post(
        "/alerts/00000000-0000-0000-0000-000000000000/acknowledge", headers=auth_headers
    )
    assert resp.status_code == 404


def test_acknowledge_requires_auth(client):
    resp = client.post("/alerts/00000000-0000-0000-0000-000000000000/acknowledge")
    assert resp.status_code == 401


def test_ai_report_generation_triggers_governance_alert(client):
    company_id = _create_company(client, "REPORTALERT")
    client.post(
        f"/companies/{company_id}/financial-metrics",
        json={"period_type": "ANNUAL", "period_end_date": "2024-03-31", "fiscal_year": "FY2023-24", "roce": "20"},
    )
    # Two reports generated back to back with the fake LLM's fixed scores
    # won't naturally differ, so this test focuses on confirming the
    # trigger wiring doesn't error and returns a well-formed alerts list —
    # score-delta behavior itself is covered in test_risk_alerts_service.py.
    client.post(f"/companies/{company_id}/ai-reports")
    client.post(f"/companies/{company_id}/ai-reports")

    resp = client.get(f"/companies/{company_id}/risk-alerts")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
