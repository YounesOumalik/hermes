"use client";

import { create } from "zustand";
import type { Workspace } from "@/lib/types";
import { apiGet, apiPost } from "@/lib/api";

interface WorkspaceState {
  workspaces: Workspace[];
  activeWorkspace: Workspace | null;
  isLoading: boolean;
  error: string | null;

  /** Charge tous les workspaces de l'utilisateur. */
  fetchWorkspaces: () => Promise<Workspace[]>;
  /** Définit le workspace actif. */
  setActiveWorkspace: (w: Workspace) => void;
  /** Crée un nouveau workspace et l'ajoute à la liste. */
  createWorkspace: (name: string) => Promise<Workspace>;
  /** Reset complet. */
  reset: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  workspaces: [],
  activeWorkspace: null,
  isLoading: false,
  error: null,

  fetchWorkspaces: async () => {
    set({ isLoading: true, error: null });
    try {
      const workspaces = await apiGet<Workspace[]>("/workspaces");
      const current = get().activeWorkspace;
      // Conserver le workspace actif s'il existe encore, sinon prendre le 1er
      const stillExists = current && workspaces.find((w) => w.id === current.id);
      const active = stillExists || workspaces[0] || null;
      set({ workspaces, activeWorkspace: active, isLoading: false });
      return workspaces;
    } catch (e) {
      const message = e instanceof Error ? e.message : "Failed to load workspaces";
      set({ isLoading: false, error: message });
      return [];
    }
  },

  setActiveWorkspace: (w) => set({ activeWorkspace: w }),

  createWorkspace: async (name: string) => {
    const ws = await apiPost<Workspace>("/workspaces", { name });
    set((state) => ({
      workspaces: [...state.workspaces, ws],
      activeWorkspace: ws,
    }));
    return ws;
  },

  reset: () =>
    set({ workspaces: [], activeWorkspace: null, isLoading: false, error: null }),
}));

export default useWorkspaceStore;
