from __future__ import annotations

import math
import os
from datetime import date, timedelta
from typing import Any

import httpx

TIMEOUT = httpx.Timeout(18.0, connect=6.0)
MARKET_RESOURCE_ID = os.getenv("DATA_GOV_IN_MARKET_RESOURCE_ID", "9ef84268-d588-465a-a308-a864a43d0070")


class ProviderUnavailable(RuntimeError):
    pass


def configured_status() -> dict[str, str]:
    return {
        "googleOAuth": "configured" if os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET") else "needs_credentials",
        "smsOtp": "configured" if all(os.getenv(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_VERIFY_SERVICE_SID")) else "needs_credentials",
        "sentinelHub": "configured" if os.getenv("SENTINELHUB_CLIENT_ID") and os.getenv("SENTINELHUB_CLIENT_SECRET") else "needs_credentials",
        "marketPrices": "configured" if os.getenv("DATA_GOV_IN_API_KEY") else "needs_api_key",
    }


async def start_phone_verification(phone: str) -> dict[str, Any]:
    sid, token, service = (os.getenv(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_VERIFY_SERVICE_SID"))
    if not all((sid, token, service)):
        raise ProviderUnavailable("Phone OTP is not configured. Add Twilio Verify credentials to the server environment.")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, auth=(sid, token)) as client:
            response = await client.post(
                f"https://verify.twilio.com/v2/Services/{service}/Verifications",
                data={"To": phone, "Channel": "sms"},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderUnavailable("Twilio could not send the verification code. Check the phone number and Verify service.") from exc
    return {"status": data.get("status", "pending"), "channel": data.get("channel", "sms"), "to": data.get("to")}


async def check_phone_verification(phone: str, code: str) -> bool:
    sid, token, service = (os.getenv(k) for k in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_VERIFY_SERVICE_SID"))
    if not all((sid, token, service)):
        raise ProviderUnavailable("Phone OTP is not configured. Add Twilio Verify credentials to the server environment.")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, auth=(sid, token)) as client:
            response = await client.post(
                f"https://verify.twilio.com/v2/Services/{service}/VerificationCheck",
                data={"To": phone, "Code": code},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderUnavailable("Twilio could not verify the code. Please request a new code.") from exc
    return data.get("status") == "approved"


async def exchange_google_code(code: str, redirect_uri: str) -> dict[str, Any]:
    client_id, client_secret = os.getenv("GOOGLE_CLIENT_ID"), os.getenv("GOOGLE_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ProviderUnavailable("Google sign-in is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={"code": code, "client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri, "grant_type": "authorization_code"},
                headers={"Accept": "application/json"},
            )
            token_response.raise_for_status()
            token_data = token_response.json()
            profile_response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            profile_response.raise_for_status()
            profile = profile_response.json()
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise ProviderUnavailable("Google sign-in could not be completed. Check OAuth redirect URI and client configuration.") from exc
    if not profile.get("email") or not profile.get("email_verified"):
        raise ProviderUnavailable("Google did not return a verified email address.")
    return profile


async def fetch_sentinel_ndvi(latitude: float, longitude: float) -> dict[str, Any]:
    client_id, client_secret = os.getenv("SENTINELHUB_CLIENT_ID"), os.getenv("SENTINELHUB_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise ProviderUnavailable("Satellite NDVI is not configured. Add Sentinel Hub client credentials.")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            auth = await client.post(
                "https://services.sentinel-hub.com/auth/realms/main/protocol/openid-connect/token",
                data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
            )
            auth.raise_for_status()
            access_token = auth.json()["access_token"]
            delta = 0.00012
            body = {
                "input": {
                    "bounds": {"bbox": [longitude-delta, latitude-delta, longitude+delta, latitude+delta], "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
                    "data": [{"type": "sentinel-2-l2a", "dataFilter": {"timeRange": {"from": (date.today()-timedelta(days=45)).isoformat()+"T00:00:00Z", "to": date.today().isoformat()+"T23:59:59Z"}, "maxCloudCoverage": 35}}],
                },
                "evalscript": "//VERSION=3\nfunction setup(){return {input:[{bands:[\"B04\",\"B08\",\"dataMask\"]}],output:{bands:2,sampleType:\"FLOAT32\"}}}\nfunction evaluatePixel(s){if(s.dataMask===0)return [-9999,0];let d=(s.B08+s.B04)===0?0:(s.B08-s.B04)/(s.B08+s.B04);return [d,1]}",
                "output": {"width": 1, "height": 1, "responses": [{"identifier": "default", "format": {"type": "application/json"}}]},
            }
            response = await client.post("https://services.sentinel-hub.com/api/v1/process", json=body, headers={"Authorization": f"Bearer {access_token}"})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise ProviderUnavailable("Sentinel Hub did not return a usable NDVI sample. Check subscription, quota, and imagery availability.") from exc
    # JSON output may expose band statistics or direct sample arrays depending on the Sentinel Hub response.
    data_items = payload.get("data") or []
    ndvi = None
    if isinstance(data_items, list) and data_items:
        bands = data_items[0].get("bands", {}) if isinstance(data_items[0], dict) else {}
        band_zero = bands.get("B0", {}) if isinstance(bands, dict) else {}
        stats = band_zero.get("stats", {}) if isinstance(band_zero, dict) else {}
        if isinstance(stats.get("mean"), (int, float)):
            ndvi = float(stats["mean"])
        elif isinstance(band_zero.get("sample"), (int, float)):
            ndvi = float(band_zero["sample"])
    if ndvi is None:
        values = payload.get("default") or payload.get("data") or []
        if isinstance(values, list) and values and isinstance(values[0], (int, float)):
            ndvi = float(values[0])
        elif isinstance(payload.get("data"), dict):
            ndvi = payload["data"].get("ndvi")
    if ndvi is None:
        raise ProviderUnavailable("Sentinel Hub response contained no NDVI sample for this farm point.")
    return {"ndvi": round(ndvi, 3), "source": "Sentinel Hub Sentinel-2 L2A", "retrievedAt": date.today().isoformat(), "windowDays": 45, "cloudCoverageMaxPercent": 35, "coordinates": {"latitude": latitude, "longitude": longitude}, "notice": "Single farm-point sample; cloud filtering and a 45-day search window apply. Not a whole-field average."}


async def fetch_market_prices(state: str, district: str, commodity: str, limit: int = 10) -> dict[str, Any]:
    api_key = os.getenv("DATA_GOV_IN_API_KEY")
    if not api_key:
        raise ProviderUnavailable("Live mandi prices need a data.gov.in API key. Set DATA_GOV_IN_API_KEY on the server.")
    params = {
        "api-key": api_key,
        "format": "json",
        "limit": max(1, min(limit, 50)),
        "filters[State]": state,
        "filters[District]": district,
        "filters[Commodity]": commodity,
    }
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.get(f"https://api.data.gov.in/resource/{MARKET_RESOURCE_ID}", params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderUnavailable("The data.gov.in mandi-price service did not return usable data. Verify the API key and resource access.") from exc
    records = []
    for row in payload.get("records", []):
        try:
            records.append({
                "market": row.get("Market"),
                "commodity": row.get("Commodity"),
                "variety": row.get("Variety"),
                "arrivalDate": row.get("Arrival_Date"),
                "minPriceRsPerQuintal": float(row["Min_Price"]),
                "maxPriceRsPerQuintal": float(row["Max_Price"]),
                "modalPriceRsPerQuintal": float(row["Modal_Price"]),
                "unit": "INR/quintal",
            })
        except (KeyError, TypeError, ValueError):
            continue
    return {"source": "data.gov.in Agmarknet mandi prices", "sourceUrl": "https://data.gov.in/", "state": state, "district": district, "commodity": commodity, "records": records, "retrievedAt": date.today().isoformat(), "demoMode": False, "notice": "Prices are market-reported arrivals; verify grade, unit, date, and buyer deductions before sale."}


def estimate_yield(farm: dict[str, Any]) -> dict[str, Any]:
    crop = str(farm.get("cropName") or "").strip().lower()
    area = float(farm.get("landArea") or 0)
    unit = str(farm.get("landAreaUnit") or "Acres").lower()
    if not crop or area <= 0:
        raise ValueError("Save a crop and positive farm area before requesting yield estimation.")
    hectares = area if unit.startswith("hect") else area * 0.40468564224
    # Broad, explicitly provisional reference ranges (tonnes/ha), not a locally trained yield model.
    ranges = {
        "rice": (2.0, 5.0), "paddy": (2.0, 5.0), "wheat": (2.0, 4.5), "maize": (2.0, 5.5),
        "ragi": (0.8, 2.0), "finger millet": (0.8, 2.0), "jowar": (0.7, 1.8), "bajra": (0.8, 2.0),
        "cotton": (1.0, 2.5), "groundnut": (1.0, 2.5), "soybean": (0.8, 2.2),
        "sugarcane": (60.0, 100.0), "tomato": (20.0, 45.0), "potato": (15.0, 30.0),
        "onion": (15.0, 30.0), "chilli": (1.0, 3.0), "banana": (25.0, 45.0),
    }
    if crop not in ranges:
        raise ValueError(f"No reference yield range is available for {farm.get('cropName')}. Add a verified crop-specific benchmark first.")
    low, high = ranges[crop]
    midpoint = (low + high) / 2
    adjustment = 1.0
    factors = []
    irrigation = str(farm.get("irrigationType") or "").lower()
    if irrigation and "rainfed" not in irrigation:
        adjustment *= 1.08
        factors.append("irrigation method recorded; modest planning adjustment applied")
    elif "rainfed" in irrigation:
        adjustment *= 0.92
        factors.append("rainfed crop; weather variability may affect output")
    stage = str(farm.get("cropStage") or "").lower()
    if any(term in stage for term in ("stress", "drought", "disease")):
        adjustment *= 0.8
        factors.append("farmer-recorded crop stress lowers the planning estimate")
    soil_ph = farm.get("soilPh")
    if isinstance(soil_ph, (int, float)) and not 5.5 <= float(soil_ph) <= 7.5:
        adjustment *= 0.93
        factors.append("recorded soil pH is outside the broad neutral range")
    predicted = midpoint * adjustment * hectares
    return {
        "crop": farm["cropName"], "farmArea": area, "farmAreaUnit": farm.get("landAreaUnit") or "Acres",
        "areaHectares": round(hectares, 3), "lowEstimateTonnes": round(low * adjustment * hectares, 2),
        "expectedEstimateTonnes": round(predicted, 2), "highEstimateTonnes": round(high * adjustment * hectares, 2),
        "yieldRangeTonnesPerHectare": [low, high], "method": "Transparent reference-range calculation",
        "confidence": "Low - indicative only", "factors": factors,
        "notice": "This is not a trained or district-calibrated yield prediction. It scales a broad crop reference range by farm area and limited farmer-entered factors. For a reliable forecast, train and validate against multi-year district, variety, sowing-date, soil, irrigation, and actual harvest records.",
    }
