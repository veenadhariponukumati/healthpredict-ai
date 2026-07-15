'use client';

import { AuthProvider } from './auth-provider';
import { QueryProvider } from './query-provider';
import { AppShell } from '@/components/layout/app-shell';
import { type ReactNode } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      <AuthProvider>
        <AppShell>
          {children}
        </AppShell>
      </AuthProvider>
    </QueryProvider>
  );
}