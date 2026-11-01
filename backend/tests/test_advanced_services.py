from backend.app.advanced_services import configured_status, estimate_yield
from backend.app.integrations import analyze_weather_threats


def test_yield_estimate_scales_area_and_marks_low_confidence():
    result = estimate_yield({
        "cropName": "Ragi",
        "landArea": 2,
        "landAreaUnit": "Acres",
        "irrigationType": "Drip Irrigation",
        "cropStage": "Flowering",
        "soilPh": 6.5,
    })
    assert result["areaHectares"] == 0.809
    assert result["expectedEstimateTonnes"] > 0
    assert result["lowEstimateTonnes"] < result["expectedEstimateTonnes"] < result["highEstimateTonnes"]
    assert result["confidence"].startswith("Low")
    assert "not a trained" in result["notice"]


def test_yield_estimate_rejects_unknown_crop_and_missing_area():
    try:
        estimate_yield({"cropName": "Unknown Crop", "landArea": 1})
        assert False, "Unknown crops must not get invented reference yields."
    except ValueError as exc:
        assert "No reference yield range" in str(exc)

    try:
        estimate_yield({"cropName": "Rice", "landArea": 0})
        assert False, "Missing land area must be rejected."
    except ValueError as exc:
        assert "positive farm area" in str(exc)


def test_provider_status_reports_missing_credentials_without_claiming_live_data():
    status = configured_status()
    assert status["googleOAuth"] in {"configured", "needs_credentials"}
    assert status["smsOtp"] == "disabled"
    assert status["sentinelHub"] in {"configured", "needs_credentials"}
    assert status["marketPrices"] in {"configured", "needs_api_key"}


def test_weather_threat_analysis_reports_risks_from_live_weather_values():
    alerts = analyze_weather_threats({
        "current": {"windSpeedKph": 45, "condition": "Thunderstorm"},
        "forecast": [
            {"date": "2026-11-02", "temperatureMaxC": 41, "temperatureMinC": 2, "rainProbabilityPercent": 75, "rainfallMm": 55},
        ],
    })

    assert {alert["type"] for alert in alerts} == {"thunderstorm", "strong_wind", "heat", "cold", "heavy_rain"}
    assert all(alert["severity"] in {"medium", "high"} for alert in alerts)


def test_weather_threat_analysis_returns_no_alerts_below_thresholds():
    assert analyze_weather_threats({
        "current": {"windSpeedKph": 10},
        "forecast": [
            {"temperatureMaxC": 25, "temperatureMinC": 10, "rainProbabilityPercent": 10, "rainfallMm": 0},
        ],
    }) == []
