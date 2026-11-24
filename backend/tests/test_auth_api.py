def test_register_creates_account_and_returns_token(client):
    resp = client.post(
        "/auth/register",
        json={"email": "investor@example.com", "password": "correcthorsebattery", "full_name": "Investor One"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_register_duplicate_email_rejected(client):
    payload = {"email": "dupe@example.com", "password": "correcthorsebattery"}
    r1 = client.post("/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = client.post("/auth/register", json=payload)
    assert r2.status_code == 409


def test_register_short_password_rejected(client):
    resp = client.post("/auth/register", json={"email": "short@example.com", "password": "short"})
    assert resp.status_code == 422


def test_login_with_correct_credentials(client):
    client.post("/auth/register", json={"email": "login@example.com", "password": "correcthorsebattery"})
    resp = client.post(
        "/auth/login", data={"username": "login@example.com", "password": "correcthorsebattery"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


def test_login_with_wrong_password_rejected(client):
    client.post("/auth/register", json={"email": "wrongpw@example.com", "password": "correcthorsebattery"})
    resp = client.post("/auth/login", data={"username": "wrongpw@example.com", "password": "nope"})
    assert resp.status_code == 401


def test_login_nonexistent_user_rejected(client):
    resp = client.post("/auth/login", data={"username": "ghost@example.com", "password": "whatever123"})
    assert resp.status_code == 401


def test_get_me_requires_auth(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_get_me_with_valid_token(client):
    register = client.post(
        "/auth/register", json={"email": "me@example.com", "password": "correcthorsebattery", "full_name": "Me"}
    )
    token = register.json()["access_token"]
    resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"
    assert resp.json()["full_name"] == "Me"


def test_get_me_with_invalid_token_rejected(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
