'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { patientsApi, predictionsApi, workflowsApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useState } from 'react';
import { ArrowLeft, Edit3, User, Calendar, Activity, GitBranch, AlertTriangle } from 'lucide-react';
import { formatDate, getRiskColor, getRiskLabel } from '@/lib/utils';

export default function PatientDetailPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, hasPermission } = useAuth();
  const isEditing = searchParams.get('edit') === 'true';
  const patientId = params.id as string;

  const { data: patient, isLoading, error } = useQuery({
    queryKey: ['patient', patientId],
    queryFn: () => patientsApi.getById(patientId),
    enabled: isAuthenticated && !!patientId,
  });

  const { data: predictions } = useQuery({
    queryKey: ['patientPredictions', patientId],
    queryFn: () => predictionsApi.list({ patient_id: patientId, per_page: 5, sort_by: 'prediction_timestamp', sort_order: 'desc' }),
    enabled: isAuthenticated && !!patientId,
  });

  const { data: workflows } = useQuery({
    queryKey: ['patientWorkflows', patientId],
    queryFn: () => workflowsApi.list({ patient_id: patientId, per_page: 5 }),
    enabled: isAuthenticated && !!patientId && hasPermission(['admin', 'clinician']),
  });

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  if (authLoading || isLoading) {
    return (
      <div className="page-container">
        <div className="space-y-4">
          <div className="h-8 w-48 skeleton" />
          <div className="h-64 skeleton" />
          <div className="h-48 skeleton" />
        </div>
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="page-container">
        <div className="error-state">
          <AlertTriangle className="w-12 h-12 text-danger-400" />
          <h3 className="error-state-title">Patient not found</h3>
          <p className="error-state-description">The patient record could not be loaded.</p>
          <button onClick={() => router.push('/patients')} className="btn btn-primary">Back to Patients</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container max-w-4xl">
      <div className="page-header">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push('/patients')} className="btn btn-ghost btn-sm">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="page-title">{patient.last_name}, {patient.first_name}</h1>
            <p className="page-subtitle">MRN: {patient.mrn} • {patient.age} years • {patient.gender || 'N/A'}</p>
          </div>
        </div>
        {hasPermission(['admin', 'clinician']) && (
          <button onClick={() => router.push(`/predictions/new?patient_id=${patient.id}`)} className="btn btn-primary">
            <Activity className="w-4 h-4" />
            Run Prediction
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Patient Info */}
        <div className="card lg:col-span-2">
          <div className="card-header">
            <h3 className="card-title">Patient Information</h3>
          </div>
          <dl className="grid grid-cols-2 gap-4">
            <div><dt className="text-xs text-surface-500">Date of Birth</dt><dd className="text-sm font-medium text-surface-900">{formatDate(patient.date_of_birth)}</dd></div>
            <div><dt className="text-xs text-surface-500">Gender</dt><dd className="text-sm font-medium text-surface-900">{patient.gender || '—'}</dd></div>
            <div><dt className="text-xs text-surface-500">Primary Diagnosis</dt><dd className="text-sm font-medium text-surface-900">{patient.primary_diagnosis || '—'}</dd></div>
            <div><dt className="text-xs text-surface-500">Insurance</dt><dd className="text-sm font-medium text-surface-900">{patient.insurance_type || '—'}</dd></div>
            <div><dt className="text-xs text-surface-500">Discharge Disposition</dt><dd className="text-sm font-medium text-surface-900">{patient.discharge_disposition || '—'}</dd></div>
            <div><dt className="text-xs text-surface-500">Previous Admissions (6mo)</dt><dd className="text-sm font-medium text-surface-900">{patient.previous_admissions_6mo}</dd></div>
            <div><dt className="text-xs text-surface-500">Length of Stay</dt><dd className="text-sm font-medium text-surface-900">{patient.length_of_stay_days || '—'} days</dd></div>
            <div><dt className="text-xs text-surface-500">ICU Days</dt><dd className="text-sm font-medium text-surface-900">{patient.icu_days}</dd></div>
            <div><dt className="text-xs text-surface-500">Procedures</dt><dd className="text-sm font-medium text-surface-900">{patient.procedure_count}</dd></div>
            <div><dt className="text-xs text-surface-500">Medications</dt><dd className="text-sm font-medium text-surface-900">{patient.medication_count}</dd></div>
          </dl>
        </div>

        {/* Quick Stats */}
        <div className="space-y-4">
          <div className="card">
            <h3 className="card-title mb-4">Predictions</h3>
            {predictions && predictions.data.length > 0 ? (
              <div className="space-y-2">
                {predictions.data.slice(0, 3).map((p: any) => (
                  <div key={p.id} className="flex items-center justify-between p-2 rounded bg-surface-50 cursor-pointer" onClick={() => router.push(`/predictions/${p.id}`)}>
                    <span className="text-sm">{formatDate(p.prediction_timestamp)}</span>
                    <span className={`badge ${getRiskColor(p.risk_level)}`}>{getRiskLabel(p.risk_level)}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm text-surface-500">No predictions yet</div>
            )}
          </div>

          {hasPermission(['admin', 'clinician']) && workflows && (
            <div className="card">
              <h3 className="card-title mb-4">Workflows</h3>
              {workflows.data.length > 0 ? (
                <div className="space-y-2">
                  {workflows.data.slice(0, 3).map((w: any) => (
                    <div key={w.id} className="flex items-center justify-between p-2 rounded bg-surface-50">
                      <span className="text-sm">{w.workflow_type}</span>
                      <span className={`badge ${w.status === 'completed' ? 'badge-success' : w.status === 'failed' ? 'badge-danger' : 'badge-info'}`}>{w.status}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-surface-500">No workflows triggered</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}