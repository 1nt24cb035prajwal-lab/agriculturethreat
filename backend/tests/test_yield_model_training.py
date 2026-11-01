import csv
from pathlib import Path

import pytest

from backend.app.yield_model import YieldPredictionModel


def test_yield_model_trains_all_crops_and_evaluates_later_years(tmp_path: Path):
    dataset = tmp_path / "india_crop_production.csv"
    with dataset.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["State_Name", "District_Name", "Crop_Year", "Season", "Crop", "Area", "Production"])
        for year in range(2010, 2016):
            for crop, base_yield in (("Rice", 4.0), ("Maize", 3.0)):
                for index in range(30):
                    area = 1 + index % 8
                    yield_per_hectare = base_yield + (year - 2010) * 0.1 + (index % 3) * 0.05
                    writer.writerow([
                        "Karnataka",
                        "Mysuru" if index % 2 else "Mandya",
                        year,
                        "Kharif",
                        crop,
                        area,
                        area * yield_per_hectare,
                    ])

    model = YieldPredictionModel(tmp_path)
    bundle = model.train_from_csv(dataset)

    assert bundle["class_count"] == 2
    assert bundle["metrics"]["validationYears"][0] > bundle["validation_training_years"][1]
    assert bundle["metrics"]["validationRows"] > 0
    assert 0 <= bundle["metrics"]["within25PercentPercent"] <= 100

    prediction = model.predict({
        "cropName": "Rice",
        "state": "Karnataka",
        "district": "Mysuru",
        "season": "Kharif",
        "landArea": 2,
        "landAreaUnit": "Hectares",
    })
    assert prediction["predictedYieldTonnesPerHectare"] > 0
    assert prediction["expectedEstimateTonnes"] == pytest.approx(
        prediction["predictedYieldTonnesPerHectare"] * 2,
        abs=0.01,
    )
    assert prediction["modelMetrics"] == bundle["metrics"]

    old_year_prediction = model.predict({
        "cropName": "Rice",
        "state": "Karnataka",
        "district": "Mysuru",
        "season": "Kharif",
        "cropYear": 1980,
        "landArea": 2,
        "landAreaUnit": "Hectares",
    })
    assert old_year_prediction["predictionYear"] == bundle["years"][0]
    assert "outside the dataset range" in old_year_prediction["notice"]

    with pytest.raises(ValueError, match="positive farm area"):
        model.predict({
            "cropName": "Rice",
            "state": "Karnataka",
            "landArea": float("nan"),
        })


def test_yield_model_rejects_crops_without_observed_training_records(tmp_path: Path):
    dataset = tmp_path / "india_crop_production.csv"
    with dataset.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["State_Name", "District_Name", "Crop_Year", "Season", "Crop", "Area", "Production"])
        for year in range(2010, 2016):
            for index in range(40):
                writer.writerow(["Karnataka", "Mysuru", year, "Kharif", "Rice", 1 + index, 4 * (1 + index)])
    model = YieldPredictionModel(tmp_path)
    model.train_from_csv(dataset)

    with pytest.raises(ValueError, match="No yield training records"):
        model.predict({
            "cropName": "Unknown Crop",
            "state": "Karnataka",
            "landArea": 1,
        })
