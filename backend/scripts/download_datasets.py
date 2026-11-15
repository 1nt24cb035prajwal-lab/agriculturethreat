from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "backend" / "data"
CROP_CSV = DATA_DIR / "crop_recommendation.csv"
YIELD_CSV = DATA_DIR / "india_crop_production.csv"
CROP_MIRROR_URL = (
    "https://huggingface.co/datasets/liaad/agricultural-data/"
    "resolve/main/Crop_recommendation.csv"
)
YIELD_DATASET_URL = (
    "https://huggingface.co/datasets/jason1966/"
    "abhinand05_crop-production-in-india/resolve/main/crop_production.csv"
)
REQUIRED_CROP_COLUMNS = [
    "N", "P", "K", "temperature", "humidity", "ph", "rainfall", "label"
]


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

    # Prefer the original Kaggle dataset when the Kaggle CLI is authenticated.
    kaggle = shutil.which("kaggle")
    if kaggle:
        result = subprocess.run(
            [
                kaggle, "datasets", "download",
                "-d", "atharvaingle/crop-recommendation-dataset",
                "--unzip", "-p", str(DATA_DIR),
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


def download_yield_dataset(force: bool = False) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not YIELD_CSV.exists() or YIELD_CSV.stat().st_size == 0 or force:
        download_file(YIELD_DATASET_URL, YIELD_CSV, force=force)
    required = {"State_Name", "District_Name", "Crop_Year", "Season", "Crop", "Area", "Production"}
    with YIELD_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                f"{YIELD_CSV} is missing required columns: {', '.join(sorted(missing))}."
            )
        rows = sum(1 for _ in reader)
    if rows < 100:
        raise ValueError(f"Yield dataset has only {rows} rows; at least 100 are required.")
    print(f"Validated India crop production CSV: {rows:,} rows")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download crop recommendation and crop production datasets."
    )
    parser.add_argument("--skip-crop", action="store_true")
    parser.add_argument("--skip-yield", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if not args.skip_crop:
        download_crop_dataset(force=args.force)
    if not args.skip_yield:
        download_yield_dataset(force=args.force)
    print("\nDataset preparation complete.")
    print("Train crop model:    python backend/scripts/train_crop_model.py")
    print("For the ten-photo reference prototype, run train_disease_model.py with the reference ZIP.")
    print("That prototype reports visual similarity only; it does not establish diagnostic accuracy.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Dataset preparation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
