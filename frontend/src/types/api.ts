// ── API Response Types ──────────────────────────────────────────────

export interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: PaginationMeta;
}

export interface ErrorResponse {
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    request_id: string;
    timestamp: string;
  };
}

// ── Auth Types ──────────────────────────────────────────────────────

export interface UserInfo {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export type UserRole = 'admin' | 'clinician' | 'viewer' | 'coordinator';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserInfo;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  role: string;
}

export interface AuthState {
  user: UserInfo | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// ── Patient Types ───────────────────────────────────────────────────

export interface PatientResponse {
  id: string;
  mrn: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  age: number | null;
  gender: string | null;
  primary_diagnosis: string | null;
  discharge_disposition: string | null;
  insurance_type: string | null;
  previous_admissions_6mo: number;
  length_of_stay_days: number | null;
  icu_days: number;
  procedure_count: number;
  medication_count: number;
}

export interface PatientCreate {
  mrn: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  gender?: string;
  primary_diagnosis?: string;
  discharge_disposition?: string;
  insurance_type?: string;
  previous_admissions_6mo?: number;
  length_of_stay_days?: number;
  icu_days?: number;
  procedure_count?: number;
  medication_count?: number;
}

export interface PatientUpdate {
  first_name?: string;
  last_name?: string;
  gender?: string;
  primary_diagnosis?: string;
  discharge_disposition?: string;
  insurance_type?: string;
  previous_admissions_6mo?: number;
  length_of_stay_days?: number;
  icu_days?: number;
  procedure_count?: number;
  medication_count?: number;
}

// ── Prediction Types ────────────────────────────────────────────────

export interface PredictionRequest {
  patient_id: string;
  generate_explanation: boolean;
  trigger_workflow: boolean;
  features: Record<string, number>;
}

export interface PredictionResponse {
  id: string;
  patient_id: string;
  risk_score: number;
  risk_level: string;
  confidence: number;
  threshold: number;
  model_version: string | null;
  prediction_timestamp: string;
  inference_latency_ms: number | null;
}

export interface PredictionDetail extends PredictionResponse {
  features: Record<string, number> | null;
  shap_values: Record<string, number> | null;
  llm_explanation: Record<string, unknown> | null;
}

// ── Workflow Types ──────────────────────────────────────────────────

export interface WorkflowEventResponse {
  id: string;
  patient_id: string | null;
  prediction_id: string | null;
  workflow_type: string;
  status: string;
  retry_count: number;
  triggered_at: string | null;
  completed_at: string | null;
  error_details: Record<string, unknown> | null;
}

export interface WorkflowDetailResponse extends WorkflowEventResponse {
  input_payload: Record<string, unknown> | null;
  output_result: Record<string, unknown> | null;
  temporal_workflow_id: string | null;
  n8n_execution_id: string | null;
}

export interface WorkflowTriggerRequest {
  patient_id: string;
  risk_score: number;
  risk_level: string;
}

export interface WorkflowTriggerResponse {
  workflow_id: string;
  correlation_id: string;
  status: string;
  message: string;
}

export interface WorkflowStats {
  total: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
  retrying: number;
  escalated: number;
}

// ── Audit Types ─────────────────────────────────────────────────────

export interface AuditLogResponse {
  id: string;
  actor_id: string;
  actor_role: string;
  action: string;
  resource_type: string;
  resource_id: string | null;
  request_id: string | null;
  ip_address: string | null;
  success: boolean;
  detail: Record<string, unknown> | null;
  event_timestamp: string;
}

// ── Model Registry Types ────────────────────────────────────────────

export interface ModelVersionResponse {
  id: string;
  model_name: string;
  model_type: string;
  version: string;
  stage: string;
  f1_score: number | null;
  roc_auc: number | null;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
}

// ── Health Types ────────────────────────────────────────────────────

export interface HealthCheck {
  status: string;
  version: string;
  uptime_seconds: number;
}

export interface ReadinessCheck {
  ready: boolean;
  dependencies: Record<string, { status: string; latency_ms?: number; error?: string }>;
}

// ── Dashboard Types ─────────────────────────────────────────────────

export interface DashboardSummary {
  total_predictions: number;
  high_risk: number;
  critical: number;
  moderate: number;
  mean_risk_score: number;
  current_model: string | null;
  current_model_version: string | null;
}

// ── Common Types ────────────────────────────────────────────────────

export interface SelectOption {
  value: string;
  label: string;
}

export interface FilterState {
  page: number;
  per_page: number;
  search?: string;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  [key: string]: unknown;
}