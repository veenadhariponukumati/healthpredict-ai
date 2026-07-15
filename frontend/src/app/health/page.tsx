'use client';

import { useQuery } from '@tanstack/react-query';
import { healthApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { HeartPulse, AlertTriangle, CheckCircle2, XCircle, Activity } from 'lucide-react';

export default function HealthPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  const { data: health, isLoading: healthLoading, error: healthError, refetch } = useQuery({
    queryKey: ['health-check'],
    queryFn: () => healthApi.check(),
    enabled: isAuthenticated,
  });

  const { data: readiness, isLoading: readyLoading, error: readyError } = useQuery({
    queryKey: ['readiness'],
    queryFn: () => healthApi.readiness(),
    enabled: isAuthenticated,
  });

  if (authLoading || !isAuthenticated) {
    return <div className="page-container"><div className="h-8 w-48 skeleton" /><div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">{[...Array(4)].map((_, i) => <div key={i} className="h-24 skeleton" />)}</div></div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">System Health</h1>
          <p className="page-subtitle">Platform service status and dependencies</p>
        </div>
        <button onClick={() => refetch()} className="btn btn-secondary">
          <Activity className="w-4 h-4" /> Refresh
        </button>
      </div>

      {/* API Health */}
      <div className="card mb-6">
        <div className="card-header">
          <h3 className="card-title">API Service</h3>
        </div>
        {healthLoading ? (
          <div className="h-16 skeleton" />
        ) : healthError || !health ? (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-danger-50">
            <XCircle className="w-5 h-5 text-danger-600" />
            <span className="text-sm text-danger-700">Unable to reach API</span>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-success-50">
              <CheckCircle2 className="w-5 h-5 text-success-600" />
              <div className="flex-1">
                <div className="text-sm font-medium text-surface-900">API is healthy</div>
                <div className="text-xs text-surface-500">Version: {health.version} • Uptime: {Math.floor(health.uptime_seconds / 60)}m</div>
              </div>
              <span className="badge badge-success">{health.status}</span>
            </div>
          </div>
        )}
      </div>

      {/* Dependencies */}
      <div className="card">
        <div className="card-header">
          <h3 className="card-title">Service Dependencies</h3>
        </div>
        {readyLoading ? (
          <div className="space-y-3">{[...Array(3)].map((_, i) => <div key={i} className="h-16 skeleton" />)}</div>
        ) : readyError || !readiness ? (
          <div className="flex items-center gap-3 p-4 rounded-lg bg-danger-50">
            <XCircle className="w-5 h-5 text-danger-600" />
            <span className="text-sm text-danger-700">Unable to check dependencies</span>
          </div>
        ) : (
          <div className="space-y-3">
            {Object.entries(readiness.dependencies).map(([name, dep]: [string, any]) => (
              <div key={name} className="flex items-center justify-between p-3 rounded-lg bg-surface-50">
                <div className="flex items-center gap-3">
                  {dep.status === 'up' ? (
                    <CheckCircle2 className="w-5 h-5 text-success-600" />
                  ) : (
                    <XCircle className="w-5 h-5 text-danger-600" />
                  )}
                  <div>
                    <div className="text-sm font-medium text-surface-900 capitalize">{name}</div>
                    {dep.latency_ms && <div className="text-xs text-surface-500">{dep.latency_ms}ms latency</div>}
                    {dep.error && <div className="text-xs text-danger-600">{dep.error}</div>}
                  </div>
                </div>
                <span className={`badge ${dep.status === 'up' ? 'badge-success' : 'badge-danger'}`}>
                  {dep.status === 'up' ? 'Online' : 'Offline'}
                </span>
              </div>
            ))}
            {Object.keys(readiness.dependencies).length === 0 && (
              <p className="text-sm text-surface-500">No dependencies reported</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}