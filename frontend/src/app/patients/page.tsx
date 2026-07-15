'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { patientsApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Users, Plus, Search, AlertTriangle, Trash2, Edit3 } from 'lucide-react';
import { formatDate, getInitials, truncate } from '@/lib/utils';
import { Pagination } from '@/components/shared/pagination';
import type { PatientResponse } from '@/types/api';

export default function PatientsPage() {
  const { isAuthenticated, isLoading: authLoading, hasPermission } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [searchInput, setSearchInput] = useState('');
  const [deleteId, setDeleteId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['patients', page, search],
    queryFn: () => patientsApi.list({ page, per_page: 15, search: search || undefined, sort_by: 'last_name', sort_order: 'asc' }),
    enabled: isAuthenticated,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => patientsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
      setDeleteId(null);
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearch(searchInput);
    setPage(1);
  };

  const canEdit = hasPermission(['admin', 'clinician']);

  if (authLoading || !isAuthenticated) {
    return (
      <div className="page-container">
        <div className="h-8 w-48 skeleton mb-6" />
        <div className="h-96 skeleton" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="error-state">
          <AlertTriangle className="w-12 h-12 text-danger-400" />
          <h3 className="error-state-title">Failed to load patients</h3>
          <p className="error-state-description">Could not connect to the backend API.</p>
          <button onClick={() => window.location.reload()} className="btn btn-primary">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Patients</h1>
          <p className="page-subtitle">Manage patient records and view readmission risk</p>
        </div>
        {canEdit && (
          <button onClick={() => router.push('/patients/new')} className="btn btn-primary">
            <Plus className="w-4 h-4" />
            Add Patient
          </button>
        )}
      </div>

      {/* Search */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-surface-400" />
          <input
            type="text"
            value={searchInput}
            onChange={e => setSearchInput(e.target.value)}
            placeholder="Search by name, MRN, or diagnosis..."
            className="input pl-10"
          />
        </div>
      </form>

      {/* Table */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(8)].map((_, i) => <div key={i} className="h-14 skeleton" />)}
        </div>
      ) : data && data.data.length > 0 ? (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Patient</th>
                <th>MRN</th>
                <th>Age</th>
                <th>Gender</th>
                <th>Diagnosis</th>
                <th>Admissions</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((patient: PatientResponse) => (
                <tr
                  key={patient.id}
                  className="cursor-pointer"
                  onClick={() => router.push(`/patients/${patient.id}`)}
                >
                  <td>
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-full bg-primary-100 flex items-center justify-center text-sm font-medium text-primary-700">
                        {getInitials(patient.first_name, patient.last_name)}
                      </div>
                      <div>
                        <div className="font-medium text-surface-900">
                          {patient.last_name}, {patient.first_name}
                        </div>
                        <div className="text-xs text-surface-500">{patient.mrn}</div>
                      </div>
                    </div>
                  </td>
                  <td className="font-mono text-xs">{patient.mrn}</td>
                  <td>{patient.age ?? '—'}</td>
                  <td>{patient.gender || '—'}</td>
                  <td className="max-w-[200px] truncate">{truncate(patient.primary_diagnosis || '—', 40)}</td>
                  <td>{patient.previous_admissions_6mo}</td>
                  <td>
                    <div className="flex items-center gap-2" onClick={e => e.stopPropagation()}>
                      {canEdit && (
                        <button
                          onClick={() => router.push(`/patients/${patient.id}?edit=true`)}
                          className="btn btn-ghost btn-sm"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                      )}
                      {hasPermission(['admin']) && (
                        <button
                          onClick={() => setDeleteId(patient.id)}
                          className="btn btn-ghost btn-sm text-danger-500 hover:text-danger-700"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-3 border-t border-surface-100">
            <Pagination
              page={data.pagination.page}
              totalPages={data.pagination.total_pages}
              total={data.pagination.total}
              perPage={data.pagination.per_page}
              onPageChange={setPage}
            />
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="empty-state">
            <Users className="w-12 h-12 text-surface-300" />
            <h3 className="empty-state-title">No patients found</h3>
            <p className="empty-state-description">
              {search ? 'No patients match your search criteria.' : 'Get started by adding your first patient.'}
            </p>
            {canEdit && !search && (
              <button onClick={() => router.push('/patients/new')} className="btn btn-primary">
                <Plus className="w-4 h-4" />
                Add Patient
              </button>
            )}
          </div>
        </div>
      )}

      {/* Delete confirmation */}
      {deleteId && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="card max-w-md w-full">
            <h3 className="text-lg font-semibold text-surface-900 mb-2">Delete Patient</h3>
            <p className="text-sm text-surface-500 mb-6">Are you sure you want to delete this patient? This action cannot be undone.</p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setDeleteId(null)} className="btn btn-secondary">Cancel</button>
              <button
                onClick={() => deleteMutation.mutate(deleteId)}
                disabled={deleteMutation.isPending}
                className="btn btn-danger"
              >
                {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}