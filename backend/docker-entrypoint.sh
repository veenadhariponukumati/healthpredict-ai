#!/bin/sh
set -e

echo "[entrypoint] Running database migrations..."
alembic upgrade head

echo "[entrypoint] Seeding default users..."
python -m app.db.seed

echo "[entrypoint] Starting API server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
