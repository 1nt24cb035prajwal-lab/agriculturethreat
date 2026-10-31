from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app


def test_farmer_account_and_farm_profile_persist_with_private_activity():
    client = TestClient(app)
    mobile = f"+1555{uuid4().int % 10_000_000:07d}"
    registration = client.post(
        "/api/auth/register",
        json={
            "fullName": "Test Farmer",
            "mobile": mobile,
            "email": f"{uuid4().hex}@example.test",
            "password": "CorrectHorseBattery!9",
            "termsAccepted": True,
            "state": "Karnataka",
            "district": "Mysuru",
            "village": "Hunsur",
        },
    )
    assert registration.status_code == 201, registration.text

    login = client.post("/api/auth/login", json={"mobile": mobile, "password": "CorrectHorseBattery!9"})
    assert login.status_code == 200, login.text
    assert client.cookies.get("farmer_session")

    saved = client.put(
        "/api/farm/profile",
        json={
            "farmName": "Rainfield Farm",
            "cropName": "Ragi",
            "state": "Karnataka",
            "district": "Mysuru",
            "village": "Hunsur",
            "latitude": 12.3,
            "longitude": 76.6,
            "landArea": 3.5,
            "soilType": "Red Soil",
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["farm"]["cropName"] == "Ragi"

    profile = client.get("/api/me")
    assert profile.status_code == 200
    assert profile.json()["farmer"]["name"] == "Test Farmer"
    assert profile.json()["farm"]["farmName"] == "Rainfield Farm"

    history = client.get("/api/activity")
    assert history.status_code == 200
    assert history.json()["items"][0]["type"] == "farm_profile_saved"


def test_farmer_private_endpoints_require_login():
    response = TestClient(app).get("/api/activity")
    assert response.status_code == 401


def test_registration_rejects_duplicate_account_and_weak_password():
    client = TestClient(app)
    payload = {
        "fullName": "Duplicate Farmer",
        "mobile": f"+1777{uuid4().int % 10_000_000:07d}",
        "email": f"{uuid4().hex}@example.test",
        "password": "CorrectHorseBattery!9",
        "termsAccepted": True,
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409
    weak_payload = {**payload, "mobile": f"+1888{uuid4().int % 10_000_000:07d}", "password": "short"}
    assert client.post("/api/auth/register", json=weak_payload).status_code == 400
