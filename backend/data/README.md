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

The yield trainer evaluates on later years that are excluded from training and reports MAE, RMSE, R², and the share of predictions within 25% of observed yield. It trains on all valid rows after the holdout evaluation, uses the 254 most common districts plus an "other" bucket, and retains all supported crop labels. This is regional historical data, not a farm-level yield benchmark.

## Plant disease images

- Dataset: PlantVillage, by Mohanty, Hughes, and Salathé (2016)
- Source: https://huggingface.co/datasets/mohanty/PlantVillage
- License declared on the Hugging Face dataset card: CC BY-SA 3.0
- Dataset card describes 54,306 images, 14 crop species, and 26 diseases.
- Downloaded archive: `plantvillage_data.zip`
- Extracted folders: `plant_disease/train/<Crop___Disease>/...` and `plant_disease/test/<Crop___Disease>/...`.

The downloader extracts only the RGB color images and uses the dataset's published `color_train.txt` and `color_test.txt` manifests. These splits preserve leaf grouping, avoiding the leakage that can occur when images of the same physical leaf are randomly split. Keep the attribution and share-alike terms with any redistributed adapted dataset or model; verify the source terms for your intended use.

## Train the models

After the downloads and image preparation finish:

```powershell
python backend\scripts\train_crop_model.py
python backend\scripts\train_yield_model.py
python backend\scripts\train_disease_model.py
```

The resulting model files are written to `backend/models/`. They are deliberately excluded from Git because they are generated artifacts and may be large. Each developer or deployment should download the datasets and train locally, or store the model artifacts in an appropriate model registry.

## Important limitations

PlantVillage is a controlled-image research benchmark. The disease model uses HOG and color-histogram features with a linear classifier, not a field-validated diagnostic CNN. Its published split score must not be treated as field diagnostic accuracy. Confirm disease and treatment with an agricultural expert.
