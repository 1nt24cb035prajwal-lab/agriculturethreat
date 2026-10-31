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

This project includes realistic demo data and clearly labeled demo-mode outputs for AI and external data services.

## Farmer map and recommendations

After login, enter the current crop, soil, season, farm area, weather estimates, and location. The OpenStreetMap picker updates latitude and longitude when the map is clicked or its pin is moved. The browser's location button requires permission; map tiles require an internet connection. Those coordinates and farm inputs are sent to `POST /api/farm/recommendation`. Camera/gallery images and the same farm profile are sent to `POST /api/disease/analyze`.

## Model limitations

The built-in crop recommender is a prototype trained on 18 in-code records across nine crop categories. The image classifier is also trained on synthetic samples. Neither model is a verified agricultural diagnostic or covers every crop, cultivar, disease, or growing region. Do not use the predictions alone to select treatments; field verification and a locally validated dataset/model are needed before production use. No Google or other external dataset is downloaded automatically.

To run the backend regression tests, install `backend/test-requirements.txt`, then run `pytest backend/tests` from the project root.
