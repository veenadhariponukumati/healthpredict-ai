import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatDateTime(dateString: string): string {
  return new Date(dateString).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatNumber(num: number): string {
  return new Intl.NumberFormat('en-US').format(num);
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

export function getRiskColor(level: string): string {
  switch (level?.toLowerCase()) {
    case 'high':
    case 'critical':
      return 'badge-danger';
    case 'moderate':
    case 'medium':
      return 'badge-warning';
    case 'low':
      return 'badge-success';
    default:
      return 'badge-neutral';
  }
}

export function getRiskLabel(level: string): string {
  return level ? level.charAt(0).toUpperCase() + level.slice(1).toLowerCase() : 'Unknown';
}

export function getWorkflowStatusColor(status: string): string {
  switch (status?.toLowerCase()) {
    case 'completed':
      return 'badge-success';
    case 'active':
    case 'running':
    case 'in_progress':
      return 'badge-info';
    case 'failed':
      return 'badge-danger';
    case 'pending':
      return 'badge-warning';
    default:
      return 'badge-neutral';
  }
}

export function getInitials(firstName: string, lastName: string): string {
  return `${firstName?.charAt(0) || ''}${lastName?.charAt(0) || ''}`.toUpperCase();
}

export function truncate(str: string, length: number): string {
  if (!str) return '';
  return str.length > length ? `${str.slice(0, length)}...` : str;
}

export function buildQueryString(params: Record<string, string | number | boolean | undefined | null>): string {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value));
    }
  });
  const qs = searchParams.toString();
  return qs ? `?${qs}` : '';
}