from uuid import uuid4
from unittest.mock import AsyncMock, patch

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


def test_auth_and_farmer_pages_have_separate_direct_urls():
    client = TestClient(app)
    for path in ("/login", "/register", "/dashboard", "/farm", "/recommendations", "/disease", "/weather", "/satellite", "/yield", "/threats", "/history", "/reports", "/settings"):
        response = client.get(path)
        assert response.status_code == 200, (path, response.text)


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
    assert payload["integrations"]["weather"] == "configured"

    weather = client.get("/api/weather")
    assert weather.status_code == 400
    assert "map location" in weather.json()["detail"]
    threats = client.get("/api/threats")
    assert threats.status_code == 400
    assert "map location" in threats.json()["detail"]


def test_weather_and_location_providers_use_saved_coordinates_and_return_source_data():
    client = TestClient(app)
    mobile = f"+1776{uuid4().int % 10_000_000:07d}"
    client.post(
        "/api/auth/register",
        json={
            "fullName": "Weather Farmer",
            "mobile": mobile,
            "email": f"{uuid4().hex}@example.test",
            "password": "CorrectHorseBattery!9",
            "termsAccepted": True,
        },
    )
    client.post("/api/auth/login", json={"identifier": mobile, "password": "CorrectHorseBattery!9"})
    client.put(
        "/api/farm/profile",
        json={
            "farmName": "Weather Farm",
            "cropName": "Rice",
            "state": "Karnataka",
            "district": "Mysuru",
            "latitude": 12.3,
            "longitude": 76.6,
            "landArea": 2,
        },
    )
    weather_data = {
        "source": "Open-Meteo",
        "retrievedAt": "2026-10-31T12:00",
        "current": {"temperatureC": 27, "humidityPercent": 60, "rainfallMm": 0, "windSpeedKph": 45, "condition": "Clear sky"},
        "forecast": [{"date": "2026-10-31", "condition": "Clear sky", "temperatureMinC": 20, "temperatureMaxC": 41, "rainProbabilityPercent": 10, "rainfallMm": 0}],
    }
    with patch("backend.app.main.integrations.fetch_weather", new=AsyncMock(return_value=weather_data)) as provider:
        response = client.get("/api/weather")
    assert response.status_code == 200
    assert response.json()["source"] == "Open-Meteo"
    provider.assert_awaited_once_with(12.3, 76.6)

    with patch("backend.app.main.integrations.fetch_weather", new=AsyncMock(return_value=weather_data)) as provider:
        response = client.get("/api/threats")
    assert response.status_code == 200
    assert {alert["type"] for alert in response.json()["alerts"]} == {"strong_wind", "heat"}
    assert "not a pest" in response.json()["notice"]
    assert response.json()["weather"]["current"]["windSpeedKph"] == 45
    provider.assert_awaited_once_with(12.3, 76.6)

    with patch("backend.app.main.integrations.fetch_weather", new=AsyncMock(return_value=weather_data)) as provider:
        response = client.get("/api/weather/preview", params={"latitude": 10.1, "longitude": 77.2})
    assert response.status_code == 200
    provider.assert_awaited_once_with(10.1, 77.2)
    assert client.get("/api/weather/preview", params={"latitude": 91, "longitude": 77.2}).status_code == 400

    place_data = {"displayName": "Hunsur, Mysuru, Karnataka", "village": "Hunsur", "district": "Mysuru", "state": "Karnataka", "coordinates": {"latitude": 12.3, "longitude": 76.6}, "source": "OpenStreetMap Nominatim"}
    with patch("backend.app.main.integrations.reverse_geocode", new=AsyncMock(return_value=place_data)) as provider:
        response = client.post("/api/location/reverse", json={"latitude": 12.3, "longitude": 76.6})
    assert response.status_code == 200
    assert response.json()["village"] == "Hunsur"
    provider.assert_awaited_once_with(12.3, 76.6)

    with patch("backend.app.main.integrations.search_location", new=AsyncMock(return_value=[place_data])) as provider:
        response = client.get("/api/location/search", params={"q": "Hunsur Karnataka"})
    assert response.status_code == 200
    assert response.json()["results"][0]["state"] == "Karnataka"
    provider.assert_awaited_once_with("Hunsur Karnataka")


def test_water_estimate_uses_weather_et0_saved_crop_area_and_irrigation():
    client = TestClient(app)
    mobile = f"+1775{uuid4().int % 10_000_000:07d}"
    client.post(
        "/api/auth/register",
        json={
            "fullName": "Water Farmer",
            "mobile": mobile,
            "email": f"{uuid4().hex}@example.test",
            "password": "CorrectHorseBattery!9",
            "termsAccepted": True,
        },
    )
    client.post("/api/auth/login", json={"identifier": mobile, "password": "CorrectHorseBattery!9"})
    client.put(
        "/api/farm/profile",
        json={
            "farmName": "Water Farm",
            "cropName": "Rice",
            "cropStage": "Flowering",
            "state": "Karnataka",
            "district": "Mysuru",
            "latitude": 12.3,
            "longitude": 76.6,
            "landArea": 1,
            "landAreaUnit": "Acres",
            "irrigationType": "Drip Irrigation",
        },
    )
    forecast = [{"date": f"2026-11-0{day}", "referenceEvapotranspirationMm": 5, "rainfallMm": 0} for day in range(1, 8)]
    provider_data = {"source": "Open-Meteo", "sourceUrl": "https://open-meteo.com/", "forecast": forecast}
    with patch("backend.app.main.integrations.fetch_weather", new=AsyncMock(return_value=provider_data)):
        response = client.get("/api/water")
    assert response.status_code == 200
    result = response.json()
    assert result["estimate"] is True
    assert result["cropCoefficient"] == 1.2
    assert result["dailyIrrigationLitersEstimate"] > 0
    assert result["nextSevenDaysLitersEstimate"] == result["dailyIrrigationLitersEstimate"] * 7
    assert "generic crop coefficients" in result["notice"]


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


def test_yield_endpoint_returns_transparent_estimate_for_saved_farm():
    client = TestClient(app)
    mobile = f"+1999{uuid4().int % 10_000_000:07d}"
    client.post("/api/auth/register", json={
        "fullName": "Yield Farmer",
        "mobile": mobile,
        "email": f"{uuid4().hex}@example.test",
        "password": "CorrectHorseBattery!9",
        "termsAccepted": True,
    })
    assert client.post("/api/auth/login", json={"identifier": mobile, "password": "CorrectHorseBattery!9"}).status_code == 200
    saved = client.put("/api/farm/profile", json={
        "farmName": "Yield Farm", "cropName": "Ragi", "state": "Karnataka",
        "district": "Mysuru", "latitude": 12.3, "longitude": 76.6,
        "landArea": 2, "landAreaUnit": "Acres",
    })
    assert saved.status_code == 200
    result = client.get("/api/yield")
    assert result.status_code == 200, result.text
    assert result.json()["crop"] == "Ragi"
    assert result.json()["confidence"].startswith("Low")
    assert "not a trained" in result.json()["notice"]
