# Developer Onboarding Guide

## Welcome

Welcome to the Clinical Readmission Prediction & AI Care Coordination Platform team. This guide will help you get your development environment set up and understand the system architecture.

## Prerequisites

### Required Software

| Tool | Version | Purpose |
|------|---------|---------|
| Docker | 24.0+ | Container runtime |
| Docker Compose | 2.20+ | Multi-container orchestration |
| Python | 3.12 | All backend services |
| Node.js | 20+ | Frontend development |
| Git | 2.40+ | Version control |
| Azure CLI | 2.57+ | Azure deployment (optional) |
| `gh` CLI | 2.40+ | GitHub operations |

### Recommended Tools

- VS Code with Python, ESLint, Prettier extensions
- Postman or Bruno for API testing
- TablePlus or DBeaver for database inspection
- MLflow UI at `http://localhost:5000`

## Getting Started

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd clinical-readmission-platform
```

### Step 2: Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Generate JWT keys (for local development)
mkdir -p secrets
openssl genrsa -out secrets/jwt_private_key.pem 2048
openssl rsa -in secrets/jwt_private_key.pem -pubout -out secrets/jwt_public_key.pem
```

### Step 3: Start All Services

```bash
# Build and start all services
docker compose up --build -d

# Wait for all services to be healthy
docker compose ps

# Check logs for any errors
docker compose logs -f
```

### Step 4: Verify Services

```bash
# API Gateway
curl http://localhost:8000/health
# Expected: {"status": "healthy", ...}

# Prediction Service
curl http://localhost:8001/health
# Expected: {"status": "healthy", ...}

# Frontend
open http://localhost:3000

# MLflow
open http://localhost:5000

# n8n
open http://localhost:5678
```

### Step 5: Run Database Migrations

```bash
# Run migrations
docker compose exec api-gateway alembic upgrade head

# Seed sample data
docker compose exec api-gateway python scripts/seed_data.py
```

### Step 6: Run the Tests

```bash
# Run all tests
docker compose exec api-gateway pytest -v

# Run with coverage
docker compose exec api-gateway pytest --cov=services/api-gateway --cov-report=html

# Run frontend tests
cd frontend && npm test

# Run E2E tests
cd frontend && npx playwright test
```

## Project Structure

```
clinical-readmission-platform/
│
├── frontend/                    # Next.js application
│   ├── src/
│   │   ├── app/                 # Pages (Next.js App Router)
│   │   │   ├── dashboard/       # Dashboard page
│   │   │   ├── patients/        # Patient management
│   │   │   ├── experiments/     # MLflow experiment viewer
│   │   │   ├── models/          # Model registry browser
│   │   │   ├── workflows/       # Workflow monitoring
│   │   │   ├── monitoring/      # Prediction monitoring
│   │   │   └── admin/           # Admin panel
│   │   ├── components/          # Reusable components
│   │   │   ├── ui/              # Base UI components
│   │   │   ├── charts/          # Recharts / D3 components
│   │   │   ├── predictions/     # Prediction display components
│   │   │   └── workflows/       # Workflow display components
│   │   ├── lib/                 # Utilities and API client
│   │   │   ├── api/             # Generated API client
│   │   │   └── hooks/           # React hooks
│   │   └── types/               # TypeScript type definitions
│   ├── e2e/                     # Playwright tests
│   └── public/                  # Static assets
│
├── services/
│   ├── api-gateway/             # FastAPI gateway
│   │   ├── src/
│   │   │   ├── routes/          # API route handlers
│   │   │   ├── middleware/      # Auth, rate limiting, logging
│   │   │   ├── schemas/         # Pydantic models
│   │   │   ├── models/          # SQLAlchemy models
│   │   │   └── core/            # Config, security, database
│   │   ├── tests/
│   │   │   ├── unit/
│   │   │   └── integration/
│   │   └── Dockerfile
│   │
│   ├── prediction/              # Prediction service
│   │   ├── src/
│   │   │   ├── inference/       # Model inference engine
│   │   │   ├── features/        # Feature preprocessing
│   │   │   ├── explainability/  # SHAP integration
│   │   │   └── models/          # Model loading
│   │   └── Dockerfile
│   │
│   ├── training/                # Training service
│   │   ├── src/
│   │   │   ├── trainers/        # Model training implementations
│   │   │   ├── evaluation/      # Metrics and comparison
│   │   │   ├── hp_search/       # Optuna hyperparameter search
│   │   │   └── pipeline/        # Feature engineering pipeline
│   │   └── Dockerfile
│   │
│   ├── llm/                     # LLM service
│   │   ├── src/
│   │   │   ├── prompts/         # Prompt templates
│   │   │   ├── validation/      # Output validation
│   │   │   └── safety/          # PHI stripping, content checks
│   │   └── Dockerfile
│   │
│   └── workflow/                # Workflow service
│       ├── src/
│       │   ├── workflows/       # Temporal workflow definitions
│       │   ├── activities/      # Workflow activities
│       │   └── n8n/             # n8n webhook client
│       └── Dockerfile
│
├── ml/                          # ML library (shared)
│   ├── models/                  # Model definitions
│   │   ├── logistic_regression.py
│   │   ├── random_forest.py
│   │   ├── xgboost_model.py
│   │   └── pytorch_nn.py
│   ├── features/                # Feature engineering
│   │   ├── pipeline.py
│   │   ├── encoders.py
│   │   └── selectors.py
│   ├── evaluation/              # Metrics and comparison
│   │   ├── metrics.py
│   │   ├── comparison.py
│   │   └── visualization.py
│   └── explainability/          # SHAP integration
│       ├── shap_explainer.py
│       └── visualizations.py
│
├── mlflow/                      # MLflow configuration
│   └── Dockerfile
│
├── n8n/                         # n8n workflow definitions
│   └── workflows/
│       ├── care-coordination.json
│       ├── notify-physician.json
│       └── send-reminder.json
│
├── temporal/                    # Temporal worker configuration
│   └── Dockerfile
│
├── infrastructure/              # Infrastructure as Code
│   ├── bicep/                   # Azure Bicep templates
│   ├── terraform/               # Terraform modules (alternative)
│   └── monitoring/              # Prometheus/Grafana config
│
├── tests/                       # Cross-service tests
│   ├── ml/                      # ML-specific tests
│   ├── workflow/                # Workflow tests
│   └── conftest.py              # Shared fixtures
│
├── docs/                        # Documentation
│   ├── ARCHITECTURE.md
│   ├── API_SPECIFICATION.md
│   ├── MODEL_CARD.md
│   ├── DATA_MODEL.md
│   ├── WORKFLOWS.md
│   ├── TESTING_STRATEGY.md
│   ├── DEPLOYMENT_GUIDE.md
│   ├── EXPERIMENT_TRACKING.md
│   ├── DEVELOPER_ONBOARDING.md
│   └── adr/                     # Architecture Decision Records
│
├── .github/workflows/           # CI/CD pipelines
│   ├── ci.yml
│   ├── cd.yml
│   └── test.yml
│
├── scripts/                     # Utility scripts
│   ├── seed_data.py
│   ├── generate_synthetic_data.py
│   └── backup.sh
│
├── docker-compose.yml           # Local development
├── .env.example
├── .pre-commit-config.yaml
└── README.md
```

## Development Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code following the established patterns
- Add tests for new functionality
- Update documentation if needed

### 3. Run Tests Locally

```bash
# Lint
ruff check .
mypy .

# Unit tests
pytest services/your-service/tests/unit/

# Integration tests
pytest services/your-service/tests/integration/
```

### 4. Commit

```bash
git add .
git commit -m "feat: your descriptive commit message"

# Follow conventional commits:
# feat: new feature
# fix: bug fix
# docs: documentation
# test: testing
# refactor: code restructuring
# chore: maintenance
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
gh pr create --fill
```

## Key Commands

### Service Management

```bash
# Start all services
docker compose up -d

# Start a specific service
docker compose up -d prediction-service

# View logs
docker compose logs -f api-gateway

# Rebuild a service
docker compose build prediction-service

# Restart a service
docker compose restart prediction-service

# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v
```

### Database

```bash
# Connect to PostgreSQL
docker compose exec postgres psql -U app -d readmission

# Run migrations
docker compose exec api-gateway alembic upgrade head

# Rollback migration
docker compose exec api-gateway alembic downgrade -1

# Create new migration
docker compose exec api-gateway alembic revision --autogenerate -m "description"
```

### MLflow

```bash
# View experiment UI
open http://localhost:5000

# List experiments
docker compose exec mlflow mlflow experiments list

# Export run data
docker compose exec mlflow mlflow runs download -u <run-id>
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=services/api-gateway --cov-report=html

# Run specific test file
pytest tests/unit/test_prediction_service.py -v

# Run tests matching a keyword
pytest -k "test_high_risk"

# Run E2E tests
cd frontend && npx playwright test --headed
```

## Common Issues

### Issue: "Port already in use"

```bash
# Check what's using the port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change the port in docker-compose.yml
```

### Issue: "Database connection refused"

```bash
# Ensure PostgreSQL is running
docker compose ps postgres

# Check logs
docker compose logs postgres

# Restart
docker compose restart postgres
```

### Issue: "MLflow connection failed"

```bash
# Ensure MLflow started
docker compose ps mlflow

# Check MLflow logs
docker compose logs mlflow

# Verify MLflow is accessible
curl http://localhost:5000/health
```

### Issue: "Out of memory"

```bash
# Check Docker resource usage
docker stats

# Reduce memory limits in docker-compose.yml
# Or restart Docker Desktop with more RAM allocated
```

## Code Style Guide

### Python

- Follow PEP 8 (enforced by `ruff`)
- Type hints required for all functions
- Docstrings for public APIs (Google style)
- Use `async`/`await` for I/O-bound operations
- Prefer Pydantic v2 for data validation

### TypeScript

- Use strict TypeScript configuration
- Define interfaces for all data shapes
- Use `const` over `let`, prefer `const` over `function`
- React components: functional with hooks

### Git

- Conventional commits (feat, fix, docs, test, refactor, chore)
- Branch naming: `feature/`, `fix/`, `docs/`, `chore/`
- PRs require at least 1 reviewer
- Squash merge to main

## Architecture Decision Records

ADRs are stored in `docs/adr/`. When making a significant architectural decision:

1. Create a new ADR using the template
2. Add it to the ADR index
3. Discuss in the PR for review

## Getting Help

- **Documentation:** Start with `docs/` directory
- **Team Chat:** [Link to team channel]
- **Issue Tracker:** [Link to GitHub Issues]
- **On-call Engineer:** See team roster

## Service Ports Reference

| Service | Port | Internal URL | External URL (dev) |
|---------|------|-------------|-------------------|
| Frontend | 3000 | http://frontend:3000 | http://localhost:3000 |
| API Gateway | 8000 | http://api-gateway:8000 | http://localhost:8000 |
| Prediction Service | 8001 | http://prediction-service:8001 | http://localhost:8001 |
| Training Service | 8002 | http://training-service:8002 | http://localhost:8002 |
| LLM Service | 8003 | http://llm-service:8003 | http://localhost:8003 |
| Workflow Service | 8004 | http://workflow-service:8004 | http://localhost:8004 |
| PostgreSQL | 5432 | postgres:5432 | localhost:5432 |
| Redis | 6379 | redis:6379 | localhost:6379 |
| MLflow | 5000 | http://mlflow:5000 | http://localhost:5000 |
| Temporal | 7233 | temporal:7233 | localhost:7233 |
| n8n | 5678 | http://n8n:5678 | http://localhost:5678 |