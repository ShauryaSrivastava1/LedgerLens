import datetime


def _create_company(client, symbol="VALCO", sector="Retail"):
    return client.post("/companies", json={"symbol": symbol, "name": f"{symbol} Ltd", "sector": sector}).json()["id"]


def test_portfolio_summary_no_price_data_all_nulls(client, auth_headers):
    company_id = _create_company(client)
    client.post(
        "/portfolio/holdings",
        json={"company_id": company_id, "quantity": "10", "average_buy_price": "100"},
        headers=auth_headers,
    )
    resp = client.get("/portfolio/summary", headers=auth_headers)
    body = resp.json()
    assert body["total_current_value"] is None
    assert body["all_holdings_priced"] is False
    holding = body["holdings"][0]
    assert holding["current_price"] is None
    assert holding["current_value"] is None
    assert holding["unrealized_pnl"] is None


def test_portfolio_summary_with_price_data_computes_valuation(client, auth_headers):
    company_id = _create_company(client)
    client.post(
        "/portfolio/holdings",
        json={"company_id": company_id, "quantity": "10", "average_buy_price": "100"},  # invested 1000
        headers=auth_headers,
    )
    today = datetime.date.today().isoformat()
    client.post(f"/companies/{company_id}/prices", json={"price_date": today, "close_price": "120"})

    resp = client.get("/portfolio/summary", headers=auth_headers)
    body = resp.json()
    assert body["all_holdings_priced"] is True
    assert body["total_current_value"] == "1200.00000000"
    assert float(body["total_unrealized_pnl"]) == 200.0
    assert float(body["total_unrealized_pnl_pct"]) == 20.0

    holding = body["holdings"][0]
    assert holding["current_price"] == "120.0000"
    assert holding["current_value"] == "1200.00000000"
    assert float(holding["unrealized_pnl_pct"]) == 20.0
    assert holding["price_staleness_days"] == 0
    assert holding["down_significantly_from_buy"] is False


def test_holding_down_significantly_flagged(client, auth_headers):
    company_id = _create_company(client)
    client.post(
        "/portfolio/holdings",
        json={"company_id": company_id, "quantity": "10", "average_buy_price": "100"},
        headers=auth_headers,
    )
    today = datetime.date.today().isoformat()
    client.post(f"/companies/{company_id}/prices", json={"price_date": today, "close_price": "80"})  # -20%

    resp = client.get("/portfolio/summary", headers=auth_headers)
    holding = resp.json()["holdings"][0]
    assert float(holding["unrealized_pnl_pct"]) == -20.0
    assert holding["down_significantly_from_buy"] is True


def test_portfolio_summary_partial_pricing(client, auth_headers):
    priced_id = _create_company(client, "PRICEDCO")
    unpriced_id = _create_company(client, "UNPRICEDCO")

    client.post(
        "/portfolio/holdings",
        json={"company_id": priced_id, "quantity": "10", "average_buy_price": "100"},
        headers=auth_headers,
    )
    client.post(
        "/portfolio/holdings",
        json={"company_id": unpriced_id, "quantity": "5", "average_buy_price": "200"},
        headers=auth_headers,
    )
    today = datetime.date.today().isoformat()
    client.post(f"/companies/{priced_id}/prices", json={"price_date": today, "close_price": "110"})

    resp = client.get("/portfolio/summary", headers=auth_headers)
    body = resp.json()
    assert body["all_holdings_priced"] is False
    # total_current_value reflects only the priced holding (1100), not the unpriced one
    assert body["total_current_value"] == "1100.00000000"

    by_symbol = {h["symbol"]: h for h in body["holdings"]}
    assert by_symbol["PRICEDCO"]["current_value"] is not None
    assert by_symbol["UNPRICEDCO"]["current_value"] is None


def test_price_staleness_reflects_old_price(client, auth_headers):
    company_id = _create_company(client)
    client.post(
        "/portfolio/holdings",
        json={"company_id": company_id, "quantity": "10", "average_buy_price": "100"},
        headers=auth_headers,
    )
    old_date = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    client.post(f"/companies/{company_id}/prices", json={"price_date": old_date, "close_price": "100"})

    resp = client.get("/portfolio/summary", headers=auth_headers)
    holding = resp.json()["holdings"][0]
    assert holding["price_staleness_days"] == 30
