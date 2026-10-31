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

Registration validates credentials and stores a phone as unverified. SMS OTP, Google OAuth, email recovery, admin accounts, and role-based administration are not configured, so the app does not claim that a phone was verified and password recovery returns an unavailable-integration response rather than a fixed OTP.

## Farmer map and recommendations

After login, enter the current crop, soil, season, farm area, weather estimates, and location. The OpenStreetMap picker updates latitude and longitude when the map is clicked or its pin is moved. The browser's location button requires permission; map tiles require an internet connection. Those coordinates and farm inputs are sent to `POST /api/farm/recommendation`. Camera/gallery images and the same farm profile are sent to `POST /api/disease/analyze`.

## Model limitations

The built-in crop recommender is a prototype trained on 18 in-code records across nine crop categories. The image classifier is also trained on synthetic samples. Neither model is a verified agricultural diagnostic or covers every crop, cultivar, disease, or growing region. Validated disease photos are stored in SQLite and served only to their owning authenticated farmer. Do not use predictions alone to select treatments; field verification and a locally validated dataset/model are needed before production use. No Google or other external dataset is downloaded automatically.

Weather forecasts, satellite/NDVI, market prices, nearby markets, SMS/email alerts, OAuth, and admin roles are not configured. Their API routes do not provide fake current readings. Connect a licensed/provider API with server-side credentials before representing those values as current. OpenStreetMap tiles and Leaflet are used for the interactive location picker; exact village/taluk reverse geocoding is not yet configured.

To run the backend regression tests, install `backend/test-requirements.txt`, then run `pytest backend/tests` from the project root.
