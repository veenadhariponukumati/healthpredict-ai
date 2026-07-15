'use client';

import { useAuth } from '@/providers/auth-provider';
import { Sidebar, MobileSidebar } from '@/components/layout/sidebar';
import { Menu } from 'lucide-react';
import { useState } from 'react';
import { usePathname } from 'next/navigation';

export function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  const isLoginPage = pathname === '/login';

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-surface-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <div className="text-sm text-surface-500">Loading...</div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || isLoginPage) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen bg-surface-50">
      <Sidebar />
      <MobileSidebar open={mobileOpen} onClose={() => setMobileOpen(false)} />

      {/* Mobile header */}
      <div className="lg:hidden fixed top-0 left-0 right-0 h-16 bg-white border-b border-surface-200 flex items-center px-4 z-30">
        <button
          onClick={() => setMobileOpen(true)}
          className="text-surface-600 hover:text-surface-900 p-1"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2 ml-3">
          <div className="w-6 h-6 rounded-md bg-primary-600 flex items-center justify-center">
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <span className="text-sm font-semibold text-surface-900">HealthPredict</span>
        </div>
      </div>

      <main className="lg:pl-64 pt-0 lg:pt-0 pt-16">
        {children}
      </main>
    </div>
  );
}