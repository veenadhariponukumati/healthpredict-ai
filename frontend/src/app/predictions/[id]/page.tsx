'use client';

import { useQuery } from '@tanstack/react-query';
import { predictionsApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { ArrowLeft, AlertTriangle, Activity, Shield, TrendingUp, BarChart3 } from 'lucide-react';
import { formatDateTime, getRiskColor, getRiskLabel, formatPercent, formatNumber } from '@/lib/utils';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

export default function PredictionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const predictionId = params.id as string;

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  const { data: prediction, isLoading, error } = useQuery({
    queryKey: ['prediction', predictionId],
    queryFn: () => predictionsApi.getById(predictionId),
    enabled: isAuthenticated && !!predictionId,
  });

  if (authLoading || isLoading) {
    return (
      <div className="page-container">
        <div className="space-y-4">
          <div className="h-8 w-48 skeleton" />
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <div className="h-32 skeleton lg:col-span-2" />
            <div className="h-32 skeleton" />
          </div>
          <div className="h-72 skeleton" />
        </div>
      </div>
    );
  }

  if (error || !prediction) {
    return (
      <div className="page-container">
        <div className="error-state">
          <AlertTriangle className="w-12 h-12 text-danger-400" />
          <h3 className="error-state-title">Prediction not found</h3>
          <p className="error-state-description">The prediction record could not be loaded.</p>
          <button onClick={() => router.push('/predictions')} className="btn btn-primary">Back to Predictions</button>
        </div>
      </div>
    );
  }

  const shapEntries = Object.entries(prediction.shap_values || {});
  const shapData = shapEntries
    .map(([key, val]) => ({
      name: key.replace(/_/g, ' ').replace(/\b\w/g, (l: string) => l.toUpperCase()),
      value: Math.abs(val as number),
      raw: val as number,
    }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 10);

  return (
    <div className="page-container max-w-4xl">
      <div className="page-header">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="btn btn-ghost btn-sm">
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <h1 className="page-title">Prediction Detail</h1>
            <p className="page-subtitle">Readmission risk assessment</p>
          </div>
        </div>
      </div>

      {/* Risk Score Card */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="lg:col-span-2 card">
          <div className="flex items-center gap-4">
            <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${
              prediction.risk_level === 'high' || prediction.risk_level === 'critical' ? 'bg-danger-50' :
              prediction.risk_level === 'moderate' || prediction.risk_level === 'medium' ? 'bg-warning-50' :
              'bg-success-50'
            }`}>
              <Activity className={`w-8 h-8 ${
                prediction.risk_level === 'high' || prediction.risk_level === 'critical' ? 'text-danger-600' :
                prediction.risk_level === 'moderate' || prediction.risk_level === 'medium' ? 'text-warning-600' :
                'text-success-600'
              }`} />
            </div>
            <div>
              <div className="text-sm text-surface-500 mb-1">Risk Assessment</div>
              <div className="flex items-center gap-3">
                <span className={`badge text-sm px-3 py-1 ${getRiskColor(prediction.risk_level)}`}>
                  {getRiskLabel(prediction.risk_level)}
                </span>
                <span className="text-2xl font-bold text-surface-900">
                  {(prediction.risk_score * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-surface-500">Confidence</span>
              <span className="text-sm font-semibold text-surface-900">{formatPercent(prediction.confidence)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-surface-500">Threshold</span>
              <span className="text-sm font-semibold text-surface-900">{(prediction.threshold * 100).toFixed(0)}%</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-surface-500">Model</span>
              <span className="text-sm font-mono text-surface-900">{prediction.model_version || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-surface-500">Latency</span>
              <span className="text-sm font-mono text-surface-900">{prediction.inference_latency_ms ? `${prediction.inference_latency_ms}ms` : 'N/A'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Metadata */}
      <div className="card mb-6">
        <div className="card-header">
          <h3 className="card-title">Details</h3>
        </div>
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <dt className="text-xs text-surface-500">Prediction ID</dt>
            <dd className="text-sm font-mono text-surface-900">{prediction.id.slice(0, 16)}...</dd>
          </div>
          <div>
            <dt className="text-xs text-surface-500">Patient ID</dt>
            <dd className="text-sm font-mono text-surface-900">{prediction.patient_id.slice(0, 16)}...</dd>
          </div>
          <div>
            <dt className="text-xs text-surface-500">Timestamp</dt>
            <dd className="text-sm text-surface-900">{formatDateTime(prediction.prediction_timestamp)}</dd>
          </div>
          <div>
            <dt className="text-xs text-surface-500">Risk Level</dt>
            <dd><span className={`badge ${getRiskColor(prediction.risk_level)}`}>{getRiskLabel(prediction.risk_level)}</span></dd>
          </div>
        </dl>
      </div>

      {/* SHAP Explanation */}
      {shapData.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div>
              <h3 className="card-title">Feature Importance</h3>
              <p className="card-description">SHAP-based explanation of factors driving this prediction</p>
            </div>
          </div>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={shapData} layout="vertical" margin={{ top: 5, right: 30, left: 100, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis type="number" fontSize={12} tick={{ fill: '#64748b' }} />
                <YAxis type="category" dataKey="name" fontSize={12} tick={{ fill: '#64748b' }} width={120} />
                <Tooltip />
                <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Raw SHAP values */}
      {prediction.shap_values && Object.keys(prediction.shap_values).length > 0 && (
        <div className="card mt-6">
          <div className="card-header">
            <h3 className="card-title">SHAP Values</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
            {Object.entries(prediction.shap_values).slice(0, 12).map(([key, value]) => (
              <div key={key} className="flex justify-between p-2 rounded bg-surface-50 text-sm">
                <span className="text-surface-600">{key.replace(/_/g, ' ')}</span>
                <span className={`font-mono font-medium ${(value as number) >= 0 ? 'text-danger-600' : 'text-success-600'}`}>
                  {(value as number).toFixed(4)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}