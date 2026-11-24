def _create_company(client, symbol="HOLDCO", sector="Retail"):
    return client.post("/companies", json={"symbol": symbol, "name": f"{symbol} Ltd", "sector": sector}).json()["id"]


def test_add_holding_requires_auth(client):
    company_id = _create_company(client)
    resp = client.post(
        "/portfolio/holdings", json={"company_id": company_id, "quantity": "10", "average_buy_price": "100"}
    )
    assert resp.status_code == 401


def test_add_and_list_holding(client, auth_headers):
    company_id = _create_company(client)
    resp = client.post(
        "/portfolio/holdings",
        json={"company_id": company_id, "quantity": "10", "average_buy_price": "100", "target_allocation_pct": "20"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert resp.json()["quantity"] == "10.0000"

    list_resp = client.get("/portfolio/holdings", headers=auth_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1


def test_add_holding_for_missing_company_404(client, auth_headers):
    resp = client.post(
        "/portfolio/holdings",
        json={"company_id": "00000000-0000-0000-0000-000000000000", "quantity": "10", "average_buy_price": "100"},
        headers=auth_headers,
    )
    assert resp.status_code == 404


def test_duplicate_holding_for_same_company_rejected(client, auth_headers):
    company_id = _create_company(client)
    payload = {"company_id": company_id, "quantity": "10", "average_buy_price": "100"}
    client.post("/portfolio/holdings", json=payload, headers=auth_headers)
    resp = client.post("/portfolio/holdings", json=payload, headers=auth_headers)
    assert resp.status_code == 409


def test_update_holding(client, auth_headers):
    company_id = _create_company(client)
    create = client.post(
        "/portfolio/holdings",
        json={"company_id": company_id, "quantity": "10", "average_buy_price": "100"},
        headers=auth_headers,
    )
    holding_id = create.json()["id"]

    resp = client.patch(
        f"/portfolio/holdings/{holding_id}", json={"quantity": "15"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["quantity"] == "15.0000"


def test_delete_holding(client, auth_headers):
    company_id = _create_company(client)
    create = client.post(
        "/portfolio/holdings",
        json={"company_id": company_id, "quantity": "10", "average_buy_price": "100"},
        headers=auth_headers,
    )
    holding_id = create.json()["id"]

    resp = client.delete(f"/portfolio/holdings/{holding_id}", headers=auth_headers)
    assert resp.status_code == 204
    assert client.get("/portfolio/holdings", headers=auth_headers).json() == []


def test_user_cannot_modify_another_users_holding(client, auth_headers):
    company_id = _create_company(client)
    create = client.post(
        "/portfolio/holdings",
        json={"company_id": company_id, "quantity": "10", "average_buy_price": "100"},
        headers=auth_headers,
    )
    holding_id = create.json()["id"]

    other_register = client.post(
        "/auth/register", json={"email": "other@example.com", "password": "correcthorsebattery"}
    )
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}

    resp = client.delete(f"/portfolio/holdings/{holding_id}", headers=other_headers)
    assert resp.status_code == 404


def test_portfolio_summary_computes_invested_and_allocation(client, auth_headers):
    retail_id = _create_company(client, "RETAILCO", sector="Retail")
    tech_id = _create_company(client, "TECHCO", sector="Technology")

    client.post(
        "/portfolio/holdings",
        json={"company_id": retail_id, "quantity": "10", "average_buy_price": "100"},  # 1000
        headers=auth_headers,
    )
    client.post(
        "/portfolio/holdings",
        json={"company_id": tech_id, "quantity": "5", "average_buy_price": "600"},  # 3000
        headers=auth_headers,
    )

    resp = client.get("/portfolio/summary", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_invested"] == "4000.00000000"
    assert "cost" in body["note"].lower()

    holdings_by_symbol = {h["symbol"]: h for h in body["holdings"]}
    assert holdings_by_symbol["RETAILCO"]["invested_amount"] == "1000.00000000"
    assert float(holdings_by_symbol["RETAILCO"]["actual_allocation_pct"]) == 25.0
    assert float(holdings_by_symbol["TECHCO"]["actual_allocation_pct"]) == 75.0

    sectors_by_name = {s["sector"]: s for s in body["sector_allocation"]}
    assert float(sectors_by_name["Retail"]["actual_allocation_pct"]) == 25.0
    assert float(sectors_by_name["Technology"]["actual_allocation_pct"]) == 75.0


def test_portfolio_summary_empty_portfolio(client, auth_headers):
    resp = client.get("/portfolio/summary", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_invested"] == "0"
    assert body["holdings"] == []
