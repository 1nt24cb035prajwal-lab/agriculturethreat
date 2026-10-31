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

To load local provider settings, copy `backend/.env.example` to `backend/.env` and start with:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --env-file backend\.env
```

Never commit `.env` or paste provider secrets into source control.

## Google-only farmer authentication

The farmer-facing sign-in uses Google OAuth. A first-time Google sign-in creates a farmer account after Google returns a verified email. Existing accounts are linked by verified email. After sign-in, the farmer fills in farm, crop, soil, and map-location details in the dashboard. Twilio OTP and phone-based passwords are not required for the sign-in flow.

In Google Cloud, create an OAuth 2.0 Web application client and add this exact local redirect URI:

`http://localhost:8000/auth/google/callback`

Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI` in the server environment. Production deployments must use HTTPS and the matching production callback URI.

## Farmer data and integrations

Farmer accounts, farm profiles, image records, and activity history are stored in SQLite. Each authenticated farmer can save farm name, crop and variety, crop stage, land area, season, soil measurements, irrigation details, coordinates, and administrative location fields.

- Weather and forecast: Open-Meteo, using saved farm coordinates.
- Location search and reverse geocoding: OpenStreetMap Nominatim.
- Satellite NDVI: Sentinel Hub Sentinel-2 L2A point sample; configure `SENTINELHUB_CLIENT_ID` and `SENTINELHUB_CLIENT_SECRET`.
- Mandi prices: data.gov.in Agmarknet resource; configure `DATA_GOV_IN_API_KEY` and, if needed, `DATA_GOV_IN_MARKET_RESOURCE_ID`.
- Yield: low-confidence reference-range estimate, not a trained regional yield model.

External integrations remain unavailable until their provider credentials and subscriptions are configured. The application should not display fabricated live readings.

## Training the crop recommendation model

The repository does not currently include a licensed real-world crop training dataset. The fallback recommender uses 18 hand-entered demo records and must not be represented as a validated agronomic model.

To train with a real labelled dataset:

1. Create `backend/data/`.
2. Place the licensed CSV at `backend/data/crop_recommendation.csv`.
3. Ensure it contains these exact columns: `N,P,K,temperature,humidity,ph,rainfall,label`.
4. From the repository root, run:

```powershell
.\.venv\Scripts\python.exe backend\scripts\train_crop_model.py
```

The trainer validates the required columns, requires at least 30 labelled rows and two crop classes, performs a stratified 80/20 hold-out split, reports validation accuracy, and writes the model to `backend/models/crop_recommendation_model.joblib`. The application automatically loads a trained CSV model when it is newer than the saved model file. Missing soil NPK or pH values are imputed from the training data's median.

Do not commit private or restricted datasets or generated model binaries. A validation score on one dataset is not a guarantee of crop suitability in a particular field.

## Disease model limitation

The current disease-image classifier still trains on synthetic image-feature samples. It is a software prototype, not a validated plant-disease diagnosis. A real disease-image dataset (for example, a properly licensed folder of crop/disease-labelled images) is still required before a trustworthy image model can be trained. Farmers should confirm suspected disease and treatment with a local agricultural expert.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
```

The GitHub Actions workflow runs the backend regression tests on pull requests.
