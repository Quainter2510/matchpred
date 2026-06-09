import { create } from "zustand";
import { api, Me } from "../api/endpoints";
import { setAccessToken } from "../api/client";

interface AuthState {
  user: Me | null;
  loading: boolean;
  loadMe: () => Promise<Me | null>;
  setUser: (u: Me | null) => void;
  logout: () => Promise<void>;
  isAdmin: () => boolean;
  isSuperadmin: () => boolean;
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  loading: true,
  setUser: (u) => set({ user: u }),
  loadMe: async () => {
    try {
      const me = await api.me();
      set({ user: me, loading: false });
      return me;
    } catch {
      set({ user: null, loading: false });
      return null;
    }
  },
  logout: async () => {
    try {
      await api.logout();
    } catch {
      /* ignore */
    }
    setAccessToken(null);
    set({ user: null });
  },
  isAdmin: () => {
    const u = get().user;
    return (
      u?.system_role === "superadmin" || u?.tournament_role === "admin"
    );
  },
  isSuperadmin: () => get().user?.system_role === "superadmin",
}));
