'use client';

import { useAuth } from '@/providers/auth-provider';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Users,
  Activity,
  GitBranch,
  ScrollText,
  Cpu,
  HeartPulse,
  UserCircle,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Shield,
} from 'lucide-react';
import { useState } from 'react';

const navItems = [
  { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard, roles: ['admin', 'clinician', 'viewer'] },
  { href: '/patients', label: 'Patients', icon: Users, roles: ['admin', 'clinician', 'viewer'] },
  { href: '/predictions', label: 'Predictions', icon: Activity, roles: ['admin', 'clinician', 'viewer'] },
  { href: '/workflows', label: 'Workflows', icon: GitBranch, roles: ['admin', 'clinician'] },
  { href: '/audit', label: 'Audit Logs', icon: ScrollText, roles: ['admin'] },
  { href: '/models', label: 'Model Registry', icon: Cpu, roles: ['admin', 'clinician', 'viewer'] },
  { href: '/health', label: 'System Health', icon: HeartPulse, roles: ['admin', 'clinician', 'viewer'] },
];

export function Sidebar() {
  const { user, hasPermission, logout } = useAuth();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  if (!user) return null;

  return (
    <aside
      className={cn(
        'fixed left-0 top-0 h-screen bg-white border-r border-surface-200 flex flex-col transition-all duration-200 z-50',
        collapsed ? 'w-16' : 'w-64',
      )}
    >
      {/* Logo */}
      <div className={cn('flex items-center h-16 px-4 border-b border-surface-200', collapsed && 'justify-center px-0')}>
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center flex-shrink-0">
            <Shield className="w-4 h-4 text-white" />
          </div>
          {!collapsed && (
            <div>
              <div className="text-sm font-semibold text-surface-900">HealthPredict</div>
              <div className="text-xs text-surface-500">Clinical Platform</div>
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
        {navItems
          .filter(item => hasPermission(item.roles as any))
          .map(item => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
            return (
              <Link
                key={item.href}
                href={item.href}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary-50 text-primary-700'
                    : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900',
                  collapsed && 'justify-center px-2',
                )}
                title={collapsed ? item.label : undefined}
              >
                <item.icon className="w-5 h-5 flex-shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </Link>
            );
          })}
      </nav>

      {/* User section */}
      <div className="border-t border-surface-200 p-3">
        <Link
          href="/profile"
          className={cn(
            'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-surface-600 hover:bg-surface-50 hover:text-surface-900 transition-colors',
            collapsed && 'justify-center px-2',
          )}
          title={collapsed ? 'Profile' : undefined}
        >
          <UserCircle className="w-5 h-5 flex-shrink-0" />
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <div className="truncate text-surface-900">{user.full_name}</div>
              <div className="text-xs text-surface-500 truncate">{user.role}</div>
            </div>
          )}
        </Link>
        <button
          onClick={logout}
          className={cn(
            'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-surface-600 hover:bg-surface-50 hover:text-danger-600 transition-colors w-full mt-1',
            collapsed && 'justify-center px-2',
          )}
          title={collapsed ? 'Logout' : undefined}
        >
          <LogOut className="w-5 h-5 flex-shrink-0" />
          {!collapsed && <span>Logout</span>}
        </button>
      </div>

      {/* Collapse button */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-white border border-surface-200 flex items-center justify-center text-surface-400 hover:text-surface-600 shadow-sm"
      >
        {collapsed ? <ChevronRight className="w-3.5 h-3.5" /> : <ChevronLeft className="w-3.5 h-3.5" />}
      </button>
    </aside>
  );
}

export function MobileSidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { user, hasPermission, logout } = useAuth();
  const pathname = usePathname();

  if (!user) return null;

  return (
    <>
      {/* Overlay */}
      {open && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={onClose} />
      )}
      <aside
        className={cn(
          'fixed left-0 top-0 h-screen w-64 bg-white border-r border-surface-200 flex flex-col z-50 transition-transform duration-200 lg:hidden',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-surface-200">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center">
              <Shield className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="text-sm font-semibold text-surface-900">HealthPredict</div>
              <div className="text-xs text-surface-500">Clinical Platform</div>
            </div>
          </div>
          <button onClick={onClose} className="text-surface-400 hover:text-surface-600 p-1">
            <ChevronLeft className="w-5 h-5" />
          </button>
        </div>

        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems
            .filter(item => hasPermission(item.roles as any))
            .map(item => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/');
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={onClose}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-surface-600 hover:bg-surface-50 hover:text-surface-900',
                  )}
                >
                  <item.icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
        </nav>

        <div className="border-t border-surface-200 p-3">
          <Link
            href="/profile"
            onClick={onClose}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-surface-600 hover:bg-surface-50 hover:text-surface-900 transition-colors"
          >
            <UserCircle className="w-5 h-5" />
            <div className="flex-1 min-w-0">
              <div className="truncate text-surface-900">{user.full_name}</div>
              <div className="text-xs text-surface-500 truncate">{user.role}</div>
            </div>
          </Link>
          <button
            onClick={() => { logout(); onClose(); }}
            className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium text-surface-600 hover:bg-surface-50 hover:text-danger-600 transition-colors w-full mt-1"
          >
            <LogOut className="w-5 h-5" />
            <span>Logout</span>
          </button>
        </div>
      </aside>
    </>
  );
}