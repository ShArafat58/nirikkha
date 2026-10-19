# Nirikkha frontend (Next.js)

The frontend talks to the backend ONLY through the REST API (see `../docs/API.md`).
All API calls live in `src/lib/api.ts`. Never import anything from `../backend`.

## Quick start (no Python, no database, no keys needed)

Windows PowerShell:

    cd frontend
    npm install
    Copy-Item .env.example .env.local
    npm run dev

Mac / Linux:

    cd frontend
    npm install
    cp .env.example .env.local
    npm run dev

Open http://localhost:3000

## Choose what the frontend talks to (edit `.env.local`)

| Goal | NEXT_PUBLIC_API_URL | NEXT_PUBLIC_USE_MOCK |
|---|---|---|
| Design work, no backend | (anything) | `true` |
| Use the live backend | `https://nirikkha-api.onrender.com` | `false` |
| Use a local backend | `http://localhost:8000` | `false` |

The live backend is on a free server: the first request can take ~50 seconds to wake it up.

## Before you push

    npm run build

The build must pass with no errors.