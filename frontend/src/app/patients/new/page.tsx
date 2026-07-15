'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { patientsApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useEffect } from 'react';
import { ArrowLeft, Save } from 'lucide-react';
import type { PatientCreate } from '@/types/api';

export default function NewPatientPage() {
  const { isAuthenticated, isLoading: authLoading, hasPermission } = useAuth();
  const router = useRouter();
  const [error, setError] = useState('');

  useEffect(() => {
    if (!authLoading && (!isAuthenticated || !hasPermission(['admin', 'clinician']))) {
      router.push('/patients');
    }
  }, [isAuthenticated, authLoading, hasPermission, router]);

  const [form, setForm] = useState<PatientCreate>({
    mrn: '',
    first_name: '',
    last_name: '',
    date_of_birth: '',
    gender: '',
    primary_diagnosis: '',
    discharge_disposition: '',
    insurance_type: '',
    previous_admissions_6mo: 0,
    length_of_stay_days: 0,
    icu_days: 0,
    procedure_count: 0,
    medication_count: 0,
  });

  const mutation = useMutation({
    mutationFn: (data: PatientCreate) => patientsApi.create(data),
    onSuccess: (patient) => {
      router.push(`/patients/${patient.id}`);
    },
    onError: (err: any) => {
      setError(err.message || 'Failed to create patient');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    mutation.mutate(form);
  };

  const updateField = (field: keyof PatientCreate, value: string | number) => {
    setForm(prev => ({ ...prev, [field]: value }));
  };

  if (authLoading) return <div className="page-container"><div className="h-8 w-48 skeleton" /></div>;

  return (
    <div className="page-container max-w-2xl">
      <div className="page-header">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="btn btn-ghost btn-sm">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="page-title">Add Patient</h1>
            <p className="page-subtitle">Register a new patient record</p>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-lg bg-danger-50 border border-danger-200 text-sm text-danger-700">{error}</div>
      )}

      <form onSubmit={handleSubmit} className="card space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="label">MRN *</label>
            <input className="input" value={form.mrn} onChange={e => updateField('mrn', e.target.value)} required placeholder="MRN-XXXXX" />
          </div>
          <div>
            <label className="label">Date of Birth *</label>
            <input type="date" className="input" value={form.date_of_birth} onChange={e => updateField('date_of_birth', e.target.value)} required />
          </div>
          <div>
            <label className="label">First Name *</label>
            <input className="input" value={form.first_name} onChange={e => updateField('first_name', e.target.value)} required />
          </div>
          <div>
            <label className="label">Last Name *</label>
            <input className="input" value={form.last_name} onChange={e => updateField('last_name', e.target.value)} required />
          </div>
          <div>
            <label className="label">Gender</label>
            <select className="input" value={form.gender} onChange={e => updateField('gender', e.target.value)}>
              <option value="">Select...</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div>
            <label className="label">Insurance Type</label>
            <select className="input" value={form.insurance_type} onChange={e => updateField('insurance_type', e.target.value)}>
              <option value="">Select...</option>
              <option value="Medicare">Medicare</option>
              <option value="Medicaid">Medicaid</option>
              <option value="Private">Private</option>
              <option value="Uninsured">Uninsured</option>
            </select>
          </div>
        </div>

        <div>
          <label className="label">Primary Diagnosis</label>
          <input className="input" value={form.primary_diagnosis} onChange={e => updateField('primary_diagnosis', e.target.value)} placeholder="e.g., Congestive Heart Failure" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="label">Previous Admissions (6mo)</label>
            <input type="number" min="0" className="input" value={form.previous_admissions_6mo} onChange={e => updateField('previous_admissions_6mo', parseInt(e.target.value) || 0)} />
          </div>
          <div>
            <label className="label">Length of Stay (days)</label>
            <input type="number" min="0" className="input" value={form.length_of_stay_days} onChange={e => updateField('length_of_stay_days', parseInt(e.target.value) || 0)} />
          </div>
          <div>
            <label className="label">ICU Days</label>
            <input type="number" min="0" className="input" value={form.icu_days} onChange={e => updateField('icu_days', parseInt(e.target.value) || 0)} />
          </div>
        </div>

        <div className="flex justify-end gap-3">
          <button type="button" onClick={() => router.back()} className="btn btn-secondary">Cancel</button>
          <button type="submit" disabled={mutation.isPending} className="btn btn-primary">
            <Save className="w-4 h-4" />
            {mutation.isPending ? 'Saving...' : 'Save Patient'}
          </button>
        </div>
      </form>
    </div>
  );
}