"use client";

import { useRouter, usePathname } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import { ChevronDown, Shield } from "lucide-react";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { useAuth } from "@/stores/authStore";
import type { Workspace } from "@/lib/types";

interface TopBarProps {
  /** Titre affiché à gauche (souvent le nom de la page courante). */
  title?: string;
}

/**
 * Barre supérieure : workspace switcher + avatar + accès admin.
 * Visible uniquement sur mobile (masquée en desktop où la Sidebar suffit).
 */
export function TopBar({ title }: TopBarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { workspaces, activeWorkspace, setActiveWorkspace } = useWorkspaceStore();
  const user = useAuth((s) => s.user);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelect = (ws: Workspace) => {
    setActiveWorkspace(ws);
    setDropdownOpen(false);
  };

  const initials = user?.display_name?.charAt(0).toUpperCase() || "?";

  return (
    <header className="topbar">
      <div className="topbar-left">
        <h1 className="topbar-title" title={title || getPageTitle(pathname)}>
          {truncate(title || getPageTitle(pathname), 28)}
        </h1>
      </div>

      <div className="topbar-right">
        {/* Workspace switcher */}
        <div className="workspace-switcher" ref={dropdownRef}>
          <button
            type="button"
            className="workspace-switcher-trigger"
            onClick={() => setDropdownOpen((o) => !o)}
            aria-haspopup="listbox"
            aria-expanded={dropdownOpen}
          >
            <span className="workspace-dot" />
            <span className="workspace-name">
              {activeWorkspace?.name || "Select workspace"}
            </span>
            <ChevronDown size={14} />
          </button>

          {dropdownOpen && (
            <ul className="workspace-dropdown" role="listbox" aria-label="Workspaces">
              {workspaces.length === 0 && (
                <li className="workspace-dropdown-empty">No workspace</li>
              )}
              {workspaces.map((ws) => (
                <li key={ws.id}>
                  <button
                    type="button"
                    role="option"
                    aria-selected={ws.id === activeWorkspace?.id}
                    className={`workspace-dropdown-item ${
                      ws.id === activeWorkspace?.id ? "workspace-dropdown-active" : ""
                    }`}
                    onClick={() => handleSelect(ws)}
                  >
                    {ws.name}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Avatar → /settings */}
        <button
          type="button"
          className="topbar-avatar"
          onClick={() => router.push("/settings")}
          aria-label="Open settings"
          style={{
            backgroundImage: user?.avatar_url ? `url(${user.avatar_url})` : "none",
          }}
        >
          {!user?.avatar_url && initials}
        </button>

        {/* Admin shortcut */}
        {user?.is_superadmin && (
          <button
            type="button"
            className="topbar-admin"
            onClick={() => router.push("/admin")}
            aria-label="Open admin panel"
          >
            <Shield size={16} />
          </button>
        )}
      </div>
    </header>
  );
}

function getPageTitle(pathname: string | null): string {
  if (!pathname) return "AgentAI";
  if (pathname === "/") return "Dashboard";
  if (pathname.startsWith("/jobs")) return "Jobs";
  if (pathname.startsWith("/settings")) return "Settings";
  if (pathname.startsWith("/admin")) return "Admin";
  if (pathname.startsWith("/pending")) return "Pending";
  return "AgentAI";
}

/**
 * Tronque un texte trop long avec ellipse.
 */
function truncate(text: string, max: number): string {
  if (!text) return "";
  return text.length > max ? `${text.slice(0, max)}…` : text;
}

export default TopBar;
