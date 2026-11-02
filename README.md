# Campaign Launcher

A beta prototype for preparing and launching advertising campaigns from reusable templates. The project includes a FastAPI backend, PostgreSQL persistence, a background job worker, and a React + TypeScript frontend.

> **Integration status:** TikTok Marketing API access is not enabled yet. Campaign creation currently uses `FakePlatform`, which simulates successful or failed campaign creation. The TikTok OAuth endpoints currently create and validate one-time `state` values; they do not exchange authorization codes for TikTok access tokens.

## Features

- User registration and login with password hashing and JWT bearer authentication.
- User-owned campaign templates and launch jobs.
- Ownership checks so users can access only their own templates and jobs.
- Background processing of campaign launch items with per-item status, error information, and retry attempts.
- A React interface for registration, login, creating templates, launching jobs, and viewing job status.
- Alembic database migrations and integration tests.

## Tech stack

- Python, FastAPI, Pydantic
- SQLAlchemy, PostgreSQL, Alembic
- JWT authentication and Argon2 password hashing
- React, TypeScript, Vite
- Docker Compose for local PostgreSQL

## Requirements

- Python 3.13 (or a compatible supported Python version)
- Node.js and npm
- Docker Desktop with the Docker engine running

## Local setup (Windows PowerShell)

Run these commands from the repository root.

### 1. Create and activate the Python environment

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

If PowerShell blocks activation, use a terminal where script activation is allowed, or invoke the environment's Python directly as `.\.venv\Scripts\python.exe`.

### 2. Configure environment variables

Create a `.env` file in the repository root. Keep it local; `.env` is ignored by Git.

```dotenv
POSTGRES_PASSWORD=launcher
JWT_SECRET_KEY=replace-this-with-a-long-random-secret
DATABASE_URL=postgresql+psycopg://launcher:launcher@127.0.0.1:5434/launcher
TEST_DATABASE_URL=postgresql+psycopg://launcher:launcher@127.0.0.1:5434/launcher_test
```

`POSTGRES_PASSWORD` must match the password in both database URLs. Replace the example JWT secret with a random value. Do not commit real passwords, API keys, JWT secrets, or access tokens.

### 3. Start PostgreSQL

```powershell
docker compose up -d postgres
docker compose ps
```

Wait until the PostgreSQL container reports `healthy`.

### 4. Create the separate test database

The test fixture clears and recreates tables in `TEST_DATABASE_URL`, so tests must use a database separate from the application database.

```powershell
docker compose exec postgres createdb -U launcher launcher_test
```

Run this once for a fresh Docker volume. If the test database already exists, skip this command.

### 5. Apply migrations and start the API

```powershell
alembic upgrade head
python -m uvicorn app.main:app --reload
```

The API runs at <http://127.0.0.1:8000>. Interactive API documentation is at <http://127.0.0.1:8000/docs>.

## Run the frontend

Open a second terminal. From the repository root:

```powershell
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually <http://localhost:5173>. During development, Vite proxies API requests to `http://127.0.0.1:8000`; keep both the frontend and backend running.

## Tests and frontend checks

Make sure the PostgreSQL container is running, the `.env` points `TEST_DATABASE_URL` to the separate `launcher_test` database, and the Python virtual environment is active.

```powershell
python -m pytest -q
```

Frontend checks, from the `frontend` directory:

```powershell
npm run lint
npm run build
```

## API overview

| Method | Endpoint | Purpose | Authentication |
| --- | --- | --- | --- |
| `POST` | `/register` | Register a user | No |
| `POST` | `/login` | Verify credentials and return a JWT | No |
| `GET` | `/users/me` | Return the authenticated user | Bearer token |
| `POST` | `/templates` | Create a campaign template | Bearer token |
| `GET` | `/templates` | List the authenticated user's templates | Bearer token |
| `POST` | `/launches` | Create a launch job from a template | Bearer token |
| `GET` | `/launches/{job_id}` | Get a job and its item statuses | Bearer token |
| `GET` | `/auth/tiktok/start` | Create a one-time OAuth state value | Bearer token |
| `GET` | `/auth/tiktok/callback` | Validate and consume the state value | No |

For protected endpoints, send the token in the request header:

```http
Authorization: Bearer <access_token>
```

## Current limitations

- `FakePlatform` simulates platform responses; it does not create real TikTok campaigns.
- TikTok OAuth token exchange, token storage, advertiser account selection, and real Marketing API calls are not implemented.
- The worker currently runs through FastAPI background tasks. A durable external queue is not configured.
- The frontend is a beta workflow, not a production-ready billing, team-management, or analytics product.

## Repository layout

```text
app/          FastAPI routes, auth, models, platform adapter, and worker
migrations/   Alembic migrations
tests/        Backend integration and unit tests
frontend/     React + TypeScript + Vite application
```
