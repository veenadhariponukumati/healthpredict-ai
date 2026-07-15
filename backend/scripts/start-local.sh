#!/bin/bash
# Start all services
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

echo "Starting Healthcare Readmission Platform..."

# Check PostgreSQL
if ! pg_isready -q 2>/dev/null; then
    echo "ERROR: PostgreSQL is not running"
    echo "Start it with: sudo service postgresql start"
    exit 1
fi

# Run migrations
echo "Running migrations..."
cd "$BACKEND_DIR"
alembic upgrade head 2>/dev/null || echo "Migrations skipped (may already be current)"

# Start services
echo "Starting Prediction Service on port 8001..."
uvicorn services.prediction.main:app --host 127.0.0.1 --port 8001 --log-level warning &
PRED_PID=$!

echo "Starting Workflow Service on port 8004..."
uvicorn services.workflow.main:app --host 127.0.0.1 --port 8004 --log-level warning &
WF_PID=$!

echo "Starting Main API on port 8000..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

echo ""
echo "Services started:"
echo "  Main API:       http://localhost:8000  (PID: $API_PID)"
echo "  Prediction:     http://localhost:8001  (PID: $PRED_PID)"
echo "  Workflow:       http://localhost:8004  (PID: $WF_PID)"
echo ""
echo "Press Ctrl+C to stop all services."
echo "Or run: ./scripts/stop-local.sh"

wait