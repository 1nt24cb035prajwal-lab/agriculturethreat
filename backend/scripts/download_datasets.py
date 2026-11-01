from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "backend" / "data"
CROP_CSV = DATA_DIR / "crop_recommendation.csv"
PLANT_ZIP = DATA_DIR / "plantvillage_data.zip"
PLANT_DIR = DATA_DIR / "plant_disease"

CROP_MIRROR_URL = (
    "https://huggingface.co/datasets/liaad/agricultural-data/"
    "resolve/main/Crop_recommendation.csv"
)
PLANT_VILLAGE_URL = (
    "https://huggingface.co/datasets/mohanty/PlantVillage/"
    "resolve/main/data.zip"
)
REQUIRED_CROP_COLUMNS = [
    "N", "P", "K", "temperature", "humidity", "ph", "rainfall", "label"
]
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def download_file(url: str, destination: Path, force: bool = False) -> None:
    if destination.exists() and destination.stat().st_size > 0 and not force:
        print(f"Already downloaded: {destination}")
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(
        url, headers={"User-Agent": "AgricultureThreatFusion/1.0"}
    )
    print(f"Downloading {url}")
    try:
        with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as output:
            shutil.copyfileobj(response, output, length=1024 * 1024)
        if temporary.stat().st_size == 0:
            raise RuntimeError(f"Downloaded file is empty: {destination.name}")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)


def download_crop_dataset(force: bool = False) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if CROP_CSV.exists() and CROP_CSV.stat().st_size > 0 and not force:
        validate_crop_csv(CROP_CSV)
        print(f"Crop dataset already exists: {CROP_CSV}")
        return

    # Prefer the official Kaggle dataset when the Kaggle CLI is authenticated.
    kaggle = shutil.which("kaggle")
    if kaggle:
        result = subprocess.run(
            [
                kaggle,
                "datasets",
                "download",
                "-d",
                "atharvaingle/crop-recommendation-dataset",
                "--unzip",
                "-p",
                str(DATA_DIR),
            ],
            check=False,
        )
        if result.returncode == 0:
            candidates = list(DATA_DIR.glob("*.csv"))
            matching = next(
                (path for path in candidates if path.name.lower() in {
                    "crop_recommendation.csv", "crop_recommendation_dataset.csv"
                }),
                None,
            )
            if matching:
                if matching != CROP_CSV:
                    matching.replace(CROP_CSV)
                validate_crop_csv(CROP_CSV)
                print(f"Crop dataset ready: {CROP_CSV}")
                return
        print("Kaggle download was unavailable; using the public Hugging Face CSV mirror.")

    download_file(CROP_MIRROR_URL, CROP_CSV, force=force)
    validate_crop_csv(CROP_CSV)
    print(f"Crop dataset ready: {CROP_CSV}")


def validate_crop_csv(path: Path) -> None:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        missing = [name for name in REQUIRED_CROP_COLUMNS if name not in columns]
        if missing:
            raise ValueError(
                f"{path} is missing required columns: {', '.join(missing)}. "
                f"Found: {columns}"
            )
        rows = sum(1 for _ in reader)
    if rows < 30:
        raise ValueError(f"Crop dataset has only {rows} rows; at least 30 are required.")
    print(f"Validated crop CSV: {rows:,} rows, {len(columns)} columns")


def extract_plantvillage(force: bool = False) -> None:
    if PLANT_DIR.exists() and any(PLANT_DIR.rglob("*")) and not force:
        print(f"Plant disease image folders already exist: {PLANT_DIR}")
        return

    download_file(PLANT_VILLAGE_URL, PLANT_ZIP, force=force)
    if not zipfile.is_zipfile(PLANT_ZIP):
        raise ValueError(f"PlantVillage download is not a valid ZIP file: {PLANT_ZIP}")

    if PLANT_DIR.exists():
        shutil.rmtree(PLANT_DIR)
    PLANT_DIR.mkdir(parents=True, exist_ok=True)

    copied = 0
    classes: set[str] = set()
    with zipfile.ZipFile(PLANT_ZIP) as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            member_path = PurePosixPath(member.filename)
            if member_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue

            # PlantVillage labels use Crop___Disease folder names. Select the
            # deepest such folder so split/modality wrappers do not become labels.
            class_indexes = [
                index for index, part in enumerate(member_path.parts)
                if "___" in part
            ]
            if class_indexes:
                class_index = class_indexes[-1]
                class_name = member_path.parts[class_index]
                relative_parts = member_path.parts[class_index + 1 :]
            else:
                if len(member_path.parts) < 2:
                    continue
                class_name = member_path.parts[-2]
                relative_parts = (member_path.name,)

            if not class_name or class_name in {".", ".."}:
                continue
            relative = Path(*relative_parts) if relative_parts else Path(member_path.name)
            target = (PLANT_DIR / class_name / relative).resolve()
            if not target.is_relative_to(PLANT_DIR.resolve()):
                raise ValueError(f"Unsafe path in PlantVillage archive: {member.filename}")
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            copied += 1
            classes.add(class_name)

    if copied < 30 or len(classes) < 2:
        shutil.rmtree(PLANT_DIR, ignore_errors=True)
        raise ValueError(
            "PlantVillage archive did not contain enough class-labelled images. "
            "Check the dataset archive layout before training."
        )
    print(f"Extracted {copied:,} images across {len(classes)} classes to {PLANT_DIR}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download the crop recommendation CSV and PlantVillage images."
    )
    parser.add_argument("--skip-crop", action="store_true")
    parser.add_argument("--skip-disease", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.skip_crop:
        download_crop_dataset(force=args.force)
    if not args.skip_disease:
        extract_plantvillage(force=args.force)

    print("\nDataset preparation complete.")
    print("Train crop model:   python backend/scripts/train_crop_model.py")
    print("Train disease model: python backend/scripts/train_disease_model.py")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Dataset preparation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
