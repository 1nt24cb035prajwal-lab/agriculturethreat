# agriculturethreat

# Agriculture Threat Fusion

A demo-ready full-stack agriculture monitoring prototype built to match the requested workflow: farmer registration, weather monitoring, disease prediction, water recommendations, fertilizer insights, yield forecasting, and agricultural threat detection.

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies:
   `pip install -r backend/requirements.txt`
3. Start the app:
   `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload`
4. Open http://localhost:8000

## Project structure

- `backend/` - FastAPI server and static frontend assets
- `frontend/` - React/Vite scaffold aligned with the requested stack

The authenticated dashboard reads each farmer's saved farm profile and activity. External feeds that are not configured are displayed as unavailable; they are not returned as plausible-looking sample measurements. Crop and image models remain prototype ML outputs.

## Accounts and persistence

Farmer accounts, PBKDF2 password hashes, HTTP-only login sessions, farm profiles, and activity history are stored in SQLite at `backend/agriculture.sqlite3` by default. Set `AGRI_DATABASE_PATH` to choose another database file. Set `COOKIE_SECURE=true` when serving the app over HTTPS. Do not expose the development server directly to the public internet.

Registration validates credentials and stores a phone as unverified unless Twilio Verify is configured and the user completes the OTP step. Google OAuth can sign in an existing farmer account whose email matches a Google-verified email. New Google users must register first. Password recovery and admin roles are still not configured.

## Farmer map and recommendations

After login, enter the current crop, soil, season, farm area, weather estimates, and location. The OpenStreetMap picker updates latitude and longitude when the map is clicked or its pin is moved. The browser's location button requires permission; map tiles require an internet connection. Those coordinates and farm inputs are sent to `POST /api/farm/recommendation`. Camera/gallery images and the same farm profile are sent to `POST /api/disease/analyze`.

## Model limitations

The built-in crop recommender is a prototype trained on 18 in-code records across nine crop categories. The image classifier is also trained on synthetic samples. Neither model is a verified agricultural diagnostic or covers every crop, cultivar, disease, or growing region. Validated disease photos are stored in SQLite and served only to their owning authenticated farmer. Do not use predictions alone to select treatments; field verification and a locally validated dataset/model are needed before production use. No Google or other external dataset is downloaded automatically.

Current conditions and a seven-day forecast are fetched from Open-Meteo using the saved farm coordinates. Place search and reverse geocoding use OpenStreetMap Nominatim; service availability and its usage policy apply. Sentinel-2 NDVI, Agmarknet mandi prices, Twilio OTP, and Google OAuth now have configurable server-side adapters. They remain unavailable until the provider credentials below are supplied. The yield estimate is a low-confidence reference-range calculation, not a trained district-level model. Admin roles and password recovery remain unconfigured.

### Provider configuration\n\nCopy `backend/.env.example` to `backend/.env` and set only the providers you have configured. Install requirements first; Uvicorn loads this file through python-dotenv. Start with `uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload --env-file backend/.env` when you have created that file. Never commit real keys.\n\n- Google Cloud: create an OAuth 2.0 Web client and add the exact callback URL `http://localhost:8000/auth/google/callback` (production must use HTTPS). Set `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, and `GOOGLE_REDIRECT_URI`. Google login is for existing registered farmer emails.\n- Twilio: create a Verify service and set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_VERIFY_SERVICE_SID`. OTP is mandatory at registration when these are all present. Enter phone numbers in E.164 format.\n- Sentinel Hub: create an OAuth client with Process API access and set `SENTINELHUB_CLIENT_ID` and `SENTINELHUB_CLIENT_SECRET`. The satellite endpoint requests a cloud-filtered Sentinel-2 L2A point sample around the saved farm coordinate; it is not a full-field zonal mean.\n- data.gov.in: subscribe to the Agmarknet daily mandi prices resource and set `DATA_GOV_IN_API_KEY`. Resource ID can be overridden with `DATA_GOV_IN_MARKET_RESOURCE_ID`. Prices are reported arrivals, not guaranteed farm-gate offers.\n\nSet `COOKIE_SECURE=true` in HTTPS production. Do not commit `.env` files.\n\nTo run the backend regression tests, install `backend/test-requirements.txt`, then run `pytest backend/tests` from the project root.
