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

## Plant disease images

- Dataset: PlantVillage, by Mohanty, Hughes, and Salathé (2016)
- Source: https://huggingface.co/datasets/mohanty/PlantVillage
- License declared on the Hugging Face dataset card: CC BY-SA 3.0
- Dataset card describes 54,306 images, 14 crop species, and 26 diseases.
- Downloaded archive: `plantvillage_data.zip`
- Extracted folders: `plant_disease/train/<Crop___Disease>/...` and `plant_disease/test/<Crop___Disease>/...`.

The downloader extracts only the RGB color images and uses the dataset's published `color_train.txt` and `color_test.txt` manifests. These splits preserve leaf grouping, avoiding the leakage that can occur when images of the same physical leaf are randomly split. Keep the attribution and share-alike terms with any redistributed adapted dataset or model; verify the source terms for your intended use.

The trained `backend/models/plant_disease_model.joblib` artifact is included in this repository. It is an adaptation trained from PlantVillage and is distributed under CC BY-SA 3.0. Attribution: Mohanty, Hughes, and Salathé (2016), PlantVillage ([dataset card](https://huggingface.co/datasets/mohanty/PlantVillage)); see the [CC BY-SA 3.0 license](https://creativecommons.org/licenses/by-sa/3.0/).

## Train the models

After the downloads and image preparation finish:

```powershell
python backend\scripts\train_crop_model.py
python backend\scripts\train_yield_model.py
python backend\scripts\train_disease_model.py
```

The resulting model files are written to `backend/models/`. The trained disease model is versioned with Git LFS; the other generated model files are excluded from Git. Each developer or deployment can download the datasets and train locally, or store model artifacts in an appropriate model registry.

## Important limitations

PlantVillage is a controlled-image research benchmark. The disease model uses HOG and color-histogram features with a linear classifier, not a field-validated diagnostic CNN. Its published split score must not be treated as field diagnostic accuracy. Confirm disease and treatment with an agricultural expert.


## Additional crop-disease dataset: Sugarcane

- Dataset: [Sugarcane Leaf Disease Classification](https://huggingface.co/datasets/Project-AgML/sugarcane_leaf_disease_classification), based on Thite et al. (2024), DOI: 10.1016/j.dib.2024.110268.
- License declared by the dataset card: CC BY 4.0. Retain attribution to Thite, Suryawanshi, Patil, and Chumchu.
- Contains 6,748 field-collected images in 11 classes: Banded Chlorosis, Brown Spot, Brown Rust, Dried, Grassy Shoot, Healthy, Pokkah Boeng, Sett Rot, Smut, Viral Disease, and Yellow Leaf.
- The preparation script stores this as Sugarcane___<class> folders alongside PlantVillage classes, with a stratified 80/20 split. This is a random split because the dataset provides a single training split; it is not an author-provided independent test set.
- Install training-only dependencies with: python -m pip install -r backend/training-requirements.txt
- Run: python backend/scripts/prepare_sugarcane_dataset.py, then python backend/scripts/train_disease_model.py.

**Coverage warning:** this adds Sugarcane; it does not yet provide validated disease datasets for every crop in the website's 24-crop selector. The current PlantVillage model plus this dataset must not be advertised as supporting all 24 crops. Rice, Wheat, Cotton, Groundnut, Onion, Coconut, Arecanut, Ragi, Jowar, Bajra, Sunflower, Mustard, Chilli, Brinjal, Cabbage, Cauliflower, Banana, Mango, and other crops require their own verified image coverage and crop-specific evaluation before activation. A crop absent from the trained class list remains unsupported.


## 15-crop / 45-disease dataset (FC45DHLPD)

- Source: [Mendeley Data FC45DHLPD, version 1](https://data.mendeley.com/datasets/ph9g2cfxwm/1), DOI `10.17632/ph9g2cfxwm.1`.
- Author: Anand Kumar Jain and contributors; dataset institutions include MNIT Jaipur, Bikaner Technical University, and Kota Agriculture University / Rajasthan Agriculture Department.
- Published description lists Cashew, Cassava, Tomato, Potato, Maize, Papaya, Sugarcane, Rice, Chilli, Grapes, Citrus, Groundnut, Cotton, Wheat, and Soyabean. The ZIP is about 4.15 GB. Licence: CC BY 4.0. Cite the dataset and retain attribution.
- Download and prepare: `python backend/scripts/prepare_fc45_dataset.py`. If the automatic public API download fails, download the ZIP from the Mendeley page and run `python backend/scripts/prepare_fc45_dataset.py --archive "C:\\path\\to\\15 Crop 45 Disease and Healthy Leaf dataset.zip"`.
- Then train: `python backend/scripts/train_disease_model.py`. The script combines the new class folders with the existing PlantVillage and Sugarcane folders under `backend/data/plant_disease/train` and `test`.
- The prepared FC45 images are stored as local links/copies under the data directory. Do not commit the ZIP or extracted images to Git; they are multi-gigabyte data assets. The downloader emits `fc45_dataset_report.json` with detected classes and counts.
- The published title describes 15 crops and 45 disease/healthy categories; the preparation script reports the actual folder-derived crop and class counts instead of assuming a specific class count. Check that all 15 crops and expected classes are recognized before training.
- The existing HOG + colour histogram SGD classifier is a lightweight baseline. It is not a modern deep-learning model and should be validated on independent field photos before being used for farm decisions. A random image split may contain near-duplicates; do not present its score as field accuracy.
