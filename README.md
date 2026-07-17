# Car Parking Multiplayer Account Modifier

This repository contains a small Flask app to perform actions on Car Parking Multiplayer (CPM) accounts.

Quick deployment notes for Railway:

1. Create a new project on Railway and connect your GitHub repository (this repo).
2. Railway will detect Python; ensure the project uses the `main` branch.
3. In Railway, set environment variables if desired:
   - FLASK_SECRET: your secret key (recommended for production)
4. Deploy. Railway will use the Procfile which runs `web: python app.py`.

Run locally:

1. python -m venv venv
2. source venv/bin/activate  (or `venv\Scripts\activate` on Windows)
3. pip install -r requirements.txt
4. python app.py
5. Visit http://127.0.0.1:5000

Note: Replace the stub async implementations in cpm_nuker.py with the real CPM logic when available.