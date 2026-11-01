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


def analyze_weather_threats(weather: dict) -> list[dict]:
    current = weather.get("current") or {}
    forecast = weather.get("forecast") or []
    alerts = []

    if current.get("condition") == "Thunderstorm":
        alerts.append({
            "type": "thunderstorm",
            "severity": "high",
            "title": "Thunderstorm conditions",
            "detail": "A thunderstorm is reported at the farm location. Follow local warnings and avoid exposed field work.",
        })

    wind_speed = current.get("windSpeedKph")
    if isinstance(wind_speed, (int, float)) and wind_speed >= 60:
        alerts.append({
            "type": "strong_wind",
            "severity": "high",
            "title": "Very strong wind",
            "detail": f"Current wind is {wind_speed} km/h. Secure light structures and check exposed crops.",
        })
    elif isinstance(wind_speed, (int, float)) and wind_speed >= 40:
        alerts.append({
            "type": "strong_wind",
            "severity": "medium",
            "title": "Strong wind",
            "detail": f"Current wind is {wind_speed} km/h. Monitor tall or exposed crops.",
        })

    temperatures = [
        day.get("temperatureMaxC")
        for day in forecast
        if isinstance(day.get("temperatureMaxC"), (int, float))
    ]
    max_temperature = max(temperatures, default=None)
    if max_temperature is not None and max_temperature >= 40:
        alerts.append({
            "type": "heat",
            "severity": "high",
            "title": "Very high temperature forecast",
            "detail": f"A forecast high of {max_temperature}°C may increase crop heat stress. Check irrigation and local advisories.",
        })
    elif max_temperature is not None and max_temperature >= 35:
        alerts.append({
            "type": "heat",
            "severity": "medium",
            "title": "High temperature forecast",
            "detail": f"A forecast high of {max_temperature}°C may increase crop heat stress. Monitor soil moisture.",
        })

    minimum_temperatures = [
        day.get("temperatureMinC")
        for day in forecast
        if isinstance(day.get("temperatureMinC"), (int, float))
    ]
    min_temperature = min(minimum_temperatures, default=None)
    if min_temperature is not None and min_temperature <= 0:
        alerts.append({
            "type": "cold",
            "severity": "high",
            "title": "Freezing temperature forecast",
            "detail": f"A forecast low of {min_temperature}°C may damage sensitive crops. Check local crop-protection guidance.",
        })
    elif min_temperature is not None and min_temperature <= 3:
        alerts.append({
            "type": "cold",
            "severity": "medium",
            "title": "Low temperature forecast",
            "detail": f"A forecast low of {min_temperature}°C may affect sensitive crops. Monitor local conditions.",
        })

    heavy_rain_days = [
        day for day in forecast
        if isinstance(day.get("rainProbabilityPercent"), (int, float))
        and isinstance(day.get("rainfallMm"), (int, float))
        and day["rainProbabilityPercent"] >= 70
        and day["rainfallMm"] >= 50
    ]
    if heavy_rain_days:
        day = max(heavy_rain_days, key=lambda item: item["rainfallMm"])
        alerts.append({
            "type": "heavy_rain",
            "severity": "high",
            "title": "Heavy rain forecast",
            "detail": f"{day['rainfallMm']} mm of rain is forecast for {day.get('date', 'an upcoming day')} with a {day['rainProbabilityPercent']}% chance. Check drainage and local warnings.",
        })
    else:
        rain_days = [
            day for day in forecast
            if isinstance(day.get("rainProbabilityPercent"), (int, float))
            and isinstance(day.get("rainfallMm"), (int, float))
            and day["rainProbabilityPercent"] >= 60
            and day["rainfallMm"] >= 25
        ]
        if rain_days:
            day = max(rain_days, key=lambda item: item["rainfallMm"])
            alerts.append({
                "type": "rain",
                "severity": "medium",
                "title": "Rain forecast",
                "detail": f"{day['rainfallMm']} mm of rain is forecast for {day.get('date', 'an upcoming day')} with a {day['rainProbabilityPercent']}% chance. Plan field work accordingly.",
            })

    return alerts


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
