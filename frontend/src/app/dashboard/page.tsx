'use client';

import { useQuery } from '@tanstack/react-query';
import { predictionsApi, healthApi, patientsApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  TrendingUp,
  Shield,
} from 'lucide-react';
import { formatNumber, getRiskColor, getRiskLabel } from '@/lib/utils';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts';

const COLORS = {
  high: '#ef4444',
  critical: '#dc2626',
  moderate: '#f59e0b',
};

export default function DashboardPage() {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  const { data: dashboard, isLoading: dashLoading, error: dashError } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => predictionsApi.getDashboard(),
    enabled: isAuthenticated,
  });

  const { data: health } = useQuery({
    queryKey: ['health'],
    queryFn: () => healthApi.check(),
    enabled: isAuthenticated,
  });

  const { data: recentPredictions } = useQuery({
    queryKey: ['recentPredictions'],
    queryFn: () => predictionsApi.list({ per_page: 5, sort_by: 'prediction_timestamp', sort_order: 'desc' }),
    enabled: isAuthenticated,
  });

  if (isLoading || !isAuthenticated) {
    return (
      <div className="page-container">
        <div className="space-y-6">
          <div className="h-8 w-48 skeleton" />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => <div key={i} className="h-28 skeleton" />)}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-80 skeleton" />
            <div className="h-80 skeleton" />
          </div>
        </div>
      </div>
    );
  }

  if (dashError) {
    return (
      <div className="page-container">
        <div className="error-state">
          <AlertTriangle className="w-12 h-12 text-danger-400" />
          <h3 className="error-state-title">Failed to load dashboard</h3>
          <p className="error-state-description">Could not connect to the backend API. Please ensure the server is running.</p>
          <button onClick={() => window.location.reload()} className="btn btn-primary">Retry</button>
        </div>
      </div>
    );
  }

  const riskData = dashboard ? [
    { name: 'Critical', value: dashboard.critical, color: COLORS.critical },
    { name: 'High Risk', value: dashboard.high_risk, color: COLORS.high },
    { name: 'Moderate', value: dashboard.moderate, color: COLORS.moderate },
  ] : [];

  const totalRiskCount = dashboard
    ? dashboard.critical + dashboard.high_risk + dashboard.moderate
    : 0;

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Clinical readmission prediction overview</p>
        </div>
        {health && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-success-50 text-success-700 text-sm">
            <div className="w-2 h-2 rounded-full bg-success-500" />
            System: {health.status}
          </div>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Predictions</span>
            <div className="w-9 h-9 rounded-lg bg-primary-50 flex items-center justify-center">
              <Activity className="w-5 h-5 text-primary-600" />
            </div>
          </div>
          <span className="stat-value">{formatNumber(dashboard?.total_predictions || 0)}</span>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">High Risk</span>
            <div className="w-9 h-9 rounded-lg bg-danger-50 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-danger-600" />
            </div>
          </div>
          <span className="stat-value text-danger-600">{formatNumber(dashboard?.high_risk || 0)}</span>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Critical</span>
            <div className="w-9 h-9 rounded-lg bg-danger-50 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-danger-600" />
            </div>
          </div>
          <span className="stat-value text-danger-800">{formatNumber(dashboard?.critical || 0)}</span>
        </div>

        <div className="stat-card">
          <div className="flex items-center justify-between">
            <span className="stat-label">Mean Risk Score</span>
            <div className="w-9 h-9 rounded-lg bg-primary-50 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-primary-600" />
            </div>
          </div>
          <span className="stat-value">{dashboard ? (dashboard.mean_risk_score * 100).toFixed(1) + '%' : 'N/A'}</span>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Risk Distribution */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Risk Distribution</h3>
              <p className="card-description">Patient readmission risk breakdown</p>
            </div>
          </div>
          <div className="h-72">
            {dashboard && totalRiskCount > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    dataKey="value"
                    label={(entry: { name?: string; percent?: number; value: number }) => `${entry.name ?? ''} ${entry.value}`}
                  >
                    {riskData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state h-full">
                <Activity className="w-8 h-8 text-surface-300" />
                <p className="text-sm text-surface-500">No predictions yet</p>
              </div>
            )}
          </div>
        </div>

        {/* Risk Level Bar Chart */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Risk Levels</h3>
              <p className="card-description">Count by prediction category</p>
            </div>
          </div>
          <div className="h-72">
            {dashboard && totalRiskCount > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={riskData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" fontSize={12} tick={{ fill: '#64748b' }} />
                  <YAxis fontSize={12} tick={{ fill: '#64748b' }} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {riskData.map((entry, idx) => (
                      <Cell key={idx} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state h-full">
                <Activity className="w-8 h-8 text-surface-300" />
                <p className="text-sm text-surface-500">No risk data yet</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Bottom row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Predictions */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Recent Predictions</h3>
              <p className="card-description">Latest readmission risk assessments</p>
            </div>
          </div>
          {recentPredictions && recentPredictions.data.length > 0 ? (
            <div className="space-y-3">
              {recentPredictions.data.slice(0, 5).map((p: { id: string; patient_id: string; prediction_timestamp: string; risk_score: number; risk_level: string }) => (
                <div key={p.id} className="flex items-center justify-between p-3 rounded-lg bg-surface-50 hover:bg-surface-100 transition-colors cursor-pointer" onClick={() => router.push(`/predictions/${p.id}`)}>
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${getRiskColor(p.risk_level)}`} />
                    <div>
                      <div className="text-sm font-medium text-surface-900">
                        Patient: {p.patient_id.slice(0, 8)}...
                      </div>
                      <div className="text-xs text-surface-500">
                        {new Date(p.prediction_timestamp).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className={`badge ${getRiskColor(p.risk_level)}`}>
                    {getRiskLabel(p.risk_level)} ({(p.risk_score * 100).toFixed(0)}%)
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">
              <Activity className="w-8 h-8 text-surface-300" />
              <p className="text-sm text-surface-500">No predictions yet</p>
            </div>
          )}
        </div>

        {/* System Info */}
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">System Overview</h3>
              <p className="card-description">Platform health and model information</p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface-50">
              <div className="flex items-center gap-3">
                <Shield className="w-5 h-5 text-primary-500" />
                <div>
                  <div className="text-sm font-medium text-surface-900">Active Model</div>
                  <div className="text-xs text-surface-500">Currently deployed</div>
                </div>
              </div>
              <div className="text-sm font-medium text-surface-900">
                {dashboard?.current_model || 'N/A'} {dashboard?.current_model_version ? `v${dashboard.current_model_version}` : ''}
              </div>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-surface-50">
              <div className="flex items-center gap-3">
                <TrendingUp className="w-5 h-5 text-success-500" />
                <div>
                  <div className="text-sm font-medium text-surface-900">Mean Risk Score</div>
                  <div className="text-xs text-surface-500">Average across predictions</div>
                </div>
              </div>
              <div className="text-sm font-semibold text-surface-900">
                {dashboard ? `${(dashboard.mean_risk_score * 100).toFixed(1)}%` : 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}