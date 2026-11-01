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
SPLIT_DIR = DATA_DIR / "plantvillage_splits"

CROP_MIRROR_URL = (
    "https://huggingface.co/datasets/liaad/agricultural-data/"
    "resolve/main/Crop_recommendation.csv"
)
PLANT_REPO = "https://huggingface.co/datasets/mohanty/PlantVillage/resolve/main"
PLANT_VILLAGE_URL = f"{PLANT_REPO}/data.zip"
SPLIT_URLS = {
    "train": f"{PLANT_REPO}/splits/color_train.txt",
    "test": f"{PLANT_REPO}/splits/color_test.txt",
}
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


def _read_split(path: Path) -> list[str]:
    with path.open("r", encoding="utf-8") as handle:
        return [line.strip().replace("\\", "/") for line in handle if line.strip()]


def extract_plantvillage(force: bool = False) -> None:
    train_dir = PLANT_DIR / "train"
    test_dir = PLANT_DIR / "test"
    if train_dir.is_dir() and test_dir.is_dir() and any(train_dir.rglob("*")) and any(test_dir.rglob("*")) and not force:
        print(f"PlantVillage train/test folders already exist: {PLANT_DIR}")
        return

    download_file(PLANT_VILLAGE_URL, PLANT_ZIP, force=force)
    if not zipfile.is_zipfile(PLANT_ZIP):
        raise ValueError(f"PlantVillage download is not a valid ZIP file: {PLANT_ZIP}")

    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    split_paths = {}
    for split_name, url in SPLIT_URLS.items():
        split_path = SPLIT_DIR / f"color_{split_name}.txt"
        download_file(url, split_path, force=force)
        split_paths[split_name] = _read_split(split_path)

    if PLANT_DIR.exists():
        shutil.rmtree(PLANT_DIR)
    for split_name in ("train", "test"):
        (PLANT_DIR / split_name).mkdir(parents=True, exist_ok=True)

    copied = {"train": 0, "test": 0}
    classes = {"train": set(), "test": set()}
    with zipfile.ZipFile(PLANT_ZIP) as archive:
        members = {}
        for info in archive.infolist():
            normalized = PurePosixPath(info.filename).as_posix().lstrip("./")
            members[normalized] = info

        for split_name, file_list in split_paths.items():
            for relative_name in file_list:
                member = members.get(relative_name)
                if member is None:
                    # Some ZIP writers add a single wrapper directory.
                    member = next(
                        (
                            info for name, info in members.items()
                            if name.endswith("/" + relative_name)
                        ),
                        None,
                    )
                if member is None:
                    raise FileNotFoundError(
                        f"PlantVillage image listed in {split_name} split was not found: {relative_name}"
                    )

                parts = PurePosixPath(relative_name).parts
                if len(parts) < 4 or parts[0] != "raw" or parts[1] != "color":
                    raise ValueError(f"Unexpected PlantVillage color image path: {relative_name}")
                class_name = parts[2]
                if "___" not in class_name:
                    raise ValueError(f"PlantVillage class label is missing crop/disease separator: {class_name}")
                image_relative = Path(*parts[3:])
                target = (PLANT_DIR / split_name / class_name / image_relative).resolve()
                if not target.is_relative_to(PLANT_DIR.resolve()):
                    raise ValueError(f"Unsafe path in PlantVillage archive: {relative_name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                copied[split_name] += 1
                classes[split_name].add(class_name)

    if copied["train"] < 30 or copied["test"] < 10 or classes["train"] != classes["test"]:
        shutil.rmtree(PLANT_DIR, ignore_errors=True)
        raise ValueError(
            "PlantVillage archive did not contain matching train/test class folders. "
            "The download may be incomplete or its layout may have changed."
        )
    print(
        f"Prepared PlantVillage color split: {copied['train']:,} train images, "
        f"{copied['test']:,} test images, {len(classes['train'])} classes"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download the crop recommendation CSV and PlantVillage color images."
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
    print("Train crop model:    python backend/scripts/train_crop_model.py")
    print("Train disease model: python backend/scripts/train_disease_model.py")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Dataset preparation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
