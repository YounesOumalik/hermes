"use client";

import { create } from "zustand";
import type { User } from "@/lib/types";
import { apiGet, clearSessionAndRedirect } from "@/lib/api";

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isInitialized: boolean;
  error: string | null;

  /** Charge le profil utilisateur depuis /api/auth/me. */
  fetchUser: () => Promise<User | null>;
  /** Définit l'utilisateur manuellement (après login). */
  setUser: (user: User | null) => void;
  /** Déconnexion : clear localStorage + redirect /login. */
  logout: () => void;
  /** Reset erreur. */
  clearError: () => void;
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  isInitialized: false,
  error: null,

  fetchUser: async () => {
    set({ isLoading: true, error: null });
    try {
      const user = await apiGet<User>("/auth/me");
      set({ user, isLoading: false, isInitialized: true });
      return user;
    } catch (e) {
      const message = e instanceof Error ? e.message : "Failed to load user";
      set({
        isLoading: false,
        isInitialized: true,
        error: message,
        user: null,
      });
      return null;
    }
  },

  setUser: (user) => set({ user, isInitialized: true }),

  logout: () => {
    set({ user: null, isInitialized: true });
    clearSessionAndRedirect();
  },

  clearError: () => set({ error: null }),
}));

export default useAuth;
