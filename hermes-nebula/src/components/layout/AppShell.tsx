"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { TopBar } from "./TopBar";
import { BottomNav } from "./BottomNav";
import { useAuth } from "@/stores/authStore";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { isAuthenticated } from "@/lib/api";
import { Spinner } from "@/components/ui";

interface AppShellProps {
  children: ReactNode;
  title?: string;
  /** Si true, masque la TopBar (utile pour les pages qui gèrent leur propre header). */
  hideTopBar?: boolean;
  /** Si false, désactive l'auth guard (utile pour les pages publiques). */
  requireAuth?: boolean;
}

/**
 * Layout global de l'app authentifiée.
 * - Desktop : sidebar native (gérée par chaque page, ex: dashboard)
 * - Mobile : TopBar + BottomNav
 * - Auth guard : redirige vers /login si non authentifié
 * - Hydrate authStore + workspaceStore au montage
 */
export function AppShell({
  children,
  title,
  hideTopBar = false,
  requireAuth = true,
}: AppShellProps) {
  const router = useRouter();
  const { user, isInitialized, fetchUser } = useAuth();
  const { fetchWorkspaces } = useWorkspaceStore();

  useEffect(() => {
    if (requireAuth && !isAuthenticated()) {
      router.push("/login");
      return;
    }
    if (requireAuth && !isInitialized) {
      fetchUser();
      fetchWorkspaces();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  // Loading plein écran pendant l'init auth
  if (requireAuth && !user && !isInitialized) {
    return <Spinner fullscreen label="Loading your workspace..." />;
  }

  return (
    <div className="app-shell">
      {!hideTopBar && <TopBar title={title} />}
      <main className="app-shell-main">{children}</main>
      <BottomNav />
    </div>
  );
}

export default AppShell;
