from __future__ import annotations

import csv
import json
from pathlib import Path

import joblib
import numpy as np
from PIL import Image
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, f1_score
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


# PlantVillage labels are crop-specific. Keep the raw dataset label for traceability,
# but return readable disease names and actionable, conservative IPM guidance.
PLANT_DISEASE_CROPS = {
    "Apple": "Apple", "Blueberry": "Blueberry", "Cherry_(including_sour)": "Cherry",
    "Corn_(maize)": "Corn", "Grape": "Grape", "Orange": "Orange", "Peach": "Peach",
    "Pepper,_bell": "Bell Pepper", "Potato": "Potato", "Raspberry": "Raspberry",
    "Soybean": "Soybean", "Squash": "Squash", "Strawberry": "Strawberry", "Tomato": "Tomato",
    "Sugarcane": "Sugarcane",
    "Cashew": "Cashew", "Cassava": "Cassava", "Maize": "Corn", "Papaya": "Papaya",
    "Rice": "Rice", "Chilli": "Chilli", "Grapes": "Grape", "Citrus": "Citrus",
    "Groundnut": "Groundnut", "Cotton": "Cotton", "Wheat": "Wheat", "Soyabean": "Soybean",
}
DISEASE_CLASS_INFO = {
    "healthy": ("Healthy", "No disease pattern was identified in this image. Continue scouting; a healthy-looking leaf does not rule out other plant problems.", "Keep using clean seed or planting material, balanced nutrition, and regular field scouting.", "Low"),
    "apple_scab": ("Apple Scab", "Olive-green to dark, velvety spots can develop on leaves and fruit; infected leaves may distort or drop.", "Remove fallen infected leaves, prune for airflow, and ask local horticulture staff about locally registered scab-control products at the correct growth stage.", "Moderate"),
    "black_rot": ("Black Rot", "Dark circular leaf lesions and fruit rot may occur; on grapes, berries can shrivel into dark mummies.", "Remove mummified fruit and infected debris, prune for airflow, and use locally approved disease management only after confirmation.", "High"),
    "cedar_apple_rust": ("Cedar-Apple Rust", "Bright orange-yellow leaf spots may develop, sometimes with tube-like structures on the leaf underside.", "Remove nearby alternate-host junipers where practical and use resistant apple varieties; confirm local control timing with an extension officer.", "Moderate"),
    "powdery_mildew": ("Powdery Mildew", "White powder-like fungal growth may appear on leaf surfaces; leaves can curl or become stunted.", "Improve airflow, remove heavily affected leaves, avoid excessive nitrogen, and use a locally registered mildew treatment only as advised.", "Moderate"),
    "cercospora_leaf_spot_gray_leaf_spot": ("Cercospora / Gray Leaf Spot", "Rectangular grey-tan lesions bounded by leaf veins can expand and merge on maize leaves.", "Use resistant hybrids, rotate crops, manage infected residue, and consult local agronomy advice on fungicide need.", "Moderate"),
    "common_rust": ("Common Rust", "Small raised cinnamon-brown to dark rust pustules occur on both leaf surfaces.", "Grow resistant hybrids, scout early, and seek local advice on fungicide timing when disease pressure is high.", "Moderate"),
    "northern_leaf_blight": ("Northern Leaf Blight", "Long, cigar-shaped grey-green to tan lesions develop along maize leaves.", "Use resistant hybrids, rotate crops, manage infected residue, and seek local disease-management advice.", "High"),
    "esca_black_measles": ("Esca (Black Measles)", "Grapevine leaves may show tiger-stripe discoloration; berries can develop dark specks and vines may decline.", "Prune in dry weather, protect pruning wounds using locally recommended methods, remove severely affected wood, and seek vineyard specialist advice.", "High"),
    "leaf_blight_isariopsis_leaf_spot": ("Isariopsis Leaf Blight", "Grape leaves can develop angular brown lesions that enlarge and cause premature leaf drop.", "Remove infected fallen leaves, improve canopy airflow, avoid prolonged leaf wetness, and confirm control options locally.", "Moderate"),
    "haunglongbing_citrus_greening": ("Citrus Greening (Huanglongbing / HLB)", "Blotchy asymmetric leaf yellowing, yellow shoots, small lopsided fruit, and poor fruit color may occur.", "There is no curative treatment for infected trees. Use certified planting material, monitor and manage citrus psyllids under local guidance, and follow official removal advice.", "High"),
    "bacterial_spot": ("Bacterial Spot", "Small water-soaked spots can become dark, angular or shot-holed; fruit may show raised scabby lesions.", "Use clean certified seed or transplants, avoid handling wet plants, remove infected residue, and ask an extension officer about locally registered bacterial-spot management.", "Moderate"),
    "early_blight": ("Early Blight", "Brown leaf spots with concentric target-like rings often begin on older leaves; yellowing and leaf drop can follow.", "Remove lower infected leaves, rotate away from solanaceous crops, mulch to reduce soil splash, and confirm local fungicide advice.", "Moderate"),
    "late_blight": ("Late Blight", "Water-soaked, rapidly expanding dark lesions may appear; white growth can form on leaf undersides in humid conditions.", "Act quickly: isolate affected plants, avoid overhead irrigation, remove infected material safely, and contact local extension staff urgently about registered late-blight control.", "High"),
    "leaf_mold": ("Leaf Mold", "Pale yellow patches on upper leaves may correspond to olive-green or grey fuzzy growth underneath, especially in humid conditions.", "Improve ventilation, avoid wet foliage, remove affected leaves, and use resistant varieties where available.", "Moderate"),
    "septoria_leaf_spot": ("Septoria Leaf Spot", "Numerous small circular spots with pale centres and dark margins can spread from older tomato leaves upward.", "Remove infected lower leaves, rotate crops, mulch against soil splash, and maintain dry foliage.", "Moderate"),
    "spider_mites_two_spotted_spider_mite": ("Two-Spotted Spider Mite", "Fine pale stippling, bronzing, and sometimes fine webbing can appear on leaf undersides.", "Inspect leaf undersides, reduce dust and plant stress, conserve predatory mites, and use only locally approved mite controls if thresholds justify it.", "Moderate"),
    "target_spot": ("Target Spot", "Brown circular lesions with concentric rings may appear on leaves and can cause defoliation.", "Improve airflow, avoid prolonged leaf wetness, remove infected debris, and confirm diagnosis before applying a locally registered fungicide.", "Moderate"),
    "tomato_yellow_leaf_curl_virus": ("Tomato Yellow Leaf Curl Virus", "Leaves may curl upward, turn yellow, become small, and show stunted growth; whiteflies commonly spread the virus.", "Remove confirmed infected plants, use virus-free transplants and resistant varieties, and manage whiteflies through integrated pest management. There is no cure for infected plants.", "High"),
    "tomato_mosaic_virus": ("Tomato Mosaic Virus", "Light and dark green mottling, leaf distortion, and stunted growth may occur.", "Remove confirmed infected plants, disinfect tools and hands, use certified seed, and control weeds that can host the virus. There is no curative spray.", "High"),
    "leaf_scorch": ("Leaf Scorch", "Strawberry leaves may develop reddish-purple margins and dry brown scorched areas.", "Remove old affected leaves, maintain even soil moisture, improve airflow, and confirm whether the cause is fungal or environmental.", "Moderate"),
}
CROP_DISPLAY_ALIASES = {"apple": "Apple", "blueberry": "Blueberry", "cherry": "Cherry", "corn": "Corn", "grape": "Grape", "orange": "Orange", "peach": "Peach", "bell pepper": "Bell Pepper", "pepper": "Bell Pepper", "potato": "Potato", "raspberry": "Raspberry", "soybean": "Soybean", "squash": "Squash", "strawberry": "Strawberry", "tomato": "Tomato"}

# Common crop nutrient issues to inspect in the field. These are screening clues,
# not diagnoses inferred from a leaf-disease classifier.
NUTRIENT_GUIDANCE = {
    "nitrogen": {
        "name": "Nitrogen (N)",
        "symptoms": "Older leaves may turn pale green or yellow; growth can be stunted.",
        "fertilizers": ["Urea", "Ammonium sulphate"],
    },
    "phosphorus": {
        "name": "Phosphorus (P)",
        "symptoms": "Plants may grow slowly; older leaves can look dark green or purplish.",
        "fertilizers": ["DAP", "Single Super Phosphate (SSP)"],
    },
    "potassium": {
        "name": "Potassium (K)",
        "symptoms": "Older leaf edges may yellow, scorch, or become brown and dry.",
        "fertilizers": ["Muriate of Potash (MOP)", "Sulphate of Potash (SOP)"],
    },
    "zinc": {
        "name": "Zinc (Zn)",
        "symptoms": "Interveinal yellowing, pale bands, or small leaves may appear; signs vary by crop.",
        "fertilizers": ["Zinc sulphate (ZnSO4)"],
    },
    "iron": {
        "name": "Iron (Fe)",
        "symptoms": "Young leaves may yellow between veins while veins remain greener.",
        "fertilizers": ["Ferrous sulphate"],
    },
    "magnesium": {
        "name": "Magnesium (Mg)",
        "symptoms": "Older leaves may show yellowing between veins while the veins remain green.",
        "fertilizers": ["Magnesium sulphate (Epsom salt)"],
    },
    "calcium": {
        "name": "Calcium (Ca)",
        "symptoms": "New growth may deform; growing tips or fruit ends may show necrosis or blossom-end rot.",
        "fertilizers": ["Agricultural lime (if soil pH is low)", "Gypsum (where calcium is needed without raising pH)"],
    },
    "boron": {
        "name": "Boron (B)",
        "symptoms": "Growing points, flowers, or young leaves may become distorted; fruit or pod set may be poor.",
        "fertilizers": ["Borax or another locally approved boron source"],
    },
    "sulphur": {
        "name": "Sulphur (S)",
        "symptoms": "Young leaves may become uniformly pale yellow; growth and protein formation may be reduced.",
        "fertilizers": ["Single Super Phosphate (SSP)", "Ammonium sulphate", "Gypsum"],
    },
}

CROP_NUTRIENT_CHECKS = {
    "rice": ["nitrogen", "zinc", "potassium"],
    "paddy": ["nitrogen", "zinc", "potassium"],
    "maize": ["nitrogen", "zinc", "phosphorus"],
    "corn": ["nitrogen", "zinc", "phosphorus"],
    "wheat": ["nitrogen", "zinc", "potassium"],
    "tomato": ["potassium", "calcium", "magnesium", "nitrogen"],
    "potato": ["potassium", "magnesium", "nitrogen"],
    "cotton": ["nitrogen", "potassium", "zinc"],
    "groundnut": ["calcium", "sulphur", "boron"],
    "sugarcane": ["nitrogen", "potassium", "zinc"],
    "chili": ["potassium", "calcium", "magnesium"],
    "chilli": ["potassium", "calcium", "magnesium"],
    "banana": ["potassium", "magnesium", "nitrogen"],
    "onion": ["nitrogen", "sulphur", "potassium"],
    "grape": ["potassium", "magnesium", "boron"],
    "apple": ["potassium", "calcium", "boron"],
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

    def _extract_plantvillage_features(self, image: Image.Image) -> np.ndarray:
        image_size = 32
        cell_size = 8
        cell_count = image_size // cell_size
        rgb_image = image.convert("RGB").resize((image_size, image_size), Image.Resampling.BILINEAR)
        rgb = np.asarray(rgb_image, dtype=np.float32)
        gray = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
        gradient_y, gradient_x = np.gradient(gray)
        magnitude = np.hypot(gradient_x, gradient_y)
        orientation = np.mod(np.arctan2(gradient_y, gradient_x), np.pi) * (9 / np.pi)
        lower_bin = np.floor(orientation).astype(np.int32) % 9
        bin_fraction = orientation - np.floor(orientation)
        cell_rows, cell_columns = np.indices((image_size, image_size))
        cell_ids = ((cell_rows // cell_size) * cell_count + cell_columns // cell_size).ravel()
        magnitude = magnitude.ravel()
        lower_bin = lower_bin.ravel()
        bin_fraction = bin_fraction.ravel()
        cell_total = cell_count * cell_count
        cell_histograms = np.zeros((cell_total, 9), dtype=np.float32)
        for bin_index in range(9):
            lower_weights = magnitude * (1 - bin_fraction) * (lower_bin == bin_index)
            upper_weights = magnitude * bin_fraction * (((lower_bin + 1) % 9) == bin_index)
            cell_histograms[:, bin_index] = (
                np.bincount(cell_ids, weights=lower_weights, minlength=cell_total)
                + np.bincount(cell_ids, weights=upper_weights, minlength=cell_total)
            )
        cell_histograms = cell_histograms.reshape(cell_count, cell_count, 9)
        cell_histograms /= np.maximum(
            np.linalg.norm(cell_histograms, axis=2, keepdims=True),
            1e-6,
        )

        color_histograms = []
        hsv = np.asarray(rgb_image.convert("HSV"), dtype=np.uint8)
        for channel in range(3):
            color_histograms.extend(
                np.histogram(rgb[:, :, channel], bins=16, range=(0, 256))[0].astype(np.float32)
                / (image_size * image_size)
            )
            color_histograms.extend(
                np.histogram(hsv[:, :, channel], bins=16, range=(0, 256))[0].astype(np.float32)
                / (image_size * image_size)
            )
        return np.concatenate([cell_histograms.ravel(), color_histograms]).astype(np.float32)

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
                            features.append(self._extract_plantvillage_features(image))
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

        classifier = SGDClassifier(
            loss="log_loss",
            alpha=0.0001,
            max_iter=30,
            tol=0.001,
            random_state=42,
            class_weight="balanced",
            n_jobs=1,
        )
        classifier.fit(X_train, y_train)
        predictions = classifier.predict(X_test)
        accuracy = float(accuracy_score(y_test, predictions))
        macro_f1 = float(f1_score(y_test, predictions, average="macro", zero_division=0))
        bundle = {
            "kind": "plant_disease_hog_v2",
            "classifier": classifier,
            "dataset_path": source.name,
            "dataset_images": int(len(X_train) + len(X_test)),
            "class_counts": class_counts,
            "validation_accuracy": accuracy,
            "macro_f1": macro_f1,
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
            needs_training = not self.model_path.exists()
            if not needs_training:
                cached_model = joblib.load(self.model_path)
                needs_training = not (
                    isinstance(cached_model, dict)
                    and cached_model.get("kind") == "plant_disease_hog_v2"
                )
                if not needs_training:
                    self.model = cached_model
            if not needs_training and max(
                (path.stat().st_mtime for path in self.image_dataset_path.rglob("*") if path.is_file()),
                default=0,
            ) > self.model_path.stat().st_mtime:
                needs_training = True
            if needs_training:
                return self.train_from_directory(self.image_dataset_path)
            return self.model
        if self.model_path.exists():
            self.model = joblib.load(self.model_path)
            if isinstance(self.model, dict) and self.model.get("kind") in {
                "plant_disease_folders_v1",
                "plant_disease_hog_v2",
            }:
                return self.model
            if getattr(self.model, "n_features_in_", None) == 9:
                return self.model
            self.model = None
        raise FileNotFoundError(
            f"Trained PlantVillage model not found at {self.model_path}. "
            "Download the PlantVillage dataset and run backend/scripts/train_disease_model.py. "
            "Synthetic disease predictions are disabled."
        )

    @staticmethod
    def nutrient_guidance(crop_name: str | None) -> dict:
        crop_key = str(crop_name or "").strip().lower()
        keys = CROP_NUTRIENT_CHECKS.get(crop_key, ["nitrogen", "phosphorus", "potassium", "zinc"])
        items = []
        fertilizer_names = []
        for key in keys:
            item = NUTRIENT_GUIDANCE.get(key)
            if not item:
                continue
            items.append({
                "nutrient": item["name"],
                "possibleSymptoms": item["symptoms"],
                "fertilizers": item["fertilizers"],
            })
            fertilizer_names.extend(item["fertilizers"])
        return {
            "nutrientDeficienciesToCheck": items,
            "fertilizerRecommendations": list(dict.fromkeys(fertilizer_names)),
            "nutrientNotice": (
                "These are common nutrient issues to inspect for this crop, not deficiencies diagnosed from this photo. "
                "Confirm with a soil or plant-tissue test and local agricultural advice before applying fertilizer."
            ),
        }

    @staticmethod
    def _normalize_crop_name(crop_name: str) -> str:
        value = str(crop_name or "").strip().lower().replace("_", " ").replace("-", " ")
        aliases = {
            "maize": "corn", "corn maize": "corn", "pepper": "bell pepper",
            "capsicum": "bell pepper", "chilli": "chilli", "grapes": "grape", "maize": "corn", "soyabean": "soybean",
        }
        return aliases.get(value, value)

    def predict(self, image: Image.Image, crop_name: str | None = None):
        loaded = self.load_or_train()
        trained_bundle = isinstance(loaded, dict) and loaded.get("kind") == "plant_disease_hog_v2"
        if trained_bundle:
            model = loaded["classifier"]
            warning = (
                "Image-based guidance is a starting point only. Compare the symptoms in the field and confirm serious problems with a local agricultural expert."
            )
        else:
            raise RuntimeError("A real PlantVillage disease model is required; synthetic fallback predictions are disabled.")

        features = self._extract_plantvillage_features(image).reshape(1, -1)
        probabilities = model.predict_proba(features)[0]
        # Restrict diagnosis to the farmer's selected crop. The PlantVillage
        # model contains no Sugarcane/Rice/Wheat/etc. classes, so never label
        # those crops as an unrelated supported crop.
        requested_crop = self._normalize_crop_name(crop_name)
        if requested_crop:
            crop_indices = [
                index for index, label in enumerate(model.classes_)
                if "___" in str(label)
                and self._normalize_crop_name(
                    PLANT_DISEASE_CROPS.get(str(label).split("___", 1)[0],
                        str(label).split("___", 1)[0].replace("_", " ").replace(",", "").title())
                ) == requested_crop
            ]
            if not crop_indices:
                supported = sorted(set(PLANT_DISEASE_CROPS.values()))
                raise ValueError(
                    f"Disease detection for {crop_name} is not supported by the installed PlantVillage model. "
                    f"Supported crops: {', '.join(supported)}. Do not use another crop's result as a diagnosis."
                )
            probabilities = probabilities.copy()
            excluded = np.ones(len(probabilities), dtype=bool)
            excluded[crop_indices] = False
            probabilities[excluded] = 0.0
        # Normalize probabilities within the selected crop after filtering other crops.
        total_probability = float(probabilities.sum())
        if total_probability > 0:
            probabilities = probabilities / total_probability
        ranked = np.argsort(probabilities)[::-1][:3]
        raw_label = str(model.classes_[int(ranked[0])])
        confidence = float(probabilities[int(ranked[0])])
        second_probability = float(probabilities[int(ranked[1])]) if len(ranked) > 1 else 0.0
        probability_gap = confidence - second_probability
        parts = raw_label.split("___", 1)
        crop_key = parts[0] if len(parts) == 2 else ""
        disease_key = parts[1] if len(parts) == 2 else raw_label
        detected_crop = PLANT_DISEASE_CROPS.get(crop_key, crop_key.replace("_", " ").replace(",", "").title()) if crop_key else "Unspecified crop"
        disease_slug = disease_key.lower().replace(" ", "_").replace("-", "_").strip("_")
        disease_info = DISEASE_CLASS_INFO.get(disease_slug)
        if disease_info is None:
            display_disease = disease_key.replace("_", " ").strip().title()
            symptoms = "The model matched this PlantVillage class. Compare the visible signs with the crop and ask an agricultural expert to confirm."
            treatment = "Do not apply a pesticide based only on this image. Remove heavily affected material where appropriate and obtain local crop-protection advice."
            prevention = "Use clean planting material, field sanitation, crop rotation where suitable, and regular scouting."
            severity = "Needs expert review"
        else:
            display_disease, symptoms, treatment, severity = disease_info
            prevention = "Use disease-free planting material, rotate crops where practical, remove infected crop debris, avoid prolonged leaf wetness, and scout the crop regularly."
        healthy = disease_slug == "healthy"
        display_label = f"{detected_crop} — {display_disease}"
        top_predictions = []
        for index in ranked:
            candidate = str(model.classes_[int(index)])
            candidate_parts = candidate.split("___", 1)
            candidate_crop = PLANT_DISEASE_CROPS.get(candidate_parts[0], candidate_parts[0].replace("_", " ").title())
            candidate_disease = candidate_parts[1] if len(candidate_parts) == 2 else candidate
            candidate_slug = candidate_disease.lower().replace(" ", "_").replace("-", "_").strip("_")
            candidate_info = DISEASE_CLASS_INFO.get(candidate_slug)
            candidate_name = candidate_info[0] if candidate_info else candidate_disease.replace("_", " ").strip().title()
            top_predictions.append({
                "crop": candidate_crop,
                "disease": candidate_name,
                "label": f"{candidate_crop} — {candidate_name}",
                "scorePct": round(float(probabilities[int(index)]) * 100, 1),
            })

        # A "healthy" result needs substantially stronger evidence than a disease
        # suggestion. Otherwise abstain rather than reassure the farmer incorrectly.
        if (disease_slug == "healthy" and (confidence < 0.92 or probability_gap < 0.35)) or confidence < 0.50 or probability_gap < 0.08:
            prediction_status = "needs_review"
            display_disease = "Unable to identify clearly"
            display_label = f"{detected_crop} — {display_disease}"
            symptoms = "The photo does not provide a clear enough match. Check both sides of several leaves for spots, streaks, rust-coloured marks, curling, or yellowing."
            treatment = "Do not apply pesticide or fertilizer based on this result. Take clear close-up photos of affected and healthy leaves and ask a local agricultural officer to confirm the cause."
            prevention = "Keep the field clean, avoid prolonged leaf wetness, use healthy planting material, and inspect the crop regularly."
            severity = "Needs field inspection"
            healthy = False
        else:
            prediction_status = "prediction"

        return {
            "predictedDisease": display_label,
            "diseaseName": display_disease,
            "detectedCrop": detected_crop,
            "modelClass": raw_label,
            "predictionStatus": prediction_status,
            "confidence": round(confidence, 3),
            "confidencePct": round(confidence * 100, 1),
            "severity": severity,
            "symptoms": symptoms,
            "treatment": treatment,
            "prevention": prevention,
            "affectedCropParts": ["Leaves", "Fruit", "Stem"] if not healthy else ["Whole plant"],
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
