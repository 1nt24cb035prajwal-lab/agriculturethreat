from io import BytesIO
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app


client = TestClient(app)


def test_crop_recommendation_endpoint_accepts_farmer_inputs():
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
    assert payload["farmer"]["name"] == "Ravi Kumar"
    assert payload["recommendation"]["requestedCrop"] == "Rice"
    assert payload["recommendation"]["crop"]
    assert payload["location"]["coordinates"]["latitude"] == 12.3


def test_crop_recommendation_rejects_invalid_coordinates():
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
