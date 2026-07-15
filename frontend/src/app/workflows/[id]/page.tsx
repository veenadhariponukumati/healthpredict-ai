'use client';

import { useQuery } from '@tanstack/react-query';
import { workflowsApi } from '@/services/api';
import { useAuth } from '@/providers/auth-provider';
import { useParams, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { ArrowLeft, AlertTriangle, GitBranch, Clock, CheckCircle2, XCircle, Activity } from 'lucide-react';
import { formatDateTime, getWorkflowStatusColor, getRiskLabel } from '@/lib/utils';

export default function WorkflowDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const workflowId = params.id as string;

  useEffect(() => {
    if (!authLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, authLoading, router]);

  const { data: workflow, isLoading, error } = useQuery({
    queryKey: ['workflow', workflowId],
    queryFn: () => workflowsApi.getById(workflowId),
    enabled: isAuthenticated && !!workflowId,
  });

  if (authLoading || isLoading) {
    return <div className="page-container"><div className="space-y-4"><div className="h-8 w-48 skeleton" /><div className="h-64 skeleton" /></div></div>;
  }

  if (error || !workflow) {
    return <div className="page-container"><div className="error-state"><AlertTriangle className="w-12 h-12 text-danger-400" /><h3 className="error-state-title">Workflow not found</h3><button onClick={() => router.push('/workflows')} className="btn btn-primary">Back to Workflows</button></div></div>;
  }

  const timeline = [
    { label: 'Triggered', value: workflow.triggered_at ? formatDateTime(workflow.triggered_at) : '—', icon: Clock, status: 'done' },
    { label: 'Completed', value: workflow.completed_at ? formatDateTime(workflow.completed_at) : 'Pending', icon: Activity, status: workflow.status === 'completed' ? 'done' : workflow.status === 'failed' ? 'failed' : 'current' },
    { label: 'Status', value: workflow.status, icon: workflow.status === 'completed' ? CheckCircle2 : workflow.status === 'failed' ? XCircle : GitBranch, status: workflow.status === 'completed' ? 'done' : workflow.status === 'failed' ? 'failed' : 'current' },
  ];

  return (
    <div className="page-container max-w-4xl">
      <div className="page-header">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="btn btn-ghost btn-sm"><ArrowLeft className="w-4 h-4" /></button>
          <div>
            <h1 className="page-title">Workflow Detail</h1>
            <p className="page-subtitle">Care coordination workflow: {workflow.workflow_type}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Info */}
        <div className="card lg:col-span-2">
          <div className="card-header">
            <h3 className="card-title">Workflow Information</h3>
          </div>
          <dl className="grid grid-cols-2 gap-4">
            <div><dt className="text-xs text-surface-500">Type</dt><dd className="text-sm font-medium">{workflow.workflow_type}</dd></div>
            <div><dt className="text-xs text-surface-500">Status</dt><dd><span className={`badge ${getWorkflowStatusColor(workflow.status)}`}>{workflow.status}</span></dd></div>
            <div><dt className="text-xs text-surface-500">Patient ID</dt><dd className="text-sm font-mono">{workflow.patient_id || '—'}</dd></div>
            <div><dt className="text-xs text-surface-500">Retry Count</dt><dd className="text-sm">{workflow.retry_count}</dd></div>
            <div><dt className="text-xs text-surface-500">Temporal Workflow ID</dt><dd className="text-sm font-mono text-xs">{workflow.temporal_workflow_id || '—'}</dd></div>
            <div><dt className="text-xs text-surface-500">n8n Execution ID</dt><dd className="text-sm font-mono text-xs">{workflow.n8n_execution_id || '—'}</dd></div>
            <div><dt className="text-xs text-surface-500">Triggered</dt><dd className="text-sm">{workflow.triggered_at ? formatDateTime(workflow.triggered_at) : '—'}</dd></div>
            <div><dt className="text-xs text-surface-500">Completed</dt><dd className="text-sm">{workflow.completed_at ? formatDateTime(workflow.completed_at) : '—'}</dd></div>
          </dl>
          {workflow.error_details && (
            <div className="mt-4 p-3 rounded-lg bg-danger-50 border border-danger-200 text-sm text-danger-700">
              <strong>Error:</strong> {JSON.stringify(workflow.error_details)}
            </div>
          )}
        </div>

        {/* Timeline */}
        <div className="card">
          <h3 className="card-title mb-4">Timeline</h3>
          <div className="space-y-0">
            {timeline.map((item, idx) => (
              <div key={idx} className="relative flex gap-4 pb-6 last:pb-0">
                <div className="flex flex-col items-center">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    item.status === 'done' ? 'bg-success-100 text-success-600' :
                    item.status === 'failed' ? 'bg-danger-100 text-danger-600' :
                    'bg-primary-100 text-primary-600'
                  }`}>
                    <item.icon className="w-4 h-4" />
                  </div>
                  {idx < timeline.length - 1 && <div className="w-0.5 flex-1 bg-surface-200 mt-1" />}
                </div>
                <div className="pt-1.5">
                  <div className="text-sm font-medium text-surface-900">{item.label}</div>
                  <div className="text-xs text-surface-500">{item.value}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}