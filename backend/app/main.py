from pathlib import Path
from io import BytesIO
import os
import re
import sqlite3
import secrets
from urllib.parse import quote, urlencode

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
# Load backend/.env even when the developer starts Uvicorn without --env-file.
# Existing process/deployment variables always take precedence.
load_dotenv(BASE_DIR / ".env", override=False)

from . import database
from . import integrations
from . import advanced_services
from .ml_model import CropRecommendationModel, PlantDiseaseModel
MODEL_ENGINE = PlantDiseaseModel(BASE_DIR)
CROP_MODEL_ENGINE = CropRecommendationModel(BASE_DIR)

app = FastAPI(title="Agriculture Threat Fusion", version="1.0.0")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": "Agriculture Threat Fusion", "database": "sqlite", "integrations": advanced_services.configured_status()}


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

    mobile = re.sub(r"[ ()-]", "", mobile)
    if advanced_services.configured_status()["smsOtp"] == "configured" and not mobile.startswith("+"):
        raise HTTPException(status_code=400, detail="Use international phone format including country code, such as +919876543210.")

    farm_profile = {
        "farmName": str(payload.get("farmName") or "").strip(),
        "state": str(payload.get("state") or "").strip(),
        "district": str(payload.get("district") or "").strip(),
        "village": str(payload.get("village") or "").strip(),
        "cropName": "",
        "latitude": None,
        "longitude": None,
    }
    phone_verified = False
    if advanced_services.configured_status()["smsOtp"] == "configured":
        phone_verified = database.consume_phone_verification(mobile)
        if not phone_verified:
            raise HTTPException(status_code=400, detail="Verify this phone number with the OTP before creating your account.")

    try:
        farmer = database.create_farmer(full_name, mobile, email, password, farm_profile)
        if phone_verified:
            database.set_farmer_phone_verified(int(farmer["id"].removeprefix("F-")))
            farmer["phoneVerified"] = True
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="That mobile number or email is already registered.") from exc
    return {
        "message": "Account created. Phone verification status is shown on your profile.",
        "farmer": farmer,
        "phoneVerified": bool(farmer.get("phoneVerified")),
        "integrations": {"smsOtp": advanced_services.configured_status()["smsOtp"]},
    }


@app.get("/api/integrations/status")
async def integrations_status():
    return advanced_services.configured_status()


@app.post("/api/auth/otp/send")
async def send_registration_otp(payload: dict):
    phone = str(payload.get("mobile") or "").strip()
    if not re.fullmatch(r"\+[0-9]{8,15}", phone):
        raise HTTPException(status_code=400, detail="Enter a phone number in international format, for example +919876543210.")
    try:
        result = await advanced_services.start_phone_verification(phone)
    except advanced_services.ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"message": "Verification code sent.", "verification": result}


@app.post("/api/auth/otp/verify")
async def verify_registration_otp(payload: dict):
    phone = str(payload.get("mobile") or "").strip()
    code = str(payload.get("code") or "").strip()
    if not re.fullmatch(r"\+[0-9]{8,15}", phone) or not re.fullmatch(r"[0-9]{4,10}", code):
        raise HTTPException(status_code=400, detail="Enter the phone number and numeric OTP.")
    try:
        approved = await advanced_services.check_phone_verification(phone, code)
    except advanced_services.ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if not approved:
        raise HTTPException(status_code=400, detail="The OTP is invalid or expired.")
    database.mark_phone_verified(phone)
    return {"message": "Phone number verified. Complete registration using this number.", "verified": True}


@app.get("/auth/google/start")
async def google_oauth_start(request: Request):
    status = advanced_services.configured_status()["googleOAuth"]
    if status != "configured":
        return RedirectResponse("/login?auth_error=google_not_configured", status_code=303)
    state = secrets.token_urlsafe(32)
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI") or str(request.url_for("google_oauth_callback"))
    params = {"client_id": os.environ["GOOGLE_CLIENT_ID"], "redirect_uri": redirect_uri, "response_type": "code", "scope": "openid email profile", "state": state, "prompt": "select_account"}
    response = RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params))
    secure_cookie = request.url.scheme == "https" or os.getenv("COOKIE_SECURE", "false").lower() == "true"
    response.set_cookie("google_oauth_state", state, max_age=600, httponly=True, secure=secure_cookie, samesite="lax", path="/")
    return response


@app.get("/auth/google/callback", name="google_oauth_callback")
async def google_oauth_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None):
    if error:
        return RedirectResponse("/login?auth_error=google_cancelled", status_code=303)
    expected_state = request.cookies.get("google_oauth_state")
    if not code or not state or not expected_state or not secrets.compare_digest(state, expected_state):
        response = RedirectResponse("/login?auth_error=google_state", status_code=303)
        response.delete_cookie("google_oauth_state", path="/")
        return response
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI") or str(request.url_for("google_oauth_callback"))
    try:
        profile = await advanced_services.exchange_google_code(code, redirect_uri)
    except advanced_services.ProviderUnavailable as exc:
        response = RedirectResponse("/login?auth_error=google_exchange", status_code=303)
        response.delete_cookie("google_oauth_state", path="/")
        return response
    google_sub = str(profile.get("sub") or "").strip()
    email = str(profile.get("email") or "").strip().lower()
    if not google_sub or not email:
        raise HTTPException(status_code=400, detail="Google did not return a complete verified account identity.")

    account = database.get_farmer_by_google_sub(google_sub)
    if not account:
        account = database.get_farmer_by_login(email)
        if account:
            try:
                database.link_google_account(int(account["id"]), google_sub)
                account = database.get_farmer_by_login(email)
            except sqlite3.IntegrityError as exc:
                raise HTTPException(status_code=409, detail="This Google account is already linked to another farmer.") from exc
        else:
            try:
                database.create_google_farmer(str(profile.get("name") or "Farmer"), email, google_sub)
                account = database.get_farmer_by_login(email)
            except sqlite3.IntegrityError as exc:
                raise HTTPException(status_code=409, detail="A farmer account already exists for this Google email. Please sign in again.") from exc

    if not account:
        raise HTTPException(status_code=500, detail="Unable to create or load the Google farmer account.")
    token = database.create_session(account["id"])
    response = RedirectResponse("/dashboard", status_code=303)
    response.set_cookie("farmer_session", token, max_age=database.SESSION_TTL_SECONDS, httponly=True, secure=os.getenv("COOKIE_SECURE", "false").lower() == "true", samesite="lax", path="/")
    response.delete_cookie("google_oauth_state")
    database.record_activity(database.farmer_public(account)["id"], "google_login", {"email": profile["email"]})
    return response


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
            "humidity", "temperature", "soilPh", "nitrogen", "phosphorus", "potassium", "soilMoisture", "organicCarbon",
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
        "demoMode": not (
            isinstance(CROP_MODEL_ENGINE.model, dict)
            and CROP_MODEL_ENGINE.model.get("kind") == "crop_csv_v1"
        ),
        "datasetNotice": recommendation["datasetNotice"],
    }


@app.post("/api/auth/forgot-password")
async def reset_password(payload: dict):
    identifier = payload.get("identifier") or payload.get("mobile")
    if not identifier:
        raise HTTPException(status_code=400, detail="Enter your registered phone number or email.")
    raise HTTPException(status_code=503, detail="Password recovery is unavailable until an SMS or email provider is configured.")


@app.get("/api/dashboard")
async def get_dashboard(farmer: dict = Depends(require_farmer)):
    farm = database.get_farm(farmer["id"])
    return {
        "welcome": f"Welcome, {farmer['name']}",
        "farmer": farmer,
        "farm": farm,
        "integrations": {
            "weather": "configured",
            "satellite": advanced_services.configured_status()["sentinelHub"],
            "marketPrices": advanced_services.configured_status()["marketPrices"],
            "nearbyMarkets": advanced_services.configured_status()["marketPrices"],
            "smsAlerts": advanced_services.configured_status()["smsOtp"],
            "googleOAuth": advanced_services.configured_status()["googleOAuth"],
        },
    }


def integration_unavailable(name: str) -> None:
    raise HTTPException(status_code=503, detail=f"{name} data is unavailable because its provider integration is not configured.")


@app.get("/api/weather")
async def get_weather(farmer: dict = Depends(require_farmer)):
    farm = database.get_farm(farmer["id"])
    latitude = farm.get("latitude")
    longitude = farm.get("longitude")
    if latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Save a farm map location before requesting local weather.")
    try:
        result = await integrations.fetch_weather(float(latitude), float(longitude))
    except integrations.ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    database.record_activity(farmer["id"], "weather_lookup", {"source": result["source"], "observedAt": result["retrievedAt"]})
    return result


@app.get("/api/weather/preview")
async def preview_weather(latitude: float, longitude: float, farmer: dict = Depends(require_farmer)):
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise HTTPException(status_code=400, detail="Latitude or longitude is outside the valid geographic range.")
    try:
        return await integrations.fetch_weather(latitude, longitude)
    except integrations.ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/location/reverse")
async def reverse_farm_location(payload: dict, farmer: dict = Depends(require_farmer)):
    try:
        latitude = float(payload["latitude"])
        longitude = float(payload["longitude"])
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Latitude and longitude are required numeric coordinates.") from exc
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        raise HTTPException(status_code=400, detail="Latitude or longitude is outside the valid geographic range.")
    try:
        return await integrations.reverse_geocode(latitude, longitude)
    except integrations.ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.get("/api/location/search")
async def search_farm_location(q: str, farmer: dict = Depends(require_farmer)):
    query = q.strip()
    if len(query) < 3 or len(query) > 160:
        raise HTTPException(status_code=400, detail="Search location must contain 3 to 160 characters.")
    try:
        results = await integrations.search_location(query)
    except integrations.ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"results": results, "source": "OpenStreetMap Nominatim"}


@app.get("/api/vegetation")
async def get_vegetation(farmer: dict = Depends(require_farmer)):
    farm = database.get_farm(farmer["id"])
    if farm.get("latitude") is None or farm.get("longitude") is None:
        raise HTTPException(status_code=400, detail="Save farm coordinates before requesting satellite NDVI.")
    try:
        result = await advanced_services.fetch_sentinel_ndvi(float(farm["latitude"]), float(farm["longitude"]))
    except advanced_services.ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    database.record_activity(farmer["id"], "satellite_ndvi", {"ndvi": result["ndvi"], "source": result["source"]})
    return result


@app.get("/api/disease")
async def get_disease(farmer: dict = Depends(require_farmer)):
    integration_unavailable("Disease history")


@app.get("/api/water")
async def get_water(farmer: dict = Depends(require_farmer)):
    farm = database.get_farm(farmer["id"])
    if farm.get("latitude") is None or farm.get("longitude") is None:
        raise HTTPException(status_code=400, detail="Save a farm map location before calculating water needs.")
    if not farm.get("cropName") or not farm.get("landArea"):
        raise HTTPException(status_code=400, detail="Save crop and land area before calculating water needs.")
    try:
        weather = await integrations.fetch_weather(float(farm["latitude"]), float(farm["longitude"]))
    except integrations.ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    crop = str(farm["cropName"]).strip().lower()
    stage = str(farm.get("cropStage") or "").lower()
    stage_name = "initial" if any(word in stage for word in ("sowing", "seed", "germination", "transplant")) else "late" if any(word in stage for word in ("ripening", "mature", "harvest")) else "mid"
    crop_coefficients = {
        "rice": {"initial": 0.3, "mid": 1.2, "late": 0.6},
        "wheat": {"initial": 0.3, "mid": 1.15, "late": 0.25},
        "maize": {"initial": 0.3, "mid": 1.2, "late": 0.6},
        "ragi": {"initial": 0.3, "mid": 1.0, "late": 0.3},
        "tomato": {"initial": 0.6, "mid": 1.15, "late": 0.8},
        "potato": {"initial": 0.5, "mid": 1.15, "late": 0.75},
        "cotton": {"initial": 0.35, "mid": 1.15, "late": 0.7},
    }
    coefficients = crop_coefficients.get(crop)
    crop_coefficient = coefficients[stage_name] if coefficients else 0.85
    unit = str(farm.get("landAreaUnit") or "Acres").lower()
    area_sqm = float(farm["landArea"]) * (10_000 if unit.startswith("hect") else 4046.8564224)
    irrigation_method = str(farm.get("irrigationType") or "").lower()
    efficiency = 0.9 if "drip" in irrigation_method else 0.75 if "sprinkler" in irrigation_method else 0.6 if "flood" in irrigation_method else 0.65 if "furrow" in irrigation_method else 1.0
    forecast = weather["forecast"]
    if not forecast or forecast[0].get("referenceEvapotranspirationMm") is None:
        raise HTTPException(status_code=503, detail="Reference evapotranspiration is missing from the weather provider response.")

    daily_estimates = []
    for day in forecast:
        reference_et = day.get("referenceEvapotranspirationMm")
        if reference_et is None:
            continue
        crop_et_mm = float(reference_et) * crop_coefficient
        effective_rain_mm = float(day.get("rainfallMm") or 0) * 0.8
        net_irrigation_mm = max(crop_et_mm - effective_rain_mm, 0)
        gross_irrigation_liters = net_irrigation_mm * area_sqm / efficiency
        daily_estimates.append({
            "date": day["date"],
            "referenceEvapotranspirationMm": reference_et,
            "cropEvapotranspirationMm": round(crop_et_mm, 2),
            "effectiveRainfallMm": round(effective_rain_mm, 2),
            "estimatedIrrigationLiters": round(gross_irrigation_liters),
        })

    result = {
        "source": weather["source"],
        "sourceUrl": weather["sourceUrl"],
        "crop": farm["cropName"],
        "cropStage": farm.get("cropStage") or "Not provided; mid-season coefficient assumed",
        "landArea": farm["landArea"],
        "landAreaUnit": farm.get("landAreaUnit") or "Acres",
        "irrigationMethod": farm.get("irrigationType") or "Not provided; gross application efficiency not adjusted",
        "cropCoefficient": crop_coefficient,
        "dailyIrrigationLitersEstimate": daily_estimates[0]["estimatedIrrigationLiters"],
        "nextSevenDaysLitersEstimate": sum(day["estimatedIrrigationLiters"] for day in daily_estimates),
        "forecast": daily_estimates,
        "estimate": True,
        "notice": "Planning estimate from Open-Meteo FAO reference ET, generic crop coefficients, forecast rainfall, and assumed irrigation efficiency. Soil moisture, local calibration, and sensor readings are not included.",
    }
    database.record_activity(farmer["id"], "water_requirement_estimate", {"crop": result["crop"], "dailyLiters": result["dailyIrrigationLitersEstimate"], "source": result["source"]})
    return result


@app.get("/api/fertilizer")
async def get_fertilizer(farmer: dict = Depends(require_farmer)):
    integration_unavailable("Soil-test fertilizer data")


@app.get("/api/yield")
async def get_yield(farmer: dict = Depends(require_farmer)):
    farm = database.get_farm(farmer["id"])
    try:
        result = advanced_services.estimate_yield(farm)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    database.record_activity(farmer["id"], "yield_estimate", {"crop": result["crop"], "expectedEstimateTonnes": result["expectedEstimateTonnes"], "method": result["method"]})
    return result


@app.get("/api/markets")
async def get_market_prices(commodity: str | None = None, farmer: dict = Depends(require_farmer)):
    farm = database.get_farm(farmer["id"])
    state = str(farm.get("state") or "").strip()
    district = str(farm.get("district") or "").strip()
    crop = str(commodity or farm.get("cropName") or "").strip()
    if not state or not district or not crop:
        raise HTTPException(status_code=400, detail="Save farm state, district, and crop before checking mandi prices.")
    try:
        result = await advanced_services.fetch_market_prices(state, district, crop)
    except advanced_services.ProviderUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    database.record_activity(farmer["id"], "market_price_lookup", {"commodity": crop, "records": len(result["records"]), "source": result["source"]})
    return result


@app.get("/api/threats")
async def get_threats(farmer: dict = Depends(require_farmer)):
    integration_unavailable("Live threat analysis")


@app.get("/api/admin")
async def get_admin_details():
    raise HTTPException(status_code=503, detail="Administrator accounts and role permissions are not configured.")


@app.get("/api/reports")
async def get_reports(farmer: dict = Depends(require_farmer)):
    return {"items": database.get_activity(farmer["id"]), "pdfExport": "not_configured"}


@app.post("/api/disease/analyze")
async def analyze_disease(
    file: UploadFile = File(...),
    cropName: str = Form(None),
    cropStage: str = Form(None),
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
        image_data = await file.read()
        if not image_data or len(image_data) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Crop images must be non-empty and no larger than 10 MB.")
        source_image = Image.open(BytesIO(image_data))
        if source_image.format not in {"JPEG", "PNG", "WEBP"}:
            raise HTTPException(status_code=400, detail="Upload a JPEG, PNG, or WebP crop image.")
        if source_image.width < 16 or source_image.height < 16:
            raise HTTPException(status_code=400, detail="Please upload a clear crop image at least 16 × 16 pixels.")
        if source_image.width * source_image.height > 20_000_000:
            raise HTTPException(status_code=400, detail="Crop image dimensions are too large to analyze.")
        image = source_image.convert("RGB")
        result = MODEL_ENGINE.predict(image)
        farm = database.get_farm(farmer["id"])
        result["cropName"] = cropName or farm.get("cropName") or "Not provided"
        result["cropStage"] = cropStage or farm.get("cropStage") or "Not provided"
        result["location"] = {
            "state": state or farm.get("state") or "",
            "district": district or farm.get("district") or "",
            "village": village or farm.get("village") or "",
            "coordinates": {
                "latitude": float(latitude) if latitude is not None else farm.get("latitude"),
                "longitude": float(longitude) if longitude is not None else farm.get("longitude"),
            },
        }
        image_id = database.store_disease_image(
            farmer["id"],
            file.filename,
            {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[source_image.format],
            image_data,
        )
        result["imageId"] = image_id
        database.record_activity(
            farmer["id"],
            "disease_detection",
            {"imageId": image_id, "filename": file.filename, "cropName": result["cropName"], "cropStage": result["cropStage"], "predictedDisease": result["predictedDisease"], "confidencePct": result["confidencePct"]},
        )
        trained_bundle = MODEL_ENGINE.model
        return {
            "message": "Disease analysis completed.",
            "result": result,
            "demoMode": not (
                isinstance(trained_bundle, dict)
                and trained_bundle.get("kind") == "plant_disease_folders_v1"
            ),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Unable to process crop image: {str(exc)}") from exc


@app.get("/api/disease/history/{image_id}/image")
async def get_disease_history_image(image_id: str, farmer: dict = Depends(require_farmer)):
    stored_image = database.get_disease_image(farmer["id"], image_id)
    if not stored_image:
        raise HTTPException(status_code=404, detail="Disease image was not found in your account.")
    return Response(
        content=stored_image["imageData"],
        media_type=stored_image["mediaType"],
        headers={"Content-Disposition": f"inline; filename*=UTF-8''{quote(stored_image['filename'], safe='')}", "X-Content-Type-Options": "nosniff"},
    )


@app.get("/api/disease/status")
async def disease_status():
    model = MODEL_ENGINE.load_or_train()
    if isinstance(model, dict) and model.get("kind") == "plant_disease_folders_v1":
        classifier = model["classifier"]
        return {
            "status": "ready",
            "classes": list(classifier.classes_),
            "demoMode": False,
            "datasetImages": model["dataset_images"],
            "classCounts": model["class_counts"],
            "testAccuracy": model.get("test_accuracy") or model["validation_accuracy"],
        }
    return {
        "status": "ready",
        "classes": list(model.classes_),
        "demoMode": True,
        "datasetImages": 0,
        "notice": "Synthetic demonstration model only; download PlantVillage and train the real image-folder model.",
    }


@app.get("/{page_name}", response_class=HTMLResponse)
async def application_page(page_name: str, request: Request):
    pages = {
        "login", "register", "dashboard", "farm", "recommendations", "disease",
        "weather", "satellite", "yield", "threats", "history", "reports", "settings",
    }
    if page_name not in pages:
        raise HTTPException(status_code=404, detail="Page not found.")
    return templates.TemplateResponse(request, "index.html")
