'use client';

import { createContext, useContext, useEffect, useState, useCallback, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { authApi, setTokenStore } from '@/services/api';
import type { AuthState, UserInfo, UserRole } from '@/types/api';

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasPermission: (requiredRole: UserRole[]) => boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

const TOKEN_KEY = 'hc_access_token';
const REFRESH_KEY = 'hc_refresh_token';
const USER_KEY = 'hc_user';

function getStoredTokens() {
  if (typeof window === 'undefined') return { accessToken: null, refreshToken: null };
  return {
    accessToken: localStorage.getItem(TOKEN_KEY),
    refreshToken: localStorage.getItem(REFRESH_KEY),
  };
}

function getStoredUser(): UserInfo | null {
  if (typeof window === 'undefined') return null;
  try {
    const stored = localStorage.getItem(USER_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    refreshToken: null,
    isAuthenticated: false,
    isLoading: true,
  });
  const router = useRouter();

  // Set up token store for API client
  useEffect(() => {
    setTokenStore({
      getAccessToken: () => localStorage.getItem(TOKEN_KEY),
      getRefreshToken: () => localStorage.getItem(REFRESH_KEY),
      setTokens: (access: string, refresh: string) => {
        localStorage.setItem(TOKEN_KEY, access);
        localStorage.setItem(REFRESH_KEY, refresh);
      },
      clearTokens: () => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_KEY);
        localStorage.removeItem(USER_KEY);
      },
    });
  }, []);

  // Restore session on mount — validate JWT expiry locally
  useEffect(() => {
    const stored = getStoredTokens();
    const user = getStoredUser();

    if (stored.accessToken && user) {
      // Decode the JWT payload (base64) to check expiry
      try {
        const payload = JSON.parse(atob(stored.accessToken.split('.')[1]));
        const now = Math.floor(Date.now() / 1000);
        if (payload.exp && payload.exp > now) {
          setState({
            user,
            accessToken: stored.accessToken,
            refreshToken: stored.refreshToken,
            isAuthenticated: true,
            isLoading: false,
          });
          return;
        }
      } catch {
        // Malformed token — fall through to clear
      }
      // Token expired or invalid — clear session
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem(REFRESH_KEY);
      localStorage.removeItem(USER_KEY);
      setState({
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
      });
    } else {
      setState(prev => ({ ...prev, isLoading: false }));
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const response = await authApi.login({ email, password });

    localStorage.setItem(TOKEN_KEY, response.access_token);
    localStorage.setItem(REFRESH_KEY, response.refresh_token);
    localStorage.setItem(USER_KEY, JSON.stringify(response.user));

    setState({
      user: response.user,
      accessToken: response.access_token,
      refreshToken: response.refresh_token,
      isAuthenticated: true,
      isLoading: false,
    });
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(USER_KEY);

    setState({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
    });
    router.push('/login');
  }, [router]);

  const hasPermission = useCallback((requiredRoles: UserRole[]): boolean => {
    if (!state.user) return false;
    if (state.user.role === 'admin') return true; // admin has all access
    return requiredRoles.includes(state.user.role);
  }, [state.user]);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, hasPermission }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}