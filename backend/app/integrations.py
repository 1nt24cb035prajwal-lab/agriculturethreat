from __future__ import annotations

import httpx

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_SEARCH_URL = "https://nominatim.openstreetmap.org/search"
HTTP_TIMEOUT = httpx.Timeout(8.0, connect=4.0)


class ProviderUnavailable(Exception):
    pass


def _weather_code_description(code: int) -> str:
    if code == 0:
        return "Clear sky"
    if code in {1, 2, 3}:
        return "Mainly clear to overcast"
    if code in {45, 48}:
        return "Fog"
    if code in {51, 53, 55, 56, 57}:
        return "Drizzle"
    if code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "Rain"
    if code in {71, 73, 75, 77, 85, 86}:
        return "Snow"
    if code in {95, 96, 99}:
        return "Thunderstorm"
    return "Unknown conditions"


async def fetch_weather(latitude: float, longitude: float) -> dict:
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,cloud_cover,weather_code",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,precipitation_sum,et0_fao_evapotranspiration",
        "timezone": "auto",
        "forecast_days": 7,
    }
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": "AgricultureThreatFusion/1.0 (farm weather lookup)"}) as client:
            response = await client.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderUnavailable("Open-Meteo weather service did not return usable data.") from exc

    current = payload.get("current") or {}
    daily = payload.get("daily") or {}
    required_current = ("temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m", "weather_code")
    if any(current.get(key) is None for key in required_current):
        raise ProviderUnavailable("Open-Meteo returned an incomplete current-weather record.")

    forecast = []
    day_count = len(daily.get("time") or [])
    for index in range(day_count):
        forecast.append({
            "date": daily["time"][index],
            "condition": _weather_code_description(int(daily["weather_code"][index])),
            "temperatureMaxC": daily["temperature_2m_max"][index],
            "temperatureMinC": daily["temperature_2m_min"][index],
            "rainProbabilityPercent": daily["precipitation_probability_max"][index],
            "rainfallMm": daily["precipitation_sum"][index],
            "referenceEvapotranspirationMm": (daily.get("et0_fao_evapotranspiration") or [None] * day_count)[index],
        })

    return {
        "source": "Open-Meteo",
        "sourceUrl": "https://open-meteo.com/",
        "timezone": payload.get("timezone"),
        "coordinates": {"latitude": payload.get("latitude"), "longitude": payload.get("longitude")},
        "current": {
            "temperatureC": current["temperature_2m"],
            "feelsLikeC": current.get("apparent_temperature"),
            "humidityPercent": current["relative_humidity_2m"],
            "rainfallMm": current["precipitation"],
            "windSpeedKph": current["wind_speed_10m"],
            "cloudCoverPercent": current.get("cloud_cover"),
            "condition": _weather_code_description(int(current["weather_code"])),
            "observedAt": current.get("time"),
        },
        "forecast": forecast,
        "retrievedAt": current.get("time"),
        "demoMode": False,
    }


async def reverse_geocode(latitude: float, longitude: float) -> dict:
    params = {"lat": latitude, "lon": longitude, "format": "jsonv2", "addressdetails": 1, "zoom": 18}
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": "AgricultureThreatFusion/1.0 (farm location lookup)"}) as client:
            response = await client.get(NOMINATIM_REVERSE_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderUnavailable("OpenStreetMap location lookup is temporarily unavailable.") from exc

    address = payload.get("address") or {}
    return {
        "displayName": payload.get("display_name", ""),
        "village": address.get("village") or address.get("hamlet") or address.get("town") or address.get("suburb") or "",
        "taluk": address.get("county") or address.get("municipality") or address.get("subdistrict") or "",
        "district": address.get("state_district") or address.get("district") or "",
        "state": address.get("state") or "",
        "country": address.get("country") or "",
        "coordinates": {"latitude": latitude, "longitude": longitude},
        "source": "OpenStreetMap Nominatim",
        "demoMode": False,
    }


async def search_location(query: str) -> list[dict]:
    params = {"q": query, "format": "jsonv2", "addressdetails": 1, "limit": 5}
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, headers={"User-Agent": "AgricultureThreatFusion/1.0 (farm location search)"}) as client:
            response = await client.get(NOMINATIM_SEARCH_URL, params=params)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderUnavailable("OpenStreetMap place search is temporarily unavailable.") from exc

    results = []
    for item in payload:
        address = item.get("address") or {}
        results.append({
            "displayName": item.get("display_name", ""),
            "latitude": float(item["lat"]),
            "longitude": float(item["lon"]),
            "village": address.get("village") or address.get("town") or address.get("suburb") or "",
            "district": address.get("state_district") or address.get("district") or "",
            "state": address.get("state") or "",
        })
    return results
