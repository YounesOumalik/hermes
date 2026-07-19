"use client";

import { useRouter } from "next/navigation";
import { Plus, LogOut, Shield } from "lucide-react";
import { useAuth } from "@/stores/authStore";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { Button, Badge } from "@/components/ui";
import type { Agent } from "@/lib/types";

interface SidebarProps {
  agents: Agent[];
  activeAgentId: string | null;
  onSelectAgent: (agent: Agent) => void;
  onOpenWorkspaceModal: () => void;
  onOpenAgentModal: () => void;
}

/**
 * Sidebar gauche du dashboard.
 * Contient : sélecteur de workspace + liste d'agents + profil utilisateur.
 */
export function Sidebar({
  agents,
  activeAgentId,
  onSelectAgent,
  onOpenWorkspaceModal,
  onOpenAgentModal,
}: SidebarProps) {
  const router = useRouter();
  const user = useAuth((s) => s.user);
  const logout = useAuth((s) => s.logout);
  const { workspaces, activeWorkspace, setActiveWorkspace } = useWorkspaceStore();

  return (
    <aside
      className="glass-panel"
      style={{
        width: "300px",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        borderRadius: "0",
        borderTop: "none",
        borderBottom: "none",
        borderLeft: "none",
      }}
    >
      {/* En-tête : sélecteur de workspace */}
      <div style={{ padding: "20px", borderBottom: "1px solid var(--border-glass)" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h2 style={{ fontSize: "16px", fontWeight: "700" }}>Workspaces</h2>
          <Button
            variant="secondary"
            size="sm"
            icon={<Plus size={12} />}
            onClick={onOpenWorkspaceModal}
          >
            New
          </Button>
        </div>

        <select
          value={activeWorkspace?.id || ""}
          onChange={(e) => {
            const ws = workspaces.find((w) => w.id === e.target.value);
            if (ws) setActiveWorkspace(ws);
          }}
          className="input-field"
          style={{ marginTop: "12px" }}
          aria-label="Active workspace"
        >
          {workspaces.length === 0 && <option value="">No workspace</option>}
          {workspaces.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
      </div>

      {/* Section Agents */}
      <div
        style={{
          flex: 1,
          padding: "20px",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3
            style={{
              fontSize: "14px",
              fontWeight: "600",
              color: "var(--text-secondary)",
              textTransform: "uppercase",
            }}
          >
            Agents
          </h3>
          <Button
            variant="secondary"
            size="sm"
            icon={<Plus size={12} />}
            onClick={onOpenAgentModal}
            disabled={!activeWorkspace}
          >
            Create
          </Button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {agents.length === 0 && (
            <p style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic" }}>
              No agents yet. Click "Create" to deploy one.
            </p>
          )}
          {agents.map((a) => (
            <button
              key={a.id}
              onClick={() => onSelectAgent(a)}
              className="glass-card"
              style={{
                width: "100%",
                padding: "12px",
                display: "flex",
                alignItems: "center",
                gap: "10px",
                borderLeft:
                  activeAgentId === a.id
                    ? `4px solid ${a.avatar_color}`
                    : "1px solid rgba(255,255,255,0.05)",
                cursor: "pointer",
                color: "#fff",
                textAlign: "left",
                background:
                  activeAgentId === a.id ? "rgba(255,255,255,0.03)" : "transparent",
                transition: "all var(--transition-fast)",
              }}
            >
              <div
                style={{
                  width: "12px",
                  height: "12px",
                  borderRadius: "50%",
                  backgroundColor: a.avatar_color,
                  flexShrink: 0,
                }}
              />
              <div style={{ minWidth: 0, flex: 1 }}>
                <h4 style={{ fontSize: "13px", fontWeight: "600" }}>{a.name}</h4>
                <p
                  style={{
                    fontSize: "11px",
                    color: "var(--text-muted)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    maxWidth: "200px",
                  }}
                >
                  {a.description || "No description"}
                </p>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* Pied : profil utilisateur */}
      {user && (
        <div
          style={{
            padding: "20px",
            borderTop: "1px solid var(--border-glass)",
            display: "flex",
            flexDirection: "column",
            gap: "12px",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
              <div
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "50%",
                  backgroundColor: "var(--bg-tertiary)",
                  backgroundImage: user.avatar_url ? `url(${user.avatar_url})` : "none",
                  backgroundSize: "cover",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontSize: "12px",
                  fontWeight: "bold",
                  flexShrink: 0,
                }}
              >
                {!user.avatar_url && user.display_name.charAt(0)}
              </div>
              <div style={{ minWidth: 0 }}>
                <h4
                  style={{
                    fontSize: "12px",
                    fontWeight: "600",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                >
                  {user.display_name}
                </h4>
                {user.is_superadmin && (
                  <Badge variant="superadmin">Admin</Badge>
                )}
              </div>
            </div>

            <button
              onClick={logout}
              aria-label="Logout"
              style={{
                border: "none",
                background: "none",
                color: "var(--color-error)",
                cursor: "pointer",
                padding: "4px",
                display: "flex",
              }}
            >
              <LogOut size={16} />
            </button>
          </div>

          {user.is_superadmin && (
            <Button
              variant="primary"
              size="sm"
              icon={<Shield size={12} />}
              fullWidth
              onClick={() => router.push("/admin")}
            >
              System Admin Panel
            </Button>
          )}
        </div>
      )}
    </aside>
  );
}

export default Sidebar;
