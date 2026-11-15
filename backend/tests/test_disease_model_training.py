from pathlib import Path
from io import BytesIO
import zipfile

from PIL import Image

from backend.app.ml_model import PlantDiseaseModel
from backend.scripts.train_disease_model import REFERENCE_IMAGE_LABELS, load_reference_images


def test_disease_model_trains_from_class_labelled_image_folders(tmp_path: Path):
    dataset = tmp_path / "data" / "labeled_diseases"
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
    assert engine._extract_image_features(Image.new("RGB", (64, 64))).shape == (240,)
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


def test_reference_archive_builds_similarity_model_without_claiming_confidence(tmp_path: Path):
    archive_path = tmp_path / "references.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        for index, (filename, label) in enumerate(REFERENCE_IMAGE_LABELS.items()):
            image = Image.new("RGB", (48, 48), color=(index * 22, 240 - index * 19, 40 + index * 17))
            buffer = BytesIO()
            image_format = {".png": "PNG", ".jpg": "JPEG", ".webp": "WEBP"}[
                Path(filename).suffix.lower()
            ]
            image.save(buffer, format=image_format)
            archive.writestr(f"dataset_@/{filename}", buffer.getvalue())

    reference_images = load_reference_images(archive_path)
    engine = PlantDiseaseModel(tmp_path)
    bundle = engine.train_from_reference_images(reference_images)
    prediction = engine.predict(reference_images["Maize___Banded_Leaf_and_Sheath_Blight"])

    assert bundle["kind"] == "plant_disease_reference_v1"
    assert bundle["dataset_images"] == 10
    assert prediction["predictedDisease"] == "Maize — Banded Leaf and Sheath Blight"
    assert prediction["detectedCrop"] == "Maize"
    assert prediction["scoreType"] == "reference_similarity"
    assert prediction["similarityPct"] == 100
    assert prediction["confidencePct"] is None
    assert "not diagnostic confidence" in prediction["confidenceStatus"]
    assert "not diagnostic confidence or measured accuracy" in prediction["warning"]
