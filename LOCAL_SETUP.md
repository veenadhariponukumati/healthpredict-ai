# Local Setup Guide — Healthcare Readmission Prediction Platform

## Prerequisites

- Python 3.12+
- PostgreSQL 16+ (or Docker for containerized DB)
- curl (for verification script)

## Quick Start (Native)

```bash
# 1. Start PostgreSQL
# Option A: With Docker
docker compose -f docker-compose.local.yml up -d postgres

# Option B: Direct install
# sudo service postgresql start
# createdb readmission

# 2. Create virtual environment
cd backend
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit DATABASE_URL in .env for your PostgreSQL connection

# 5. Run database migrations
alembic upgrade head

# 6. Start all services
./scripts/start-local.sh
```

## Quick Start (Full Docker)

```bash
cd backend
docker compose -f docker-compose.local.yml up -d --build
# API is at http://localhost:8000
```

## Frontend

The backend steps above do not start the frontend. See [frontend/INTEGRATION_README.md](frontend/INTEGRATION_README.md) for frontend setup (`npm install` / `npm run dev`, served on port 3000).

## Services

| Service | Port | URL |
|---------|------|-----|
| Main API | 8000 | http://localhost:8000 |
| Prediction Service | 8001 | http://localhost:8001/health |
| Workflow Service | 8004 | http://localhost:8004/health |

## Environment Variables

See `.env.example` for all required variables. Key ones:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://app:dev_password@localhost:5432/readmission` |
| `JWT_SECRET_KEY` | Secret for token signing | `dev-secret-change-in-production` |
| `JWT_ALGORITHM` | Token algorithm | `HS256` |
| `PREDICTION_SERVICE_URL` | Prediction service endpoint | `http://localhost:8001` |
| `WORKFLOW_SERVICE_URL` | Workflow service endpoint | `http://localhost:8004` |

## Default Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@test.com` | `Test123!` |
| Clinician | `clinician@test.com` | `Test123!` |
| Viewer | `viewer@test.com` | `Test123!` |

## Verification

```bash
# After starting services, run:
./scripts/verify-local.sh
```

> **Known issue:** this script fails immediately on machines without a native `pg_isready` binary installed (its first check runs `pg_isready` against the host rather than inside the `postgres` container), even when Postgres itself is running correctly in Docker. See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) for details and a manual alternative.

## Architecture

See `docs/ARCHITECTURE.md` for full documentation.

## API Documentation

See `docs/API_SPECIFICATION.md` for complete API reference.