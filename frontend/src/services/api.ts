// ── API Client ──────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

type TokenStore = {
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  setTokens: (access: string, refresh: string) => void;
  clearTokens: () => void;
};

let tokenStore: TokenStore = {
  getAccessToken: () => null,
  getRefreshToken: () => null,
  setTokens: () => {},
  clearTokens: () => {},
};

export function setTokenStore(store: TokenStore) {
  tokenStore = store;
}

export class ApiError extends Error {
  status: number;
  code: string;
  details: Record<string, unknown>;

  constructor(status: number, message: string, code: string = 'UNKNOWN', details: Record<string, unknown> = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) return null;

  try {
    const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!res.ok) {
      tokenStore.clearTokens();
      return null;
    }

    const data = await res.json();
    tokenStore.setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  } catch {
    tokenStore.clearTokens();
    return null;
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  auth: boolean = true,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (auth) {
    const token = tokenStore.getAccessToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  let res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  // Token expired — try refresh once
  if (res.status === 401 && auth) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers['Authorization'] = `Bearer ${newToken}`;
      res = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
      });
    }
  }

  if (!res.ok) {
    let errorBody: { error?: { code?: string; message?: string; details?: Record<string, unknown> } } = {};
    try {
      errorBody = await res.json();
    } catch {
      // ignore parse errors
    }
    throw new ApiError(
      res.status,
      errorBody.error?.message || `Request failed with status ${res.status}`,
      errorBody.error?.code || 'UNKNOWN',
      errorBody.error?.details || {},
    );
  }

  if (res.status === 204) return {} as T;
  return res.json();
}

// ── Auth API ────────────────────────────────────────────────────────

import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  UserInfo,
  PatientCreate,
  PatientResponse,
  PatientUpdate,
  PaginatedResponse,
  PredictionDetail,
  PredictionRequest,
  PredictionResponse,
  DashboardSummary,
  WorkflowDetailResponse,
  WorkflowEventResponse,
  WorkflowStats,
  WorkflowTriggerRequest,
  WorkflowTriggerResponse,
  AuditLogResponse,
  ModelVersionResponse,
  HealthCheck,
  ReadinessCheck,
} from '@/types/api';

import { buildQueryString } from '@/lib/utils';

export const authApi = {
  login: (data: LoginRequest) =>
    request<LoginResponse>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(data),
    }, false),

  register: (data: RegisterRequest) =>
    request<{ user: UserInfo; message: string }>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    }, false),

  me: () =>
    request<UserInfo>('/api/v1/auth/me'),
};

// ── Patients API ────────────────────────────────────────────────────

export const patientsApi = {
  list: (params: Record<string, string | number | boolean | undefined | null> = {}) => {
    const qs = buildQueryString(params);
    return request<PaginatedResponse<PatientResponse>>(`/api/v1/patients${qs}`);
  },

  getById: (id: string) =>
    request<PatientResponse>(`/api/v1/patients/${id}`),

  create: (data: PatientCreate) =>
    request<PatientResponse>('/api/v1/patients', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: PatientUpdate) =>
    request<PatientResponse>(`/api/v1/patients/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),

  delete: (id: string) =>
    request<void>(`/api/v1/patients/${id}`, { method: 'DELETE' }),
};

// ── Predictions API ─────────────────────────────────────────────────

export const predictionsApi = {
  create: (data: PredictionRequest) =>
    request<PredictionDetail>('/api/v1/predict', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  list: (params: Record<string, string | number | boolean | undefined | null> = {}) => {
    const qs = buildQueryString(params);
    return request<PaginatedResponse<PredictionResponse>>(`/api/v1/predictions${qs}`);
  },

  getById: (id: string) =>
    request<PredictionDetail>(`/api/v1/predictions/${id}`),

  getDashboard: () =>
    request<DashboardSummary>('/api/v1/predictions/dashboard/summary'),
};

// ── Workflows API ───────────────────────────────────────────────────

export const workflowsApi = {
  list: (params: Record<string, string | number | boolean | undefined | null> = {}) => {
    const qs = buildQueryString(params);
    return request<PaginatedResponse<WorkflowEventResponse>>(`/api/v1/workflows${qs}`);
  },

  getById: (id: string) =>
    request<WorkflowDetailResponse>(`/api/v1/workflows/${id}`),

  trigger: (data: WorkflowTriggerRequest) =>
    request<WorkflowTriggerResponse>('/api/v1/workflows/trigger', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getStats: () =>
    request<WorkflowStats>('/api/v1/workflows/stats'),
};

// ── Audit API ───────────────────────────────────────────────────────

export const auditApi = {
  list: (params: Record<string, string | number | boolean | undefined | null> = {}) => {
    const qs = buildQueryString(params);
    return request<PaginatedResponse<AuditLogResponse>>(`/api/v1/audit${qs}`);
  },
};

// ── Models API ──────────────────────────────────────────────────────

export const modelsApi = {
  list: (params: Record<string, string | number | boolean | undefined | null> = {}) => {
    const qs = buildQueryString(params);
    return request<PaginatedResponse<ModelVersionResponse>>(`/api/v1/models${qs}`);
  },
};

// ── Health API ──────────────────────────────────────────────────────

export const healthApi = {
  check: () =>
    request<HealthCheck>('/health', {}, false),

  readiness: () =>
    request<ReadinessCheck>('/ready', {}, false),
};