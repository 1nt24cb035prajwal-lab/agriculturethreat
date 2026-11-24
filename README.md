# Agriculture Threat Fusion

A farmer-focused agriculture platform for farm records, AI crop-disease image screening, a farmer AI chat assistant, weather, water planning, mandi prices, yield estimates, and saved activity.

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
- Mandi prices: in-app price results use the data.gov.in API and require `DATA_GOV_IN_API_KEY` and, if needed, `DATA_GOV_IN_MARKET_RESOURCE_ID`.
- Weather threat alerts: current farm weather and a seven-day forecast from Open-Meteo are checked for configured heat, cold, strong-wind, and heavy-rain thresholds. Alerts refresh on dashboard load and every 15 minutes while open. These are weather indicators only, not pest/disease diagnoses or official emergency warnings.
- Yield: regional yield estimate from the trained India crop-production model when available; this is historical and not a farm-level or weather-adjusted forecast. See [dataset and licensing notes](backend/data/README.md).

External integrations remain unavailable until their provider credentials and subscriptions are configured. The application should not display fabricated live readings.

## Download datasets and train models

From the repository root, install the backend dependencies and download the crop and yield datasets:

```powershell
.\\.venv\\Scripts\\python.exe -m pip install -r backend\\requirements.txt
.\\.venv\\Scripts\\python.exe backend\\scripts\\download_datasets.py
```

The downloader prepares:

- `backend/data/crop_recommendation.csv`: the 2,200-row crop recommendation dataset with N, P, K, temperature, humidity, pH, rainfall, and crop label columns. It prefers the Kaggle CLI if configured and otherwise uses a public Hugging Face CSV mirror.
- `backend/data/india_crop_production.csv`: historical state/district/crop/season/area/production records used to derive yield in tonnes per hectare.

Train the crop recommendation and yield models:

```powershell
.\\.venv\\Scripts\\python.exe backend\\scripts\\train_crop_model.py
.\\.venv\\Scripts\\python.exe backend\\scripts\\train_yield_model.py
```

The crop trainer validates the eight required columns, requires at least 30 labelled rows and two crop classes, performs a stratified 80/20 hold-out split, reports validation accuracy, and writes `backend/models/crop_recommendation_model.joblib`. The yield trainer holds out the latest years, reports MAE, RMSE, R², and a within-25%-of-observed rate, and writes `backend/models/yield_prediction_model.joblib`. The app loads trained models when available. The crop and yield model files are generated locally.

To build the ten-photo disease reference prototype, pass the supplied ZIP to the trainer:

```powershell
.\\.venv\\Scripts\\python.exe backend\\scripts\\train_disease_model.py "C:\\path\\to\\dataset_@1.zip"
```

This writes `backend/models/plant_disease_reference_model.joblib`. The app matches uploads to the closest of one reference image per disease and reports visual similarity—not diagnostic confidence or measured accuracy.

Dataset archives and generated crop and yield model files are excluded from Git to avoid committing large data or build artifacts. The downloader no longer downloads PlantVillage; existing local PlantVillage files are left untouched and unused. See [backend/data/README.md](backend/data/README.md).

The yield dataset mirror marks its license unknown; check the original Kaggle terms before redistribution or commercial use.

**Disease-model limitations:** Gemini can make mistakes, and one photograph cannot confirm a field diagnosis. Disease-specific fertilizer notes are nutritional support only; fertilizer does not cure fungal, bacterial, or viral infections. Confirm disease and nutrient needs with a local agricultural expert and soil test.

**Other model limitations:** the crop recommendation dataset is a benchmark and does not guarantee crop suitability in a specific field. Yield estimates use regional historical production records, do not include weather, variety, soil, or farm-level observations, and report temporal holdout metrics for transparency.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

The GitHub Actions workflow runs the backend regression tests on pull requests.

## Disease detection and weather forecast

Disease photo analysis screens the upload with Gemini Vision first. Non-plant images are rejected with 0% confidence and a request to upload a clear plant photo. Plant images are then checked for possible disease symptoms with cautious guidance; this is not a confirmed field diagnosis.

The farm dashboard retrieves a live seven-day Open-Meteo forecast for saved farm coordinates, including temperature, rainfall probability, rainfall totals, and FAO reference evapotranspiration. It refreshes automatically every 15 minutes and can be refreshed manually.



## Plant disease detection setup

Disease photo screening, disease guidance, and the farmer chat assistant use Google's Gemini API with the `gemini-2.5-flash-lite` model by default. Create a free-tier API key in Google AI Studio and add it to Render as `GEMINI_API_KEY`. The optional `GEMINI_MODEL` setting selects another supported Gemini model.

Google's Gemini API free tier has model-specific rate limits and availability; usage is not unlimited. Review Google's current pricing and rate-limit pages before using the app with many users. The chatbot gives general farming guidance, while image analysis is not a confirmed field diagnosis. Non-plant images are screened before disease analysis.


