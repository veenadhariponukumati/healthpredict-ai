# Clinical Re-admission Prediction & AI Care Co-ordination Platform

## Overview

Hospital readmissions within 30 days are a major cost and quality problem for health systems - they trigger CMS reimbursement penalties and often signal gaps in post-discharge care. This platform predicts which patients are at high risk of readmission at discharge time, explains *why* using SHAP, and automatically kicks off a durable, auditable care-coordination workflow (Temporal + n8n) so at-risk patients don't fall through the cracks. All data used is synthetic/demo data - no real patient data is processed.

This architecture is designed to the standards of enterprise healthcare technology at scale - Microsoft, Google, Amazon, and Epic-level engineering rigor, with HIPAA-aware patterns, observability, MLOps, and explainable AI throughout.

**What's real vs. simulated:** Authentication, RBAC, the prediction pipeline (12-feature model contract), SHAP explanations, audit logging, and the Temporal + n8n workflow orchestration (durable state machine, retries, real HTTP webhook delivery) are fully implemented and verified end-to-end - Temporal orchestration is real, and n8n workflow execution is real. The **final notification step of each workflow is simulated** - n8n's workflows (patient reminders, care-team notifications, and appointment scheduling) all return a hardcoded mock response instead of calling a real SMS/email/scheduling provider (see [Known Limitations](KNOWN_LIMITATIONS.md)). No real text messages, emails, or appointment bookings are sent by this application today.

## Key Features

- JWT authentication with role-based access control (admin / clinician / viewer)
- 30-day hospital readmission risk prediction (scikit-learn RandomForest, 12-feature contract)
- SHAP-based per-patient explainability
- Durable care-coordination workflows via Temporal, with n8n webhook automation
- Patient management, prediction history, and audit logging
- Playwright E2E test suite (14 tests) covering auth, RBAC, and core flows

## Architecture at a Glance

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  Next.js    │────▶│  FastAPI     │────▶│  Prediction      │
│  Frontend   │     │  Gateway     │     │  Service         │
└─────────────┘     └──────┬───────┘     └────────┬─────────┘
                           │                      │
                           │               ┌──────▼─────────┐
                           │               │  LLM Service   │
                           │               │  (Azure OpenAI)│
                           │               └──────┬─────────┘
                           │                      │
                           │               ┌──────▼─────────┐
                           │               │  Training       │
                           │               │  Service        │
                           │               └──────┬─────────┘
                           │                      │
                           │               ┌──────▼─────────┐
                           │               │  MLflow         │
                           │               │  (Tracking +    │
                           │               │   Registry)     │
                           │               └────────────────┘
                           │
                    ┌──────▼──────────────────────┐
                    │  Workflow Service           │
                    │  ┌────────┐  ┌───────────┐  │
                    │  │ n8n    │  │ Temporal  │  │
                    │  └────────┘  └───────────┘  │
                    └─────────────┬────────────────┘
                                  │
                    ┌─────────────▼────────────────┐
                    │  PostgreSQL                   │
                    │  (Patients, Predictions,      │
                    │   Workflows, Models, Audit)   │
                    └───────────────────────────────┘
```

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, React, TypeScript, Tailwind CSS |
| API Gateway | FastAPI (Python 3.12) |
| ML Framework | PyTorch, Scikit-learn, XGBoost |
| Experiment Tracking | MLflow |
| Workflow Orchestration | n8n + Temporal |
| AI Explanations | SHAP |
| LLM Integration | Azure OpenAI Service |
| Database | PostgreSQL 16 |
| Containerization | Docker, Docker Compose |
| CI/CD | GitHub Actions |
| Deployment | Azure App Service, Azure Container Apps |
| Observability | OpenTelemetry, Prometheus, Grafana |

> **Note on this table:** OpenTelemetry and Prometheus instrumentation are wired into the running FastAPI services. The **Azure deployment path, GitHub Actions CI/CD pipeline, and Grafana dashboards** described in [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) are a **design document only** - there is no `.github/workflows/`, no IaC (Bicep/Terraform) files, no Grafana dashboard config, and no frontend `Dockerfile` in this repository. Separately, **MLflow, the LLM Service (Azure OpenAI), the Training Service, and Redis** are scaffolded in code but are **not part of the verified local stack** (`backend/docker-compose.local.yml` runs 8 containers and includes none of these four) - the prediction service runs from a bundled model file instead of an MLflow registry, and rate limiting is in-memory rather than Redis-backed. The only deployment/runtime path that has been built and verified end-to-end is local Docker Compose (backend, 8 services) + `npm run dev`/`npm run build` (frontend). See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md).

## Key Design Decisions

1. **Service-Oriented Architecture** - Each service is independently deployable, scalable, and testable
2. **MLflow as Source of Truth** - All experiments, models, and artifacts are tracked; the registry governs promotion
3. **Temporal + n8n Dual Orchestration** - Temporal for durable, long-running ML workflows; n8n for rapid care coordination automations
4. **SHAP for Explainability** - Model-agnostic, mathematically grounded explanations at global and patient levels
5. **LLM as Decision Support Only** - Azure OpenAI never predicts; it only translates model outputs into clinician-friendly language
6. **HIPAA-Aware by Default** - Encryption at rest and in transit, RBAC, audit logs, synthetic data, least privilege

## Documentation Index

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Full system architecture with all diagrams |
| [ADRs](docs/adr/) | Architecture Decision Records |
| [API_SPECIFICATION.md](docs/API_SPECIFICATION.md) | Complete API contract |
| [MODEL_CARD.md](docs/MODEL_CARD.md) | Model documentation and intended use |
| [DATA_MODEL.md](docs/DATA_MODEL.md) | ER diagrams and data model |
| [WORKFLOWS.md](docs/WORKFLOWS.md) | Workflow orchestration design |
| [DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) | Deployment and operations |
| [DEVELOPER_ONBOARDING.md](docs/DEVELOPER_ONBOARDING.md) | Getting started guide |
| [EXPERIMENT_TRACKING.md](docs/EXPERIMENT_TRACKING.md) | MLflow experiment design |
| [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) | Comprehensive testing approach |

## Quick Start (Development)

Full step-by-step instructions live in [LOCAL_SETUP.md](LOCAL_SETUP.md) (backend) and [frontend/INTEGRATION_README.md](frontend/INTEGRATION_README.md) (frontend). Summary:

```bash
# Start the backend (Docker)
cd backend
docker compose -f docker-compose.local.yml up -d --build

# Start the frontend (separate terminal)
cd frontend
npm install
npm run dev

# Access services
# Frontend:    http://localhost:3000
# API Gateway: http://localhost:8000
# n8n:         http://localhost:5678
```

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | `admin@test.com` | `Test123!` |
| Clinician | `clinician@test.com` | `Test123!` |
| Viewer | `viewer@test.com` | `Test123!` |

These are seeded automatically on first backend startup - no manual setup required. There is no signup UI; these three accounts are the only way to log in.

## Project Structure

```
.
├── backend/                    # FastAPI gateway + supporting services
│   ├── app/                    # API gateway (routes, schemas, db, middleware)
│   ├── ml/                     # Feature pipeline, model definitions, explainability
│   ├── mlflow/                 # MLflow configuration
│   ├── n8n/                    # n8n Docker image + workflow definitions
│   ├── services/
│   │   ├── prediction/          # Model inference service
│   │   ├── training/            # Model training pipeline
│   │   ├── llm/                 # Azure OpenAI integration
│   │   ├── workflow/            # Workflow orchestration service
│   │   └── temporal_worker/     # Temporal worker
│   ├── postgres-init/          # Postgres init scripts (creates the n8n database)
│   ├── scripts/                 # start-local.sh, stop-local.sh, verify-local.sh
│   ├── tests/                   # Backend test suite
│   └── docker-compose.local.yml
├── frontend/                   # Next.js application
│   ├── src/
│   │   ├── app/                 # Pages and routes
│   │   ├── components/          # Reusable UI components
│   │   ├── features/             # Feature-scoped modules
│   │   ├── hooks/                # React hooks
│   │   ├── lib/                  # Utilities
│   │   ├── providers/             # Auth/query context providers
│   │   ├── services/               # API client
│   │   └── types/                  # Shared TypeScript types
│   ├── e2e/                      # Playwright tests
│   └── INTEGRATION_README.md      # Frontend setup guide
└── docs/                          # Documentation (architecture, ADRs, API spec, etc.)
```

## Known Limitations

See [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) for the full, verified list. Highlights: n8n notification actions are simulated (no real SMS/email is sent), workflow triggering has no UI entry point yet, and `scripts/verify-local.sh` requires a manual workaround on machines without a native `pg_isready`.

## Roadmap

- [ ] Wire n8n's notification actions to a real provider (e.g. Twilio, SendGrid)
- [ ] Add a UI entry point for triggering a workflow from the prediction detail page
- [ ] Fix `n8n`/`temporal-worker` Docker healthcheck configuration
- [ ] Add a frontend `Dockerfile` and wire it into a deployment pipeline
- [ ] Show patient names instead of raw UUIDs in prediction list views

## License

All Rights Reserved - see [LICENSE](LICENSE). This repository is public for portfolio and demonstration purposes only; no reuse, modification, or redistribution is permitted without written permission. All patient data referenced is synthetic. Not for use with real patient data without proper HIPAA compliance review.