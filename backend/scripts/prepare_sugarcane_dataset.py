from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    from datasets import load_dataset
except ImportError as exc:
    raise SystemExit(
        "Missing training dependency. Run: "
        "python -m pip install -r backend/training-requirements.txt"
    ) from exc

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "backend" / "data" / "plant_disease"
DATASET_ID = "Project-AgML/sugarcane_leaf_disease_classification"


def safe_label(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_")
    if not value:
        raise ValueError("Dataset contains an empty class label.")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and prepare the 6,748-image Sugarcane Leaf Disease dataset.")
    parser.add_argument("--force", action="store_true", help="Replace previously prepared Sugarcane folders.")
    args = parser.parse_args()

    print(f"Downloading {DATASET_ID} from Hugging Face...")
    dataset = load_dataset(DATASET_ID, split="train")
    label_feature = dataset.features["label"]
    label_names = getattr(label_feature, "names", None)
    if not label_names:
        raise RuntimeError("Expected a ClassLabel 'label' column in the Sugarcane dataset.")

    counts = {name: 0 for name in label_names}
    for row in dataset:
        counts[label_names[int(row["label"])]] += 1
    if len(counts) != 11 or sum(counts.values()) != 6748 or min(counts.values()) < 2:
        raise RuntimeError(f"Unexpected Sugarcane dataset distribution: {counts}")

    split = dataset.train_test_split(test_size=0.20, seed=42, stratify_by_column="label")
    written = {"train": 0, "test": 0}
    for split_name in ("train", "test"):
        for index, row in enumerate(split[split_name]):
            class_name = f"Sugarcane___{safe_label(label_names[int(row['label'])])}"
            target_dir = OUTPUT / split_name / class_name
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"sugarcane_{split_name}_{index:05d}.jpg"
            if target.exists() and not args.force:
                continue
            image = row["image"]
            if not hasattr(image, "convert"):
                raise RuntimeError(f"Could not decode Sugarcane image at {split_name} row {index}.")
            image.convert("RGB").save(target, format="JPEG", quality=95)
            written[split_name] += 1

    print("Sugarcane dataset prepared.")
    print(f"Dataset images: {sum(counts.values()):,}")
    print(f"Classes: {len(counts)}")
    for name, count in sorted(counts.items()):
        print(f"  {name}: {count:,}")
    print(f"New images written: {written}")
    print("\nNext: python backend/scripts/train_disease_model.py")
    print("The combined model still supports only crops present in its labelled class folders.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Sugarcane dataset preparation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
