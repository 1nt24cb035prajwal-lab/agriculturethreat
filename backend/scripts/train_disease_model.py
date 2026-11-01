from pathlib import Path
import json
import sys

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from backend.app.ml_model import PlantDiseaseModel


def main() -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    dataset = backend_dir / "data" / "plant_disease"
    model = PlantDiseaseModel(backend_dir)
    bundle = model.train_from_directory(dataset)
    report = {
        "dataset": str(dataset),
        "images": bundle["dataset_images"],
        "class_counts": bundle["class_counts"],
        "test_images": bundle.get("test_images") or bundle["validation_images"],
        "test_accuracy": round(bundle.get("test_accuracy") or bundle["validation_accuracy"], 4),
        "model_path": str(model.model_path),
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
