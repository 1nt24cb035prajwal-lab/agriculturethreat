from __future__ import annotations

import csv
import json
from pathlib import Path

import joblib
import numpy as np
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline


LABELS = ["Healthy", "Leaf Spot", "Rust", "Blight", "Mosaic"]
DISEASE_INFO = {
    "Healthy": {
        "severity": "Low",
        "symptoms": "No visible disease symptoms detected.",
        "treatment": "Continue regular irrigation and crop health monitoring.",
        "prevention": "Maintain balanced nutrition and monitor pest activity.",
    },
    "Leaf Spot": {
        "severity": "Moderate",
        "symptoms": "Small circular lesions with yellow halos on leaves.",
        "treatment": "Apply a recommended fungicide and remove severely infected leaves.",
        "prevention": "Improve spacing, avoid overhead watering, and mulch affected debris.",
    },
    "Rust": {
        "severity": "High",
        "symptoms": "Orange-brown pustules and leaf yellowing.",
        "treatment": "Use disease-resistant varieties and apply protective fungicide early.",
        "prevention": "Reduce high humidity, improve airflow, and avoid excess nitrogen.",
    },
    "Blight": {
        "severity": "High",
        "symptoms": "Dark lesions with rapid spreading patterns on leaves and stems.",
        "treatment": "Spray targeted fungicide and quarantine infected plants.",
        "prevention": "Early scouting and field sanitation reduce spread.",
    },
    "Mosaic": {
        "severity": "Moderate",
        "symptoms": "Mottled light and dark patterns on leaves.",
        "treatment": "Remove infected crops and monitor vector control.",
        "prevention": "Use clean seed and maintain insect control around field edges.",
    },
}


CROP_RECOMMENDATION_DATA = [
    {"crop": "Rice", "state": "Karnataka", "district": "Mysuru", "soilType": "Black Soil", "season": "Kharif", "temperature": 29, "humidity": 74, "rainfall": 1200, "latitude": 12.3, "longitude": 76.6},
    {"crop": "Rice", "state": "Tamil Nadu", "district": "Thanjavur", "soilType": "Clay Loam", "season": "Kharif", "temperature": 31, "humidity": 72, "rainfall": 1100, "latitude": 10.8, "longitude": 79.1},
    {"crop": "Maize", "state": "Karnataka", "district": "Bellary", "soilType": "Red Soil", "season": "Rabi", "temperature": 28, "humidity": 64, "rainfall": 650, "latitude": 15.1, "longitude": 76.9},
    {"crop": "Maize", "state": "Maharashtra", "district": "Nashik", "soilType": "Loam", "season": "Kharif", "temperature": 27, "humidity": 62, "rainfall": 700, "latitude": 20.0, "longitude": 73.8},
    {"crop": "Cotton", "state": "Maharashtra", "district": "Aurangabad", "soilType": "Black Soil", "season": "Kharif", "temperature": 32, "humidity": 58, "rainfall": 550, "latitude": 19.9, "longitude": 75.3},
    {"crop": "Cotton", "state": "Gujarat", "district": "Surendranagar", "soilType": "Sandy Loam", "season": "Kharif", "temperature": 33, "humidity": 55, "rainfall": 500, "latitude": 22.7, "longitude": 71.6},
    {"crop": "Groundnut", "state": "Andhra Pradesh", "district": "Anantapur", "soilType": "Red Soil", "season": "Kharif", "temperature": 30, "humidity": 60, "rainfall": 520, "latitude": 14.7, "longitude": 77.6},
    {"crop": "Groundnut", "state": "Tamil Nadu", "district": "Madurai", "soilType": "Loam", "season": "Rabi", "temperature": 29, "humidity": 62, "rainfall": 560, "latitude": 9.9, "longitude": 78.1},
    {"crop": "Wheat", "state": "Punjab", "district": "Ludhiana", "soilType": "Loam", "season": "Rabi", "temperature": 22, "humidity": 52, "rainfall": 480, "latitude": 30.9, "longitude": 75.8},
    {"crop": "Wheat", "state": "Haryana", "district": "Hisar", "soilType": "Sandy Loam", "season": "Rabi", "temperature": 23, "humidity": 54, "rainfall": 420, "latitude": 29.1, "longitude": 75.7},
    {"crop": "Sugarcane", "state": "Uttar Pradesh", "district": "Muzaffarnagar", "soilType": "Alluvial", "season": "Kharif", "temperature": 31, "humidity": 60, "rainfall": 800, "latitude": 29.4, "longitude": 77.7},
    {"crop": "Sugarcane", "state": "Maharashtra", "district": "Pune", "soilType": "Black Soil", "season": "Kharif", "temperature": 30, "humidity": 58, "rainfall": 760, "latitude": 18.5, "longitude": 73.8},
    {"crop": "Tomato", "state": "Karnataka", "district": "Bengaluru Rural", "soilType": "Red Soil", "season": "Rabi", "temperature": 26, "humidity": 68, "rainfall": 680, "latitude": 13.2, "longitude": 77.7},
    {"crop": "Tomato", "state": "Telangana", "district": "Hyderabad", "soilType": "Loam", "season": "Rabi", "temperature": 25, "humidity": 66, "rainfall": 700, "latitude": 17.4, "longitude": 78.5},
    {"crop": "Chili", "state": "Andhra Pradesh", "district": "Guntur", "soilType": "Black Soil", "season": "Kharif", "temperature": 30, "humidity": 70, "rainfall": 820, "latitude": 16.3, "longitude": 80.4},
    {"crop": "Chili", "state": "Karnataka", "district": "Haveri", "soilType": "Black Soil", "season": "Rabi", "temperature": 28, "humidity": 72, "rainfall": 760, "latitude": 14.8, "longitude": 75.4},
    {"crop": "Potato", "state": "Himachal Pradesh", "district": "Shimla", "soilType": "Loam", "season": "Rabi", "temperature": 18, "humidity": 58, "rainfall": 620, "latitude": 31.1, "longitude": 77.2},
    {"crop": "Potato", "state": "Uttarakhand", "district": "Nainital", "soilType": "Loam", "season": "Rabi", "temperature": 19, "humidity": 60, "rainfall": 640, "latitude": 29.4, "longitude": 79.5},
]

CROP_RECOMMENDATION_INFO = {
    "Rice": {"irrigationAdvice": "Maintain standing water and monitor drainage, especially during vegetative growth.", "fertilizerAdvice": "Apply nitrogen in split doses, then add phosphorus and potassium at transplanting.", "risk": "Moderate fungus risk during humid conditions.", "yieldExpectation": "High yield with proper water timing."},
    "Maize": {"irrigationAdvice": "Use moderate irrigation, avoid waterlogging during tasseling and grain filling.", "fertilizerAdvice": "Apply balanced NPK and supplement zinc where deficiency is observed.", "risk": "Low to moderate stress during flowering.", "yieldExpectation": "Strong yield under warm and well-drained conditions."},
    "Cotton": {"irrigationAdvice": "Schedule irrigation to reduce drought stress early and during boll formation.", "fertilizerAdvice": "Use potassium-rich fertilization and maintain timely nitrogen splits.", "risk": "Moderate pest pressure in dry seasons.", "yieldExpectation": "Good profitability with careful moisture control."},
    "Groundnut": {"irrigationAdvice": "Keep soil moisture moderate; avoid overwatering during pegging.", "fertilizerAdvice": "Use gypsum and phosphorus to strengthen root setup and pod development.", "risk": "Low unless rainfall is uneven.", "yieldExpectation": "Reliable pod yield in warm, sunny conditions."},
    "Wheat": {"irrigationAdvice": "Use controlled irrigation during tillering and grain filling stages.", "fertilizerAdvice": "Apply nitrogen and sulfur in split doses for uniform tillering.", "risk": "Low with cool, dry conditions.", "yieldExpectation": "Stable production in cooler agro-climatic regions."},
    "Sugarcane": {"irrigationAdvice": "Keep irrigation regular with strong water planning due to long crop duration.", "fertilizerAdvice": "Use potash and micronutrients according to soil test recommendations.", "risk": "Moderate water stress if rainfall is low.", "yieldExpectation": "Excellent sugar recovery under adequate moisture.",},
    "Tomato": {"irrigationAdvice": "Apply frequent but moderate irrigation to avoid leaf stress and blossom end rot.", "fertilizerAdvice": "Use phosphorus-rich basal application and micronutrient foliar support.", "risk": "Moderate disease risk in humid weather.", "yieldExpectation": "High-quality fruit yield with canopy control."},
    "Chili": {"irrigationAdvice": "Maintain moderate soil moisture and reduce stress during flowering.", "fertilizerAdvice": "Apply nitrogen in stages along with potassium for fruit quality.", "risk": "Moderate pest and fungal pressure in humidity.", "yieldExpectation": "Good marketable output when rain is well-managed."},
    "Potato": {"irrigationAdvice": "Keep soil evenly moist, especially during tuber bulking.", "fertilizerAdvice": "Balance nitrogen and potash to improve tuber quality and size.", "risk": "Low to moderate disease risk under cool conditions.", "yieldExpectation": "Consistent tuber yield with proper moisture control."},
}


class PlantDiseaseModel:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.model_dir = base_dir / "models"
        self.model_dir.mkdir(exist_ok=True)
        self.model_path = self.model_dir / "plant_disease_model.joblib"
        self.dataset_path = self.model_dir / "plant_disease_dataset.json"
        self.image_dataset_path = base_dir / "data" / "plant_disease"
        self.model = None

    def _build_synthetic_dataset(self):
        rng = np.random.default_rng(42)
        class_centers = {
            "Healthy": np.array([120, 150, 85], dtype=np.float32),
            "Leaf Spot": np.array([166, 128, 103], dtype=np.float32),
            "Rust": np.array([150, 92, 70], dtype=np.float32),
            "Blight": np.array([98, 138, 88], dtype=np.float32),
            "Mosaic": np.array([128, 120, 142], dtype=np.float32),
        }

        samples = []
        for label, center in class_centers.items():
            for _ in range(30):
                offset = rng.normal(0, 22, size=3)
                mean_rgb = np.clip(center + offset, 0, 255)
                std_rgb = np.clip(rng.normal(25, 10, size=3), 5, 90)
                brightness = float(rng.normal(0.55, 0.12))
                contrast = float(rng.normal(0.68, 0.13))
                texture = float(rng.normal(22, 8))
                features = np.concatenate([mean_rgb, std_rgb, [brightness, contrast, texture]])
                samples.append({"label": label, "features": features.astype(float).tolist()})

        self.dataset_path.write_text(json.dumps(samples), encoding="utf-8")
        return samples

    def _load_dataset(self):
        if self.dataset_path.exists():
            data = json.loads(self.dataset_path.read_text(encoding="utf-8"))
            if data and all(len(item.get("features", [])) == 9 for item in data):
                return data
        return self._build_synthetic_dataset()

    def _extract_features(self, image: Image.Image) -> np.ndarray:
        image = image.convert("RGB")
        arr = np.asarray(image.resize((64, 64)), dtype=np.float32)
        mean = arr.mean(axis=(0, 1))
        std = arr.std(axis=(0, 1))
        brightness = float(arr.mean())
        contrast = float(arr.std())
        texture = float(np.mean(np.abs(arr - arr.mean(axis=(0, 1), keepdims=True))))
        features = np.concatenate([mean, std, [brightness, contrast, texture]])
        return features.astype(np.float32)

    def train_from_directory(self, dataset_dir: Path | None = None):
        """Train from class folders, using supplied train/test folders when present."""
        source = Path(dataset_dir or self.image_dataset_path)
        if not source.is_dir():
            raise FileNotFoundError(
                f"Disease image dataset not found: {source}. Download the labelled image dataset first."
            )

        image_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

        def load_class_folders(folder: Path):
            features, labels, counts = [], [], {}
            for class_dir in sorted(path for path in folder.iterdir() if path.is_dir()):
                for image_path in sorted(class_dir.rglob("*")):
                    if image_path.suffix.lower() not in image_extensions:
                        continue
                    try:
                        with Image.open(image_path) as image:
                            features.append(self._extract_features(image))
                        labels.append(class_dir.name)
                        counts[class_dir.name] = counts.get(class_dir.name, 0) + 1
                    except (OSError, ValueError) as exc:
                        raise ValueError(f"Unable to read disease image: {image_path}") from exc
            if not features:
                raise ValueError(f"No labelled images found under {folder}")
            return np.vstack(features), np.asarray(labels), counts

        train_dir = source / "train"
        test_dir = source / "test"
        if train_dir.is_dir() and test_dir.is_dir():
            X_train, y_train, train_counts = load_class_folders(train_dir)
            X_test, y_test, test_counts = load_class_folders(test_dir)
            if set(train_counts) != set(test_counts):
                raise ValueError("Training and test folders must contain the same disease classes.")
            if min(train_counts.values()) < 2 or min(test_counts.values()) < 1:
                raise ValueError("Each disease class needs at least two train images and one test image.")
            class_counts = {
                label: train_counts[label] + test_counts[label]
                for label in sorted(train_counts)
            }
            split_strategy = "provided_train_test_split"
        else:
            X, y, class_counts = load_class_folders(source)
            if len(X) < 30 or len(class_counts) < 2:
                raise ValueError("Use at least 30 labelled images across at least two disease classes.")
            if min(class_counts.values()) < 2:
                raise ValueError("Each disease class needs at least two images for stratified validation.")
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            split_strategy = "stratified_random_80_20"

        if len(X_train) < 30 or len(set(y_train)) < 2 or len(set(y_test)) < 2:
            raise ValueError("The disease train/test split must contain at least two classes and enough images.")

        classifier = RandomForestClassifier(
            n_estimators=300,
            random_state=42,
            class_weight="balanced",
            min_samples_leaf=2,
            n_jobs=-1,
        )
        classifier.fit(X_train, y_train)
        accuracy = float(accuracy_score(y_test, classifier.predict(X_test)))
        bundle = {
            "kind": "plant_disease_folders_v1",
            "classifier": classifier,
            "dataset_path": source.name,
            "dataset_images": int(len(X_train) + len(X_test)),
            "class_counts": class_counts,
            "validation_accuracy": accuracy,
            "validation_images": int(len(y_test)),
            "test_accuracy": accuracy if split_strategy == "provided_train_test_split" else None,
            "test_images": int(len(y_test)) if split_strategy == "provided_train_test_split" else None,
            "split_strategy": split_strategy,
        }
        joblib.dump(bundle, self.model_path)
        self.model = bundle
        return bundle

    def train(self):
        if self.image_dataset_path.is_dir():
            return self.train_from_directory(self.image_dataset_path)
        dataset = self._load_dataset()
        X = []
        y = []

        for item in dataset:
            X.append(np.asarray(item["features"], dtype=np.float32))
            y.append(item["label"])

        X = np.vstack(X)
        y = np.array(y)

        model = RandomForestClassifier(
            n_estimators=180,
            random_state=42,
            class_weight="balanced",
        )
        model.fit(X, y)
        joblib.dump(model, self.model_path)
        self.model = model
        return model

    def load_or_train(self):
        if self.model is not None:
            return self.model
        if self.image_dataset_path.is_dir():
            if not self.model_path.exists() or max(
                (path.stat().st_mtime for path in self.image_dataset_path.rglob("*") if path.is_file()),
                default=0,
            ) > self.model_path.stat().st_mtime:
                return self.train_from_directory(self.image_dataset_path)
        if self.model_path.exists():
            self.model = joblib.load(self.model_path)
            if isinstance(self.model, dict) and self.model.get("kind") == "plant_disease_folders_v1":
                return self.model
            if getattr(self.model, "n_features_in_", None) == 9:
                return self.model
            self.model = None
        return self.train()

    def predict(self, image: Image.Image):
        loaded = self.load_or_train()
        if isinstance(loaded, dict) and loaded.get("kind") == "plant_disease_folders_v1":
            model = loaded["classifier"]
            score_name = (
                "test accuracy"
                if loaded.get("split_strategy") == "provided_train_test_split"
                else "validation accuracy"
            )
            warning = (
                f"Prototype image model trained on {loaded['dataset_images']} labelled images; "
                f"held-out {score_name} {loaded['validation_accuracy']:.1%}. "
                "This dataset score is not a field diagnosis; confirm with an agricultural expert."
            )
        else:
            model = loaded
            warning = "Prototype classifier trained on synthetic samples; this is not a diagnosis. Confirm with a local agronomist."
        features = self._extract_features(image).reshape(1, -1)
        probabilities = model.predict_proba(features)[0]
        label = str(model.classes_[int(np.argmax(probabilities))])
        confidence = float(np.max(probabilities))

        info = DISEASE_INFO.get(label, {
            "severity": "Needs expert review",
            "symptoms": "The image model matched this dataset class; verify symptoms in the field.",
            "treatment": "Do not apply pesticide based only on this model output. Confirm the disease with a local agricultural expert.",
            "prevention": "Use field scouting, clean tools, and locally recommended integrated pest management.",
        })

        return {
            "predictedDisease": label,
            "confidence": round(confidence, 3),
            "confidencePct": int(confidence * 100),
            "severity": info["severity"],
            "symptoms": info["symptoms"],
            "treatment": info["treatment"],
            "prevention": info["prevention"],
            "affectedCropParts": ["Leaves", "Stem"] if label != "Healthy" else ["Whole plant"],
            "warning": warning,
        }


class CropRecommendationModel:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.model_dir = base_dir / "models"
        self.model_dir.mkdir(exist_ok=True)
        self.model_path = self.model_dir / "crop_recommendation_model.joblib"
        self.dataset_path = self.model_dir / "crop_recommendation_dataset.json"
        self.csv_dataset_path = base_dir / "data" / "crop_recommendation.csv"
        self.model = None

    def _build_dataset(self):
        rows = []
        for item in CROP_RECOMMENDATION_DATA:
            rows.append(
                {
                    "crop": item["crop"],
                    "features": [
                        float(item["temperature"]),
                        float(item["humidity"]),
                        float(item["rainfall"]),
                        self._soil_code(item["soilType"]),
                        self._season_code(item["season"]),
                        float(item["latitude"]),
                        float(item["longitude"]),
                    ],
                }
            )

        self.dataset_path.write_text(json.dumps(rows), encoding="utf-8")
        return rows

    def _load_dataset(self):
        if self.dataset_path.exists():
            stored = json.loads(self.dataset_path.read_text(encoding="utf-8"))
            if stored:
                return stored
        return self._build_dataset()

    def _soil_code(self, soil_type: str) -> int:
        soil_map = {
            "Black Soil": 1,
            "Clay Loam": 2,
            "Red Soil": 3,
            "Loam": 4,
            "Sandy Loam": 5,
            "Alluvial": 6,
        }
        return soil_map.get(str(soil_type or "Loam"), 4)

    def _season_code(self, season: str) -> int:
        season_map = {"Kharif": 1, "Rabi": 2, "Summer": 3, "Monsoon": 1}
        return season_map.get(str(season or "Kharif"), 1)

    def _location_zone(self, latitude: float, longitude: float) -> str:
        if 8 <= latitude <= 13 and 76 <= longitude <= 80:
            return "South India Coastal & Plateau"
        if 13 <= latitude <= 18 and 74 <= longitude <= 81:
            return "Deccan Plateau"
        if latitude >= 19 and longitude <= 78:
            return "Western Dry Zone"
        if latitude >= 28:
            return "North India Plains"
        return "Agro-climatic zone"

    def train_from_csv(self, dataset_path: Path | None = None):
        """Train from a real, labelled crop suitability CSV dataset."""
        source = Path(dataset_path or self.csv_dataset_path)
        if not source.is_file():
            raise FileNotFoundError(
                f"Crop dataset not found: {source}. Add crop_recommendation.csv before training."
            )

        feature_columns = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
        X, y = [], []
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = {str(name).strip().lower(): name for name in (reader.fieldnames or [])}
            required = feature_columns + ["label"]
            missing = [name for name in required if name.lower() not in headers]
            if missing:
                raise ValueError(
                    "Dataset is missing required columns: " + ", ".join(missing)
                )
            for line_number, row in enumerate(reader, start=2):
                try:
                    values = [float(row[headers[name.lower()]]) for name in feature_columns]
                    label = str(row[headers["label"]] or "").strip()
                    if not label:
                        continue
                except (TypeError, ValueError, KeyError) as exc:
                    raise ValueError(
                        f"Invalid numeric feature or crop label on CSV line {line_number}."
                    ) from exc
                X.append(values)
                y.append(label)

        if len(X) < 30 or len(set(y)) < 2:
            raise ValueError("Use at least 30 labelled rows and at least two crop classes.")
        class_counts = {label: y.count(label) for label in set(y)}
        if min(class_counts.values()) < 2:
            raise ValueError("Each crop class needs at least two rows for stratified validation.")

        X_train, X_test, y_train, y_test = train_test_split(
            np.asarray(X, dtype=np.float32),
            np.asarray(y),
            test_size=0.2,
            random_state=42,
            stratify=np.asarray(y),
        )
        pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("classifier", RandomForestClassifier(
                n_estimators=300,
                random_state=42,
                class_weight="balanced",
                min_samples_leaf=2,
            )),
        ])
        pipeline.fit(X_train, y_train)
        accuracy = float(accuracy_score(y_test, pipeline.predict(X_test)))
        bundle = {
            "kind": "crop_csv_v1",
            "pipeline": pipeline,
            "feature_columns": feature_columns,
            "dataset_path": source.name,
            "dataset_rows": len(X),
            "crop_classes": sorted(set(y)),
            "validation_accuracy": accuracy,
            "validation_rows": len(y_test),
        }
        joblib.dump(bundle, self.model_path)
        self.model = bundle
        return bundle

    def train(self):
        if self.csv_dataset_path.is_file():
            return self.train_from_csv(self.csv_dataset_path)
        dataset = self._load_dataset()
        X = []
        y = []
        for item in dataset:
            X.append(np.asarray(item["features"], dtype=np.float32))
            y.append(item["crop"])

        model = RandomForestClassifier(
            n_estimators=220,
            random_state=42,
            class_weight="balanced",
        )
        model.fit(np.vstack(X), np.array(y))
        joblib.dump(model, self.model_path)
        self.model = model
        return model

    def load_or_train(self):
        if self.model is not None:
            return self.model
        if self.csv_dataset_path.is_file():
            if not self.model_path.exists() or self.csv_dataset_path.stat().st_mtime > self.model_path.stat().st_mtime:
                return self.train_from_csv(self.csv_dataset_path)
        if self.model_path.exists():
            self.model = joblib.load(self.model_path)
            return self.model
        return self.train()

    def recommend(self, farmer_profile: dict):
        crop_name = str(farmer_profile.get("cropName") or "Rice").strip() or "Rice"
        soil_type = farmer_profile.get("soilType") or "Loam"
        season = farmer_profile.get("season") or "Kharif"
        latitude = float(farmer_profile.get("latitude") or 12.5)
        longitude = float(farmer_profile.get("longitude") or 76.5)
        rainfall = float(farmer_profile.get("rainfall") or 750)
        humidity = float(farmer_profile.get("humidity") or 68)
        temperature = float(farmer_profile.get("temperature") or 28)

        model = self.load_or_train()
        if isinstance(model, dict) and model.get("kind") == "crop_csv_v1":
            feature_values = [
                farmer_profile.get("nitrogen"),
                farmer_profile.get("phosphorus"),
                farmer_profile.get("potassium"),
                temperature,
                humidity,
                farmer_profile.get("soilPh"),
                rainfall,
            ]
            features = np.asarray([
                [float(value) if value not in (None, "") else np.nan for value in feature_values]
            ], dtype=np.float32)
            probabilities = model["pipeline"].predict_proba(features)[0]
            classes = model["pipeline"].named_steps["classifier"].classes_
            dataset_notice = (
                f"Trained on {model['dataset_rows']} labelled rows from {model['dataset_path']}; "
                f"held-out validation accuracy {model['validation_accuracy']:.1%} "
                f"on {model['validation_rows']} rows. This is a dataset benchmark, not a field guarantee."
            )
        else:
            features = np.array(
                [temperature, humidity, rainfall, self._soil_code(soil_type), self._season_code(season), latitude, longitude],
                dtype=np.float32,
            ).reshape(1, -1)
            probabilities = model.predict_proba(features)[0]
            classes = model.classes_
            dataset_notice = "Demo fallback: 18 hand-entered sample rows across 9 crop categories. Add the labelled CSV dataset and retrain before relying on this model."
        predicted_index = int(np.argmax(probabilities))
        predicted_crop = str(classes[predicted_index])
        confidence = float(probabilities[predicted_index])

        info = CROP_RECOMMENDATION_INFO.get(predicted_crop, {
            "irrigationAdvice": "Keep irrigation scheduling aligned to the current weather and field moisture.",
            "fertilizerAdvice": "Use soil test-based fertilization to maintain nutrient balance.",
            "risk": "Moderate weather stress may appear depending on rainfall and field conditions.",
            "yieldExpectation": "Yield is stable when field conditions remain managed.",
        })

        reasons = [
            f"{predicted_crop} matches the current {self._location_zone(latitude, longitude).lower()} conditions and farmer input.",
            f"The climate mix of {temperature}°C, {humidity}% humidity, and {rainfall} mm rainfall is favorable for {predicted_crop}.",
            "Prediction is based on the currently loaded training dataset; local field validation is still required.",
        ]

        if crop_name.lower() == predicted_crop.lower():
            suitability = "High" if confidence >= 0.6 else "Moderate"
        else:
            suitability = "Suggested alternative" if confidence >= 0.5 else "Potential fit"

        ranked_indices = np.argsort(probabilities)[::-1][:3]
        alternatives = [
            {"crop": str(classes[int(index)]), "confidencePct": int(float(probabilities[int(index)]) * 100)}
            for index in ranked_indices
        ]

        return {
            "alternatives": alternatives,
            "crop": predicted_crop,
            "requestedCrop": crop_name,
            "confidence": round(confidence, 3),
            "confidencePct": int(confidence * 100),
            "suitability": suitability,
            "locationZone": self._location_zone(latitude, longitude),
            "reason": reasons[0],
            "reasons": reasons,
            "irrigationAdvice": info["irrigationAdvice"],
            "fertilizerAdvice": info["fertilizerAdvice"],
            "risk": info["risk"],
            "yieldExpectation": info["yieldExpectation"],
            "datasetNotice": dataset_notice,
            "temperatureC": temperature,
            "humidityPercent": humidity,
            "rainfallMm": rainfall,
            "soilType": soil_type,
            "season": season,
        }
