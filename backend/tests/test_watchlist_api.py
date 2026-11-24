def _create_company(client, symbol="WATCHCO"):
    return client.post("/companies", json={"symbol": symbol, "name": f"{symbol} Ltd"}).json()["id"]


def test_add_to_watchlist_requires_auth(client):
    company_id = _create_company(client)
    resp = client.post("/watchlist", json={"company_id": company_id})
    assert resp.status_code == 401


def test_add_and_list_watchlist(client, auth_headers):
    company_id = _create_company(client)
    resp = client.post(
        "/watchlist", json={"company_id": company_id, "note": "Watching for Q3 results"}, headers=auth_headers
    )
    assert resp.status_code == 201
    assert resp.json()["note"] == "Watching for Q3 results"

    list_resp = client.get("/watchlist", headers=auth_headers)
    assert len(list_resp.json()) == 1


def test_add_to_watchlist_missing_company_404(client, auth_headers):
    resp = client.post(
        "/watchlist", json={"company_id": "00000000-0000-0000-0000-000000000000"}, headers=auth_headers
    )
    assert resp.status_code == 404


def test_duplicate_watchlist_entry_rejected(client, auth_headers):
    company_id = _create_company(client)
    client.post("/watchlist", json={"company_id": company_id}, headers=auth_headers)
    resp = client.post("/watchlist", json={"company_id": company_id}, headers=auth_headers)
    assert resp.status_code == 409


def test_remove_from_watchlist(client, auth_headers):
    company_id = _create_company(client)
    create = client.post("/watchlist", json={"company_id": company_id}, headers=auth_headers)
    item_id = create.json()["id"]

    resp = client.delete(f"/watchlist/{item_id}", headers=auth_headers)
    assert resp.status_code == 204
    assert client.get("/watchlist", headers=auth_headers).json() == []


def test_user_cannot_remove_another_users_watchlist_item(client, auth_headers):
    company_id = _create_company(client)
    create = client.post("/watchlist", json={"company_id": company_id}, headers=auth_headers)
    item_id = create.json()["id"]

    other_register = client.post(
        "/auth/register", json={"email": "otherwatcher@example.com", "password": "correcthorsebattery"}
    )
    other_headers = {"Authorization": f"Bearer {other_register.json()['access_token']}"}

    resp = client.delete(f"/watchlist/{item_id}", headers=other_headers)
    assert resp.status_code == 404
