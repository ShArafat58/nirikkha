# Nirikkha backend (FastAPI)

## Run locally (Windows PowerShell)

    cd backend
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    Copy-Item .env.example .env   # then fill in real values
    python -m pytest -q
    uvicorn app.main:app --reload --port 8000

Open http://localhost:8000/health and http://localhost:8000/docs

## Run locally (Mac / Linux)

    cd backend
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    cp .env.example .env   # then fill in real values
    python -m pytest -q
    uvicorn app.main:app --reload --port 8000

## Run with Docker (any Docker host)

    docker build -t nirikkha-api backend
    docker run --rm --env-file backend/.env -p 7860:7860 nirikkha-api

Open http://localhost:7860/health

## Deploy (Render, free web service)

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`
- Environment variables: everything in `.env.example`, plus `APP_ENV=production` and `PYTHON_VERSION=3.12.3`

## Environment variables

See `.env.example`. Never commit `.env`.
## Local ingestion (offline, on a developer machine)

Heavy parsing / chunking runs locally, not on the 512 MB server:

    pip install -r requirements-ingest.txt
    python -m app.ingest.parse 719739 --before 2023-03-10
    python -m app.ingest.chunk
