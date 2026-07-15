'use client';

import { useQuery } from '@tanstack/react-query';
import { modelsApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useRouter } from 'next/navigation';
import type { ModelVersionResponse } from "@/types/api";
import { useEffect } from 'react';
import { Cpu, AlertTriangle, TrendingUp, BarChart3, Shield } from 'lucide-react';
import { formatPercent } from '@/lib/utils';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function ModelsPage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  const { data, isLoading, error } = useQuery({
    queryKey: ['models'],
    queryFn: () => modelsApi.list({ per_page: 50 }),
    enabled: isAuthenticated,
  });

  if (authLoading || !isAuthenticated) {
    return <div className="page-container"><div className="h-8 w-48 skeleton mb-6" /><div className="h-96 skeleton" /></div>;
  }

  if (error) {
    return <div className="page-container"><div className="error-state"><AlertTriangle className="w-12 h-12" /><h3 className="error-state-title">Failed to load models</h3><button onClick={() => window.location.reload()} className="btn btn-primary">Retry</button></div></div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Model Registry</h1>
          <p className="page-subtitle">ML model versions and performance metrics</p>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">{[...Array(4)].map((_, i) => <div key={i} className="h-32 skeleton" />)}</div>
      ) : data && data.data.length > 0 ? (
        <div className="grid grid-cols-1 gap-6">
          {data.data.map((model: ModelVersionResponse) => {
            const metrics = [
              { name: 'F1 Score', value: model.f1_score },
              { name: 'ROC AUC', value: model.roc_auc },
              { name: 'Accuracy', value: model.accuracy },
              { name: 'Precision', value: model.precision },
              { name: 'Recall', value: model.recall },
            ].filter(m => m.value !== null) as { name: string; value: number }[];

            return (
              <div key={model.id} className="card">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="card-title">{model.model_name}</h3>
                      <span className="badge badge-info">{model.stage}</span>
                    </div>
                    <p className="card-description">Version {model.version} • {model.model_type}</p>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-surface-500">Model ID</div>
                    <div className="font-mono text-xs">{model.id.slice(0, 12)}...</div>
                  </div>
                </div>

                {metrics.length > 0 && (
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={metrics} margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                        <XAxis dataKey="name" fontSize={12} tick={{ fill: '#64748b' }} />
                        <YAxis domain={[0, 1]} fontSize={12} tick={{ fill: '#64748b' }} tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
                        <Tooltip formatter={(value: any) => formatPercent(value)} />
                        <Bar dataKey="value" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4 pt-4 border-t border-surface-100">
                  {metrics.map(m => (
                    <div key={m.name}>
                      <div className="text-xs text-surface-500">{m.name}</div>
                      <div className="text-sm font-semibold text-surface-900">{formatPercent(m.value)}</div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="card">
          <div className="empty-state">
            <Cpu className="w-12 h-12 text-surface-300" />
            <h3 className="empty-state-title">No models registered</h3>
            <p className="empty-state-description">Trained models will appear here once registered in the MLflow registry.</p>
          </div>
        </div>
      )}
    </div>
  );
}