# Agriculture Threat Fusion

A full-stack agriculture monitoring prototype for farmer profiles, crop recommendations, disease-image review, weather, water planning, satellite NDVI, mandi prices, yield estimates, and saved activity.

## Run locally

On Windows, run `run_local.bat` from the repository root. It starts the
FastAPI backend, waits for its health check, and opens the full app at
http://localhost:8000. If dependencies are missing, install them as shown
below.

To start the backend manually from the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r backend\test-requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Open http://localhost:8000.

The repository-root `index.html` is a static GitHub Pages landing page, and
`frontend/` is a separate Vite preview. Neither starts the full backend app;
use the FastAPI command above (or `run_local.bat` on Windows).

## Public deployment

The GitHub Pages URL is a static landing page and cannot run the FastAPI backend. Deploy the backend using the **Deploy the backend** button on the Pages site or open the [Render Blueprint deployment](https://render.com/deploy?repo=https://github.com/1nt24cb035prajwal-lab/agriculturethreat). Once the Render service `agriculture-threat-fusion` finishes deploying, the **Open the app** button on the Pages site opens the full application.

The farmer app uses its own name/mobile/email and password authentication. Google OAuth credentials are not required. The GitHub Pages URL is a static landing page; deploy the FastAPI backend to Render for the full application.

Copy local provider settings:

```powershell
copy backend\.env.example backend\.env
```

The application automatically loads `backend/.env` at startup, so the normal Uvicorn command above is enough. Never commit `.env` or paste provider secrets into source control.

## Farmer login and registration

Farmers register with their full name, mobile number, email address, and password. After registration, the app creates a farmer record and signs the farmer in automatically. On later visits, farmers can log in using their full name, mobile number, or email address together with their password. Passwords are stored as salted PBKDF2-SHA256 hashes; plain-text passwords are never stored. Phone OTP is not required for basic account creation or login.

Farmer accounts, farm profiles, sessions, and activity history are stored in SQLite. Render's default filesystem is ephemeral, so configure a persistent disk or move to a managed database before relying on long-term production records. Never commit passwords or provider secrets to Git.

## Farmer data and integrations

Farmer accounts, farm profiles, image records, and activity history are stored in SQLite. Each authenticated farmer can save farm name, crop and variety, crop stage, land area, season, soil measurements, irrigation details, coordinates, and administrative location fields.

- Weather and forecast: Open-Meteo, using saved farm coordinates.
- Location search and reverse geocoding: OpenStreetMap Nominatim.
- Satellite NDVI: Sentinel Hub Sentinel-2 L2A point sample; configure `SENTINELHUB_CLIENT_ID` and `SENTINELHUB_CLIENT_SECRET`.
- Mandi prices: the farmer dashboard links directly to the [Agmarknet visualization dashboard](https://visualize.data.gov.in/?inst=9ef84268-d588-465a-a308-a864a43d0070). In-app price results use the data.gov.in API and require `DATA_GOV_IN_API_KEY` and, if needed, `DATA_GOV_IN_MARKET_RESOURCE_ID`.
- Weather threat alerts: current farm weather and a seven-day forecast from Open-Meteo are checked for configured heat, cold, strong-wind, and heavy-rain thresholds. Alerts refresh on dashboard load and every 15 minutes while open. These are weather indicators only, not pest/disease diagnoses or official emergency warnings.
- Yield: regional yield estimate from the trained India crop-production model when available; this is historical and not a farm-level or weather-adjusted forecast. See [dataset and licensing notes](backend/data/README.md).

External integrations remain unavailable until their provider credentials and subscriptions are configured. The application should not display fabricated live readings.

## Download datasets and train models

From the repository root, install the backend dependencies and download both datasets:

```powershell
.\\.venv\\Scripts\\python.exe -m pip install -r backend\\requirements.txt
.\\.venv\\Scripts\\python.exe backend\\scripts\\download_datasets.py
```

The downloader prepares:

- `backend/data/crop_recommendation.csv`: the 2,200-row crop recommendation dataset with N, P, K, temperature, humidity, pH, rainfall, and crop label columns. It prefers the Kaggle CLI if configured and otherwise uses a public Hugging Face CSV mirror.
- `backend/data/india_crop_production.csv`: historical state/district/crop/season/area/production records used to derive yield in tonnes per hectare.
- `backend/data/plantvillage_data.zip` and `backend/data/plant_disease/train/<Crop___Disease>/...` plus `test/<Crop___Disease>/...`: the PlantVillage color images (about 2.2 GB) arranged using the published train/test manifests.

Train the crop recommendation model and disease image model:

```powershell
.\\.venv\\Scripts\\python.exe backend\\scripts\\train_crop_model.py
.\\.venv\\Scripts\\python.exe backend\\scripts\\train_yield_model.py
.\\.venv\\Scripts\\python.exe backend\\scripts\\train_disease_model.py
```

The crop trainer validates the eight required columns, requires at least 30 labelled rows and two crop classes, performs a stratified 80/20 hold-out split, reports validation accuracy, and writes `backend/models/crop_recommendation_model.joblib`. The yield trainer holds out the latest years, reports MAE, RMSE, R², and a within-25%-of-observed rate, and writes `backend/models/yield_prediction_model.joblib`. The disease trainer uses PlantVillage's published color train/test manifests (which preserve the dataset's leaf grouping), reports test accuracy and macro-F1, and writes `backend/models/plant_disease_model.joblib`. The app loads trained models when available. The crop and yield model files are generated locally; the trained disease model is included in Git. See [backend/data/README.md](backend/data/README.md) for its attribution and license.

Dataset archives and generated crop and yield model files are excluded from Git to avoid committing large data or build artifacts. The download script and source/licence details are tracked in the repository; run the downloader after cloning. See [backend/data/README.md](backend/data/README.md).

The PlantVillage dataset card declares CC BY-SA 3.0 and describes 54,306 images across 14 crop species and 26 diseases. Retain attribution and review share-alike terms before redistributing adapted data or models. The yield dataset mirror marks its license unknown; check the original Kaggle terms before redistribution or commercial use.

**Model limitations:** the crop recommendation dataset is a benchmark and does not guarantee crop suitability in a specific field. Yield estimates use regional historical production records, do not include weather, variety, soil, or farm-level observations, and report temporal holdout metrics for transparency. PlantVillage images are controlled research images; the disease classifier is not a field-validated CNN, and diagnoses should be confirmed by an agricultural expert.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

The GitHub Actions workflow runs the backend regression tests on pull requests.

## Disease detection and weather forecast

The disease classifier uses the PlantVillage RGB image benchmark and predicts crop-specific classes (38 labels across 14 crop species). The checked-in trained model reports 54,305 labelled images, 10,709 held-out test images, 76.9% held-out accuracy, and 71.8% macro-F1. These are controlled-dataset metrics, not guaranteed field accuracy. The app displays the crop/disease class, top model matches, symptoms, and conservative integrated pest-management guidance. If the trained model is unavailable, the app does not silently substitute synthetic predictions.

To retrain after downloading the PlantVillage dataset, run:

```powershell
python backend\scripts\download_datasets.py --skip-crop --skip-yield
python backend\scripts\train_disease_model.py
```

The farm dashboard retrieves a live seven-day Open-Meteo forecast for saved farm coordinates, including temperature, rainfall probability, rainfall totals, and FAO reference evapotranspiration. It refreshes automatically every 15 minutes and can be refreshed manually.


## Plant disease detection setup

Disease photo analysis uses the fine-tuned MobileNetV2 PlantVillage classifier through Hugging Face Inference Providers. Add a fine-grained Hugging Face token with **Make calls to Inference Providers** permission as the `HF_TOKEN` environment variable in the Render service. Do not put the token in source code or commit it.

The model covers the 38 PlantVillage classes across 14 crops; crops outside those classes are not diagnosed by this model. Results are image-based guidance, not a confirmed field diagnosis. The disease page provides a Google Images search link for visual comparison; Google Images is a reference aid and is not used as the model or as proof of diagnosis.

Model reference: https://huggingface.co/linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification
