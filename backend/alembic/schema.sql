-- Readmission Platform DDL v1.0 (extracted from Alembic migration 001)
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_login_at TIMESTAMPTZ,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_users_email ON users(email);
CREATE INDEX IF NOT EXISTS ix_users_role ON users(role);

CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mrn VARCHAR(50) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    gender VARCHAR(20),
    primary_diagnosis VARCHAR(255),
    discharge_disposition VARCHAR(100),
    insurance_type VARCHAR(50),
    age INTEGER,
    previous_admissions_6mo INTEGER DEFAULT 0,
    length_of_stay_days INTEGER,
    icu_days INTEGER DEFAULT 0,
    procedure_count INTEGER DEFAULT 0,
    medication_count INTEGER DEFAULT 0,
    comorbidity_score FLOAT DEFAULT 0.0,
    lab_results JSONB,
    vital_signs JSONB,
    social_determinants JSONB,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_patients_mrn ON patients(mrn);
CREATE INDEX IF NOT EXISTS ix_patients_diagnosis ON patients(primary_diagnosis);
CREATE INDEX IF NOT EXISTS ix_patients_name ON patients(last_name, first_name);

CREATE TABLE IF NOT EXISTS model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mlflow_experiment_id INTEGER,
    mlflow_run_id VARCHAR(50),
    model_name VARCHAR(100) NOT NULL,
    model_type VARCHAR(30) NOT NULL,
    version VARCHAR(20) NOT NULL,
    stage VARCHAR(20) NOT NULL DEFAULT 'None',
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    roc_auc FLOAT,
    pr_auc FLOAT,
    brier_score FLOAT,
    inference_latency_ms FLOAT,
    model_description TEXT,
    hyperparameters_json JSONB,
    feature_importance JSONB,
    artifact_uri VARCHAR(500),
    pipeline_version VARCHAR(20),
    training_duration_seconds INTEGER,
    n_features INTEGER,
    n_samples INTEGER,
    dataset_hash VARCHAR(64),
    trained_at TIMESTAMPTZ,
    promoted_at TIMESTAMPTZ,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_model_versions_name ON model_versions(model_name);
CREATE INDEX IF NOT EXISTS ix_model_versions_stage ON model_versions(stage);
CREATE UNIQUE INDEX IF NOT EXISTS uq_model_versions_name_version ON model_versions(model_name, version);

CREATE TABLE IF NOT EXISTS predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE CASCADE NOT NULL,
    model_version_id UUID REFERENCES model_versions(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    risk_score FLOAT NOT NULL,
    risk_level VARCHAR(10) NOT NULL,
    confidence FLOAT NOT NULL DEFAULT 0.0,
    threshold FLOAT NOT NULL,
    features JSONB NOT NULL,
    shap_values JSONB,
    base_value FLOAT,
    llm_explanation JSONB,
    llm_explanation_version VARCHAR(20),
    inference_latency_ms INTEGER,
    feature_version INTEGER NOT NULL DEFAULT 1,
    request_id UUID,
    prediction_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_predictions_patient ON predictions(patient_id);
CREATE INDEX IF NOT EXISTS ix_predictions_risk_level ON predictions(risk_level);
CREATE INDEX IF NOT EXISTS ix_predictions_timestamp ON predictions(prediction_timestamp);
CREATE INDEX IF NOT EXISTS ix_predictions_risk_partial ON predictions(risk_level, prediction_timestamp) WHERE risk_level IN ('HIGH', 'CRITICAL');

CREATE TABLE IF NOT EXISTS workflow_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    prediction_id UUID REFERENCES predictions(id) ON DELETE SET NULL,
    workflow_type VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    temporal_workflow_id VARCHAR(100),
    n8n_execution_id VARCHAR(100),
    input_payload JSONB,
    output_result JSONB,
    error_details JSONB,
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    next_retry_at TIMESTAMPTZ,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_workflow_events_patient ON workflow_events(patient_id);
CREATE INDEX IF NOT EXISTS ix_workflow_events_type ON workflow_events(workflow_type);
CREATE INDEX IF NOT EXISTS ix_workflow_events_status ON workflow_events(status);
CREATE INDEX IF NOT EXISTS ix_workflow_events_pending ON workflow_events(status, triggered_at) WHERE status IN ('PENDING', 'RUNNING', 'RETRYING');

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id VARCHAR(100) NOT NULL,
    actor_role VARCHAR(20) NOT NULL,
    action VARCHAR(20) NOT NULL,
    resource_type VARCHAR(20) NOT NULL,
    resource_id VARCHAR(100),
    request_id UUID,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    success BOOLEAN NOT NULL DEFAULT true,
    detail JSONB,
    event_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_audit_logs_actor ON audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs(action);
CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_type ON audit_logs(resource_type);
CREATE INDEX IF NOT EXISTS ix_audit_logs_timestamp ON audit_logs(event_timestamp);

CREATE TABLE IF NOT EXISTS uploaded_datasets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    version VARCHAR(20) NOT NULL,
    description VARCHAR(500),
    source VARCHAR(100),
    file_path VARCHAR(500),
    file_size_bytes BIGINT,
    row_count INTEGER,
    column_count INTEGER,
    feature_count INTEGER,
    target_column VARCHAR(100),
    dataset_hash VARCHAR(64),
    metadata_json JSONB,
    upload_status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    positive_class_ratio FLOAT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_datasets_name ON uploaded_datasets(name);
CREATE INDEX IF NOT EXISTS ix_datasets_hash ON uploaded_datasets(dataset_hash);