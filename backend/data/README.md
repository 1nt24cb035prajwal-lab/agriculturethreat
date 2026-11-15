# Dataset sources and local storage

Run `python backend/scripts/download_datasets.py` from the repository root to prepare the datasets under this directory.

## Crop recommendation

- Primary dataset page: https://www.kaggle.com/datasets/atharvaingle/crop-recommendation-dataset
- Public CSV mirror used by the downloader: https://huggingface.co/datasets/liaad/agricultural-data/resolve/main/Crop_recommendation.csv
- Expected file: `crop_recommendation.csv`
- Required columns: `N,P,K,temperature,humidity,ph,rainfall,label`
- The commonly cited version contains 2,200 rows and 22 crop labels.

The downloader prefers the Kaggle CLI if it is installed and authenticated; otherwise it uses the public Hugging Face CSV mirror. Review the original dataset terms and attribution before redistributing the CSV or using it commercially.

## Crop yield

- Dataset: [Crop Production in India](https://huggingface.co/datasets/jason1966/abhinand05_crop-production-in-india), mirrored from [Kaggle](https://www.kaggle.com/datasets/abhinand05/crop-production-in-india)
- Expected file: `india_crop_production.csv`
- The downloaded snapshot contains 246,091 records from 1997–2015 and 124 crop labels.
- Features: state, district, crop year, season, crop, area, and production. Yield is derived as production divided by area.
- The mirror marks its license as unknown. Do not redistribute the CSV or trained model until the original dataset terms are reviewed.

The yield trainer evaluates on later years that are excluded from training and reports MAE, RMSE, R², and the share of predictions within 25% of observed yield. It excludes validation targets above each crop's 99.5th-percentile yield calculated from training years only, and reports the number excluded. It trains on all valid rows after the holdout evaluation, uses the 254 most common districts plus an "other" bucket, and retains all supported crop labels. This is regional historical data, not a farm-level yield benchmark.

## Target plant disease images

The disease catalog contains these ten class labels:

- `Maize___Banded_Leaf_and_Sheath_Blight`
- `Maize___Downy_Mildew`
- `Wheat___Foot_and_Root_Rots`
- `Wheat___Black_Stem_Rust`
- `Rice___Blast`
- `Tomato___Early_blight`
- `Tomato___Fusarium_and_Verticillium_Wilts`
- `Sugarcane___Red_Rot`
- `Potato___Black_Scurf`
- `Finger_millet___Blast`

The supplied ZIP contains one reference image per class, with numbered filenames mapped by `backend/scripts/train_disease_model.py`. Train the reference matcher by passing the ZIP path:

```powershell
python backend\scripts\train_disease_model.py "C:\path\to\dataset_@1.zip"
```

The script uses only those ten mapped images and writes `backend/models/plant_disease_reference_model.joblib`. At runtime, uploads are matched to the closest reference using cosine similarity over image features. The displayed percentage is visual similarity, not disease confidence, probability, or measured accuracy; this one-shot prototype always returns a closest class, including for unrelated images. Ten images cannot validate a >95% accuracy claim. More labeled field photos and an independent representative test set are required for that.

The compact reference feature artifact is included for deployment. PlantVillage is no longer downloaded or used by the disease workflow; any existing local PlantVillage files are left untouched.

## Train the models

After downloading the crop and yield datasets, run the crop and yield trainers. Train the ten-image disease reference matcher separately using the ZIP command above.

```powershell
python backend\scripts\train_crop_model.py
python backend\scripts\train_yield_model.py
```

The crop and yield model files are written to `backend/models/` and excluded from Git. The reference disease artifact contains image feature vectors, not the original images.

## Important limitations

The disease application uses Gemini Vision unless the ten-image reference artifact is present. The reference matcher uses HOG and color-histogram features with cosine similarity; it is not a field-validated diagnostic model. Its visual-similarity score must not be treated as diagnostic confidence or measured accuracy. Confirm disease and treatment with an agricultural expert.


## Additional crop-disease dataset: Sugarcane

- Dataset: [Sugarcane Leaf Disease Classification](https://huggingface.co/datasets/Project-AgML/sugarcane_leaf_disease_classification), based on Thite et al. (2024), DOI: 10.1016/j.dib.2024.110268.
- License declared by the dataset card: CC BY 4.0. Retain attribution to Thite, Suryawanshi, Patil, and Chumchu.
- Contains 6,748 field-collected images in 11 classes: Banded Chlorosis, Brown Spot, Brown Rust, Dried, Grassy Shoot, Healthy, Pokkah Boeng, Sett Rot, Smut, Viral Disease, and Yellow Leaf.
- The preparation script stores this as Sugarcane___<class> folders with a stratified 80/20 split. This is a random split because the dataset provides a single training split; it is not an author-provided independent test set.
- Install training-only dependencies with: python -m pip install -r backend/training-requirements.txt
- Run: python backend/scripts/prepare_sugarcane_dataset.py. This dataset preparation does not retrain the current Gemini or ten-reference disease modes.

**Coverage warning:** this adds Sugarcane source data but does not train the current classifier. Do not treat dataset presence as validated model support for the website's crops.


## 15-crop / 45-disease dataset (FC45DHLPD)

- Source: [Mendeley Data FC45DHLPD, version 1](https://data.mendeley.com/datasets/ph9g2cfxwm/1), DOI `10.17632/ph9g2cfxwm.1`.
- Author: Anand Kumar Jain and contributors; dataset institutions include MNIT Jaipur, Bikaner Technical University, and Kota Agriculture University / Rajasthan Agriculture Department.
- Published description lists Cashew, Cassava, Tomato, Potato, Maize, Papaya, Sugarcane, Rice, Chilli, Grapes, Citrus, Groundnut, Cotton, Wheat, and Soyabean. The ZIP is about 4.15 GB. Licence: CC BY 4.0. Cite the dataset and retain attribution.
- Download and prepare: `python backend/scripts/prepare_fc45_dataset.py`. If the automatic public API download fails, download the ZIP from the Mendeley page and run `python backend/scripts/prepare_fc45_dataset.py --archive "C:\\path\\to\\15 Crop 45 Disease and Healthy Leaf dataset.zip"`.
- These prepared images are not used by the Gemini or ten-reference disease modes.
- The prepared FC45 images are stored as local links/copies under the data directory. Do not commit the ZIP or extracted images to Git; they are multi-gigabyte data assets. The downloader emits `fc45_dataset_report.json` with detected classes and counts.
- The published title describes 15 crops and 45 disease/healthy categories; the preparation script reports the actual folder-derived crop and class counts instead of assuming a specific class count. Check that all 15 crops and expected classes are recognized before training.
- Do not present dataset preparation or image-folder counts as measured model accuracy.
The disease reference matcher uses HOG and color-histogram features with cosine similarity, not a field-validated diagnostic CNN. Its similarity score must not be treated as diagnostic confidence. Confirm disease and treatment with an agricultural expert; fertilizer recommendations are not cures and should be based on soil tests.
