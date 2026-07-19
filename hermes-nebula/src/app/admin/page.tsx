"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import "../globals.css";

interface UserItem {
  id: string;
  email: string;
  display_name: string;
  username: string | null;
  avatar_url: string | null;
  is_active: boolean;
  is_superadmin: boolean;
  created_at: string;
}

interface QuotaDetails {
  user_id: string;
  max_disk_bytes: number;
  used_disk_bytes: number;
  max_monthly_llm_tokens: number;
  used_monthly_llm_tokens: number;
  allowed_models: string[];
  allowed_tools: string[];
  notes_admin: string | null;
}

interface GlobalStats {
  total_users: number;
  active_users: number;
  pending_users: number;
  total_disk_used_bytes: number;
  total_api_keys: number;
}

interface ApiKeyItem {
  id: string;
  provider: string;
  key_name: string;
  base_url: string | null;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

interface AuditLogItem {
  id: string;
  admin_user_id: string;
  action: string;
  target_user_id: string | null;
  details_json: any;
  created_at: string;
}

export default function AdminDashboard() {
  const router = useRouter();
  const [me, setMe] = useState<any>(null);
  const [stats, setStats] = useState<GlobalStats | null>(null);
  const [users, setUsers] = useState<UserItem[]>([]);
  const [apiKeys, setApiKeys] = useState<ApiKeyItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  
  // Quota Modal state
  const [selectedUser, setSelectedUser] = useState<UserItem | null>(null);
  const [quotaForm, setQuotaForm] = useState<{
    max_disk_gb: number;
    max_monthly_tokens_m: number;
    allowed_models: string[];
    allowed_tools: string[];
    notes_admin: string;
  }>({
    max_disk_gb: 1,
    max_monthly_tokens_m: 1,
    allowed_models: [],
    allowed_tools: []
  });

  // Global API Key state
  const [newKey, setNewKey] = useState({
    provider: "minimax",
    key_name: "",
    api_key: "",
    base_url: ""
  });
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  // Load Admin status and data
  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      router.push("/login");
      return;
    }

    const fetchMe = async () => {
      try {
        const res = await fetch("/api/auth/me", {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (!res.ok) throw new Error();
        const data = await res.json();
        if (!data.is_superadmin) {
          router.push("/");
          return;
        }
        setMe(data);
        // Charger les données admin
        loadAllData(token);
      } catch (err) {
        localStorage.clear();
        router.push("/login");
      }
    };

    fetchMe();
  }, [router]);

  const loadAllData = async (token: string) => {
    try {
      const h = { Authorization: `Bearer ${token}` };
      
      // Stats
      const resStats = await fetch("/api/admin/stats", { headers: h });
      if (resStats.ok) setStats(await resStats.json());

      // Users
      const resUsers = await fetch("/api/admin/users", { headers: h });
      if (resUsers.ok) setUsers(await resUsers.json());

      // Global API Keys
      const resKeys = await fetch("/api/admin/api-keys", { headers: h });
      if (resKeys.ok) setApiKeys(await resKeys.json());

      // Audit Logs
      const resAudit = await fetch("/api/admin/audit-log", { headers: h });
      if (resAudit.ok) setAuditLogs(await resAudit.json());
    } catch (e) {
      console.error("Failed to load admin dashboard data", e);
    }
  };

  const handleApprove = async (userId: string) => {
    const token = localStorage.getItem("access_token");
    const res = await fetch(`/api/admin/users/${userId}/approve`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      loadAllData(token!);
    }
  };

  const handleDisable = async (userId: string) => {
    const token = localStorage.getItem("access_token");
    const res = await fetch(`/api/admin/users/${userId}/disable`, {
      method: "PATCH",
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      loadAllData(token!);
    }
  };

  // Open Quotas edit modal
  const openQuotaModal = async (user: UserItem) => {
    const token = localStorage.getItem("access_token");
    setSelectedUser(user);
    try {
      const res = await fetch(`/api/admin/users/${user.id}/quota`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data: QuotaDetails = await res.json();
        setQuotaForm({
          max_disk_gb: data.max_disk_bytes / 1073741824,
          max_monthly_tokens_m: data.max_monthly_llm_tokens / 1000000,
          allowed_models: data.allowed_models || [],
          allowed_tools: data.allowed_tools || [],
          notes_admin: data.notes_admin || ""
        });
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSaveQuota = async () => {
    if (!selectedUser) return;
    const token = localStorage.getItem("access_token");

    const payload = {
      max_disk_bytes: Math.floor(quotaForm.max_disk_gb * 1073741824),
      max_monthly_llm_tokens: Math.floor(quotaForm.max_monthly_tokens_m * 1000000),
      allowed_models: quotaForm.allowed_models,
      allowed_tools: quotaForm.allowed_tools,
      notes_admin: quotaForm.notes_admin
    };

    const res = await fetch(`/api/admin/users/${selectedUser.id}/quota`, {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (res.ok) {
      setSelectedUser(null);
      loadAllData(token!);
    }
  };

  const handleAddApiKey = async () => {
    const token = localStorage.getItem("access_token");
    const res = await fetch("/api/admin/api-keys", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(newKey)
    });

    if (res.ok) {
      setNewKey({ provider: "minimax", key_name: "", api_key: "", base_url: "" });
      setTestResult(null);
      loadAllData(token!);
    }
  };

  const handleDeleteApiKey = async (keyId: string) => {
    if (!confirm("Are you sure you want to delete this global key?")) return;
    const token = localStorage.getItem("access_token");
    const res = await fetch(`/api/admin/api-keys/${keyId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` }
    });
    if (res.ok) {
      loadAllData(token!);
    }
  };

  const handleTestKey = async () => {
    setTestResult(null);
    const token = localStorage.getItem("access_token");
    const res = await fetch("/api/admin/api-keys/test", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        provider: newKey.provider,
        base_url: newKey.base_url || undefined,
        api_key: newKey.api_key
      })
    });

    const data = await res.json();
    if (res.ok && data.success) {
      setTestResult({ success: true, message: `Connected! Available models: ${data.models.join(", ")}` });
    } else {
      setTestResult({ success: false, message: `Connection failed: ${data.detail || data.error || "Unknown error"}` });
    }
  };

  if (!me) return <div style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)" }}>Loading Admin Area...</div>;

  return (
    <div style={{ minHeight: "100vh", backgroundColor: "var(--bg-primary)" }}>
      {/* Navbar admin */}
      <header className="glass-panel" style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "16px 40px",
        borderRadius: "0",
        borderTop: "none",
        borderLeft: "none",
        borderRight: "none"
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <h1 style={{ fontSize: "20px", fontWeight: "800", letterSpacing: "1px" }}>AGENTAI SUPERADMIN</h1>
          <span className="badge-superadmin">SYSTEM PANEL</span>
        </div>
        <button onClick={() => router.push("/")} className="btn-secondary" style={{ padding: "8px 16px" }}>
          Return to Workspace
        </button>
      </header>

      <main style={{ padding: "40px", display: "flex", flexDirection: "column", gap: "40px", maxWidth: "1400px", margin: "0 auto" }}>
        
        {/* Stats Section */}
        {stats && (
          <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "24px" }}>
            <div className="glass-card" style={{ padding: "24px" }}>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Total Users</p>
              <h2 style={{ fontSize: "36px", fontWeight: "800", marginTop: "8px" }}>{stats.total_users}</h2>
            </div>
            <div className="glass-card" style={{ padding: "24px" }}>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Active Users</p>
              <h2 style={{ fontSize: "36px", fontWeight: "800", color: "var(--color-success)", marginTop: "8px" }}>{stats.active_users}</h2>
            </div>
            <div className="glass-card" style={{ padding: "24px" }}>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Pending Approval</p>
              <h2 style={{ fontSize: "36px", fontWeight: "800", color: "var(--color-warning)", marginTop: "8px" }}>{stats.pending_users}</h2>
            </div>
            <div className="glass-card" style={{ padding: "24px" }}>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>Global Disk Usage</p>
              <h2 style={{ fontSize: "24px", fontWeight: "800", marginTop: "14px" }}>
                {(stats.total_disk_used_bytes / 1073741824).toFixed(3)} GiB
              </h2>
            </div>
          </section>
        )}

        {/* Dynamic Split Panels */}
        <section style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "40px" }}>
          
          {/* User management panel */}
          <div className="glass-panel" style={{ padding: "32px", display: "flex", flexDirection: "column", gap: "24px" }}>
            <h3 style={{ fontSize: "18px", fontWeight: "700" }}>Users List & Approvals</h3>
            
            <div style={{ display: "flex", flexDirection: "column", gap: "16px", maxHeight: "500px", overflowY: "auto" }}>
              {users.map(u => (
                <div key={u.id} className="glass-card" style={{ padding: "16px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div style={{
                      width: "40px",
                      height: "40px",
                      borderRadius: "50%",
                      backgroundColor: "var(--bg-tertiary)",
                      backgroundImage: u.avatar_url ? `url(${u.avatar_url})` : "none",
                      backgroundSize: "cover",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "14px",
                      fontWeight: "bold"
                    }}>
                      {!u.avatar_url && u.display_name.charAt(0)}
                    </div>
                    <div>
                      <h4 style={{ fontSize: "14px", fontWeight: "600" }}>{u.display_name}</h4>
                      <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>{u.email}</p>
                    </div>
                  </div>

                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    {u.is_active ? (
                      <span className="badge-active">Approved</span>
                    ) : (
                      <span className="badge-pending">Pending</span>
                    )}

                    <div style={{ display: "flex", gap: "8px" }}>
                      {!u.is_active ? (
                        <button onClick={() => handleApprove(u.id)} className="btn-primary" style={{ padding: "6px 12px", fontSize: "12px" }}>
                          Approve
                        </button>
                      ) : (
                        <button onClick={() => handleDisable(u.id)} className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12px", border: "1px solid var(--color-error)", color: "var(--color-error)" }}>
                          Disable
                        </button>
                      )}
                      <button onClick={() => openQuotaModal(u)} className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12px" }}>
                        Quotas
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Global API Key Configuration Panel */}
          <div className="glass-panel" style={{ padding: "32px", display: "flex", flexDirection: "column", gap: "24px" }}>
            <h3 style={{ fontSize: "18px", fontWeight: "700" }}>Global Provider API Keys</h3>

            {/* Add key form */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Provider</label>
                  <select 
                    value={newKey.provider} 
                    onChange={e => setNewKey({ ...newKey, provider: e.target.value })} 
                    className="input-field"
                    style={{ marginTop: "6px" }}
                  >
                    <option value="minimax">MiniMax</option>
                    <option value="opencode_zen">OpenCode Zen</option>
                    <option value="openai">OpenAI</option>
                    <option value="anthropic">Anthropic</option>
                    <option value="google_gemini">Google Gemini</option>
                  </select>
                </div>
                <div>
                  <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Key Name</label>
                  <input 
                    type="text" 
                    placeholder="e.g. Production Key"
                    value={newKey.key_name}
                    onChange={e => setNewKey({ ...newKey, key_name: e.target.value })}
                    className="input-field"
                    style={{ marginTop: "6px" }}
                  />
                </div>
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Base Endpoint URL (Optional)</label>
                <input 
                  type="text" 
                  placeholder="Leave empty for default"
                  value={newKey.base_url}
                  onChange={e => setNewKey({ ...newKey, base_url: e.target.value })}
                  className="input-field"
                  style={{ marginTop: "6px" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Secret API Key</label>
                <input 
                  type="password" 
                  placeholder="sk-..."
                  value={newKey.api_key}
                  onChange={e => setNewKey({ ...newKey, api_key: e.target.value })}
                  className="input-field"
                  style={{ marginTop: "6px" }}
                />
              </div>

              <div style={{ display: "flex", gap: "12px", marginTop: "8px" }}>
                <button onClick={handleTestKey} className="btn-secondary" style={{ flex: 1, justifyContent: "center" }}>
                  Test Connection
                </button>
                <button onClick={handleAddApiKey} className="btn-primary" style={{ flex: 1, justifyContent: "center" }} disabled={!newKey.key_name || !newKey.api_key}>
                  Save API Key
                </button>
              </div>

              {testResult && (
                <div style={{
                  padding: "12px",
                  borderRadius: "var(--radius-sm)",
                  fontSize: "12px",
                  backgroundColor: testResult.success ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
                  color: testResult.success ? "var(--color-success)" : "var(--color-error)",
                  border: `1px solid ${testResult.success ? "rgba(16,185,129,0.2)" : "rgba(239,68,68,0.2)"}`,
                  marginTop: "8px"
                }}>
                  {testResult.message}
                </div>
              )}
            </div>

            {/* List configured keys */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px", maxHeight: "250px", overflowY: "auto", borderTop: "1px solid var(--border-glass)", paddingTop: "16px" }}>
              {apiKeys.map(k => (
                <div key={k.id} className="glass-card" style={{ padding: "12px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <h4 style={{ fontSize: "13px", fontWeight: "600", textTransform: "uppercase" }}>{k.provider}</h4>
                    <p style={{ fontSize: "11px", color: "var(--text-secondary)", marginTop: "2px" }}>{k.key_name}</p>
                  </div>
                  <button onClick={() => handleDeleteApiKey(k.id)} className="btn-secondary" style={{ padding: "4px 8px", fontSize: "11px", color: "var(--color-error)", border: "none" }}>
                    Remove
                  </button>
                </div>
              ))}
            </div>

          </div>
        </section>

        {/* Audit Log Panel */}
        <section className="glass-panel" style={{ padding: "32px" }}>
          <h3 style={{ fontSize: "18px", fontWeight: "700", marginBottom: "24px" }}>System Admin Audit Log</h3>
          <div style={{ maxHeight: "300px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px" }}>
            {auditLogs.map(l => (
              <div key={l.id} style={{ display: "grid", gridTemplateColumns: "180px 140px 1fr", gap: "16px", padding: "10px 16px", borderBottom: "1px solid rgba(255,255,255,0.03)", fontSize: "13px" }}>
                <span style={{ color: "var(--text-muted)" }}>{new Date(l.created_at).toLocaleString()}</span>
                <span style={{ fontWeight: "600", color: "var(--accent-secondary)" }}>{l.action}</span>
                <span style={{ color: "var(--text-secondary)" }}>{JSON.stringify(l.details_json || {})}</span>
              </div>
            ))}
          </div>
        </section>

      </main>

      {/* Quota Modal Overlay */}
      {selectedUser && (
        <div style={{
          position: "fixed",
          inset: 0,
          backgroundColor: "rgba(0,0,0,0.8)",
          backdropFilter: "blur(4px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 1000
        }}>
          <div className="glass-panel" style={{ padding: "32px", width: "100%", maxWidth: "500px", display: "flex", flexDirection: "column", gap: "24px" }}>
            <div>
              <h3 style={{ fontSize: "18px", fontWeight: "700" }}>Configure Quotas</h3>
              <p style={{ fontSize: "13px", color: "var(--text-secondary)", marginTop: "4px" }}>Editing constraints for {selectedUser.display_name}</p>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div>
                <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Max Disk Space (GiB)</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={quotaForm.max_disk_gb} 
                  onChange={e => setQuotaForm({ ...quotaForm, max_disk_gb: parseFloat(e.target.value) })}
                  className="input-field"
                  style={{ marginTop: "6px" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Max Monthly Tokens Budget (Millions)</label>
                <input 
                  type="number" 
                  step="0.1"
                  value={quotaForm.max_monthly_tokens_m} 
                  onChange={e => setQuotaForm({ ...quotaForm, max_monthly_tokens_m: parseFloat(e.target.value) })}
                  className="input-field"
                  style={{ marginTop: "6px" }}
                />
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Allowed Models & Capabilities</label>
                <div style={{ display: "flex", gap: "16px", marginTop: "8px" }}>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
                    <input 
                      type="checkbox"
                      // L'utilisateur peut lier MiniMax et OpenCode Zen.
                      // On passe leurs IDs virtuels en string (que nous lisons du backend dans le routeur /api/models)
                      // Nous utiliserons la logique backend qui cherche si l'id est autorisé.
                      // Pour simplifier l'UI admin de démarrage, nous lions toutes les config.
                    />
                    Authorize MiniMax
                  </label>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px" }}>
                    <input 
                      type="checkbox"
                    />
                    Authorize OpenCode Zen
                  </label>
                </div>
              </div>

              <div>
                <label style={{ fontSize: "12px", color: "var(--text-secondary)" }}>Internal Admin Notes</label>
                <textarea 
                  rows={3}
                  value={quotaForm.notes_admin}
                  onChange={e => setQuotaForm({ ...quotaForm, notes_admin: e.target.value })}
                  className="input-field"
                  style={{ marginTop: "6px", fontFamily: "inherit", resize: "none" }}
                  placeholder="Notes..."
                />
              </div>
            </div>

            <div style={{ display: "flex", gap: "12px" }}>
              <button onClick={() => setSelectedUser(null)} className="btn-secondary" style={{ flex: 1, justifyContent: "center" }}>
                Cancel
              </button>
              <button onClick={handleSaveQuota} className="btn-primary" style={{ flex: 1, justifyContent: "center" }}>
                Save Limits
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
