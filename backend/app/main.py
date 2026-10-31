from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image

from .data import DEMO_STATE
from .ml_model import CropRecommendationModel, PlantDiseaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_ENGINE = PlantDiseaseModel(BASE_DIR)
CROP_MODEL_ENGINE = CropRecommendationModel(BASE_DIR)

app = FastAPI(title="Agriculture Threat Fusion", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Agriculture Threat Fusion", "demoMode": True}


@app.post("/api/auth/register")
async def register_farmer(payload: dict):
    if not payload.get("fullName"):
        raise HTTPException(status_code=400, detail="Full name is required.")
    farmer = payload.copy()
    farmer["id"] = "F-1002"
    farmer["demoMode"] = True
    farmer["name"] = payload.get("fullName")
    farmer["mobile"] = payload.get("mobile")
    farmer["farmName"] = payload.get("farmName")
    return {"message": "Registration successful. Demo OTP sent to mobile number.", "farmer": farmer}


@app.post("/api/auth/login")
async def login_farmer(payload: dict):
    mobile = str(payload.get("mobile") or "").strip()
    password = str(payload.get("password") or "").strip()

    if not mobile or not password:
        raise HTTPException(status_code=401, detail="Invalid mobile number or password.")

    DEMO_STATE["farmer"]["mobile"] = mobile
    DEMO_STATE["farmer"]["password"] = password
    DEMO_STATE["dashboard"]["welcome"] = f"Welcome, {DEMO_STATE['farmer'].get('name', 'Farmer')}"
    return {"message": "Login successful.", "farmer": DEMO_STATE["farmer"]}


@app.post("/api/farm/recommendation")
async def crop_recommendation(payload: dict):
    required_fields = ("fullName", "cropName", "state", "district")
    missing_fields = [field for field in required_fields if not str(payload.get(field) or "").strip()]
    if missing_fields:
        raise HTTPException(status_code=400, detail=f"Required farmer fields are missing: {', '.join(missing_fields)}.")

    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
        rainfall = float(payload.get("rainfall", 750))
        humidity = float(payload.get("humidity", 68))
        temperature = float(payload.get("temperature", 28))
        land_area = float(payload.get("landArea", 1))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Coordinates and farm measurements must be valid numbers.") from exc

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise HTTPException(status_code=400, detail="Latitude or longitude is outside the valid geographic range.")
    if rainfall < 0 or not 0 <= humidity <= 100 or not -10 <= temperature <= 60 or land_area <= 0:
        raise HTTPException(status_code=400, detail="Check rainfall, humidity, temperature, and farm area values.")

    farmer = payload.copy()
    farmer["name"] = payload.get("fullName")
    farmer["mobile"] = payload.get("mobile") or DEMO_STATE["farmer"].get("mobile")
    farmer["state"] = payload.get("state") or DEMO_STATE["farmer"].get("state")
    farmer["district"] = payload.get("district") or DEMO_STATE["farmer"].get("district")
    farmer["village"] = payload.get("village") or DEMO_STATE["farmer"].get("village")
    farmer["latitude"] = latitude
    farmer["longitude"] = longitude
    farmer["cropName"] = payload.get("cropName")
    farmer["soilType"] = payload.get("soilType") or DEMO_STATE["farmer"].get("soilType") or "Loam"
    farmer["season"] = payload.get("season") or "Kharif"
    farmer["rainfall"] = rainfall
    farmer["humidity"] = humidity
    farmer["temperature"] = temperature
    farmer["landArea"] = land_area

    DEMO_STATE["farmer"].update({
        "name": farmer["name"],
        "state": farmer["state"],
        "district": farmer["district"],
        "village": farmer["village"],
        "cropName": farmer["cropName"],
        "soilType": farmer["soilType"],
        "farmLocation": f"{farmer['district']}, {farmer['state']}",
        "latitude": farmer["latitude"],
        "longitude": farmer["longitude"],
    })

    recommendation = CROP_MODEL_ENGINE.recommend(farmer)
    return {
        "message": "Crop recommendation generated successfully.",
        "farmer": farmer,
        "location": {
            "state": farmer["state"],
            "district": farmer["district"],
            "village": farmer["village"],
            "coordinates": {"latitude": farmer["latitude"], "longitude": farmer["longitude"]},
            "zone": recommendation["locationZone"],
        },
        "recommendation": recommendation,
        "demoMode": True,
        "datasetNotice": recommendation["datasetNotice"],
    }


@app.post("/api/auth/forgot-password")
async def reset_password(payload: dict):
    mobile = payload.get("mobile")
    if not mobile:
        raise HTTPException(status_code=400, detail="Mobile number is required.")
    return {"message": "OTP sent successfully. Use demo OTP 123456 to reset the password.", "demoOtp": "123456"}


@app.get("/api/dashboard")
async def get_dashboard():
    return DEMO_STATE["dashboard"]


@app.get("/api/weather")
async def get_weather():
    return DEMO_STATE["weather"]


@app.get("/api/vegetation")
async def get_vegetation():
    return DEMO_STATE["vegetation"]


@app.get("/api/disease")
async def get_disease():
    return DEMO_STATE["disease"]


@app.get("/api/water")
async def get_water():
    return DEMO_STATE["water"]


@app.get("/api/fertilizer")
async def get_fertilizer():
    return DEMO_STATE["fertilizer"]


@app.get("/api/yield")
async def get_yield():
    return DEMO_STATE["yield"]


@app.get("/api/threats")
async def get_threats():
    return {"threats": DEMO_STATE["threats"], "notifications": DEMO_STATE["notifications"]}


@app.get("/api/admin")
async def get_admin_details():
    return DEMO_STATE["admin"]


@app.get("/api/reports")
async def get_reports():
    return DEMO_STATE["reports"]


@app.post("/api/disease/analyze")
async def analyze_disease(
    file: UploadFile = File(...),
    cropName: str = Form(None),
    state: str = Form(None),
    district: str = Form(None),
    village: str = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    try:
        image = Image.open(file.file).convert("RGB")
        if image.width < 16 or image.height < 16:
            raise HTTPException(status_code=400, detail="Please upload a clear crop image at least 16 × 16 pixels.")
        result = MODEL_ENGINE.predict(image)
        result["cropName"] = cropName or DEMO_STATE["farmer"].get("cropName") or "General crop"
        result["location"] = {
            "state": state or DEMO_STATE["farmer"].get("state") or "Karnataka",
            "district": district or DEMO_STATE["farmer"].get("district") or "Mysuru",
            "village": village or DEMO_STATE["farmer"].get("village") or "Hunsur",
            "coordinates": {
                "latitude": float(latitude) if latitude is not None else float(DEMO_STATE["farmer"].get("latitude") or 12.5),
                "longitude": float(longitude) if longitude is not None else float(DEMO_STATE["farmer"].get("longitude") or 76.5),
            },
        }
        return {
            "message": "Disease analysis completed.",
            "result": result,
            "demoMode": True,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to process crop image: {str(exc)}") from exc


@app.get("/api/disease/status")
async def disease_status():
    model = MODEL_ENGINE.load_or_train()
    return {
        "status": "ready",
        "classes": list(model.classes_),
        "demoMode": True,
    }
