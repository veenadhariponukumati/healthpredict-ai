# System Architecture

## 1. Architecture Overview

### 1.1 High-Level Architecture Diagram

```mermaid
graph TB
    subgraph "Client Layer"
        A["Web Browser"]
        B["External API Consumers"]
    end

    subgraph "Edge Layer"
        C["Azure Front Door / CDN"]
        D["WAF / DDoS Protection"]
    end

    subgraph "API Gateway Layer"
        E["FastAPI Gateway<br/>Port 8000"]
        F["Auth Service<br/>JWT / RBAC"]
        G["Rate Limiter"]
        H["Audit Logger"]
    end

    subgraph "Application Services"
        I["Prediction Service<br/>Port 8001"]
        J["Training Service<br/>Port 8002"]
        K["LLM Service<br/>Port 8003"]
        L["Workflow Service<br/>Port 8004"]
    end

    subgraph "ML Platform"
        M["MLflow Tracking<br/>Port 5000"]
        N["MLflow Registry"]
        O["Model Artifact Store<br/>Azure Blob"]
    end

    subgraph "Workflow Orchestration"
        P["n8n<br/>Port 5678"]
        Q["Temporal Server<br/>Port 7233"]
        R["Temporal Workers"]
    end

    subgraph "Data Layer"
        S["PostgreSQL<br/>Port 5432"]
        T["Redis Cache<br/>Port 6379"]
        U["Feature Store<br/>(PostgreSQL)"]
    end

    subgraph "External AI"
        V["Azure OpenAI<br/>GPT-4o"]
    end

    subgraph "Observability"
        W["Prometheus"]
        X["Grafana"]
        Y["OpenTelemetry Collector"]
        Z["Structured Logging<br/>(JSON)"]
    end

    A --> C
    B --> D
    C --> E
    D --> E
    E --> F
    E --> G
    E --> H
    E --> I
    E --> J
    E --> K
    E --> L
    I --> S
    I --> T
    I --> M
    I --> N
    J --> M
    J --> N
    J --> O
    J --> S
    K --> V
    K --> S
    L --> P
    L --> Q
    Q --> R
    P --> S
    R --> S
    I --> U
    J --> U

    I --> Y
    J --> Y
    K --> Y
    L --> Y
    E --> Y
    Y --> W
    W --> X
```

### 1.2 Request Flow Diagram

```mermaid
sequenceDiagram
    participant User as Clinician/User
    participant FE as Next.js Frontend
    participant GW as FastAPI Gateway
    participant Auth as Auth Service
    participant PS as Prediction Service
    participant LLM as LLM Service
    participant DB as PostgreSQL
    participant ML as MLflow
    participant WF as Workflow Service
    participant N8N as n8n
    participant TEMP as Temporal

    User->>FE: Login
    FE->>GW: POST /auth/login
    GW->>Auth: Validate credentials
    Auth-->>GW: JWT token
    GW-->>FE: Token + user info
    FE-->>User: Dashboard loaded

    User->>FE: Submit patient data for risk prediction
    FE->>GW: POST /api/v1/predict (Authorization: Bearer JWT)
    GW->>Auth: Validate token + RBAC
    Auth-->>GW: Authorized
    GW->>GW: Log audit event
    GW->>PS: POST /predict (sanitized payload)

    PS->>PS: Load production model from MLflow registry
    PS->>PS: Preprocess features (pipeline v2.3)
    PS->>PS: Run inference (threshold = 0.35)
    PS->>PS: Compute SHAP explanations
    PS-->>GW: PredictionResult { score, risk_level, shap_values, model_version }

    opt Risk Score > Threshold
        PS-->>GW: High risk flag
        GW->>LLM: POST /explain { features, shap_values, score }
        LLM->>LLM: Build structured prompt
        LLM->>V: Azure OpenAI API
        V-->>LLM: Clinician-friendly explanation
        LLM-->>GW: Natural language explanation + disclaimer

        GW->>WF: POST /trigger-workflow { patient_id, risk_score }
        WF->>DB: Write workflow_event (PENDING)
        WF->>TEMP: Signal start CareCoordinationWorkflow
        TEMP->>N8N: Webhook trigger
        N8N->>N8N: Create follow-up appt
        N8N->>N8N: Notify physician
        N8N->>N8N: Notify care coordinator
        N8N->>N8N: Send patient reminder
        N8N-->>WF: WorkflowResult
        WF->>DB: Update workflow_event (COMPLETED)
    end

    PS->>DB: INSERT prediction record
    PS->>ML: Log prediction metric

    GW-->>FE: Complete response
    FE-->>User: Dashboard updated with risk + explanation + workflow status
```

### 1.3 ML Lifecycle Flow

```mermaid
flowchart LR
    A["Dataset v1.0<br/>(Synthetic MIMIC-style)"] --> B["Feature Engineering<br/>Pipeline v1.0"]
    B --> C["Training Job<br/>(Docker container)"]
    C --> D{"Model Comparison"}
    D --> E["Logistic<br/>Regression"]
    D --> F["Random<br/>Forest"]
    D --> G["XGBoost"]
    D --> H["PyTorch<br/>Neural Net"]
    E --> I["MLflow Experiment<br/>{ metrics, params, artifacts }"]
    F --> I
    G --> I
    H --> I
    I --> J["Best Model<br/>Selected by F1 / ROC-AUC"]
    J --> K["MLflow Model Registry<br/>Stage: Staging"]
    K --> L{"Promotion Gate"}
    L -->|"Validation Passed"| M["MLflow Model Registry<br/>Stage: Production"]
    L -->|"Validation Failed"| N["Rollback to Previous"]
    M --> O["Prediction Service<br/>Loads model:version:latest"]
    O --> P["Online Inference"]
    P --> Q["Prediction Monitoring<br/>{ drift, latency, accuracy }"]
    Q -->|"Drift Detected"| A
```

## 2. Service Specifications

### 2.1 Frontend Application (Next.js)

**Port:** 3000
**Tech:** Next.js 14, React 18, TypeScript, Tailwind CSS, NextAuth.js, Recharts, React Query

**Routes:**

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Landing / login redirect |
| `/dashboard` | GET | Main dashboard with KPIs |
| `/patients` | GET | Patient list with search |
| `/patients/[id]` | GET | Patient detail + risk + explanation |
| `/patients/[id]/predict` | POST | Trigger prediction |
| `/experiments` | GET | MLflow experiment list |
| `/experiments/[id]` | GET | Single experiment details |
| `/models` | GET | Model registry browser |
| `/models/compare` | GET | Model comparison view |
| `/workflows` | GET | Workflow history and status |
| `/workflows/[id]` | GET | Single workflow detail |
| `/monitoring` | GET | Prediction monitoring dashboard |
| `/admin` | GET | Admin panel (RBAC restricted) |

**Key Components:**

- `PredictionPanel` — Displays risk score with gauge + model version + confidence
- `ShapForcePlot` — Interactive SHAP waterfall/summary plot (React + D3)
- `ModelComparisonChart` — Side-by-side metric comparison
- `WorkflowTimeline` — Visual workflow execution trace
- `ExperimentTable` — Paginated MLflow experiment list with search/filter
- `AuditLogTable` — Searchable audit log viewer (admin only)

**State Management:**

- Server state: React Query (TanStack Query) with stale-while-revalidate
- Client state: React Context for auth, local state for UI
- Real-time: Server-Sent Events for workflow status updates

### 2.2 API Gateway (FastAPI)

**Port:** 8000
**Tech:** FastAPI, Pydantic v2, PyJWT, Prometheus client, structlog

**Middleware Stack (order):**

```
1. HTTPS Redirect (production)
2. CORS (configured per environment)
3. Request ID (UUID v4 per request)
4. Structured Logging (structlog, JSON output)
5. Rate Limiting (token bucket, per-user per-endpoint)
6. JWT Authentication (Bearer token validation)
7. RBAC Authorization (role → permission → resource)
8. Request Validation (Pydantic models)
9. Audit Logging (async write to PostgreSQL)
10. Latency Tracking (OpenTelemetry span)
11. Response Compression (gzip/brotli)
```

**Rate Limits:**

| Endpoint Group | Rate |
|----------------|------|
| Auth endpoints | 10/min per IP |
| Prediction API | 100/min per user |
| Training API | 5/min per user (long-running) |
| Workflow queries | 200/min per user |
| Admin endpoints | 50/min per user |
| Read-only endpoints | 500/min per user |

**Error Response Format:**

```json
{
    "error": {
        "code": "INVALID_PATIENT_DATA",
        "message": "Missing required field: age",
        "details": {
            "field": "age",
            "reason": "required",
            "schema_path": "$.patient.age"
        },
        "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
        "timestamp": "2026-07-15T14:30:00Z"
    }
}
```

### 2.3 Prediction Service

**Port:** 8001
**Tech:** FastAPI, PyTorch, Scikit-learn, SHAP, Pandas, NumPy, MLflow client

**Architecture:**

```mermaid
graph TB
    subgraph "Prediction Service Internals"
        A["REST Endpoint<br/>/predict"]
        B["REST Endpoint<br/>/predict/batch"]
        C["Model Loader"]
        D["Feature Preprocessor"]
        E["Inference Engine"]
        F["SHAP Explainer"]
        G["PostProcessor"]
        H["Health Check<br/>/health"]
    end

    subgraph "Model Loading Strategy"
        I["MLflow Registry<br/>Production Alias"]
        J["Local Model Cache<br/>(disk)"]
        K["In-Memory Model<br/>(hot)"]
        L["Background Refresh<br/>Thread"]
    end

    A --> D
    B --> D
    D --> E
    E --> F
    F --> G
    C --> K
    I --> C
    C --> J
    J --> K
    L --> I
    L --> K
    G --> A
    G --> B
```

**Model Loading Strategy:**

- On startup: load production model from MLflow registry → cache locally → load into memory
- Background thread: polls MLflow registry every 60s for new production model version
- On update: hot-reloads new model without dropping in-flight requests (readers-writer lock)
- Fallback: if registry is unreachable, serve last cached model; log warning
- Cold start: ~2 seconds (download model + load + compile SHAP explainer)

**Prediction Response Schema:**

```json
{
    "prediction": {
        "risk_score": 0.72,
        "risk_level": "HIGH",
        "confidence": 0.89,
        "threshold": 0.35,
        "model_version": "3.2.1",
        "model_name": "xgboost-readmission-v3",
        "prediction_id": "pred_abc123",
        "timestamp": "2026-07-15T14:30:00.123Z",
        "latency_ms": 142
    },
    "features": {
        "age": 72,
        "previous_admissions": 3,
        "comorbidity_score": 7.5,
        "lab_result_abnormal": 1,
        "medication_count": 8,
        "length_of_stay_days": 14
    },
    "explanation": {
        "shap_values": {
            "age": 0.15,
            "previous_admissions": 0.22,
            "comorbidity_score": 0.18,
            "lab_result_abnormal": 0.09,
            "medication_count": 0.05,
            "length_of_stay_days": 0.03
        },
        "base_value": 0.28,
        "top_features": [
            {
                "feature": "previous_admissions",
                "value": 3,
                "shap_value": 0.22,
                "contribution": "increases_risk"
            },
            {
                "feature": "comorbidity_score",
                "value": 7.5,
                "shap_value": 0.18,
                "contribution": "increases_risk"
            },
            {
                "feature": "age",
                "value": 72,
                "shap_value": 0.15,
                "contribution": "increases_risk"
            }
        ]
    },
    "llm_explanation": {
        "summary": "This patient has significantly elevated readmission risk primarily driven by 3 prior admissions in 6 months and a high comorbidity burden. Close follow-up within 48 hours is recommended.",
        "disclaimer": "This explanation is generated by AI for decision support only. It does not constitute a clinical diagnosis or medical advice. All outputs should be reviewed by a qualified healthcare professional.",
        "generated_at": "2026-07-15T14:30:01.456Z"
    },
    "workflow": {
        "triggered": true,
        "workflow_id": "wf_xyz789",
        "workflow_type": "care_coordination",
        "status": "pending",
        "tracking_url": "/workflows/wf_xyz789"
    }
}
```

### 2.4 Training Service

**Port:** 8002
**Tech:** FastAPI, PyTorch, Scikit-learn, XGBoost, Optuna, Pandas, NumPy, MLflow client

**Training Pipeline Architecture:**

```mermaid
flowchart TB
    A["POST /training/start"] --> B["Load Dataset"]
    B --> C["Split<br/>Train / Val / Test<br/>(70/15/15)"]
    C --> D["Feature Engineering<br/>Pipeline"]
    D --> E["Parallel Model Training"]

    subgraph "Training Workers"
        F["Logistic<br/>Regression<br/>+ Optuna"]
        G["Random<br/>Forest<br/>+ Optuna"]
        H["XGBoost<br/>+ Optuna"]
        I["PyTorch<br/>Neural Net<br/>+ Optuna"]
    end

    E --> F
    E --> G
    E --> H
    E --> I

    F --> J["Evaluate on<br/>Validation Set"]
    G --> J
    H --> J
    I --> J

    J --> K["Compare Models<br/>{ F1, ROC-AUC, PR-AUC }"]
    K --> L["Select Best Model"]
    L --> M["Train on<br/>Train + Val"]
    M --> N["Evaluate on<br/>Test Set (held out)"]
    N --> O["Register to MLflow<br/>Stage: Staging"]
    O --> P["Generate Model Card"]
    P --> Q["Update Dashboard"]
```

**Hyperparameter Search Spaces:**

| Model | Parameters | Search Method | Trials |
|-------|-----------|---------------|--------|
| Logistic Regression | C, penalty, solver, max_iter | Grid Search | 24 |
| Random Forest | n_estimators, max_depth, min_samples_split, min_samples_leaf, max_features | Optuna (TPE) | 50 |
| XGBoost | learning_rate, max_depth, n_estimators, subsample, colsample_bytree, gamma, reg_alpha, reg_lambda | Optuna (TPE) | 80 |
| PyTorch NN | n_layers, hidden_dim, dropout, learning_rate, batch_size, weight_decay | Optuna (TPE) | 60 |

**Cross-Validation Strategy:**

- 5-fold stratified cross-validation (preserves class distribution)
- Temporal holdout: last N months as validation (prevents data leakage from future)
- Multiple random seed trials (seeds 42, 123, 2024) for robustness

**Dataset Versioning:**

Each training run records:
- Dataset hash (SHA-256 of feature matrix + targets)
- Dataset version tag (from MLflow dataset tracking)
- Feature pipeline version
- Source data timestamps
- Train/val/test split indices

### 2.5 LLM Service

**Port:** 8003
**Tech:** FastAPI, OpenAI Python SDK, Pydantic, tiktoken

**Architecture:**

```mermaid
sequenceDiagram
    participant GW as API Gateway
    participant LLM as LLM Service
    participant RC as Rate Limiter
    participant CC as Content Checker
    participant PC as Prompt Constructor
    participant AOAI as Azure OpenAI
    participant VAL as Output Validator

    GW->>LLM: POST /explain { features, shap_values, score }
    LLM->>RC: Check rate limit (20/min)
    RC-->>LLM: OK
    LLM->>CC: Validate no PHI in payload
    CC-->>LLM: Clean
    LLM->>PC: Build structured prompt
    PC->>PC: Insert feature values + SHAP contributions
    PC->>PC: Insert model prediction + threshold
    PC->>PC: Inject system prompt + safety guardrails
    PC-->>LLM: Prompt (800 tokens)
    LLM->>AOAI: ChatCompletion (gpt-4o, temp=0.3)
    AOAI-->>LLM: Generated text
    LLM->>VAL: Validate output constraints
    VAL->>VAL: Contains diagnosis? Reject
    VAL->>VAL: Contains override language? Reject
    VAL->>VAL: Contains disclaimer? Verify
    VAL-->>LLM: Validated
    LLM-->>GW: { explanation, disclaimer, latency_ms }
```

**Prompt Template Architecture:**

```
System:
You are a clinical decision support assistant. You receive structured model output
and explain it in clinician-friendly language. You NEVER diagnose, NEVER recommend
specific treatments, and NEVER override the risk score. You always include the
disclaimer that this is AI-generated decision support only.

Context:
- Model: {model_name} v{version}
- Risk score: {score} ({risk_level})
- Threshold: {threshold}
- Top contributing factors: {top_features}

Feature Data:
{feature_table}

Patient Context:
- Age: {age}
- Previous admissions (6mo): {previous_admissions}
- Primary diagnosis: {primary_diagnosis}

Instructions:
1. Summarize the readmission risk level in one sentence.
2. Explain the top 3-4 contributing factors in plain clinical language.
3. Suggest general monitoring considerations (no specific treatments).
4. End with the exact disclaimer text.

Output Format (JSON):
{
    "summary": "...",
    "contributing_factors": [{ "factor": "...", "explanation": "..." }],
    "monitoring_suggestions": ["..."],
    "disclaimer": "..."
}

Disclaimer: "This analysis is AI-generated decision support only. It does not
constitute a clinical diagnosis, medical advice, or a substitute for professional
clinical judgment. All AI-generated outputs must be reviewed by a qualified
healthcare professional before any clinical action is taken."
```

**Safety Guards:**

- Input: PHI regex scanner rejects known PHI patterns (MRNs, SSNs, DOBs)
- Input: Token limit (2048 max), prompt injection detection via delimiters
- Inference: Temperature 0.3 for reproducibility; max_tokens 1024
- Output: Regex validator rejects any diagnosis statements ("patient has X")
- Output: Validator checks for mandatory disclaimer inclusion
- Output: If quality < 0.8 (via embedding similarity to expected form), fallback to template-based explanation
- Latency target: < 3s p95
- Rate limit: 20 requests/minute per user, 100/minute overall

### 2.6 Workflow Service

**Port:** 8004
**Tech:** FastAPI, Temporal Python SDK, n8n webhook client, PostgreSQL

**Dual orchestration design:**

```mermaid
graph TB
    subgraph "Workflow Service"
        A["POST /workflow/trigger"]
        B["GET /workflow/{id}"]
        C["GET /workflow/status"]
    end

    subgraph "Temporal (Durable Execution)"
        D["CareCoordination<br/>Workflow"]
        E["ModelRetraining<br/>Workflow"]
        F["DataRefresh<br/>Workflow"]
        G["Monitoring<br/>Workflow"]
    end

    subgraph "n8n (Rapid Automation)"
        H["Create Follow-up<br/>Appointment"]
        I["Notify Physician<br/>(email/SMS)"]
        J["Notify Care<br/>Coordinator"]
        K["Send Patient<br/>Reminder"]
        L["Log to Audit<br/>Trail"]
    end

    subgraph "Failure Handling"
        M["Retry Queue<br/>(3 attempts)"]
        N["Dead Letter Queue"]
        O["Escalation Path"]
    end

    A --> D
    D --> H
    H --> I
    I --> J
    J --> K
    K --> L
    D --> M
    M --> D
    M --> N
    N --> O
```

**Temporal Workflow: Care Coordination**

```python
# Pseudocode — the actual durable workflow
async def CareCoordinationWorkflow(ctx: WorkflowContext, patient_id: str, risk_score: float):
    # Step 1: Check for existing active care plan
    existing = await lookup_active_care_plan(patient_id)
    if existing:
        return {"skipped": True, "reason": "Active care plan exists"}

    # Step 2: Create care episode
    episode_id = await create_care_episode(patient_id, risk_score)

    # Step 3: Execute n8n workflows with compensation
    notification_result = await execute_activity(
        NotifyCareTeam,
        args=[patient_id, risk_score, episode_id],
        retry_policy={"max_retries": 3, "backoff": "exponential"},
        compensation=delete_notification
    )

    # Step 4: Schedule follow-up (with Temporal timer)
    await asyncio.sleep(3600)  # 1-hour delay for scheduling
    schedule_result = await execute_activity(
        ScheduleFollowUp,
        args=[patient_id, episode_id],
        retry_policy={"max_retries": 3}
    )

    # Step 5: Monitor adherence (child workflow)
    child = await start_child_workflow(
        MonitorAdherenceWorkflow,
        args=[patient_id, episode_id],
        execution_timeout="30 days"
    )

    return {"episode_id": episode_id, "status": "ACTIVE"}
```

**n8n Workflow: Care Coordination Automation**

```json
{
    "name": "High Risk Care Coordination",
    "trigger": "webhook",
    "steps": [
        {
            "id": 1,
            "node": "Webhook Receiver",
            "parameters": {
                "path": "care-coordination-trigger"
            }
        },
        {
            "id": 2,
            "node": "HTTP Request",
            "name": "Get Patient Details",
            "parameters": {
                "url": "http://api-gateway:8000/api/v1/patients/{{$json.patient_id}}",
                "method": "GET"
            }
        },
        {
            "id": 3,
            "node": "IF",
            "name": "Check Risk Level",
            "parameters": {
                "conditions": {
                    "string": [
                        { "value1": "={{$json.risk_level}}", "operation": "equal", "value2": "HIGH" }
                    ]
                }
            }
        },
        {
            "id": 4,
            "node": "Gmail",
            "name": "Notify Physician",
            "parameters": {
                "to": "={{$json.physician_email}}",
                "subject": "High Readmission Risk Alert - Patient {{$json.patient_name}}",
                "html": "<p>Patient <b>{{$json.patient_name}}</b> (MRN: {{$json.mrn}}) has been identified with <b>{{$json.risk_level}}</b> readmission risk.</p><p>Risk Score: {{$json.risk_score}}</p><p>A follow-up appointment has been scheduled.</p>"
            }
        },
        {
            "id": 5,
            "node": "Gmail",
            "name": "Notify Care Coordinator",
            "parameters": {
                "to": "={{$json.coordinator_email}}",
                "subject": "Care Coordination Required - Patient {{$json.patient_name}}"
            }
        },
        {
            "id": 6,
            "node": "Twilio",
            "name": "Send Patient SMS Reminder",
            "parameters": {
                "to": "={{$json.patient_phone}}",
                "message": "Your follow-up appointment has been scheduled for {{$json.appointment_date}}. Please call (555) 123-4567 to confirm or reschedule."
            }
        },
        {
            "id": 7,
            "node": "PostgreSQL",
            "name": "Log Workflow Event",
            "parameters": {
                "query": "INSERT INTO workflow_events (patient_id, workflow_type, status, triggered_at) VALUES ($1, 'care_coordination', 'COMPLETED', NOW())",
                "params": ["={{$json.patient_id}}"]
            }
        },
        {
            "id": 8,
            "node": "HTTP Request",
            "name": "Update Dashboard",
            "parameters": {
                "url": "http://api-gateway:8000/api/v1/workflows/events",
                "method": "POST",
                "body": {
                    "patient_id": "={{$json.patient_id}}",
                    "event_type": "care_coordination_triggered",
                    "status": "completed"
                }
            }
        }
    ]
}
```

### 2.7 PostgreSQL Database

**Connection:** Shared across services (service-specific roles with least-privilege)

**Schema overview:** See [DATA_MODEL.md](DATA_MODEL.md) for complete ER diagram and DDL.

**Table Summaries:**

| Table | Purpose | Estimated Rows | Growth Rate |
|-------|---------|---------------|-------------|
| `users` | Auth + RBAC | 1K | Low |
| `patients` | Patient records (synthetic) | 100K | Medium |
| `predictions` | Inference results | 10M | High |
| `workflow_events` | Workflow state machine | 5M | High |
| `model_versions` | Registry mirror | 100 | Low |
| `experiments` | MLflow experiment cache | 1K | Low |
| `audit_logs` | Access records | 50M | Very High |
| `feature_store` | Precomputed features | 1M | Medium |

**Indexing Strategy:**

- B-tree on all FK columns
- Partial index on predictions: `WHERE risk_level = 'HIGH'` for dashboard queries
- Composite index on audit_logs: `(user_id, created_at DESC)` for audit queries
- BRIN index on time-series tables (workflow_events, predictions) for range scans
- GIN index on JSONB columns where applicable

**Partitioning Strategy:**

- `predictions`: Range-partitioned by month (prediction_timestamp)
- `audit_logs`: Range-partitioned by month (created_at)
- `workflow_events`: Range-partitioned by month (triggered_at)
- Partition pruning via query constraints

## 3. ML Pipeline Design

### 3.1 Feature Engineering Pipeline

```mermaid
graph LR
    A["Raw Patient Data"] --> B["Missing Value Handler<br/>{ median impute, mode impute, indicator flags }"]
    B --> C["Categorical Encoder<br/>{ one-hot, target encoding }"]
    C --> D["Feature Scaler<br/>{ StandardScaler, RobustScaler }"]
    D --> E["Outlier Detector<br/>{ IQR, z-score, winsorization }"]
    E --> F["Feature Selector<br/>{ mutual info, RFE, L1 }"]
    F --> G["Correlation Filter<br/>{ remove > 0.95 correlated }"]
    G --> H["Final Feature Matrix"]
    H --> I["Save Pipeline Artifact<br/>{ joblib + schema.json }"]
    I --> J["Register to MLflow<br/>as Pipeline vX.Y"]
```

**Feature Groups:**

| Feature Group | Examples | Count |
|--------------|----------|-------|
| Demographics | Age, gender | 2 |
| Admission History | Previous admissions, LOS, ICU days | 6 |
| Diagnoses | Comorbidity score, primary Dx group | 10 |
| Procedures | Procedure count, recent surgeries | 4 |
| Lab Results | Abnormal labs, trend flags | 8 |
| Medications | Medication count, high-risk meds | 5 |
| Vital Signs | Discharge vitals (BP, HR, SpO2) | 4 |
| Social Factors | Discharge disposition, insurance type | 5 |
| **Total** | | **44** |

### 3.2 Model Comparison Framework

```mermaid
graph TB
    A["Training Complete<br/>4 models trained"] --> B["Collect Metrics"]
    B --> C["Primary Metric: F1<br/>(balanced precision/recall)"]
    B --> D["Secondary: ROC-AUC"]
    B --> E["Secondary: PR-AUC"]
    B --> F["Calibration<br/>Brier Score"]
    B --> G["Inference<br/>Latency (p95)"]
    B --> H["Model Size"]
    C --> I["Weighted Score<br/>Computation"]
    D --> I
    E --> I
    F --> I
    G --> I
    H --> I
    I --> J{"Best Model<br/>Selected"}
    J --> K["Register to MLflow<br/>Stage: Staging"]
    K --> L["Generate<br/>Comparison Report"]
    L --> M["Visual Comparison<br/>{ parallel coords, radar chart }"]
```

**Scoring Formula:**

```
weighted_score = 0.35 * normalized(F1)
              + 0.25 * normalized(ROC-AUC)
              + 0.15 * normalized(PR-AUC)
              - 0.10 * normalized(Brier)
              - 0.10 * normalized(latency)
              - 0.05 * normalized(model_size_mb)
```

### 3.3 Threshold Selection

```mermaid
graph LR
    A["Validation Set"] --> B["Compute precision/recall<br/>at all thresholds"]
    B --> C["Find threshold that<br/>maximizes F1"]
    C --> D["Find threshold where<br/>recall >= 0.85"]
    D --> E["Select max(F1, recall_constrained)"]
    E --> F["Validate on test set"]
    F --> G["Set production threshold"]
```

**Default Thresholds:**

| Risk Level | Score Range | Action |
|------------|-------------|--------|
| LOW | 0.00 – 0.20 | Standard discharge |
| MODERATE | 0.20 – 0.35 | Enhanced discharge instructions |
| HIGH | 0.35 – 0.65 | Care coordination workflow triggered |
| CRITICAL | 0.65 – 1.00 | Immediate care team notification |

### 3.4 Model Rollback Strategy

```mermaid
flowchart TD
    A["Monitoring detects<br/>metric degradation"] --> B{"Degradation > 10%?"}
    B -->|"Yes"| C["Automatic rollback<br/>to previous production model"]
    B -->|"No"| D["Alert engineering team"]
    C --> E["MLflow: demote current to 'Archived'"]
    C --> F["MLflow: restore previous to 'Production'"]
    F --> G["Prediction Service<br/>hot-reloads model"]
    G --> H["Incident created<br/>in tracking system"]
    H --> I["Training Service<br/>initiates investigation"]
    I --> J["Root cause analysis"]
    J --> K["Fix + new candidate model"]
    K --> L["Gate: re-enter promotion pipeline"]
```

## 4. Observability Architecture

### 4.1 Logging

Every service outputs structured JSON logs via `structlog`:

```json
{
    "timestamp": "2026-07-15T14:30:00.123Z",
    "level": "INFO",
    "service": "prediction-service",
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "event": "prediction_completed",
    "user_id": "usr_42",
    "patient_id": "pat_789",
    "model_version": "3.2.1",
    "latency_ms": 142,
    "risk_score": 0.72,
    "risk_level": "HIGH",
    "trace_id": "trace_xyz"
}
```

### 4.2 Metrics (Prometheus)

**Prediction Service:**

| Metric | Type | Labels |
|--------|------|--------|
| `predictions_total` | Counter | model, risk_level, status |
| `prediction_latency_seconds` | Histogram | model, quantile (p50/p95/p99) |
| `model_version_current` | Gauge | model_name |
| `shap_computation_time` | Histogram | - |
| `model_load_time_seconds` | Histogram | model_name |
| `model_load_attempts_total` | Counter | model_name, status |

**Workflow Service:**

| Metric | Type | Labels |
|--------|------|--------|
| `workflow_triggers_total` | Counter | workflow_type |
| `workflow_duration_seconds` | Histogram | workflow_type, status |
| `workflow_retries_total` | Counter | workflow_type |
| `workflow_failures_total` | Counter | workflow_type, reason |

**Gateway:**

| Metric | Type | Labels |
|--------|------|--------|
| `http_requests_total` | Counter | method, endpoint, status_code |
| `http_request_duration_seconds` | Histogram | method, endpoint |
| `active_connections` | Gauge | - |
| `rate_limit_exceeded_total` | Counter | user_id |

### 4.3 Alerting Rules (Prometheus)

```yaml
# prediction_alerts.yml
groups:
  - name: prediction
    rules:
      - alert: HighPredictionLatency
        expr: histogram_quantile(0.95, rate(prediction_latency_seconds_bucket[5m])) > 1.0
        for: 5m
        labels: { severity: warning }
        annotations:
          summary: "Prediction latency p95 > 1s"

      - alert: PredictionServiceDown
        expr: up{job="prediction-service"} == 0
        for: 1m
        labels: { severity: critical }
        annotations:
          summary: "Prediction service unreachable"

      - alert: ModelDriftDetected
        expr: rate(predictions_total{risk_level="HIGH"}[1h]) > 1.5 * rate(predictions_total{risk_level="HIGH"}[1d])
        for: 30m
        labels: { severity: warning }
        annotations:
          summary: "Potential data drift — HIGH risk predictions up {{ $value | humanize }}x"

  - name: workflow
    rules:
      - alert: WorkflowFailureRateHigh
        expr: rate(workflow_failures_total[15m]) > 0.1
        for: 5m
        labels: { severity: critical }

      - alert: WorkflowStuck
        expr: time() - workflow_last_success > 3600
        for: 10m
        labels: { severity: warning }
```

### 4.4 Health Endpoints

Every service implements:

```
GET /health          → {"status": "healthy", "version": "1.0.0", "uptime_seconds": 12345}
GET /health/ready    → {"ready": true, "dependencies": {"postgres": "up", "mlflow": "up", "redis": "up"}}
GET /health/live     → {"alive": true}
```

## 5. Security Architecture

### 5.1 Authentication

- JWT-based with RS256 signing
- Access token: 15-minute expiry
- Refresh token: 7-day expiry (HTTP-only secure cookie)
- Token stored: Authorization Bearer header (access), secure cookie (refresh)
- Blacklist: compromised tokens via Redis invalid set
- Roles: `admin`, `clinician`, `coordinator`, `viewer`

### 5.2 Authorization (RBAC)

| Resource | Admin | Clinician | Coordinator | Viewer |
|----------|-------|-----------|-------------|--------|
| Dashboard | R/W | R | R | R |
| Patients | R/W | R/W | R | R |
| Predictions | R/W | R/W | R | R |
| Training | R/W | - | - | - |
| Model Registry | R/W | R | - | R |
| Experiments | R/W | R | - | R |
| Workflow Config | R/W | - | R | - |
| Audit Logs | R | - | - | - |
| User Management | R/W | - | - | - |

### 5.3 Data Protection

- **At Rest:** PostgreSQL TDE, Azure Storage encryption (server-side)
- **In Transit:** TLS 1.3 minimum, mTLS between internal services
- **Secrets:** Azure Key Vault, never in environment variables or config files
- **PHI:** Synthetic data only; PHI scanner on all input/output payloads
- **Audit:** All access to prediction data logged immutably

## 6. API Versioning

- URL-based versioning: `/api/v1/`, `/api/v2/`
- Deprecation policy: minor versions backward-compatible within major version
- Sunset header: `Sunset: Sat, 15 Jan 2027 00:00:00 GMT`
- Migration guide published for each major version change
- Health endpoint reflects API version

## 7. Performance Targets

| Metric | Target | Degradation Threshold |
|--------|--------|----------------------|
| Prediction latency (p50) | < 100ms | > 200ms |
| Prediction latency (p95) | < 500ms | > 1s |
| Prediction latency (p99) | < 1s | > 2s |
| SHAP computation (p50) | < 200ms | > 500ms |
| LLM explanation (p95) | < 3s | > 5s |
| API throughput | 500 req/s | 300 req/s |
| Model hot-reload | < 5s | > 15s |
| Database query (simple) | < 10ms | > 50ms |
| Database query (complex) | < 100ms | > 500ms |
| Workflow trigger → notification | < 30s | > 60s |

## 8. Scalability Architecture

```mermaid
graph TB
    subgraph "Load Patterns"
        A["Prediction: Bursty<br/>(end-of-shift batch)"]
        B["Training: Scheduled<br/>(weekly)"]
        C["Workflow: Steady<br/>(event-driven)"]
    end

    subgraph "Horizontal Scaling"
        D["Prediction Service<br/>Horizontal Pod Autoscaler<br/>{ CPU: 70%, req/sec: 100 }"]
        E["API Gateway<br/>Horizontal Pod Autoscaler<br/>{ CPU: 60%, req/sec: 500 }"]
        F["LLM Service<br/>Limited by Azure OpenAI quota"]
    end

    subgraph "Vertical Scaling"
        G["Training Service<br/>GPU / High-memory SKU"]
        H["PostgreSQL<br/>Azure Cosmos DB for PostgreSQL<br/>(Citus distributed)"]
    end

    A --> D
    C --> E
    B --> G
    D --> H
    E --> H
```

## 9. Cost Optimization

| Strategy | Implementation | Estimated Savings |
|----------|---------------|-------------------|
| Model caching | In-memory SHAP explainer reuse | 60% on compute |
| Batch predictions | `/predict/batch` endpoint | 40% on API calls |
| Connection pooling | PgBouncer / Azure PG pool | 30% on DB connections |
| Cold start optimization | Keep-warm via health probe | Eliminates cold starts |
| MLflow artifact cleanup | Lifecycle policy (30d staging) | 50% on blob storage |
| LLM token optimization | Greedy decoding, token limits | 40% on API costs |
| Autoscaling floor | Min 2, max 10 instances | Prevents over-provisioning |