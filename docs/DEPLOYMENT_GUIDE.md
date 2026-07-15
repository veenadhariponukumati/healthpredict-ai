# Deployment Guide

> **Scope note:** This guide describes a *designed* Azure deployment path. None of it has been implemented — there is no `.github/workflows/` directory, no Bicep/Terraform files, and no frontend `Dockerfile` in this repository. The only deployment path that has been built and verified is local Docker Compose (`backend/docker-compose.local.yml`, 8 services) plus `npm run dev`/`npm run build` for the frontend. Treat everything below as a proposed target architecture, not current capability.

## Architecture Overview

```mermaid
graph TB
    subgraph "Azure Cloud"
        subgraph "Azure Container Apps"
            direction TB
            GW["API Gateway<br/>FastAPI"]
            PS["Prediction Service<br/>FastAPI"]
            TS["Training Service<br/>FastAPI"]
            LS["LLM Service<br/>FastAPI"]
            WS["Workflow Service<br/>FastAPI"]
            FE["Frontend<br/>Next.js"]
        end

        subgraph "Azure PostgreSQL<br/>(Flexible Server)"
            DB[("Main Database<br/>+ Feature Store")]
        end

        subgraph "Azure Blob Storage"
            ML_ART["MLflow Artifacts"]
            MODELS["Model Files"]
        end

        subgraph "Azure Container Registry"
            ACR["Container Images"]
        end

        subgraph "Azure Key Vault"
            KV["Secrets<br/>+ Certificates"]
        end

        subgraph "Azure OpenAI"
            AOAI["GPT-4o<br/>Deployment"]
        end

        subgraph "Azure Redis Cache"
            REDIS["Session Cache<br/>+ Rate Limiting"]
        end

        subgraph "MLflow (Azure VM / Container)"
            ML_TRACK["MLflow Tracking<br/>Server"]
            ML_REG["MLflow Model<br/>Registry"]
        end

        subgraph "Monitoring"
            PROM["Prometheus"]
            GRAF["Grafana"]
            OTE["OpenTelemetry<br/>Collector"]
        end

        subgraph "Workflow"
            N8N["n8n<br/>Container"]
            TEMP["Temporal<br/>Server"]
            TEMP_W["Temporal<br/>Worker"]
        end
    end

    subgraph "CI/CD (GitHub Actions)"
        GHA["Build + Test + Deploy"]
    end

    GHA --> ACR
    ACR --> GW
    ACR --> PS
    ACR --> TS
    ACR --> LS
    ACR --> WS
    ACR --> FE
    ACR --> N8N
    ACR --> TEMP
    ACR --> TEMP_W

    GW --> KV
    PS --> KV
    PS --> DB
    PS --> ML_REG
    PS --> REDIS
    TS --> DB
    TS --> ML_TRACK
    TS --> ML_ART
    LS --> AOAI
    LS --> KV
    WS --> DB
    WS --> N8N
    WS --> TEMP

    GW --> OTE
    PS --> OTE
    TS --> OTE
    LS --> OTE
    WS --> OTE
    OTE --> PROM
    PROM --> GRAF
```

## Prerequisites

- Azure subscription with Contributor access
- GitHub repository with Actions enabled
- Docker and Docker Compose (local development)
- Azure CLI (`az`) installed
- `kubectl` (if using AKS)
- `bicep` or `terraform` for infrastructure

## Infrastructure as Code

### Resource Group
```bash
az group create --name rg-readmission-prod --location eastus2
```

### Core Services (Bicep)

```bicep
// main.bicep — key resources
param location string = 'eastus2'
param environment string = 'prod'

resource containerEnv 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: 'cae-readmission-${environment}'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2022-12-01' = {
  name: 'psql-readmission-${environment}'
  location: location
  sku: { name: 'Standard_D4ds_v4', tier: 'GeneralPurpose' }
  properties: {
    administratorLogin: 'pgadmin'
    version: '16'
    storage: { storageSizeGB: 256 }
    highAvailability: { mode: 'ZoneRedundant' }
    backup: { backupRetentionDays: 30, geoRedundantBackup: 'Enabled' }
  }
}

resource registry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: 'crreadmission${environment}'
  location: location
  sku: { name: 'Premium' }
  properties: { adminUserEnabled: true }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: 'kv-readmission-${environment}'
  location: location
  properties: {
    sku: { name: 'standard', family: 'A' }
    tenantId: subscription().tenantId
    enableRbacAuthorization: true
    softDeleteRetentionInDays: 90
  }
}
```

## Container Build

### Docker Compose (Local Development)

```yaml
# docker-compose.yml
version: '3.9'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: readmission
      POSTGRES_USER: app
      POSTGRES_PASSWORD: dev_password
    ports: ["5432:5432"]
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./infrastructure/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d readmission"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  mlflow:
    build:
      context: ./mlflow
      dockerfile: Dockerfile
    ports: ["5000:5000"]
    environment:
      MLFLOW_TRACKING_URI: postgresql://app:dev_password@postgres:5432/readmission
      MLFLOW_ARTIFACT_ROOT: /mlflow/artifacts
    volumes:
      - mlflow_artifacts:/mlflow/artifacts
    depends_on:
      postgres: { condition: service_healthy }

  api-gateway:
    build:
      context: ./services/api-gateway
      dockerfile: Dockerfile
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://app:dev_password@postgres:5432/readmission
      REDIS_URL: redis://redis:6379/0
      MLFLOW_TRACKING_URI: http://mlflow:5000
      JWT_PUBLIC_KEY_PATH: /run/secrets/jwt_public_key.pem
      ENVIRONMENT: development
    secrets:
      - jwt_private_key
      - jwt_public_key
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }

  prediction-service:
    build:
      context: ./services/prediction
      dockerfile: Dockerfile
    ports: ["8001:8001"]
    environment:
      DATABASE_URL: postgresql://app:dev_password@postgres:5432/readmission
      MLFLOW_TRACKING_URI: http://mlflow:5000
      REDIS_URL: redis://redis:6379/0
      ENVIRONMENT: development
    depends_on:
      postgres: { condition: service_healthy }
      mlflow: { condition: service_started }
    deploy:
      resources:
        limits: { memory: 2G }

  training-service:
    build:
      context: ./services/training
      dockerfile: Dockerfile
    ports: ["8002:8002"]
    environment:
      DATABASE_URL: postgresql://app:dev_password@postgres:5432/readmission
      MLFLOW_TRACKING_URI: http://mlflow:5000
      ENVIRONMENT: development
    depends_on:
      postgres: { condition: service_healthy }
      mlflow: { condition: service_started }
    deploy:
      resources:
        limits: { memory: 4G }

  llm-service:
    build:
      context: ./services/llm
      dockerfile: Dockerfile
    ports: ["8003:8003"]
    environment:
      AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT}
      AZURE_OPENAI_API_KEY: ${AZURE_OPENAI_API_KEY}
      AZURE_OPENAI_DEPLOYMENT: gpt-4o
      ENVIRONMENT: development
    depends_on:
      postgres: { condition: service_healthy }

  workflow-service:
    build:
      context: ./services/workflow
      dockerfile: Dockerfile
    ports: ["8004:8004"]
    environment:
      DATABASE_URL: postgresql://app:dev_password@postgres:5432/readmission
      TEMPORAL_HOST: temporal:7233
      N8N_WEBHOOK_URL: http://n8n:5678/webhook
      ENVIRONMENT: development
    depends_on:
      postgres: { condition: service_healthy }

  temporal:
    image: temporalio/auto-setup:1.23
    ports: ["7233:7233"]
    environment:
      DB: postgresql
      POSTGRES_USER: app
      POSTGRES_PWD: dev_password
      POSTGRES_SEEDS: postgres
    depends_on:
      postgres: { condition: service_healthy }

  n8n:
    image: n8nio/n8n:latest
    ports: ["5678:5678"]
    environment:
      N8N_HOST: localhost
      N8N_PORT: 5678
      N8N_PROTOCOL: http
      DB_TYPE: postgresdb
      DB_POSTGRESDB_HOST: postgres
      DB_POSTGRESDB_DATABASE: readmission
      DB_POSTGRESDB_USER: app
      DB_POSTGRESDB_PASSWORD: dev_password
    volumes:
      - n8n_data:/home/node/.n8n
    depends_on:
      postgres: { condition: service_healthy }

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        NEXT_PUBLIC_API_URL: http://localhost:8000/api/v1
    ports: ["3000:3000"]
    environment:
      NEXTAUTH_URL: http://localhost:3000
      NEXTAUTH_SECRET: dev_secret_key_do_not_use_in_production
      API_URL: http://api-gateway:8000/api/v1
    depends_on:
      - api-gateway

volumes:
  pgdata:
  mlflow_artifacts:
  n8n_data:

secrets:
  jwt_private_key:
    file: ./secrets/jwt_private_key.pem
  jwt_public_key:
    file: ./secrets/jwt_public_key.pem
```

### Production Dockerfile (Example: Prediction Service)

```dockerfile
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime

WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8001

# Non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
```

## CI/CD Pipeline (GitHub Actions)

```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [api-gateway, prediction, training, llm, workflow, frontend]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install ruff mypy
      - run: ruff check services/${{ matrix.service }}/ --format github
      - run: mypy services/${{ matrix.service }}/ --strict

  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: readmission_test
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports: ["5432:5432"]
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r services/api-gateway/requirements.txt -r services/api-gateway/requirements-dev.txt
      - run: pytest services/api-gateway/tests/ --cov=services/api-gateway --cov-report=xml -v
      - uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          flags: api-gateway

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: azure/docker-login@v1
        with:
          login-server: ${{ secrets.ACR_LOGIN_SERVER }}
          username: ${{ secrets.ACR_USERNAME }}
          password: ${{ secrets.ACR_PASSWORD }}
      - run: |
          docker buildx build \
            --platform linux/amd64 \
            --tag ${{ secrets.ACR_LOGIN_SERVER }}/api-gateway:${{ github.sha }} \
            --tag ${{ secrets.ACR_LOGIN_SERVER }}/api-gateway:latest \
            --push \
            ./services/api-gateway
```

```yaml
# .github/workflows/cd.yml
name: CD Pipeline

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}

      - name: Build and push containers
        run: |
          services=("api-gateway" "prediction" "training" "llm" "workflow" "frontend")
          for service in "${services[@]}"; do
            docker buildx build \
              --platform linux/amd64 \
              --tag ${{ secrets.ACR_LOGIN_SERVER }}/$service:${{ github.sha }} \
              --tag ${{ secrets.ACR_LOGIN_SERVER }}/$service:latest \
              --push \
              ./services/$service
          done

      - name: Deploy to Azure Container Apps
        run: |
          az containerapp update \
            --name ca-api-gateway \
            --resource-group rg-readmission-prod \
            --image ${{ secrets.ACR_LOGIN_SERVER }}/api-gateway:${{ github.sha }}

      - name: Run smoke tests
        run: |
          sleep 30
          curl -f https://api.readmission-platform.com/health
          curl -f https://api.readmission-platform.com/api/v1/dashboard/summary

      - name: Notify on success
        run: echo "Deployment successful"  # Replace with Slack/Teams notification
```

## Environment Configuration

### Environment Variables by Service

| Service | Variable | Source | Required |
|---------|----------|--------|----------|
| All | `ENVIRONMENT` | Deployment | Yes |
| All | `SENTRY_DSN` | Key Vault | No |
| API Gateway | `DATABASE_URL` | Key Vault | Yes |
| API Gateway | `REDIS_URL` | Key Vault | Yes |
| API Gateway | `JWT_PUBLIC_KEY` | Key Vault | Yes |
| API Gateway | `JWT_PRIVATE_KEY` | Key Vault | Yes |
| Prediction | `DATABASE_URL` | Key Vault | Yes |
| Prediction | `MLFLOW_TRACKING_URI` | Config | Yes |
| Training | `DATABASE_URL` | Key Vault | Yes |
| Training | `MLFLOW_TRACKING_URI` | Config | Yes |
| LLM | `AZURE_OPENAI_ENDPOINT` | Key Vault | Yes |
| LLM | `AZURE_OPENAI_API_KEY` | Key Vault | Yes |
| LLM | `AZURE_OPENAI_DEPLOYMENT` | Config | Yes |
| Workflow | `DATABASE_URL` | Key Vault | Yes |
| Workflow | `TEMPORAL_HOST` | Config | Yes |
| Workflow | `N8N_WEBHOOK_URL` | Config | Yes |
| Frontend | `NEXTAUTH_URL` | Config | Yes |
| Frontend | `NEXT_PUBLIC_API_URL` | Config | Yes |

## Database Migration

```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "add_predictions_partition"

# Rollback
alembic downgrade -1
```

## Monitoring Setup

### Prometheus Targets

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'api-gateway'
    static_configs:
      - targets: ['api-gateway:8000']
  - job_name: 'prediction-service'
    static_configs:
      - targets: ['prediction-service:8001']
  - job_name: 'training-service'
    static_configs:
      - targets: ['training-service:8002']
  - job_name: 'llm-service'
    static_configs:
      - targets: ['llm-service:8003']
  - job_name: 'workflow-service'
    static_configs:
      - targets: ['workflow-service:8004']
  - job_name: 'temporal-server'
    static_configs:
      - targets: ['temporal:7233']
```

### Grafana Dashboards

1. **Service Health Dashboard** — Uptime, latency, error rates per service
2. **ML Performance Dashboard** — Model metrics, drift detection, prediction distribution
3. **Workflow Dashboard** — Workflow volume, success/failure rates, duration
4. **Infrastructure Dashboard** — CPU, memory, disk, network per container

## Disaster Recovery

| Scenario | RTO | RPO | Recovery Procedure |
|----------|-----|-----|-------------------|
| Single container crash | < 30s | 0 | Azure Container Apps auto-restart |
| Service degradation | < 5 min | 0 | Scale-out / rollback |
| Database failure | < 1 hour | < 5 min | Failover to standby + point-in-time recovery |
| Region failure | < 4 hours | < 1 hour | Deploy to secondary region + restore backup |
| Data corruption | < 2 hours | < 24 hours | Point-in-time restore to pre-corruption state |
| Model corruption | < 15 min | 0 | Rollback to previous MLflow production model |

## Rollback Procedure

```bash
# Database rollback
alembic downgrade -1

# Model rollback (via API)
curl -X POST https://api.readmission-platform.com/api/v1/models/rollback \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Performance degradation detected"}'

# Container rollback
az containerapp update \
  --name ca-prediction-service \
  --resource-group rg-readmission-prod \
  --image $ACR/prediction-service:previous-stable-tag

# Full environment rollback
az deployment group create \
  --resource-group rg-readmission-prod \
  --template-file infrastructure/rollback.bicep \
  --parameters version=previous-stable
```