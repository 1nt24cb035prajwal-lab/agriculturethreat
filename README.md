# Agriculture Threat Fusion

A full-stack agriculture monitoring prototype for farmer profiles, crop recommendations, disease-image review, weather, water planning, satellite NDVI, mandi prices, yield estimates, and saved activity.

## Run locally

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r backend\test-requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload
```

Open http://localhost:8000.

Copy local provider settings:

```powershell
copy backend\.env.example backend\.env
```

The application automatically loads `backend/.env` at startup, so the normal Uvicorn command above is enough. Never commit `.env` or paste provider secrets into source control.

## Google-only farmer authentication

The farmer-facing sign-in uses Google OAuth. A first-time Google sign-in creates a farmer account after Google returns a verified email. Existing accounts are linked by verified email. After sign-in, the farmer fills in farm, crop, soil, and map-location details in the dashboard. Twilio OTP and phone-based passwords are not required for the sign-in flow.

In Google Cloud Console, create an OAuth 2.0 **Web application** client. Add these local values:

- Authorized JavaScript origin: `http://localhost:8000`
- Authorized redirect URI: `http://localhost:8000/auth/google/callback`

Copy the client ID and secret into `backend/.env` and set:

```dotenv
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
COOKIE_SECURE=false
```

Restart the server after changing `.env`, then open the app using exactly `http://localhost:8000` (do not switch to `127.0.0.1` during the Google redirect). If the OAuth consent screen is in Testing mode, add the Google account you are signing in with as a test user. Production deployments must use HTTPS and the exact production callback URI.

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

The crop trainer validates the eight required columns, requires at least 30 labelled rows and two crop classes, performs a stratified 80/20 hold-out split, reports validation accuracy, and writes `backend/models/crop_recommendation_model.joblib`. The yield trainer holds out the latest years, reports MAE, RMSE, R², and a within-25%-of-observed rate, and writes `backend/models/yield_prediction_model.joblib`. The disease trainer uses PlantVillage's published color train/test manifests (which preserve the dataset's leaf grouping), reports test accuracy and macro-F1, and writes `backend/models/plant_disease_model.joblib`. The app loads trained models when available. Generated model files are not tracked by Git; download the datasets and run the training scripts after cloning.

Dataset and model binaries are excluded from Git to avoid committing a 2.2 GB image archive or generated model files. The download script and source/licence details are tracked in the repository; run the downloader after cloning. See [backend/data/README.md](backend/data/README.md).

The PlantVillage dataset card declares CC BY-SA 3.0 and describes 54,306 images across 14 crop species and 26 diseases. Retain attribution and review share-alike terms before redistributing adapted data or models. The yield dataset mirror marks its license unknown; check the original Kaggle terms before redistribution or commercial use.

**Model limitations:** the crop recommendation dataset is a benchmark and does not guarantee crop suitability in a specific field. Yield estimates use regional historical production records, do not include weather, variety, soil, or farm-level observations, and report temporal holdout metrics for transparency. PlantVillage images are controlled research images; the disease classifier is not a field-validated CNN, and diagnoses should be confirmed by an agricultural expert.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

The GitHub Actions workflow runs the backend regression tests on pull requests.
