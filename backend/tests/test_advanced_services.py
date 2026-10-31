from backend.app.advanced_services import configured_status, estimate_yield


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
