import { create } from 'zustand';
import { authApi } from '../api/auth';
import { tokenStore } from '../api/client';
import { can, ROLE_HOME } from '../constants/roles';
import type { Role, User } from '../types/models';

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<User>;
  logout: () => void;
  loadMe: () => Promise<User | null>;
  can: (action: string) => boolean;
  home: () => string;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: tokenStore.get(),
  loading: false,
  error: null,
  login: async (email, password) => {
    set({ loading: true, error: null });
    try {
      const response = await authApi.login(email, password);
      tokenStore.set(response.access_token, response.refresh_token);
      set({ user: response.user, token: response.access_token, loading: false });
      return response.user;
    } catch (error) {
      set({ loading: false, error: error instanceof Error ? error.message : '登录失败' });
      throw error;
    }
  },
  logout: () => {
    tokenStore.clear();
    set({ user: null, token: null });
  },
  loadMe: async () => {
    if (!tokenStore.get()) return null;
    try {
      const user = await authApi.me();
      set({ user, token: tokenStore.get() });
      return user;
    } catch {
      set({ user: null });
      return null;
    }
  },
  can: (action) => can(get().user?.role as Role | undefined, action),
  home: () => ROLE_HOME[(get().user?.role ?? 'marketing') as Role],
}));
