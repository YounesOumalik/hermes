"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import "../globals.css";
import { setTokens } from "@/lib/api";
import { useAuth } from "@/stores/authStore";
import { Spinner } from "@/components/ui";

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fetchUser = useAuth((s) => s.fetchUser);
  const [isCompletingLogin, setIsCompletingLogin] = useState(false);
  const [devLoginError, setDevLoginError] = useState<string | null>(null);

  // OAuth callback: tokens arrivent en query params (?token=...&refresh_token=...)
  useEffect(() => {
    const token = searchParams.get("token");
    const refreshToken = searchParams.get("refresh_token");

    if (token && refreshToken) {
      setIsCompletingLogin(true);
      setTokens(token, refreshToken);
      // Charger le profil avant la redirection pour que authStore soit hydraté
      fetchUser()
        .then(() => router.push("/"))
        .catch(() => {
          setIsCompletingLogin(false);
          setDevLoginError("OAuth callback failed: cannot load user profile.");
        });
    }
  }, [searchParams, router, fetchUser]);

  const handleGoogleLogin = () => {
    // URL relative : hérite automatiquement du domaine courant (agentai.smartefp.com)
    window.location.href = `/api/auth/google`;
  };

  const handleDevLogin = async (email: string) => {
    setDevLoginError(null);
    setIsCompletingLogin(true);
    try {
      const res = await fetch(`/api/auth/dev-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Erreur" }));
        throw new Error(err.detail || res.statusText);
      }
      const data = await res.json();
      setTokens(data.access_token, data.refresh_token);
      await fetchUser();
      router.push("/");
    } catch (e) {
      setIsCompletingLogin(false);
      setDevLoginError(e instanceof Error ? e.message : "Dev login failed");
    }
  };

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "100vh",
      background: "radial-gradient(circle at top right, rgba(94, 90, 246, 0.15), transparent), radial-gradient(circle at bottom left, rgba(0, 210, 255, 0.1), transparent)"
    }}>
      <div className="glass-panel" style={{
        padding: "48px",
        width: "100%",
        maxWidth: "420px",
        textAlign: "center",
        display: "flex",
        flexDirection: "column",
        gap: "24px"
      }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <h1 style={{
            fontSize: "32px",
            fontWeight: "800",
            background: "linear-gradient(135deg, #fff 0%, #94a3b8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent"
          }}>
            AgentAI
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
            The autonomous workspace for multi-agent workflows.
          </p>
        </div>

        <div style={{
          height: "1px",
          background: "linear-gradient(to right, transparent, var(--border-glass), transparent)",
          margin: "8px 0"
        }} />

        <button 
          onClick={handleGoogleLogin} 
          className="btn-primary" 
          style={{
            justifyContent: "center",
            padding: "14px",
            fontSize: "15px",
            background: "#fff",
            color: "#1e293b",
            boxShadow: "0 4px 15px rgba(255,255,255,0.1)"
          }}
        >
          {/* Logo Google SVG */}
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
          </svg>
          Continue with Google
        </button>

        <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "8px" }}>
          Authorized by Google OAuth 2.0. By signing in, you agree to our Terms of Service.
        </p>

        {devLoginError && (
          <div
            role="alert"
            style={{
              marginTop: "8px",
              padding: "10px 12px",
              background: "rgba(239, 68, 68, 0.1)",
              border: "1px solid rgba(239, 68, 68, 0.3)",
              borderRadius: "8px",
              color: "var(--color-error)",
              fontSize: "13px",
            }}
          >
            {devLoginError}
          </div>
        )}

        {/* Dev Login (visible uniquement en mode dev) */}
        {process.env.NODE_ENV !== "production" && (
          <div style={{
            marginTop: "24px",
            paddingTop: "24px",
            borderTop: "1px solid var(--border-glass)",
            display: "flex",
            flexDirection: "column",
            gap: "8px"
          }}>
            <p style={{ fontSize: "11px", color: "var(--warning, #f59e0b)", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: "600" }}>
              ⚠ Dev Mode — bypass Google
            </p>
            <div style={{ display: "flex", gap: "8px" }}>
              <button
                onClick={() => handleDevLogin("younesoumalik@gmail.com")}
                disabled={isCompletingLogin}
                style={{
                  flex: 1,
                  padding: "10px",
                  background: "rgba(245, 158, 11, 0.1)",
                  border: "1px solid rgba(245, 158, 11, 0.3)",
                  borderRadius: "8px",
                  color: "#f59e0b",
                  cursor: isCompletingLogin ? "not-allowed" : "pointer",
                  fontSize: "13px",
                  opacity: isCompletingLogin ? 0.5 : 1,
                }}
              >
                🔑 Login Younes (Admin)
              </button>
              <button
                onClick={() => handleDevLogin("younes@eaumalik.com")}
                disabled={isCompletingLogin}
                style={{
                  flex: 1,
                  padding: "10px",
                  background: "rgba(99, 102, 241, 0.1)",
                  border: "1px solid rgba(99, 102, 241, 0.3)",
                  borderRadius: "8px",
                  color: "#818cf8",
                  cursor: isCompletingLogin ? "not-allowed" : "pointer",
                  fontSize: "13px",
                  opacity: isCompletingLogin ? 0.5 : 1,
                }}
              >
                🔑 Login Younes@eaumalik
              </button>
            </div>
          </div>
        )}
      </div>

      {isCompletingLogin && (
        <Spinner fullscreen label="Signing you in..." />
      )}
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", backgroundColor: "var(--bg-primary)" }}>
        <p style={{ color: "var(--text-secondary)" }}>Loading session...</p>
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}
