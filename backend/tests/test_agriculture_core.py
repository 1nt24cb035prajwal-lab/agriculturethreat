from io import BytesIO
from uuid import uuid4

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app


client = TestClient(app)


def authenticate_test_farmer():
    mobile = f"+1444{uuid4().int % 10_000_000:07d}"
    registration = client.post(
        "/api/auth/register",
        json={
            "fullName": "Test Farmer",
            "mobile": mobile,
            "email": f"{uuid4().hex}@example.test",
            "password": "CorrectHorseBattery!9",
            "termsAccepted": True,
        },
    )
    assert registration.status_code == 201, registration.text
    login = client.post("/api/auth/login", json={"identifier": mobile, "password": "CorrectHorseBattery!9"})
    assert login.status_code == 200, login.text


def test_crop_recommendation_endpoint_accepts_farmer_inputs():
    authenticate_test_farmer()
    response = client.post(
        "/api/farm/recommendation",
        json={
            "fullName": "Ravi Kumar",
            "cropName": "Rice",
            "state": "Karnataka",
            "district": "Mysuru",
            "latitude": 12.3,
            "longitude": 76.6,
            "season": "Kharif",
            "soilType": "Black Soil",
            "landArea": 4.5,
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["farmer"]["name"] == "Test Farmer"
    assert payload["recommendation"]["requestedCrop"] == "Rice"
    assert payload["recommendation"]["crop"]
    assert payload["location"]["coordinates"]["latitude"] == 12.3
    assert client.get("/api/activity").json()["items"][0]["type"] == "crop_recommendation"


def test_crop_recommendation_rejects_invalid_coordinates():
    authenticate_test_farmer()
    response = client.post(
        "/api/farm/recommendation",
        json={
            "fullName": "Ravi Kumar",
            "cropName": "Rice",
            "state": "Karnataka",
            "district": "Mysuru",
            "latitude": 999,
            "longitude": 76.6,
        },
    )
    assert response.status_code == 400


def test_disease_analysis_accepts_crop_and_location_metadata():
    authenticate_test_farmer()
    buffer = BytesIO()
    Image.new("RGB", (32, 32), color=(120, 150, 80)).save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    response = client.post(
        "/api/disease/analyze",
        files={"file": ("leaf.png", image_bytes, "image/png")},
        data={
            "cropName": "Tomato",
            "state": "Tamil Nadu",
            "district": "Coimbatore",
            "village": "Hunsur",
            "latitude": "11.0",
            "longitude": "77.0",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["result"]["predictedDisease"]
    assert payload["result"]["cropName"] == "Tomato"
    assert payload["result"]["location"]["district"] == "Coimbatore"
    assert payload["result"]["location"]["village"] == "Hunsur"
    image_id = payload["result"]["imageId"]
    saved_image = client.get(f"/api/disease/history/{image_id}/image")
    assert saved_image.status_code == 200
    assert saved_image.headers["content-type"] == "image/png"
    assert TestClient(app).get(f"/api/disease/history/{image_id}/image").status_code == 401
    assert client.get("/api/activity").json()["items"][0]["type"] == "disease_detection"


def test_password_recovery_does_not_return_fixed_demo_otp():
    response = client.post("/api/auth/forgot-password", json={"identifier": "farmer@example.test"})
    assert response.status_code == 503
    assert "demoOtp" not in response.json()
