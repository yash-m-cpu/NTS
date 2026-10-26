import { create } from 'zustand';

interface User {
  id: string;
  email: string;
  full_name?: string;
  organizations: Org[];
}

interface Org {
  id: string;
  name: string;
  role: string;
}

interface AuthState {
  accessToken: string | null;
  user: User | null;
  activeOrgId: string | null;
  setAuth: (token: string, user: User) => void;
  clearAuth: () => void;
  setActiveOrgId: (id: string) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  activeOrgId: null,
  setAuth: (token, user) => set({ accessToken: token, user, activeOrgId: user.organizations?.[0]?.id || null }),
  clearAuth: () => set({ accessToken: null, user: null, activeOrgId: null }),
  setActiveOrgId: (id) => set({ activeOrgId: id }),
}));
