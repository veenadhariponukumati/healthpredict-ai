"""Patient, Prediction, Model, Workflow, Audit, and Dataset schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    mrn: str = Field(..., pattern=r"^MRN-\d{6}$")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    gender: str | None = None
    primary_diagnosis: str | None = None
    discharge_disposition: str | None = None
    insurance_type: str | None = None
    previous_admissions_6mo: int = Field(default=0, ge=0)
    length_of_stay_days: int | None = None
    icu_days: int = Field(default=0, ge=0)
    procedure_count: int = Field(default=0, ge=0)
    medication_count: int = Field(default=0, ge=0)
    comorbidity_score: float = Field(default=0.0, ge=0.0, le=40.0)
    lab_results: dict[str, Any] | None = None
    vital_signs: dict[str, Any] | None = None
    social_determinants: dict[str, Any] | None = None


class PatientUpdate(BaseModel):
    first_name: str | None = Field(None, min_length=1, max_length=100)
    last_name: str | None = Field(None, min_length=1, max_length=100)
    primary_diagnosis: str | None = None
    discharge_disposition: str | None = None
    insurance_type: str | None = None
    previous_admissions_6mo: int | None = Field(None, ge=0)
    length_of_stay_days: int | None = None
    icu_days: int | None = Field(None, ge=0)
    procedure_count: int | None = Field(None, ge=0)
    medication_count: int | None = Field(None, ge=0)
    comorbidity_score: float | None = Field(None, ge=0.0, le=40.0)
    lab_results: dict[str, Any] | None = None
    vital_signs: dict[str, Any] | None = None


class PatientResponse(BaseModel):
    id: str
    mrn: str
    first_name: str
    last_name: str
    date_of_birth: date
    age: int | None = None
    gender: str | None = None
    primary_diagnosis: str | None = None
    discharge_disposition: str | None = None
    insurance_type: str | None = None
    previous_admissions_6mo: int = 0
    length_of_stay_days: int | None = None
    icu_days: int = 0
    procedure_count: int = 0
    medication_count: int = 0
    comorbidity_score: float = 0.0
    lab_results: dict[str, Any] | None = None
    vital_signs: dict[str, Any] | None = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PredictionRequest(BaseModel):
    patient_id: str
    generate_explanation: bool = True
    trigger_workflow: bool = True
    features: dict[str, float]


class BatchPredictionRequest(BaseModel):
    patients: list[dict[str, Any]]
    generate_explanation: bool = False
    trigger_workflow: bool = False


class PredictionResponse(BaseModel):
    id: str
    patient_id: str
    risk_score: float
    risk_level: str
    confidence: float
    threshold: float
    model_version: str | None = None
    prediction_timestamp: datetime
    inference_latency_ms: int | None = None

    model_config = {"from_attributes": True}


class PredictionDetailResponse(PredictionResponse):
    features: dict[str, Any] | None = None
    shap_values: dict[str, Any] | None = None
    llm_explanation: dict[str, Any] | None = None


class ModelVersionResponse(BaseModel):
    id: str
    model_name: str
    model_type: str
    version: str
    stage: str
    f1_score: float | None = None
    roc_auc: float | None = None
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    trained_at: datetime | None = None
    promoted_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ModelPromoteRequest(BaseModel):
    model_version_id: str
    reason: str = ""


class WorkflowEventResponse(BaseModel):
    id: str
    patient_id: str | None = None
    prediction_id: str | None = None
    workflow_type: str
    status: str
    retry_count: int = 0
    triggered_at: datetime | None = None
    completed_at: datetime | None = None
    error_details: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class WorkflowDetailResponse(WorkflowEventResponse):
    input_payload: dict[str, Any] | None = None
    output_result: dict[str, Any] | None = None
    temporal_workflow_id: str | None = None
    n8n_execution_id: str | None = None


class AuditLogResponse(BaseModel):
    id: str
    actor_id: str
    actor_role: str
    action: str
    resource_type: str
    resource_id: str | None = None
    request_id: str | None = None
    ip_address: str | None = None
    success: bool = True
    detail: dict[str, Any] | None = None
    event_timestamp: datetime

    model_config = {"from_attributes": True}


class DatasetResponse(BaseModel):
    id: str
    name: str
    version: str
    description: str | None = None
    source: str | None = None
    row_count: int | None = None
    feature_count: int | None = None
    dataset_hash: str | None = None
    upload_status: str
    is_active: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardSummary(BaseModel):
    total_patients: int
    total_predictions: int
    high_risk_count: int
    moderate_risk_count: int
    low_risk_count: int
    active_workflows: int
    completed_workflows: int
    failed_workflows: int
    workflow_completion_rate: float
    current_model: str | None = None
    current_model_version: str | None = None