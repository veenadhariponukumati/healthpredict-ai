'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { auditApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { ScrollText, AlertTriangle } from 'lucide-react';
import { formatDateTime } from '@/lib/utils';
import type { AuditLogResponse } from '@/types/api';
import { Pagination } from '@/components/shared/pagination';

export default function AuditPage() {
  const { isAuthenticated, isLoading: authLoading, hasPermission } = useAuth();
  const router = useRouter();
  const [page, setPage] = useState(1);
  const [actionFilter, setActionFilter] = useState('');

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['audit', page, actionFilter],
    queryFn: () => auditApi.list({ page, per_page: 30, action: actionFilter || undefined, sort_by: 'event_timestamp', sort_order: 'desc' }),
    enabled: isAuthenticated && hasPermission(['admin']),
  });

  if (authLoading || !isAuthenticated) {
    return <div className="page-container"><div className="h-8 w-48 skeleton mb-6" /><div className="h-96 skeleton" /></div>;
  }

  if (!hasPermission(['admin'])) {
    return <div className="page-container"><div className="error-state"><AlertTriangle className="w-12 h-12" /><h3 className="error-state-title">Access Denied</h3><p className="error-state-description">Only administrators can view audit logs.</p></div></div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Audit Logs</h1>
          <p className="page-subtitle">Security and compliance event log</p>
        </div>
      </div>

      <div className="flex gap-3 mb-6">
        <select className="input max-w-xs" value={actionFilter} onChange={e => { setActionFilter(e.target.value); setPage(1); }}>
          <option value="">All Actions</option>
          <option value="create">Create</option>
          <option value="read">Read</option>
          <option value="update">Update</option>
          <option value="delete">Delete</option>
          <option value="login">Login</option>
          <option value="prediction">Prediction</option>
          <option value="workflow">Workflow</option>
        </select>
      </div>

      {isLoading ? (
        <div className="space-y-3">{[...Array(15)].map((_, i) => <div key={i} className="h-10 skeleton" />)}</div>
      ) : data && data.data.length > 0 ? (
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Actor</th>
                <th>Role</th>
                <th>Resource</th>
                <th>Status</th>
                <th>IP</th>
              </tr>
            </thead>
            <tbody>
              {data.data.map((log: AuditLogResponse) => (
                <tr key={log.id}>
                  <td className="text-xs">{formatDateTime(log.event_timestamp)}</td>
                  <td><span className="badge badge-neutral">{log.action}</span></td>
                  <td className="text-sm font-mono">{log.actor_id.slice(0, 12)}...</td>
                  <td className="text-xs">{log.actor_role}</td>
                  <td className="text-xs">
                    <span className="text-surface-500">{log.resource_type}</span>
                    {log.resource_id && <span className="font-mono ml-1">#{log.resource_id.slice(0, 8)}</span>}
                  </td>
                  <td>{log.success ? <span className="badge badge-success">Success</span> : <span className="badge badge-danger">Failed</span>}</td>
                  <td className="font-mono text-xs">{log.ip_address || '—'}</td>
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
            <ScrollText className="w-12 h-12 text-surface-300" />
            <h3 className="empty-state-title">No audit logs</h3>
            <p className="empty-state-description">Audit events will appear here as users interact with the system.</p>
          </div>
        </div>
      )}
    </div>
  );
}