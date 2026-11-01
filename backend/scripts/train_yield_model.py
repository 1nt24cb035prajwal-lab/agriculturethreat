from pathlib import Path
import json
import sys

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from backend.app.yield_model import YieldPredictionModel


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    dataset = backend_dir / "data" / "india_crop_production.csv"
    model = YieldPredictionModel(backend_dir)
    bundle = model.train_from_csv(dataset)
    report = {
        "dataset": str(dataset),
        "dataset_rows": bundle["dataset_rows"],
        "skipped_rows": bundle["skipped_rows"],
        "training_rows": bundle["training_rows"],
        "crop_classes": bundle["class_count"],
        "crop_labels": bundle["crop_classes"],
        "dataset_years": bundle["years"],
        "training_years": bundle["training_years"],
        "district_coverage_percent": bundle["district_coverage_percent"],
        "chronological_holdout": bundle["metrics"],
        "model_path": str(model.model_path),
        "dataset_source": bundle["dataset_source"],
        "license_notice": "The Kaggle mirror marks the dataset license unknown. Keep this data and trained artifact local unless redistribution rights are confirmed.",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
