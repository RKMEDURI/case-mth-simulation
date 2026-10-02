# Public Cloud Deployment Guide - CASE-MTH Web Application

This guide explains step-by-step how to make your **CASE-MTH Simulation Engine Web Dashboard** publicly accessible online so anyone on the internet can use it.

---

## Pre-requisites (Git Repository)

Before deploying to any platform, push your project code to a public or private GitHub repository:

```bash
cd C:\Users\rkkme\.gemini\antigravity\scratch\case_mth_simulation

# Initialize Git (if not already done)
git init
git add .
git commit -m "Initial commit of CASE-MTH Simulation Web App"

# Create a new repository on GitHub (github.com/new) and link it:
git remote add origin https://github.com/YOUR_USERNAME/case-mth-simulation.git
git branch -M main
git push -u origin main
```

---

## Option 1: Render.com (Recommended - Free Tier & Easiest)

Render provides free hosting for Python Flask web applications with automatic SSL/HTTPS certificates and automatic GitHub deploys.

### Steps:
1. Go to [https://render.com](https://render.com) and sign up for a free account.
2. Click **New +** $\to$ **Web Service**.
3. Connect your GitHub account and select your `case-mth-simulation` repository.
4. Fill in the service configuration:
   - **Name**: `case-mth-simulation` (or custom name)
   - **Region**: Choose closest to your users (e.g. Frankfurt, Oregon, Singapore)
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Instance Type**: `Free`
5. Click **Create Web Service**.
6. Render will build and deploy your app in 2-3 minutes and provide a public URL like `https://case-mth-simulation.onrender.com`.

---

## Option 2: Hugging Face Spaces (Free & Great for Academic/AI Demos)

Hugging Face Spaces offers completely free hosting with generous CPU/RAM resources.

### Steps:
1. Go to [https://huggingface.co/spaces](https://huggingface.co/spaces) and create an account.
2. Click **Create new Space**.
3. Set:
   - **Space Name**: `case-mth-simulation`
   - **License**: `mit`
   - **Select Space SDK**: `Docker` $\to$ `Blank`
4. Clone the space repository locally or upload your project files (`app.py`, `templates/`, `config.py`, `Dockerfile`, etc.) directly via the Hugging Face web UI.
5. Hugging Face will automatically build the Docker image using the provided `Dockerfile` and publish your app live at `https://huggingface.co/spaces/YOUR_USERNAME/case-mth-simulation`.

---

## Option 3: Railway.app (Instant 1-Click Deploy)

Railway automatically detects Python/Flask projects via `Procfile` and `requirements.txt`.

### Steps:
1. Go to [https://railway.app](https://railway.app) and log in with GitHub.
2. Click **New Project** $\to$ **Deploy from GitHub repo**.
3. Select `case-mth-simulation`.
4. Railway will auto-detect Gunicorn and deploy.
5. Go to **Settings** $\to$ **Domains** $\to$ **Generate Domain** to get a public URL (e.g. `https://case-mth-simulation.up.railway.app`).

---

## Option 4: Google Cloud Run (Containerized Enterprise Cloud)

For production scalability using Docker containers on Google Cloud Platform (GCP).

### Steps:
```bash
# Authenticate gcloud CLI
gcloud auth login
gcloud config set project YOUR_GCP_PROJECT_ID

# Build and submit Docker image to Google Artifact Registry
gcloud builds submit --tag gcr.io/YOUR_GCP_PROJECT_ID/case-mth-app

# Deploy to Cloud Run
gcloud run deploy case-mth-app \
  --image gcr.io/YOUR_GCP_PROJECT_ID/case-mth-app \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```
GCP will output a live HTTPS URL.

---

## Generated Deployment Configuration Files

All required deployment config files have been automatically created in your workspace:
- [`requirements.txt`](file:///C:/Users/rkkme/.gemini/antigravity/scratch/case_mth_simulation/requirements.txt) – Python package dependencies
- [`Procfile`](file:///C:/Users/rkkme/.gemini/antigravity/scratch/case_mth_simulation/Procfile) – Production Gunicorn process runner
- [`Dockerfile`](file:///C:/Users/rkkme/.gemini/antigravity/scratch/case_mth_simulation/Dockerfile) – Docker container definition
