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
            "landAreaUnit": "Hectares",
            "soilType": "Red Soil",
            "cropVariety": "GPU 28",
            "irrigationType": "Drip Irrigation",
            "waterSource": "Borewell",
            "soilPh": 6.4,
            "organicCarbon": 0.8,
        },
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["farm"]["cropName"] == "Ragi"

    profile = client.get("/api/me")
    assert profile.status_code == 200
    assert profile.json()["farmer"]["name"] == "Test Farmer"
    assert profile.json()["farm"]["farmName"] == "Rainfield Farm"
    assert profile.json()["farm"]["cropVariety"] == "GPU 28"
    assert profile.json()["farm"]["landAreaUnit"] == "Hectares"
    assert profile.json()["farm"]["soilPh"] == 6.4

    history = client.get("/api/activity")
    assert history.status_code == 200
    assert history.json()["items"][0]["type"] == "farm_profile_saved"


def test_farmer_private_endpoints_require_login():
    client = TestClient(app)
    assert client.get("/api/activity").status_code == 401
    assert client.get("/api/dashboard").status_code == 401
    assert client.get("/api/weather").status_code == 401


def test_dashboard_is_farmer_scoped_and_unconfigured_feeds_are_not_fabricated():
    client = TestClient(app)
    mobile = f"+1666{uuid4().int % 10_000_000:07d}"
    client.post(
        "/api/auth/register",
        json={
            "fullName": "Dashboard Farmer",
            "mobile": mobile,
            "email": f"{uuid4().hex}@example.test",
            "password": "CorrectHorseBattery!9",
            "termsAccepted": True,
        },
    )
    assert client.post("/api/auth/login", json={"identifier": mobile, "password": "CorrectHorseBattery!9"}).status_code == 200

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["farmer"]["name"] == "Dashboard Farmer"
    assert payload["integrations"]["weather"] == "not_configured"

    weather = client.get("/api/weather")
    assert weather.status_code == 503
    assert "not configured" in weather.json()["detail"]


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
