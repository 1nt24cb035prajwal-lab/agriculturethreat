from pathlib import Path

from PIL import Image

from backend.app.ml_model import PlantDiseaseModel


def test_disease_model_trains_from_class_labelled_image_folders(tmp_path: Path):
    dataset = tmp_path / "data" / "plant_disease"
    healthy = dataset / "Healthy"
    blight = dataset / "Tomato___Early_blight"
    healthy.mkdir(parents=True)
    blight.mkdir(parents=True)

    for index in range(20):
        Image.new("RGB", (64, 64), color=(40 + index, 180, 50)).save(healthy / f"healthy_{index}.png")
        Image.new("RGB", (64, 64), color=(180, 40 + index, 30)).save(blight / f"blight_{index}.png")

    engine = PlantDiseaseModel(tmp_path)
    bundle = engine.train_from_directory(dataset)

    assert bundle["dataset_images"] == 40
    assert bundle["validation_images"] == 8
    assert bundle["class_counts"] == {"Healthy": 20, "Tomato___Early_blight": 20}
    assert 0 <= bundle["macro_f1"] <= 1
    assert engine._extract_plantvillage_features(Image.new("RGB", (64, 64))).shape == (240,)
    engine._analyze_with_gemini = lambda image, crop_name=None: {
        "disease_name": "Early blight",
        "confidence_level": "medium",
        "severity": "Moderate",
        "symptoms": "Dark leaf spots are visible.",
        "treatment": "Remove affected leaves and seek local crop advice.",
        "prevention": "Avoid prolonged leaf wetness.",
        "affected_parts": ["Leaves"],
        "alternatives": ["Nutrient stress"],
        "farmer_note": "Confirm before spraying.",
    }
    prediction = engine.predict(Image.new("RGB", (64, 64), color=(50, 180, 50)), crop_name="Tomato")
    assert prediction["detectedCrop"] == "Tomato"
    assert prediction["diseaseName"]
    assert prediction["predictionStatus"] in {"prediction", "needs_review"}
    assert len(prediction["topPredictions"]) == 1
    assert "modelMetrics" not in prediction
    assert "labelled images" not in prediction["warning"]
    assert "accuracy" not in prediction["warning"]
