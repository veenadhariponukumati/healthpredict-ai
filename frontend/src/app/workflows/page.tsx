'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { workflowsApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { GitBranch, AlertTriangle, CheckCircle2, XCircle, Clock, Activity } from 'lucide-react';
import { formatDateTime, getWorkflowStatusColor } from '@/lib/utils';
import { Pagination } from '@/components/shared/pagination';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function WorkflowsPage() {
  const { isAuthenticated, isLoading: authLoading, hasPermission } = useAuth();
  const router = useRouter();
  const [page, setPage] = useState(1);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['workflows', page],
    queryFn: () => workflowsApi.list({ page, per_page: 20, sort_by: 'triggered_at', sort_order: 'desc' }),
    enabled: isAuthenticated && hasPermission(['admin', 'clinician']),
  });

  const { data: stats } = useQuery({
    queryKey: ['workflowStats'],
    queryFn: () => workflowsApi.getStats(),
    enabled: isAuthenticated && hasPermission(['admin', 'clinician']),
  });

  if (authLoading || !isAuthenticated) {
    return <div className="page-container"><div className="h-8 w-48 skeleton mb-6" /><div className="h-96 skeleton" /></div>;
  }

  if (!hasPermission(['admin', 'clinician'])) {
    return <div className="page-container"><div className="error-state"><AlertTriangle className="w-12 h-12" /><h3 className="error-state-title">Access Denied</h3><p className="error-state-description">You do not have permission to view workflows.</p></div></div>;
  }

  const chartData = stats ? [
    { name: 'Running', value: stats.running, color: '#3b82f6' },
    { name: 'Completed', value: stats.completed, color: '#22c55e' },
    { name: 'Failed', value: stats.failed, color: '#ef4444' },
    { name: 'Pending', value: stats.pending, color: '#f59e0b' },
    { name: 'Retrying', value: stats.retrying, color: '#a855f7' },
    { name: 'Escalated', value: stats.escalated, color: '#64748b' },
  ] : [];

  const completionRate = stats && stats.total > 0
    ? ((stats.completed / stats.total) * 100).toFixed(1)
    : '0.0';

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Workflows</h1>
          <p className="page-subtitle">Care coordination workflow monitoring</p>
        </div>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          <div className="stat-card"><span className="stat-label">Total</span><span className="stat-value">{stats.total}</span></div>
          <div className="stat-card"><span className="stat-label">Running</span><span className="stat-value text-primary-600">{stats.running}</span></div>
          <div className="stat-card"><span className="stat-label">Completed</span><span className="stat-value text-success-600">{stats.completed}</span></div>
          <div className="stat-card"><span className="stat-label">Failed</span><span className="stat-value text-danger-600">{stats.failed}</span></div>
          <div className="stat-card"><span className="stat-label">Completion Rate</span><span className="stat-value">{completionRate}%</span></div>
        </div>
      )}

      {/* Chart */}
      {stats && stats.total > 0 && (
        <div className="card mb-6">
          <h3 className="card-title mb-4">Workflow Status Distribution</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="name" fontSize={12} tick={{ fill: '#64748b' }} />
                <YAxis fontSize={12} tick={{ fill: '#64748b' }} />
                <Tooltip />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, idx) => <Bar key={idx} dataKey="value" fill={entry.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">{[...Array(8)].map((_, i) => <div key={i} className="h-14 skeleton" />)}</div>
      ) : data && data.data.length > 0 ? (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Status</th>
                <th>Patient</th>
                <th>Retries</th>
                <th>Triggered</th>
                <th>Completed</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((w: any) => (
                <tr key={w.id} className="cursor-pointer" onClick={() => router.push(`/workflows/${w.id}`)}>
                  <td className="text-sm font-medium">{w.workflow_type}</td>
                  <td><span className={`badge ${getWorkflowStatusColor(w.status)}`}>{w.status}</span></td>
                  <td className="font-mono text-xs">{w.patient_id?.slice(0, 12) || '—'}...</td>
                  <td className="text-xs">{w.retry_count}</td>
                  <td className="text-xs">{w.triggered_at ? formatDateTime(w.triggered_at) : '—'}</td>
                  <td className="text-xs">{w.completed_at ? formatDateTime(w.completed_at) : '—'}</td>
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
            <GitBranch className="w-12 h-12 text-surface-300" />
            <h3 className="empty-state-title">No workflows yet</h3>
            <p className="empty-state-description">Workflows are triggered automatically when a high-risk prediction is made.</p>
          </div>
        </div>
      )}
    </div>
  );
}