from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app import advanced_services
from backend.app.main import app


client = TestClient(app)


def test_google_sign_in_creates_new_farmer_account(monkeypatch):
    email = f"{uuid4().hex}@example.test"
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")

    async def fake_exchange_google_code(code: str, redirect_uri: str):
        assert code == "test-code"
        assert redirect_uri == "http://localhost:8000/auth/google/callback"
        return {
            "sub": f"google-{uuid4().hex}",
            "email": email,
            "email_verified": True,
            "name": "Google Test Farmer",
        }

    monkeypatch.setattr(advanced_services, "exchange_google_code", fake_exchange_google_code)

    start = client.get("/auth/google/start", follow_redirects=False)
    assert start.status_code == 307
    state = start.cookies["google_oauth_state"]

    callback = client.get(
        "/auth/google/callback",
        params={"code": "test-code", "state": state},
        follow_redirects=False,
    )
    assert callback.status_code == 303
    assert callback.headers["location"] == "/dashboard"

    current = client.get("/api/me")
    assert current.status_code == 200
    assert current.json()["farmer"]["email"] == email
    assert current.json()["farmer"]["name"] == "Google Test Farmer"
    assert current.json()["farmer"]["mobile"] is None
