# Clinical Readmission Prediction & AI Care Coordination Platform

## Overview

A production-grade ML engineering platform that predicts 30-day hospital readmission risk, explains predictions using SHAP, tracks the full ML lifecycle with MLflow, and automatically triggers n8n-based post-discharge care coordination workflows via Temporal durable execution.

This architecture is designed to the standards of enterprise healthcare technology at scale — Microsoft, Google, Amazon, and Epic-level engineering rigor, with HIPAA-aware patterns, observability, MLOps, and explainable AI throughout.

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

## Key Design Decisions

1. **Service-Oriented Architecture** — Each service is independently deployable, scalable, and testable
2. **MLflow as Source of Truth** — All experiments, models, and artifacts are tracked; the registry governs promotion
3. **Temporal + n8n Dual Orchestration** — Temporal for durable, long-running ML workflows; n8n for rapid care coordination automations
4. **SHAP for Explainability** — Model-agnostic, mathematically grounded explanations at global and patient levels
5. **LLM as Decision Support Only** — Azure OpenAI never predicts; it only translates model outputs into clinician-friendly language
6. **HIPAA-Aware by Default** — Encryption at rest and in transit, RBAC, audit logs, synthetic data, least privilege

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

```bash
# Clone the repository
git clone <repository-url>
cd clinical-readmission-platform

# Start all services
docker compose up -d

# Verify health
curl http://localhost:8000/health

# Access services
# Frontend:    http://localhost:3000
# API Gateway: http://localhost:8000
# MLflow UI:   http://localhost:5000
# n8n:         http://localhost:5678
```

## Project Structure

```
clinical-readmission-platform/
├── frontend/                 # Next.js application
│   ├── src/
│   │   ├── app/             # Pages and routes
│   │   ├── components/      # Reusable UI components
│   │   ├── lib/             # Utilities, API clients
│   │   └── hooks/           # React hooks
│   └── e2e/                 # Playwright tests
├── services/
│   ├── api-gateway/         # FastAPI gateway
│   ├── prediction/          # Model inference service
│   ├── training/            # Model training pipeline
│   ├── llm/                 # Azure OpenAI integration
│   └── workflow/            # n8n + Temporal orchestration
├── ml/
│   ├── models/              # Model definitions
│   ├── features/            # Feature engineering pipeline
│   ├── evaluation/          # Metrics and comparison
│   └── explainability/      # SHAP integration
├── mlflow/                  # MLflow configuration
├── n8n/                     # n8n workflow definitions
├── temporal/                # Temporal worker definitions
├── infrastructure/          # Terraform / Bicep
├── tests/                   # Cross-service tests
├── docs/                    # Documentation
├── docker-compose.yml       # Local development
└── .github/workflows/       # CI/CD pipelines
```

## License

This architecture is designed for portfolio and educational purposes. All patient data referenced is synthetic. Not for use with real patient data without proper HIPAA compliance review.