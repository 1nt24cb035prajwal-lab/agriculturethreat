from pathlib import Path

from backend.app.ml_model import CropRecommendationModel


def test_crop_model_trains_from_labelled_csv(tmp_path: Path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    dataset = data_dir / "crop_recommendation.csv"
    rows = ["N,P,K,temperature,humidity,ph,rainfall,label"]
    for index in range(60):
        label = "Rice" if index % 3 == 0 else "Maize" if index % 3 == 1 else "Cotton"
        rows.append(
            f"{70 + index},{40 + index},{35 + index},"
            f"{24 + index % 8},{55 + index % 20},{5.5 + (index % 5) / 10},"
            f"{450 + index * 3},{label}"
        )
    dataset.write_text("\n".join(rows), encoding="utf-8")

    engine = CropRecommendationModel(tmp_path)
    bundle = engine.train_from_csv(dataset)

    assert bundle["dataset_rows"] == 60
    assert bundle["validation_rows"] == 12
    assert set(bundle["crop_classes"]) == {"Rice", "Maize", "Cotton"}
    assert 0 <= bundle["validation_accuracy"] <= 1

    recommendation = engine.recommend({
        "cropName": "Rice",
        "soilType": "Loam",
        "season": "Kharif",
        "latitude": 12.5,
        "longitude": 76.5,
        "temperature": 28,
        "humidity": 68,
        "rainfall": 750,
        "nitrogen": 90,
        "phosphorus": 50,
        "potassium": 40,
        "soilPh": 6.5,
    })
    assert recommendation["crop"] in {"Rice", "Maize", "Cotton"}
    assert "60 labelled rows" in recommendation["datasetNotice"]
