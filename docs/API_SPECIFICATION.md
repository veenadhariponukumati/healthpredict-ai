# API Specification

## Base URL

- **Development:** `http://localhost:8000/api/v1`
- **Production:** `https://api.readmission-platform.com/api/v1`

## Authentication

All endpoints (except `/auth/*`, `/health`, `/docs`) require a Bearer JWT token:

```
Authorization: Bearer <access_token>
```

### Rate Limiting

Rate limit headers are returned on every response:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1626385200
```

### Standard Error Response

```json
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable description",
        "details": {},
        "request_id": "uuid",
        "timestamp": "2026-07-15T14:30:00Z"
    }
}
```

### Standard Headers

Every response includes:

| Header | Description |
|--------|-------------|
| `X-Request-ID` | Traceable request identifier |
| `X-Service-Version` | API gateway version |
| `X-Response-Time-Ms` | Server-side processing time |

---

## 1. Authentication Endpoints

### POST /api/v1/auth/register

Register a new user.

**Request:**
```json
{
    "email": "clinician@hospital.org",
    "password": "SecureP@ss123!",
    "full_name": "Dr. Jane Smith",
    "role": "clinician"
}
```

**Response (201):**
```json
{
    "user": {
        "id": "usr_a1b2c3d4",
        "email": "clinician@hospital.org",
        "full_name": "Dr. Jane Smith",
        "role": "clinician",
        "is_active": true,
        "created_at": "2026-07-15T14:30:00Z"
    },
    "message": "User registered. Awaiting admin activation."
}
```

### POST /api/v1/auth/login

Authenticate and receive tokens.

**Request:**
```json
{
    "email": "clinician@hospital.org",
    "password": "SecureP@ss123!"
}
```

**Response (200):**
```json
{
    "access_token": "eyJhbGciOiJSUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJSUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 900,
    "user": {
        "id": "usr_a1b2c3d4",
        "email": "clinician@hospital.org",
        "full_name": "Dr. Jane Smith",
        "role": "clinician"
    }
}
```

### POST /api/v1/auth/refresh

Refresh expired access token.

**Request:**
```
Cookie: refresh_token=eyJhbGciOiJSUzI1NiIs...
```

**Response (200):**
```json
{
    "access_token": "eyJhbGciOiJSUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 900
}
```

### POST /api/v1/auth/logout

Invalidate current tokens.

**Response (200):**
```json
{
    "message": "Logged out successfully"
}
```

---

## 2. Patient Endpoints

### GET /api/v1/patients

List patients with pagination and filtering.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number |
| `per_page` | integer | 20 | Items per page (max 100) |
| `search` | string | — | Search name or MRN |
| `risk_level` | string | — | Filter by last risk level |
| `diagnosis` | string | — | Filter by primary diagnosis |
| `sort_by` | string | `created_at` | Sort field |
| `sort_order` | string | `desc` | asc or desc |

**Response (200):**
```json
{
    "data": [
        {
            "id": "pat_abc123",
            "mrn": "MRN-001234",
            "first_name": "John",
            "last_name": "Doe",
            "age": 72,
            "gender": "M",
            "primary_diagnosis": "Congestive Heart Failure",
            "last_risk_score": 0.72,
            "last_risk_level": "HIGH",
            "last_prediction_at": "2026-07-15T14:30:00Z",
            "has_active_workflow": true
        }
    ],
    "pagination": {
        "page": 1,
        "per_page": 20,
        "total": 1542,
        "total_pages": 78
    }
}
```

### GET /api/v1/patients/{patient_id}

Get full patient details with latest prediction.

**Response (200):**
```json
{
    "patient": {
        "id": "pat_abc123",
        "mrn": "MRN-001234",
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1954-03-15",
        "age": 72,
        "gender": "M",
        "primary_diagnosis": "Congestive Heart Failure",
        "discharge_disposition": "Home with home health",
        "insurance_type": "Medicare",
        "previous_admissions_6mo": 3,
        "length_of_stay_days": 14,
        "icu_days": 2,
        "procedure_count": 4,
        "medication_count": 8,
        "comorbidity_score": 7.5,
        "lab_results": {
            "hemoglobin": 10.2,
            "creatinine": 1.8,
            "bnp": 850,
            "sodium": 132
        },
        "vital_signs": {
            "discharge_bp_systolic": 138,
            "discharge_hr": 88,
            "discharge_spo2": 94
        },
        "created_at": "2026-06-01T10:00:00Z",
        "updated_at": "2026-07-15T14:00:00Z"
    },
    "latest_prediction": {
        "id": "pred_abc123",
        "risk_score": 0.72,
        "risk_level": "HIGH",
        "confidence": 0.89,
        "prediction_timestamp": "2026-07-15T14:30:00Z"
    }
}
```

### POST /api/v1/patients

Create a new patient record.

**Request:**
```json
{
    "mrn": "MRN-001234",
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1954-03-15",
    "gender": "M",
    "primary_diagnosis": "Congestive Heart Failure",
    "discharge_disposition": "Home with home health",
    "insurance_type": "Medicare",
    "previous_admissions_6mo": 3,
    "length_of_stay_days": 14,
    "icu_days": 2,
    "procedure_count": 4,
    "medication_count": 8,
    "comorbidity_score": 7.5,
    "lab_results": {
        "hemoglobin": 10.2,
        "creatinine": 1.8,
        "bnp": 850
    },
    "vital_signs": {
        "discharge_bp_systolic": 138,
        "discharge_hr": 88,
        "discharge_spo2": 94
    }
}
```

**Validation Rules:**
- `mrn`: Required, unique, pattern `MRN-\d{6}`
- `first_name`, `last_name`: Required, 1-100 chars
- `date_of_birth`: Required, must be in the past
- `age`: Computed from date_of_birth, 0-120
- `previous_admissions_6mo`: 0-50
- `length_of_stay_days`: 0-365
- `comorbidity_score`: 0.0-40.0

**Response (201):**
```json
{
    "patient": {
        "id": "pat_abc123",
        "mrn": "MRN-001234",
        ...
    }
}
```

---

## 3. Prediction Endpoints

### POST /api/v1/predict

Generate a readmission risk prediction for a patient.

**Request:**
```json
{
    "patient_id": "pat_abc123",
    "generate_explanation": true,
    "trigger_workflow": true,
    "features": {
        "age": 72,
        "previous_admissions": 3,
        "comorbidity_score": 7.5,
        "lab_result_abnormal": 1,
        "medication_count": 8,
        "length_of_stay_days": 14
    }
}
```

**Response (200):**
```json
{
    "prediction": {
        "id": "pred_abc123",
        "risk_score": 0.72,
        "risk_level": "HIGH",
        "confidence": 0.89,
        "threshold": 0.35,
        "model_version": "3.2.1",
        "model_name": "xgboost-readmission-v3",
        "prediction_timestamp": "2026-07-15T14:30:00.123Z",
        "inference_latency_ms": 142
    },
    "explanation": {
        "shap_values": { ... },
        "base_value": 0.28,
        "top_features": [ ... ]
    },
    "llm_explanation": {
        "summary": "...",
        "disclaimer": "..."
    },
    "workflow": {
        "triggered": true,
        "workflow_id": "wf_xyz789",
        "status": "pending"
    }
}
```

### POST /api/v1/predict/batch

Batch predictions for multiple patients.

**Request:**
```json
{
    "patients": [
        {
            "patient_id": "pat_abc123",
            "features": { ... }
        },
        {
            "patient_id": "pat_def456",
            "features": { ... }
        }
    ],
    "generate_explanation": false,
    "trigger_workflow": false
}
```

**Response (200):**
```json
{
    "predictions": [
        {
            "patient_id": "pat_abc123",
            "risk_score": 0.72,
            "risk_level": "HIGH",
            "model_version": "3.2.1"
        },
        {
            "patient_id": "pat_def456",
            "risk_score": 0.15,
            "risk_level": "LOW",
            "model_version": "3.2.1"
        }
    ],
    "summary": {
        "total": 2,
        "high_risk": 1,
        "moderate_risk": 0,
        "low_risk": 1,
        "mean_risk_score": 0.435,
        "processing_time_ms": 85
    }
}
```

### GET /api/v1/predictions

Query prediction history.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `patient_id` | UUID | — | Filter by patient |
| `risk_level` | string | — | Filter by risk level |
| `model_version` | string | — | Filter by model version |
| `from_date` | ISO datetime | — | Start of time range |
| `to_date` | ISO datetime | — | End of time range |
| `page` | integer | 1 | Page number |
| `per_page` | integer | 20 | Items per page |

**Response (200):**
```json
{
    "data": [ ... ],
    "pagination": { ... }
}
```

---

## 4. Model Registry Endpoints

### GET /api/v1/models

List all registered models.

**Response (200):**
```json
{
    "data": [
        {
            "id": "mod_abc123",
            "model_name": "xgboost-readmission-v3",
            "model_type": "xgboost",
            "version": "3.2.1",
            "stage": "Production",
            "f1_score": 0.845,
            "roc_auc": 0.912,
            "trained_at": "2026-07-10T08:00:00Z",
            "promoted_at": "2026-07-12T10:00:00Z"
        }
    ],
    "pagination": { ... }
}
```

### GET /api/v1/models/production

Get the current production model.

**Response (200):**
```json
{
    "model": {
        "id": "mod_abc123",
        "model_name": "xgboost-readmission-v3",
        "version": "3.2.1",
        "stage": "Production",
        "metrics": {
            "accuracy": 0.87,
            "precision": 0.82,
            "recall": 0.88,
            "f1_score": 0.845,
            "roc_auc": 0.912,
            "pr_auc": 0.785,
            "brier_score": 0.112
        },
        "feature_importance": {
            "previous_admissions": 0.22,
            "comorbidity_score": 0.18,
            "age": 0.15,
            "lab_result_abnormal": 0.09,
            "medication_count": 0.05,
            "length_of_stay_days": 0.03
        },
        "hyperparameters": {
            "learning_rate": 0.05,
            "max_depth": 6,
            "n_estimators": 300,
            "subsample": 0.8,
            "colsample_bytree": 0.7
        },
        "pipeline_version": "2.3.1",
        "promoted_at": "2026-07-12T10:00:00Z"
    }
}
```

### GET /api/v1/models/compare

Compare multiple model versions.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_ids` | comma-separated UUIDs | — | Models to compare |

**Response (200):**
```json
{
    "comparison": [
        {
            "version": "3.2.1",
            "model_type": "xgboost",
            "f1_score": 0.845,
            "roc_auc": 0.912,
            "pr_auc": 0.785,
            "brier_score": 0.112,
            "latency_ms": 42,
            "model_size_mb": 18.5
        },
        {
            "version": "3.1.0",
            "model_type": "random_forest",
            "f1_score": 0.811,
            "roc_auc": 0.889,
            "pr_auc": 0.754,
            "brier_score": 0.134,
            "latency_ms": 65,
            "model_size_mb": 42.0
        },
        {
            "version": "2.4.0",
            "model_type": "pytorch_nn",
            "f1_score": 0.802,
            "roc_auc": 0.876,
            "pr_auc": 0.741,
            "brier_score": 0.145,
            "latency_ms": 38,
            "model_size_mb": 12.1
        }
    ],
    "best_model": "3.2.1 (xgboost)"
}
```

### POST /api/v1/models/promote

Promote a model from staging to production.

**Request:**
```json
{
    "model_version_id": "mod_abc123",
    "reason": "Improved F1 from 0.811 to 0.845, lower Brier score"
}
```

**Response (200):**
```json
{
    "message": "Model promoted to Production",
    "model": {
        "id": "mod_abc123",
        "version": "3.2.1",
        "previous_stage": "Staging",
        "current_stage": "Production",
        "promoted_at": "2026-07-15T14:30:00Z"
    },
    "previous_production": {
        "id": "mod_prev456",
        "version": "3.1.0",
        "new_stage": "Archived"
    }
}
```

---

## 5. Training Endpoints

### POST /api/v1/training/start

Trigger a new training run.

**Request:**
```json
{
    "dataset_version": "v2.1",
    "models_to_train": ["logistic_regression", "random_forest", "xgboost", "pytorch_nn"],
    "hyperparameter_trials": {
        "logistic_regression": 24,
        "random_forest": 50,
        "xgboost": 80,
        "pytorch_nn": 60
    },
    "cross_validation_folds": 5,
    "test_split": 0.15,
    "random_seed": 42
}
```

**Response (202):**
```json
{
    "experiment_id": "exp_789xyz",
    "mlflow_experiment_id": 42,
    "status": "RUNNING",
    "tracking_url": "http://localhost:5000/#/experiments/42",
    "estimated_duration_minutes": 45,
    "started_at": "2026-07-15T14:30:00Z"
}
```

### GET /api/v1/training/status/{experiment_id}

Get training run status.

**Response (200):**
```json
{
    "experiment_id": "exp_789xyz",
    "status": "RUNNING",
    "progress": {
        "models_completed": 2,
        "models_total": 4,
        "current_model": "xgboost",
        "current_trial": 32,
        "trials_total": 80,
        "best_f1_so_far": 0.84
    },
    "started_at": "2026-07-15T14:30:00Z",
    "elapsed_seconds": 1245
}
```

---

## 6. Workflow Endpoints

### GET /api/v1/workflows

List workflow events.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `patient_id` | UUID | — | Filter by patient |
| `workflow_type` | string | — | Filter by type |
| `status` | string | — | Filter by status |
| `from_date` | ISO datetime | — | Start of time range |
| `page` | integer | 1 | Page number |
| `per_page` | integer | 20 | Items per page |

**Response (200):**
```json
{
    "data": [
        {
            "id": "wf_xyz789",
            "patient_id": "pat_abc123",
            "workflow_type": "care_coordination",
            "status": "COMPLETED",
            "retry_count": 0,
            "triggered_at": "2026-07-15T14:30:00Z",
            "completed_at": "2026-07-15T14:31:15Z",
            "output_result": {
                "appointment_scheduled": true,
                "physician_notified": true,
                "coordinator_notified": true,
                "patient_reminder_sent": true
            }
        }
    ],
    "pagination": { ... }
}
```

### GET /api/v1/workflows/{workflow_id}

Get detailed workflow status.

**Response (200):**
```json
{
    "workflow": {
        "id": "wf_xyz789",
        "patient_id": "pat_abc123",
        "prediction_id": "pred_abc123",
        "workflow_type": "care_coordination",
        "status": "COMPLETED",
        "retry_count": 0,
        "max_retries": 3,
        "temporal_workflow_id": "temporal_abc123",
        "n8n_execution_id": "n8n_def456",
        "input_payload": {
            "patient_id": "pat_abc123",
            "risk_score": 0.72,
            "risk_level": "HIGH"
        },
        "output_result": {
            "appointment_scheduled": {
                "status": "success",
                "appointment_id": "apt_789",
                "date": "2026-07-18T10:00:00Z"
            },
            "physician_notified": {
                "status": "success",
                "channel": "email",
                "sent_at": "2026-07-15T14:30:45Z"
            },
            "coordinator_notified": {
                "status": "success",
                "channel": "email",
                "sent_at": "2026-07-15T14:30:47Z"
            },
            "patient_reminder": {
                "status": "success",
                "channel": "sms",
                "sent_at": "2026-07-15T14:31:00Z"
            }
        },
        "triggered_at": "2026-07-15T14:30:00Z",
        "completed_at": "2026-07-15T14:31:15Z",
        "duration_seconds": 75
    },
    "timeline": [
        {
            "step": "workflow_started",
            "timestamp": "2026-07-15T14:30:00.000Z",
            "status": "success"
        },
        {
            "step": "appointment_scheduled",
            "timestamp": "2026-07-15T14:30:30.123Z",
            "status": "success"
        },
        {
            "step": "physician_notified",
            "timestamp": "2026-07-15T14:30:45.456Z",
            "status": "success"
        },
        {
            "step": "coordinator_notified",
            "timestamp": "2026-07-15T14:30:47.789Z",
            "status": "success"
        },
        {
            "step": "patient_reminder_sent",
            "timestamp": "2026-07-15T14:31:00.012Z",
            "status": "success"
        },
        {
            "step": "workflow_completed",
            "timestamp": "2026-07-15T14:31:15.000Z",
            "status": "success"
        }
    ]
}
```

---

## 7. Dashboard / Monitoring Endpoints

### GET /api/v1/dashboard/summary

Aggregate dashboard metrics.

**Response (200):**
```json
{
    "period": {
        "start": "2026-07-01T00:00:00Z",
        "end": "2026-07-15T23:59:59Z"
    },
    "patients": {
        "total_active": 1542,
        "new_this_period": 87
    },
    "predictions": {
        "total": 3421,
        "high_risk": 342,
        "moderate_risk": 684,
        "low_risk": 2395,
        "high_risk_percentage": 10.0
    },
    "workflows": {
        "total_triggered": 342,
        "completed": 318,
        "failed": 3,
        "in_progress": 21,
        "completion_rate": 92.98
    },
    "model_performance": {
        "current_model": "xgboost-readmission-v3",
        "current_version": "3.2.1",
        "f1_score": 0.845,
        "roc_auc": 0.912,
        "monitoring_window_days": 14,
        "drift_detected": false
    }
}
```

### GET /api/v1/monitoring/drift

Feature drift monitoring data.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `window_days` | integer | 14 | Lookback window |

**Response (200):**
```json
{
    "drift_report": {
        "overall_drift_detected": false,
        "features": [
            {
                "feature": "age",
                "drift_score": 0.02,
                "drift_detected": false,
                "distribution_distance": "KS statistic = 0.03"
            },
            {
                "feature": "comorbidity_score",
                "drift_score": 0.12,
                "drift_detected": false,
                "distribution_distance": "KS statistic = 0.08"
            }
        ],
        "model_performance": {
            "current_f1": 0.845,
            "baseline_f1": 0.851,
            "f1_drop": 0.006,
            "degradation_alert": false
        },
        "data_quality": {
            "missing_values_pct": 0.5,
            "out_of_range_values_pct": 0.1,
            "new_categories_detected": 0
        }
    }
}
```

---

## 8. Health Endpoints

### GET /health

Service health check.

**Response (200):**
```json
{
    "status": "healthy",
    "version": "1.0.0",
    "uptime_seconds": 123456,
    "services": {
        "postgres": "up",
        "mlflow": "up",
        "redis": "up",
        "prediction_service": "up",
        "llm_service": "up",
        "workflow_service": "up"
    }
}
```

### GET /health/ready

Readiness check (all dependencies available).

**Response (200):**
```json
{
    "ready": true,
    "dependencies": {
        "postgres": { "status": "up", "latency_ms": 2 },
        "mlflow": { "status": "up", "latency_ms": 15 },
        "redis": { "status": "up", "latency_ms": 1 },
        "prediction_service": { "status": "up", "model_loaded": true, "model_version": "3.2.1" }
    }
}
```

### GET /health/live

Liveness check (process is alive).

**Response (200):**
```json
{
    "alive": true
}
```

---

## OpenAPI Specification

The full OpenAPI 3.0 specification is auto-generated by FastAPI and available at:

- `/docs` — Swagger UI
- `/redoc` — ReDoc UI
- `/openapi.json` — Raw JSON specification

## Client SDK Generation

The OpenAPI spec enables auto-generation of client SDKs:

```bash
# TypeScript/JavaScript
npx openapi-typescript-codegen -i http://localhost:8000/openapi.json -o frontend/src/lib/api

# Python
openapi-python-client generate --url http://localhost:8000/openapi.json
```