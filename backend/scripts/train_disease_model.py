from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath

from PIL import Image, UnidentifiedImageError

project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from backend.app.ml_model import PlantDiseaseModel, TARGET_DISEASES


REFERENCE_IMAGE_LABELS = {
    "1.maze.png": "Maize___Banded_Leaf_and_Sheath_Blight",
    "2.jpg": "Maize___Downy_Mildew",
    "3.jpg": "Wheat___Foot_and_Root_Rots",
    "4_wheat.webp": "Wheat___Black_Stem_Rust",
    "5-rice.jpg": "Rice___Blast",
    "6-tomato.jpg": "Tomato___Early_blight",
    "7_tomato.jpg": "Tomato___Fusarium_and_Verticillium_Wilts",
    "8-sugercane.jpg": "Sugarcane___Red_Rot",
    "9-potato.jpg": "Potato___Black_Scurf",
    "10-ragi.jpg": "Finger_millet___Blast",
}


def load_reference_images(archive_path: Path) -> dict[str, Image.Image]:
    if not archive_path.is_file():
        raise FileNotFoundError(f"Disease reference archive not found: {archive_path}")

    images = {}
    seen_names = set()
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                filename = PurePosixPath(entry.filename).name
                if PurePosixPath(filename).suffix.lower() not in {
                    ".jpg", ".jpeg", ".png", ".bmp", ".webp"
                }:
                    continue
                if filename not in REFERENCE_IMAGE_LABELS:
                    raise ValueError(f"Unexpected image in reference archive: {filename}")
                if filename in seen_names:
                    raise ValueError(f"Archive contains duplicate reference image name: {filename}")
                seen_names.add(filename)
                try:
                    with archive.open(entry) as stream:
                        with Image.open(stream) as image:
                            image.load()
                            images[REFERENCE_IMAGE_LABELS[filename]] = image.convert("RGB")
                except (OSError, UnidentifiedImageError) as exc:
                    raise ValueError(f"Unable to read reference image: {filename}") from exc
    except zipfile.BadZipFile as exc:
        raise ValueError(f"Invalid ZIP archive: {archive_path}") from exc

    missing = sorted(set(REFERENCE_IMAGE_LABELS) - seen_names)
    if missing:
        raise ValueError("Archive is missing expected disease reference images: " + ", ".join(missing))
    if set(images) != set(TARGET_DISEASES):
        raise ValueError("Reference archive did not map to exactly the ten target diseases.")
    return images


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a ten-image visual-reference matcher (not a validated disease classifier)."
    )
    parser.add_argument(
        "archive",
        type=Path,
        help="ZIP containing the ten numbered reference images",
    )
    args = parser.parse_args()

    backend_dir = Path(__file__).resolve().parents[1]
    model = PlantDiseaseModel(backend_dir)
    images = load_reference_images(args.archive)
    bundle = model.train_from_reference_images(images)
    report = {
        "archive": args.archive.name,
        "reference_images": bundle["dataset_images"],
        "class_counts": bundle["class_counts"],
        "validation_accuracy": None,
        "diagnostic_confidence": None,
        "model": "HOG + RGB/HSV features with cosine visual similarity to one reference per disease",
        "model_path": str(model.reference_model_path),
        "warning": "No independent validation set; this prototype does not establish 95% accuracy.",
    }
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
