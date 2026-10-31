from pathlib import Path
import os
import re
import sqlite3

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image

from .data import DEMO_STATE
from . import database
from .ml_model import CropRecommendationModel, PlantDiseaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_ENGINE = PlantDiseaseModel(BASE_DIR)
CROP_MODEL_ENGINE = CropRecommendationModel(BASE_DIR)

app = FastAPI(title="Agriculture Threat Fusion", version="1.0.0")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Agriculture Threat Fusion", "database": "sqlite", "demoMode": True}


def require_farmer(request: Request) -> dict:
    farmer = database.get_farmer_for_session(request.cookies.get("farmer_session"))
    if not farmer:
        raise HTTPException(status_code=401, detail="Please log in to access your farm data.")
    return farmer


@app.post("/api/auth/register", status_code=201)
async def register_farmer(payload: dict):
    full_name = str(payload.get("fullName") or "").strip()
    mobile = str(payload.get("mobile") or "").strip()
    email = str(payload.get("email") or "").strip().lower()
    password = str(payload.get("password") or "")
    if len(full_name) < 2:
        raise HTTPException(status_code=400, detail="Enter your full name.")
    if not re.fullmatch(r"\+?[0-9 ()-]{8,20}", mobile) or len(re.sub(r"\D", "", mobile)) < 8:
        raise HTTPException(status_code=400, detail="Enter a valid mobile number.")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(status_code=400, detail="Enter a valid email address.")
    if len(password) < 10:
        raise HTTPException(status_code=400, detail="Password must be at least 10 characters.")
    if payload.get("termsAccepted") is not True:
        raise HTTPException(status_code=400, detail="Accept the terms to create an account.")

    farm_profile = {
        "farmName": str(payload.get("farmName") or "").strip(),
        "state": str(payload.get("state") or "").strip(),
        "district": str(payload.get("district") or "").strip(),
        "village": str(payload.get("village") or "").strip(),
        "cropName": "",
        "latitude": None,
        "longitude": None,
    }
    try:
        farmer = database.create_farmer(full_name, mobile, email, password, farm_profile)
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="That mobile number or email is already registered.") from exc
    return {
        "message": "Account created. Phone verification is not active because no SMS provider is configured.",
        "farmer": farmer,
        "phoneVerified": False,
        "integrations": {"smsOtp": "not_configured"},
    }


@app.post("/api/auth/login")
async def login_farmer(payload: dict, response: Response):
    identifier = str(payload.get("identifier") or payload.get("mobile") or "").strip()
    password = str(payload.get("password") or "")

    if not identifier or not password:
        raise HTTPException(status_code=401, detail="Invalid mobile number or password.")
    account = database.get_farmer_by_login(identifier)
    if not account or not database.verify_password(password, account["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid mobile/email or password.")
    session_token = database.create_session(account["id"])
    response.set_cookie(
        "farmer_session",
        session_token,
        max_age=database.SESSION_TTL_SECONDS,
        httponly=True,
        secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/",
    )
    farmer = database.farmer_public(account)
    database.record_activity(farmer["id"], "login", {})
    return {"message": "Login successful.", "farmer": farmer}


@app.post("/api/auth/logout")
async def logout_farmer(request: Request, response: Response, farmer: dict = Depends(require_farmer)):
    database.delete_session(request.cookies.get("farmer_session"))
    response.delete_cookie("farmer_session", path="/")
    return {"message": "Logged out successfully."}


@app.get("/api/me")
async def get_current_farmer(farmer: dict = Depends(require_farmer)):
    return {"farmer": farmer, "farm": database.get_farm(farmer["id"])}


@app.put("/api/farm/profile")
async def save_farmer_profile(payload: dict, farmer: dict = Depends(require_farmer)):
    required_fields = ("farmName", "cropName", "state", "district")
    missing_fields = [field for field in required_fields if not str(payload.get(field) or "").strip()]
    if missing_fields:
        raise HTTPException(status_code=400, detail=f"Required farm fields are missing: {', '.join(missing_fields)}.")
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
        land_area = float(payload.get("landArea", 1))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Coordinates and land area must be valid numbers.") from exc
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180 or land_area <= 0:
        raise HTTPException(status_code=400, detail="Enter valid farm coordinates and a positive land area.")

    profile = {
        key: payload.get(key)
        for key in (
            "farmName", "cropName", "cropVariety", "cropStage", "farmingMethod", "previousCrop",
            "cultivationStart", "expectedHarvest", "state", "district", "taluk", "village",
            "soilType", "irrigationType", "waterSource", "season", "landAreaUnit", "rainfall",
            "humidity", "temperature", "soilPh", "nitrogen", "phosphorus", "potassium", "soilMoisture",
        )
    }
    profile["latitude"] = latitude
    profile["longitude"] = longitude
    profile["landArea"] = land_area
    database.save_farm(farmer["id"], profile)
    database.record_activity(farmer["id"], "farm_profile_saved", {"farmName": profile["farmName"], "cropName": profile["cropName"]})
    return {"message": "Farm profile saved.", "farm": profile}


@app.get("/api/activity")
async def get_farmer_activity(farmer: dict = Depends(require_farmer)):
    return {"items": database.get_activity(farmer["id"])}


@app.post("/api/farm/recommendation")
async def crop_recommendation(payload: dict, farmer: dict = Depends(require_farmer)):
    stored_farm = database.get_farm(farmer["id"])
    profile = {**stored_farm, **payload}
    required_fields = ("cropName", "state", "district")
    missing_fields = [field for field in required_fields if not str(profile.get(field) or "").strip()]
    if missing_fields:
        raise HTTPException(status_code=400, detail=f"Required farmer fields are missing: {', '.join(missing_fields)}.")

    try:
        latitude = float(profile["latitude"])
        longitude = float(profile["longitude"])
        rainfall = float(profile.get("rainfall", 750))
        humidity = float(profile.get("humidity", 68))
        temperature = float(profile.get("temperature", 28))
        land_area = float(profile.get("landArea", 1))
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Coordinates and farm measurements must be valid numbers.") from exc

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise HTTPException(status_code=400, detail="Latitude or longitude is outside the valid geographic range.")
    if rainfall < 0 or not 0 <= humidity <= 100 or not -10 <= temperature <= 60 or land_area <= 0:
        raise HTTPException(status_code=400, detail="Check rainfall, humidity, temperature, and farm area values.")

    profile.update({
        "latitude": latitude,
        "longitude": longitude,
        "rainfall": rainfall,
        "humidity": humidity,
        "temperature": temperature,
        "landArea": land_area,
        "fullName": farmer["name"],
        "soilType": profile.get("soilType") or "Loam",
        "season": profile.get("season") or "Kharif",
    })
    database.save_farm(farmer["id"], profile)

    recommendation = CROP_MODEL_ENGINE.recommend(profile)
    database.record_activity(farmer["id"], "crop_recommendation", {"requestedCrop": profile["cropName"], "suggestedCrop": recommendation["crop"], "confidencePct": recommendation["confidencePct"]})
    return {
        "message": "Crop recommendation generated successfully.",
        "farmer": farmer,
        "location": {
            "state": profile["state"],
            "district": profile["district"],
            "village": profile.get("village", ""),
            "coordinates": {"latitude": profile["latitude"], "longitude": profile["longitude"]},
            "zone": recommendation["locationZone"],
        },
        "recommendation": recommendation,
        "demoMode": True,
        "datasetNotice": recommendation["datasetNotice"],
    }


@app.post("/api/auth/forgot-password")
async def reset_password(payload: dict):
    identifier = payload.get("identifier") or payload.get("mobile")
    if not identifier:
        raise HTTPException(status_code=400, detail="Enter your registered phone number or email.")
    raise HTTPException(status_code=503, detail="Password recovery is unavailable until an SMS or email provider is configured.")


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
    raise HTTPException(status_code=503, detail="Administrator accounts and role permissions are not configured.")


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
    farmer: dict = Depends(require_farmer),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded.")

    try:
        image = Image.open(file.file).convert("RGB")
        if image.width < 16 or image.height < 16:
            raise HTTPException(status_code=400, detail="Please upload a clear crop image at least 16 × 16 pixels.")
        result = MODEL_ENGINE.predict(image)
        farm = database.get_farm(farmer["id"])
        result["cropName"] = cropName or farm.get("cropName") or "General crop"
        result["location"] = {
            "state": state or farm.get("state") or "",
            "district": district or farm.get("district") or "",
            "village": village or farm.get("village") or "",
            "coordinates": {
                "latitude": float(latitude) if latitude is not None else farm.get("latitude"),
                "longitude": float(longitude) if longitude is not None else farm.get("longitude"),
            },
        }
        database.record_activity(
            farmer["id"],
            "disease_detection",
            {"filename": file.filename, "cropName": result["cropName"], "predictedDisease": result["predictedDisease"], "confidencePct": result["confidencePct"]},
        )
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
