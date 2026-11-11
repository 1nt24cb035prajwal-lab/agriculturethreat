from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "backend" / "data"
OUTPUT = DATA_ROOT / "plant_disease"
ARCHIVE = DATA_ROOT / "fc45_plant_disease.zip"
EXTRACTED = DATA_ROOT / "fc45_extracted"
DATASET_ID = "ph9g2cfxwm"
DATASET_VERSION = 1
API = "https://api.data.mendeley.com"

CROP_ALIASES = {
    "cashew": "Cashew", "cassava": "Cassava", "tomato": "Tomato",
    "potato": "Potato", "maize": "Maize", "corn": "Maize",
    "papaya": "Papaya", "sugarcane": "Sugarcane", "rice": "Rice",
    "chilli": "Chilli", "chili": "Chilli", "pepper": "Chilli",
    "grapes": "Grapes", "grape": "Grapes", "citrus": "Citrus",
    "groundnut": "Groundnut", "peanut": "Groundnut", "cotton": "Cotton",
    "wheat": "Wheat", "soyabean": "Soyabean", "soybean": "Soyabean",
}
IGNORED_DIRS = {"train", "training", "test", "testing", "valid", "validation", "images", "image", "data", "dataset", "healthy", "unhealthy", "diseased"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

def request(url: str, timeout: int = 120):
    req = urllib.request.Request(url, headers={"User-Agent": "AgricultureThreatFusion/1.0", "Accept": "application/json, application/zip, */*"})
    return urllib.request.urlopen(req, timeout=timeout)

def download_archive(force: bool = False) -> None:
    if ARCHIVE.exists() and ARCHIVE.stat().st_size > 100_000_000 and not force:
        print(f"Using existing archive: {ARCHIVE} ({ARCHIVE.stat().st_size / 1e9:.2f} GB)")
        return
    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    url = f"{API}/datasets/{DATASET_ID}/zip/file_downloaded?version={DATASET_VERSION}"
    print("Requesting the public Mendeley Data archive download...")
    try:
        with request(url, timeout=180) as response:
            content_type = response.headers.get("Content-Type", "")
            first = response.read(4)
            if first[:2] != b"PK":
                raise RuntimeError(f"Mendeley did not return a ZIP archive (Content-Type: {content_type}). Open https://data.mendeley.com/datasets/ph9g2cfxwm/1 and download the ZIP manually, then rerun with --archive PATH.")
            with ARCHIVE.open("wb") as out:
                out.write(first)
                total = len(first)
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk: break
                    out.write(chunk); total += len(chunk)
                    if total % (100 * 1024 * 1024) < 1024 * 1024:
                        print(f"Downloaded {total / 1e9:.2f} GB...")
    except Exception as exc:
        if ARCHIVE.exists(): ARCHIVE.unlink()
        raise RuntimeError(f"Dataset download failed: {exc}") from exc
    if not zipfile.is_zipfile(ARCHIVE):
        ARCHIVE.unlink(missing_ok=True)
        raise RuntimeError("Downloaded file is not a valid ZIP. Download it manually from the dataset page and use --archive.")
    print(f"Archive downloaded: {ARCHIVE.stat().st_size / 1e9:.2f} GB")

def safe_extract(archive: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        for item in zf.infolist():
            target = (destination / item.filename).resolve()
            if destination.resolve() not in target.parents and target != destination.resolve():
                raise RuntimeError(f"Unsafe path in dataset archive: {item.filename}")
        zf.extractall(destination)

def parse_class(image_path: Path, root: Path):
    parts = list(image_path.relative_to(root).parts[:-1])
    crop = None
    disease = None
    for part in parts:
        normalized = re.sub(r"[^a-z]", "", part.lower())
        for alias, canonical in CROP_ALIASES.items():
            if normalized == re.sub(r"[^a-z]", "", alias):
                crop = canonical
                break
        if crop:
            break
    if crop is None:
        # Also accept combined directory labels such as Tomato___Early_blight.
        for part in parts:
            for alias, canonical in CROP_ALIASES.items():
                match = re.match(rf"^{re.escape(alias)}(?:___|__|[- ])(.+)$", part, flags=re.I)
                if match:
                    crop, disease = canonical, match.group(1)
                    break
            if crop: break
    if crop is None:
        return None
    if disease is None:
        crop_index = next((i for i, part in enumerate(parts) if re.sub(r"[^a-z]", "", part.lower()) in {re.sub(r"[^a-z]", "", a) for a in CROP_ALIASES}), None)
        candidates = [p for p in parts[(crop_index + 1 if crop_index is not None else 0):] if p.lower() not in IGNORED_DIRS and p.lower() not in {"healthy", "healthy_leaf"}]
        if candidates:
            disease = candidates[-1]
        elif any(p.lower() in {"healthy", "healthy_leaf"} for p in parts):
            disease = "Healthy"
    if not disease:
        return None
    disease = re.sub(r"[^A-Za-z0-9]+", "_", disease).strip("_")
    return f"{crop}___{disease}"

def main() -> int:
    parser = argparse.ArgumentParser(description="Download and prepare the Mendeley FC45DHLPD 15-crop plant disease dataset.")
    parser.add_argument("--archive", type=Path, help="Use a ZIP downloaded manually from the Mendeley dataset page.")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument("--force-extract", action="store_true")
    args = parser.parse_args()
    archive = args.archive.resolve() if args.archive else ARCHIVE
    if args.archive:
        if not archive.is_file(): raise FileNotFoundError(archive)
    else:
        download_archive(args.force_download)
    if not zipfile.is_zipfile(archive): raise RuntimeError(f"Not a valid ZIP file: {archive}")
    if args.force_extract and EXTRACTED.exists(): shutil.rmtree(EXTRACTED)
    if not any(EXTRACTED.iterdir()) if EXTRACTED.exists() else True:
        print("Extracting dataset (requires several GB of free disk space)...")
        safe_extract(archive, EXTRACTED)
    files = [p for p in EXTRACTED.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
    print(f"Found {len(files):,} image files in archive.")
    assignments = [(p, parse_class(p, EXTRACTED)) for p in files]
    assignments = [(p, label) for p, label in assignments if label]
    counts = Counter(label for _, label in assignments)
    crops = sorted({label.split("___", 1)[0] for label in counts})
    print(f"Recognized {len(assignments):,} labelled images, {len(crops)} crops, {len(counts)} crop/disease classes.")
    print("Crops:", ", ".join(crops))
    if len(crops) < 15:
        examples = [str(p.relative_to(EXTRACTED)) for p in files[:15]]
        raise RuntimeError("Could not recognize all 15 crop folders. No files were added. Inspect folder examples: " + json.dumps(examples))
    too_small = {label: n for label, n in counts.items() if n < 2}
    if too_small: raise RuntimeError(f"Classes need at least two images for a train/test split: {too_small}")
    # Stable split by image path; the test set is held out from training.
    from random import Random
    by_class = {}
    for path, label in assignments: by_class.setdefault(label, []).append(path)
    written = Counter()
    for label, paths in sorted(by_class.items()):
        paths.sort(key=lambda p: p.as_posix())
        Random(42).shuffle(paths)
        test_count = max(1, round(len(paths) * 0.20))
        if test_count >= len(paths): test_count = len(paths) - 1
        test_set = set(paths[:test_count])
        for path in paths:
            split = "test" if path in test_set else "train"
            target_dir = OUTPUT / split / label
            target_dir.mkdir(parents=True, exist_ok=True)
            digest = hashlib.sha1(path.as_posix().encode("utf-8")).hexdigest()[:12]
            target = target_dir / f"fc45_{digest}{path.suffix.lower()}"
            if not target.exists():
                try: target.symlink_to(path.resolve())
                except OSError: shutil.copy2(path, target)
            written[split] += 1
    report = {"source": "Mendeley Data FC45DHLPD", "dataset_id": DATASET_ID, "version": DATASET_VERSION, "license": "CC BY 4.0", "images": len(assignments), "crops": crops, "classes": dict(sorted(counts.items())), "written": dict(written)}
    report_path = DATA_ROOT / "fc45_dataset_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("\nNext run: python backend/scripts/train_disease_model.py")
    print("Note: the model supports only crops/classes present in the combined prepared folders; metrics are not field accuracy.")
    return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print(f"FC45 dataset preparation failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
