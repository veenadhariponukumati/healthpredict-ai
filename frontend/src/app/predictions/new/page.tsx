'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { predictionsApi, patientsApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useEffect } from 'react';
import { ArrowLeft, Activity, AlertTriangle } from 'lucide-react';

// Canonical feature order matching the production model (RandomForest, 12 features)
const MODEL_FEATURES = [
  { key: 'age', label: 'Age', type: 'number', min: 18, max: 120, step: 1 },
  { key: 'had_cvd', label: 'History of CVD', type: 'binary' },
  { key: 'had_diabetes', label: 'History of Diabetes', type: 'binary' },
  { key: 'had_hypertension', label: 'History of Hypertension', type: 'binary' },
  { key: 'num_previous_admissions', label: 'Prior Admissions', type: 'number', min: 0, max: 50, step: 1 },
  { key: 'length_of_stay_days', label: 'Length of Stay (days)', type: 'number', min: 0, max: 365, step: 1 },
  { key: 'num_procedures', label: 'Procedure Count', type: 'number', min: 0, max: 50, step: 1 },
  { key: 'num_medications', label: 'Medication Count', type: 'number', min: 0, max: 100, step: 1 },
  { key: 'has_insurance', label: 'Has Insurance', type: 'binary' },
  { key: 'gender_M', label: 'Gender: Male', type: 'binary' },
  { key: 'income_level_low', label: 'Income Level: Low', type: 'binary' },
  { key: 'income_level_medium', label: 'Income Level: Medium', type: 'binary' },
];

export default function NewPredictionPage() {
  const { isAuthenticated, isLoading: authLoading, hasPermission } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedPatient = searchParams.get('patient_id') || '';
  const [patientId, setPatientId] = useState(preselectedPatient);
  const [features, setFeatures] = useState<Record<string, string>>({});
  const [error, setError] = useState('');

  useEffect(() => {
    if (!authLoading && (!isAuthenticated || !hasPermission(['admin', 'clinician']))) router.push('/predictions');
  }, [isAuthenticated, authLoading, hasPermission, router]);

  const { data: patients } = useQuery({
    queryKey: ['patients-select'],
    queryFn: () => patientsApi.list({ per_page: 100, sort_by: 'last_name', sort_order: 'asc' }),
    enabled: isAuthenticated,
  });

  const handlePatientChange = (id: string) => {
    setPatientId(id);
    const p = patients?.data?.find((x: { id: string }) => x.id === id);
    if (p) {
      setFeatures({
        age: String(p.age ?? 45),
        had_cvd: '0',
        had_diabetes: '0',
        had_hypertension: '0',
        num_previous_admissions: String(p.previous_admissions_6mo ?? 0),
        length_of_stay_days: String(p.length_of_stay_days ?? 3),
        num_procedures: String(p.procedure_count ?? 0),
        num_medications: String(p.medication_count ?? 0),
        has_insurance: p.insurance_type ? '1' : '0',
        gender_M: p.gender === 'Male' || p.gender === 'M' ? '1' : '0',
        income_level_low: '0',
        income_level_medium: '1',
      });
    }
  };

  // Initialize features if preselected
  useEffect(() => {
    if (preselectedPatient && patients?.data) {
      handlePatientChange(preselectedPatient);
    }
  }, [preselectedPatient, patients?.data]);

  const setFeature = (key: string, value: string) => {
    setFeatures(prev => ({ ...prev, [key]: value }));
  };

  // Build features in the exact model order (deterministic)
  const buildFeaturesPayload = (): Record<string, number> => {
    const payload: Record<string, number> = {};
    for (const { key } of MODEL_FEATURES) {
      const raw = features[key];
      if (key === 'age' || key === 'num_previous_admissions' || key === 'length_of_stay_days' ||
          key === 'num_procedures' || key === 'num_medications') {
        const val = parseFloat(raw);
        payload[key] = isNaN(val) ? 0 : val;
      } else {
        // binary features: accept 0/1 or empty/checked
        payload[key] = (raw === '1' || raw === 'true') ? 1 : 0;
      }
    }
    return payload;
  };

  const mutation = useMutation({
    mutationFn: () => predictionsApi.create({
      patient_id: patientId,
      generate_explanation: true,
      trigger_workflow: true,
      features: buildFeaturesPayload(),
    }),
    onSuccess: (result) => router.push(`/predictions/${result.id}`),
    onError: (err: any) => setError(err.message || 'Prediction failed'),
  });

  if (authLoading) return <div className="page-container"><div className="h-8 w-48 skeleton" /></div>;

  return (
    <div className="page-container max-w-2xl">
      <div className="page-header">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="btn btn-ghost btn-sm"><ArrowLeft className="w-4 h-4" /></button>
          <div>
            <h1 className="page-title">Run Prediction</h1>
            <p className="page-subtitle">Assess readmission risk for a patient</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-danger-50 border border-danger-200 text-sm text-danger-700">
          {error}
        </div>
      )}

      <div className="card space-y-6">
        <div>
          <label htmlFor="patient-select" className="label">Select Patient</label>
          <select
            id="patient-select"
            className="input"
            value={patientId}
            onChange={e => handlePatientChange(e.target.value)}
          >
            <option value="">Choose a patient...</option>
            {patients?.data?.map((p: { id: string; last_name: string; first_name: string; mrn: string }) => (
              <option key={p.id} value={p.id}>{p.last_name}, {p.first_name} ({p.mrn})</option>
            ))}
          </select>
        </div>

        {patientId && (
          <div>
            <label className="label mb-2">Clinical Features</label>
            <div className="grid grid-cols-2 gap-3">
              {MODEL_FEATURES.map(({ key, label, type }) => (
                type === 'binary' ? (
                  <div key={key} className="flex items-center gap-2">
                    <input
                      id={`feat-${key}`}
                      type="checkbox"
                      className="w-4 h-4 rounded border-surface-300 text-primary-600 focus:ring-primary-500"
                      checked={features[key] === '1'}
                      onChange={e => setFeature(key, e.target.checked ? '1' : '0')}
                    />
                    <label htmlFor={`feat-${key}`} className="text-xs text-surface-500">{label}</label>
                  </div>
                ) : (
                  <div key={key}>
                    <label htmlFor={`feat-${key}`} className="text-xs text-surface-500 mb-1 block">{label}</label>
                    <input
                      id={`feat-${key}`}
                      type="number"
                      min="0"
                      step={key === 'age' ? '1' : '1'}
                      className="input text-sm"
                      value={features[key] ?? ''}
                      onChange={e => setFeature(key, e.target.value)}
                    />
                  </div>
                )
              ))}
            </div>
          </div>
        )}

        <div className="bg-surface-50 rounded-lg p-4 text-sm text-surface-600">
          <p className="font-medium mb-1">About this prediction</p>
          <p>The model will assess readmission risk based on the patient's clinical data. Results include risk score, confidence level, and SHAP-based feature explanations. A high-risk prediction will automatically trigger care coordination workflows.</p>
        </div>

        <div className="flex justify-end gap-3">
          <button onClick={() => router.back()} className="btn btn-secondary">Cancel</button>
          <button onClick={() => mutation.mutate()} disabled={!patientId || mutation.isPending} className="btn btn-primary">
            <Activity className="w-4 h-4" />
            {mutation.isPending ? 'Running...' : 'Run Prediction'}
          </button>
        </div>
      </div>
    </div>
  );
}