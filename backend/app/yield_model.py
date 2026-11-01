from __future__ import annotations

import csv
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, median_absolute_error, r2_score


MAX_DISTRICT_CATEGORIES = 254
CROP_ALIASES = {
    "chili": "dry chillies",
    "chilli": "dry chillies",
    "cotton": "cotton(lint)",
    "finger millet": "ragi",
    "mustard": "rapeseed &mustard",
    "soybean": "soyabean",
}


YIELD_DATASET_URL = (
    "https://huggingface.co/datasets/jason1966/"
    "abhinand05_crop-production-in-india"
)


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


class YieldPredictionModel:
    categorical_columns = ("state", "district", "season", "crop")
    required_columns = {
        "state_name": "state",
        "district_name": "district",
        "crop_year": "year",
        "season": "season",
        "crop": "crop",
        "area": "area",
        "production": "production",
    }

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.dataset_path = base_dir / "data" / "india_crop_production.csv"
        self.model_path = base_dir / "models" / "yield_prediction_model.joblib"
        self.bundle: dict[str, Any] | None = None

    @staticmethod
    def _new_regressor() -> HistGradientBoostingRegressor:
        return HistGradientBoostingRegressor(
            categorical_features=[True, True, True, True, False, False],
            learning_rate=0.08,
            max_iter=100,
            max_leaf_nodes=31,
            max_bins=255,
            min_samples_leaf=20,
            l2_regularization=1.0,
            random_state=42,
        )

    @staticmethod
    def _row_features(row: dict[str, Any], category_maps: dict[str, dict[str, int]], district_other: int) -> list[float]:
        values = []
        for column in ("state", "district", "season", "crop"):
            normalized = _normalize(row.get(column))
            category = category_maps[column].get(normalized)
            if column == "district" and category is None:
                category = district_other
            values.append(float(category) if category is not None else np.nan)
        values.extend((float(row["year"]), float(np.log1p(row["area"]))))
        return values

    def train_from_csv(self, dataset_path: Path | None = None) -> dict[str, Any]:
        source = Path(dataset_path or self.dataset_path)
        if not source.is_file():
            raise FileNotFoundError(f"Yield dataset not found: {source}. Download it before training.")

        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = {_normalize(name).replace(" ", "_"): name for name in (reader.fieldnames or [])}
            missing = sorted(set(self.required_columns) - set(headers))
            if missing:
                raise ValueError("Yield dataset is missing columns: " + ", ".join(missing))

            rows = []
            skipped_rows = 0
            for record in reader:
                try:
                    row = {
                        target: (record[headers[column]] or "").strip()
                        for column, target in self.required_columns.items()
                    }
                    row["year"] = int(float(row["year"]))
                    row["area"] = float(row["area"])
                    production = float(row["production"])
                    if (
                        not row["crop"]
                        or not row["state"]
                        or row["area"] <= 0
                        or production <= 0
                    ):
                        skipped_rows += 1
                        continue
                    row["yield"] = production / row["area"]
                    if not np.isfinite(row["yield"]):
                        skipped_rows += 1
                        continue
                    rows.append(row)
                except (KeyError, TypeError, ValueError, OverflowError):
                    skipped_rows += 1

        years = sorted({row["year"] for row in rows})
        if len(rows) < 100 or len(years) < 3:
            raise ValueError("Yield training needs at least 100 valid records across 3 years.")
        split_index = max(1, int(len(years) * 0.8))
        if split_index >= len(years):
            split_index = len(years) - 1
        split_year = years[split_index]
        train_rows = [row for row in rows if row["year"] < split_year]
        training_crops = {_normalize(row["crop"]) for row in train_rows}
        validation_rows = [
            row for row in rows
            if row["year"] >= split_year
            and _normalize(row["crop"]) in training_crops
        ]
        if len(train_rows) < 100 or len(validation_rows) < 20:
            raise ValueError("The chronological holdout must contain at least 100 training and 20 validation records.")

        yields_by_crop: dict[str, list[float]] = defaultdict(list)
        for row in train_rows:
            yields_by_crop[_normalize(row["crop"])].append(row["yield"])
        upper_yield_by_crop = {
            crop: float(np.quantile(values, 0.995))
            for crop, values in yields_by_crop.items()
            if len(values) >= 20
        }
        validation_rows_total = len(validation_rows)
        validation_rows = [
            row for row in validation_rows
            if row["yield"] <= upper_yield_by_crop.get(_normalize(row["crop"]), float("inf"))
        ]
        train_rows = [
            row for row in train_rows
            if row["yield"] <= upper_yield_by_crop.get(_normalize(row["crop"]), float("inf"))
        ]
        if len(train_rows) < 100 or len(validation_rows) < 20:
            raise ValueError("Too few valid yield records remain after filtering training outliers.")

        category_maps: dict[str, dict[str, int]] = {}
        for column in ("state", "season", "crop"):
            categories = sorted({_normalize(row[column]) for row in train_rows})
            if len(categories) > 255:
                raise ValueError(f"Too many {column} classes for the categorical yield model.")
            category_maps[column] = {value: index for index, value in enumerate(categories)}

        district_counts = Counter(_normalize(row["district"]) for row in train_rows)
        common_districts = [
            district for district, _ in district_counts.most_common(MAX_DISTRICT_CATEGORIES)
        ]
        category_maps["district"] = {
            value: index for index, value in enumerate(common_districts)
        }
        district_other = len(common_districts)

        def encode_rows(selected_rows: list[dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
            features = np.asarray([
                self._row_features(row, category_maps, district_other)
                for row in selected_rows
            ], dtype=np.float64)
            targets = np.log1p([row["yield"] for row in selected_rows])
            return features, targets

        X_train = np.asarray([
            self._row_features(row, category_maps, district_other)
            for row in train_rows
        ], dtype=np.float64)
        y_train = np.log1p([row["yield"] for row in train_rows])
        X_validation = np.asarray([
            self._row_features(row, category_maps, district_other)
            for row in validation_rows
        ], dtype=np.float64)
        y_validation = np.asarray([row["yield"] for row in validation_rows], dtype=np.float64)

        model = self._new_regressor()
        model.fit(X_train, y_train)
        predicted_log_yield = model.predict(X_validation)
        predicted_yield = np.maximum(0, np.expm1(predicted_log_yield))
        log_residuals = np.log1p(y_validation) - predicted_log_yield
        absolute_percentage_error = np.abs(predicted_yield - y_validation) / y_validation
        model_metrics = {
            "maeTonnesPerHectare": round(float(mean_absolute_error(y_validation, predicted_yield)), 3),
            "medianAbsoluteErrorTonnesPerHectare": round(float(median_absolute_error(y_validation, predicted_yield)), 3),
            "rmseTonnesPerHectare": round(float(np.sqrt(np.mean((y_validation - predicted_yield) ** 2))), 3),
            "r2": round(float(r2_score(y_validation, predicted_yield)), 4),
            "medianAbsolutePercentageError": round(float(np.median(absolute_percentage_error) * 100), 2),
            "within25PercentPercent": round(float(np.mean(absolute_percentage_error <= 0.25) * 100), 2),
            "validationRows": len(validation_rows),
            "validationOutlierRowsExcluded": validation_rows_total - len(validation_rows),
            "validationYears": [min(row["year"] for row in validation_rows), max(row["year"] for row in validation_rows)],
        }
        log_residual_interval = [
            float(np.quantile(log_residuals, 0.1)),
            float(np.quantile(log_residuals, 0.9)),
        ]

        final_rows = [
            row for row in rows
            if row["yield"] <= upper_yield_by_crop.get(_normalize(row["crop"]), float("inf"))
        ]
        final_category_maps: dict[str, dict[str, int]] = {}
        for column in ("state", "season", "crop"):
            categories = sorted({_normalize(row[column]) for row in final_rows})
            if len(categories) > 255:
                raise ValueError(f"Too many {column} classes for the categorical yield model.")
            final_category_maps[column] = {value: index for index, value in enumerate(categories)}
        final_district_counts = Counter(_normalize(row["district"]) for row in final_rows)
        final_common_districts = [
            district
            for district, _ in final_district_counts.most_common(MAX_DISTRICT_CATEGORIES)
        ]
        final_category_maps["district"] = {
            value: index for index, value in enumerate(final_common_districts)
        }
        final_district_other = len(final_common_districts)
        category_maps = final_category_maps
        district_other = final_district_other
        X_final, y_final = encode_rows(final_rows)
        final_model = self._new_regressor()
        final_model.fit(X_final, y_final)
        bundle = {
            "kind": "india_crop_yield_histgb_v1",
            "model": final_model,
            "category_maps": category_maps,
            "district_other": district_other,
            "dataset_path": source.name,
            "dataset_source": YIELD_DATASET_URL,
            "dataset_rows": len(rows),
            "skipped_rows": skipped_rows,
            "training_rows": len(final_rows),
            "class_count": len(category_maps["crop"]),
            "crop_classes": sorted(category_maps["crop"]),
            "district_coverage_percent": round(
                sum(count for district, count in final_district_counts.items() if district in final_category_maps["district"])
                / len(final_rows) * 100,
                2,
            ),
            "years": [min(years), max(years)],
            "training_years": [min(row["year"] for row in final_rows), max(row["year"] for row in final_rows)],
            "validation_training_years": [
                min(row["year"] for row in train_rows),
                max(row["year"] for row in train_rows),
            ],
            "metrics": model_metrics,
            "log_residual_interval": log_residual_interval,
        }
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(bundle, self.model_path)
        self.bundle = bundle
        return bundle

    def load(self) -> dict[str, Any] | None:
        if self.bundle is not None:
            return self.bundle
        if not self.model_path.is_file():
            return None
        loaded = joblib.load(self.model_path)
        if not isinstance(loaded, dict) or loaded.get("kind") != "india_crop_yield_histgb_v1":
            raise ValueError(f"Unsupported yield model artifact: {self.model_path}")
        self.bundle = loaded
        return loaded

    def predict(self, farm: dict[str, Any]) -> dict[str, Any]:
        bundle = self.load()
        if bundle is None:
            raise FileNotFoundError("The trained India crop yield model is not available.")
        crop = str(farm.get("cropName") or "").strip()
        state = str(farm.get("state") or "").strip()
        crop_key = CROP_ALIASES.get(_normalize(crop), _normalize(crop))
        state_key = _normalize(state)
        if crop_key not in bundle["category_maps"]["crop"]:
            raise ValueError(f"No yield training records are available for {crop or 'this crop'}.")
        if state_key not in bundle["category_maps"]["state"]:
            raise ValueError(f"No yield training records are available for {state or 'this state'}.")
        try:
            area = float(farm.get("landArea") or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError("Save a positive farm area before requesting a yield prediction.") from exc
        if not np.isfinite(area) or area <= 0:
            raise ValueError("Save a positive farm area before requesting a yield prediction.")
        area_unit = str(farm.get("landAreaUnit") or "Acres")
        area_hectares = area if area_unit.lower().startswith("hect") else area * 0.40468564224
        requested_year = int(farm.get("cropYear") or date.today().year)
        prediction_year = min(max(requested_year, bundle["years"][0]), bundle["years"][1])
        row = {
            "crop": crop,
            "state": state,
            "district": farm.get("district") or "",
            "season": farm.get("season") or "",
            "year": prediction_year,
            "area": area_hectares,
        }
        features = np.asarray([
            self._row_features(row, bundle["category_maps"], bundle["district_other"])
        ], dtype=np.float64)
        predicted_log_yield = float(bundle["model"].predict(features)[0])
        residual_low, residual_high = bundle["log_residual_interval"]
        expected_yield = max(0.0, float(np.expm1(predicted_log_yield)))
        low_yield = max(0.0, float(np.expm1(predicted_log_yield + residual_low)))
        high_yield = max(low_yield, float(np.expm1(predicted_log_yield + residual_high)))
        future_notice = (
            f"The requested year is outside the dataset range; year {prediction_year} was used."
            if requested_year != prediction_year
            else ""
        )
        notices = [
            f"Historical India production records ({bundle['years'][0]}–{bundle['years'][1]}); "
            "not a farm-specific or weather-adjusted forecast.",
            f"Chronological holdout MAE {bundle['metrics']['maeTonnesPerHectare']} tonnes/ha, "
            f"R² {bundle['metrics']['r2']}; performance may vary by crop and district.",
        ]
        if _normalize(row["district"]) not in bundle["category_maps"]["district"]:
            notices.append("This district had limited training coverage; the estimate relies more on crop and state patterns.")
        if future_notice:
            notices.append(future_notice)
        return {
            "crop": crop,
            "farmArea": area,
            "farmAreaUnit": area_unit,
            "areaHectares": round(area_hectares, 3),
            "predictedYieldTonnesPerHectare": round(expected_yield, 3),
            "lowEstimateTonnes": round(low_yield * area_hectares, 2),
            "expectedEstimateTonnes": round(expected_yield * area_hectares, 2),
            "highEstimateTonnes": round(high_yield * area_hectares, 2),
            "yieldRangeTonnesPerHectare": [round(low_yield, 3), round(high_yield, 3)],
            "method": "HistGradientBoosting trained on Indian district crop-production records",
            "confidence": "Low - historical regional records; review holdout metrics",
            "modelMetrics": bundle["metrics"],
            "predictionYear": prediction_year,
            "notice": " ".join(notices),
        }
