'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { predictionsApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { Activity, Plus, AlertTriangle } from 'lucide-react';
import { formatDateTime, getRiskColor, getRiskLabel, formatPercent } from '@/lib/utils';
import { Pagination } from '@/components/shared/pagination';

export default function PredictionsPage() {
  const { isAuthenticated, isLoading: authLoading, hasPermission } = useAuth();
  const router = useRouter();
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['predictions', page],
    queryFn: () => predictionsApi.list({ page, per_page: 20, sort_by: 'prediction_timestamp', sort_order: 'desc' }),
    enabled: isAuthenticated,
  });

  if (authLoading || !isAuthenticated) {
    return <div className="page-container"><div className="h-8 w-48 skeleton mb-6" /><div className="h-96 skeleton" /></div>;
  }

  if (error) {
    return <div className="page-container"><div className="error-state"><AlertTriangle className="w-12 h-12 text-danger-400" /><h3 className="error-state-title">Failed to load predictions</h3><button onClick={() => window.location.reload()} className="btn btn-primary">Retry</button></div></div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Predictions</h1>
          <p className="page-subtitle">Readmission risk assessment history</p>
        </div>
        {hasPermission(['admin', 'clinician']) && (
          <button onClick={() => router.push('/predictions/new')} className="btn btn-primary">
            <Plus className="w-4 h-4" /> New Prediction
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="space-y-3">{[...Array(10)].map((_, i) => <div key={i} className="h-14 skeleton" />)}</div>
      ) : data && data.data.length > 0 ? (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Patient ID</th>
                <th>Risk Score</th>
                <th>Risk Level</th>
                <th>Confidence</th>
                <th>Model</th>
                <th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((p: any) => (
                <tr key={p.id} className="cursor-pointer" onClick={() => router.push(`/predictions/${p.id}`)}>
                  <td className="text-sm">{formatDateTime(p.prediction_timestamp)}</td>
                  <td className="font-mono text-xs">{p.patient_id.slice(0, 12)}...</td>
                  <td className="font-mono">{(p.risk_score * 100).toFixed(1)}%</td>
                  <td><span className={`badge ${getRiskColor(p.risk_level)}`}>{getRiskLabel(p.risk_level)}</span></td>
                  <td>{formatPercent(p.confidence)}</td>
                  <td className="text-xs font-mono">{p.model_version || '—'}</td>
                  <td className="text-xs">{p.inference_latency_ms ? `${p.inference_latency_ms}ms` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-4 py-3 border-t border-surface-100">
            <Pagination page={data.pagination.page} totalPages={data.pagination.total_pages} total={data.pagination.total} perPage={data.pagination.per_page} onPageChange={setPage} />
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="empty-state">
            <Activity className="w-12 h-12 text-surface-300" />
            <h3 className="empty-state-title">No predictions yet</h3>
            <p className="empty-state-description">Run a prediction on a patient record to see results here.</p>
            {hasPermission(['admin', 'clinician']) && (
              <button onClick={() => router.push('/predictions/new')} className="btn btn-primary">
                <Plus className="w-4 h-4" /> New Prediction
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}