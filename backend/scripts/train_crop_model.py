from pathlib import Path
import json
import sys

from backend.app.ml_model import CropRecommendationModel


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    dataset = backend_dir / "data" / "crop_recommendation.csv"
    model = CropRecommendationModel(backend_dir)
    bundle = model.train_from_csv(dataset)
    report = {
        "dataset": str(dataset),
        "rows": bundle["dataset_rows"],
        "classes": bundle["crop_classes"],
        "validation_rows": bundle["validation_rows"],
        "validation_accuracy": round(bundle["validation_accuracy"], 4),
        "model_path": str(model.model_path),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
