'use client';

import { useAuth } from '@/providers/auth-provider';
import { useRouter } from 'next/navigation';
import { useEffect } from 'react';
import { UserCircle, Shield, Calendar, Mail, BadgeCheck } from 'lucide-react';
import { formatDate } from '@/lib/utils';

export default function ProfilePage() {
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) router.push('/login');
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !user) {
    return <div className="page-container"><div className="max-w-2xl mx-auto"><div className="h-48 skeleton" /></div></div>;
  }

  return (
    <div className="page-container max-w-2xl">
      <div className="page-header">
        <h1 className="page-title">Profile</h1>
      </div>

      <div className="card">
        <div className="flex items-center gap-4 mb-6 pb-6 border-b border-surface-200">
          <div className="w-16 h-16 rounded-full bg-primary-100 flex items-center justify-center">
            <span className="text-2xl font-bold text-primary-700">
              {user.full_name.charAt(0).toUpperCase()}
            </span>
          </div>
          <div>
            <h2 className="text-xl font-semibold text-surface-900">{user.full_name}</h2>
            <p className="text-sm text-surface-500">{user.email}</p>
          </div>
        </div>

        <dl className="space-y-4">
          <div className="flex items-center justify-between p-3 rounded-lg bg-surface-50">
            <div className="flex items-center gap-3">
              <Mail className="w-5 h-5 text-surface-400" />
              <div>
                <div className="text-sm font-medium text-surface-900">Email</div>
                <div className="text-xs text-surface-500">{user.email}</div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg bg-surface-50">
            <div className="flex items-center gap-3">
              <Shield className="w-5 h-5 text-surface-400" />
              <div>
                <div className="text-sm font-medium text-surface-900">Role</div>
                <div className="text-xs text-surface-500">System permissions</div>
              </div>
            </div>
            <span className="badge badge-info capitalize">{user.role}</span>
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg bg-surface-50">
            <div className="flex items-center gap-3">
              <BadgeCheck className="w-5 h-5 text-surface-400" />
              <div>
                <div className="text-sm font-medium text-surface-900">Account Status</div>
                <div className="text-xs text-surface-500">Current state</div>
              </div>
            </div>
            <span className={`badge ${user.is_active ? 'badge-success' : 'badge-danger'}`}>
              {user.is_active ? 'Active' : 'Inactive'}
            </span>
          </div>

          <div className="flex items-center justify-between p-3 rounded-lg bg-surface-50">
            <div className="flex items-center gap-3">
              <Calendar className="w-5 h-5 text-surface-400" />
              <div>
                <div className="text-sm font-medium text-surface-900">Member Since</div>
                <div className="text-xs text-surface-500">Account creation date</div>
              </div>
            </div>
            <span className="text-sm text-surface-900">{formatDate(user.created_at)}</span>
          </div>
        </dl>

        <div className="mt-6 pt-6 border-t border-surface-200">
          <button onClick={logout} className="btn btn-danger w-full">
            Sign Out
          </button>
        </div>
      </div>
    </div>
  );
}