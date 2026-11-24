def test_create_company(client):
    resp = client.post(
        "/companies",
        json={"symbol": "dmart", "name": "Avenue Supermarts Ltd", "sector": "Retail"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["symbol"] == "DMART"  # symbols normalized to uppercase
    assert body["name"] == "Avenue Supermarts Ltd"


def test_create_duplicate_symbol_rejected(client):
    payload = {"symbol": "TCS", "name": "Tata Consultancy Services"}
    r1 = client.post("/companies", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/companies", json=payload)
    assert r2.status_code == 409


def test_get_company_by_symbol(client):
    client.post("/companies", json={"symbol": "INFY", "name": "Infosys Ltd"})
    resp = client.get("/companies/symbol/INFY")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Infosys Ltd"


def test_get_nonexistent_company_returns_404(client):
    resp = client.get("/companies/symbol/NOPE")
    assert resp.status_code == 404


def test_list_companies(client):
    client.post("/companies", json={"symbol": "HDFC", "name": "HDFC Bank"})
    client.post("/companies", json={"symbol": "ICICI", "name": "ICICI Bank"})
    resp = client.get("/companies")
    assert resp.status_code == 200
    symbols = [c["symbol"] for c in resp.json()]
    assert "HDFC" in symbols and "ICICI" in symbols


def test_update_company(client):
    create = client.post("/companies", json={"symbol": "WIPRO", "name": "Wipro Ltd"})
    company_id = create.json()["id"]

    resp = client.patch(f"/companies/{company_id}", json={"sector": "IT Services"})
    assert resp.status_code == 200
    assert resp.json()["sector"] == "IT Services"


def test_delete_company(client):
    create = client.post("/companies", json={"symbol": "TEMP", "name": "Temp Corp"})
    company_id = create.json()["id"]

    resp = client.delete(f"/companies/{company_id}")
    assert resp.status_code == 204

    resp = client.get(f"/companies/{company_id}")
    assert resp.status_code == 404
