import pytest

PROTECTED = ["/api/auth/me", "/api/history", "/api/dashboard/overview", "/api/analytics/overview", "/api/models/performance",
             "/api/notifications", "/api/history/export/csv"]


@pytest.mark.parametrize("path", PROTECTED)
def test_requires_authentication(client, path):
    assert client.get(path).status_code == 401


def test_register_login_me(client):
    r = client.post("/api/auth/register", json={"name": "A B", "email": "a@example.com", "password": "Str0ng!Passw0rd"})
    assert r.status_code == 201
    login = client.post("/api/auth/login", json={"email": "a@example.com", "password": "Str0ng!Passw0rd"})
    assert login.status_code == 200
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == "a@example.com"


def test_wrong_password_weak_password_and_duplicate(client):
    client.post("/api/auth/register", json={"name": "A B", "email": "b@example.com", "password": "Str0ng!Passw0rd"})
    assert client.post("/api/auth/login", json={"email": "b@example.com", "password": "wrong-password"}).status_code == 401
    assert client.post("/api/auth/register", json={"name": "C D", "email": "c@example.com", "password": "weak"}).status_code == 422
    assert client.post("/api/auth/register", json={"name": "A B", "email": "b@example.com", "password": "Str0ng!Passw0rd"}).status_code == 409
