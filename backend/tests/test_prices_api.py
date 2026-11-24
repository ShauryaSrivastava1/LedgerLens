def _create_company(client, symbol="PRICECO"):
    return client.post("/companies", json={"symbol": symbol, "name": f"{symbol} Ltd"}).json()["id"]


def test_add_single_price(client):
    company_id = _create_company(client)
    resp = client.post(
        f"/companies/{company_id}/prices", json={"price_date": "2025-03-31", "close_price": "1234.50"}
    )
    assert resp.status_code == 201
    assert resp.json()["close_price"] == "1234.5000"
    assert resp.json()["source"] == "manual_entry"


def test_add_price_missing_company_404(client):
    resp = client.post(
        "/companies/00000000-0000-0000-0000-000000000000/prices",
        json={"price_date": "2025-03-31", "close_price": "100"},
    )
    assert resp.status_code == 404


def test_add_duplicate_price_date_rejected(client):
    company_id = _create_company(client)
    payload = {"price_date": "2025-03-31", "close_price": "100"}
    client.post(f"/companies/{company_id}/prices", json=payload)
    resp = client.post(f"/companies/{company_id}/prices", json=payload)
    assert resp.status_code == 409


def test_bulk_upload_prices(client):
    company_id = _create_company(client)
    csv_content = b"date,close\n2025-03-28,100\n2025-03-29,101\n2025-03-31,103\n"
    resp = client.post(
        f"/companies/{company_id}/prices/bulk",
        files={"file": ("prices.csv", csv_content, "text/csv")},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["rows_added"] == 3
    assert body["rows_skipped_duplicate"] == 0
    assert body["rows_with_errors"] == 0


def test_bulk_upload_skips_duplicates_on_reupload(client):
    company_id = _create_company(client)
    csv_content = b"date,close\n2025-03-28,100\n2025-03-29,101\n"
    client.post(f"/companies/{company_id}/prices/bulk", files={"file": ("p.csv", csv_content, "text/csv")})

    # Re-upload with one overlapping date and one new date
    csv_content_2 = b"date,close\n2025-03-29,101\n2025-03-30,102\n"
    resp = client.post(f"/companies/{company_id}/prices/bulk", files={"file": ("p2.csv", csv_content_2, "text/csv")})
    body = resp.json()
    assert body["rows_added"] == 1
    assert body["rows_skipped_duplicate"] == 1


def test_bulk_upload_reports_row_errors(client):
    company_id = _create_company(client)
    csv_content = b"date,close\n2025-03-28,100\nbad-date,200\n2025-03-29,not-a-number\n"
    resp = client.post(f"/companies/{company_id}/prices/bulk", files={"file": ("p.csv", csv_content, "text/csv")})
    body = resp.json()
    assert body["rows_added"] == 1
    assert body["rows_with_errors"] == 2
    assert len(body["errors"]) == 2


def test_list_prices(client):
    company_id = _create_company(client)
    client.post(f"/companies/{company_id}/prices", json={"price_date": "2025-03-28", "close_price": "100"})
    client.post(f"/companies/{company_id}/prices", json={"price_date": "2025-03-31", "close_price": "103"})

    resp = client.get(f"/companies/{company_id}/prices")
    assert resp.status_code == 200
    prices = resp.json()
    assert len(prices) == 2
    assert prices[0]["price_date"] == "2025-03-31"  # desc order


def test_list_prices_with_date_range(client):
    company_id = _create_company(client)
    for date, price in [("2025-01-01", "90"), ("2025-03-15", "95"), ("2025-06-01", "110")]:
        client.post(f"/companies/{company_id}/prices", json={"price_date": date, "close_price": price})

    resp = client.get(f"/companies/{company_id}/prices", params={"start": "2025-02-01", "end": "2025-05-01"})
    prices = resp.json()
    assert len(prices) == 1
    assert prices[0]["price_date"] == "2025-03-15"


def test_get_latest_price(client):
    company_id = _create_company(client)
    client.post(f"/companies/{company_id}/prices", json={"price_date": "2025-03-28", "close_price": "100"})
    client.post(f"/companies/{company_id}/prices", json={"price_date": "2025-03-31", "close_price": "103"})

    resp = client.get(f"/companies/{company_id}/prices/latest")
    assert resp.status_code == 200
    assert resp.json()["price_date"] == "2025-03-31"


def test_get_latest_price_no_data_404(client):
    company_id = _create_company(client)
    resp = client.get(f"/companies/{company_id}/prices/latest")
    assert resp.status_code == 404
