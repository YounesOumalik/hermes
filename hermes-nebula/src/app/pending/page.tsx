"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import "../globals.css";

function PendingContent() {
  const searchParams = useSearchParams();
  const email = searchParams.get("email") || "your email";

  return (
    <div style={{
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "100vh",
      background: "radial-gradient(circle at top right, rgba(245, 158, 11, 0.1), transparent), radial-gradient(circle at bottom left, rgba(94, 90, 246, 0.05), transparent)"
    }}>
      <div className="glass-panel" style={{
        padding: "48px",
        width: "100%",
        maxWidth: "480px",
        textAlign: "center",
        display: "flex",
        flexDirection: "column",
        gap: "24px"
      }}>
        {/* Icône d'attente animée */}
        <div style={{ display: "flex", justifyContent: "center" }}>
          <div style={{
            width: "64px",
            height: "64px",
            borderRadius: "50%",
            background: "rgba(245, 158, 11, 0.1)",
            border: "2px dashed var(--color-warning)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            animation: "spin 4s linear infinite"
          }}>
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--color-warning)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10"></circle>
              <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          <h1 style={{ fontSize: "24px", fontWeight: "700", color: "#fff" }}>
            Account Pending Approval
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px", lineHeight: "1.6" }}>
            Your account <strong style={{ color: "#fff" }}>{email}</strong> has been successfully registered on AgentAI.
          </p>
          <p style={{ color: "var(--text-muted)", fontSize: "13px", lineHeight: "1.6" }}>
            In order to optimize disk space and resource allocations, accounts require manual approval by the super administrator before accessing LLMs.
          </p>
        </div>

        <div style={{
          height: "1px",
          background: "linear-gradient(to right, transparent, var(--border-glass), transparent)"
        }} />

        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <button 
            onClick={() => window.location.href = "/login"} 
            className="btn-secondary" 
            style={{ justifyContent: "center" }}
          >
            Back to Login
          </button>
        </div>
      </div>

      <style jsx global>{`
        @keyframes spin {
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default function PendingPage() {
  return (
    <Suspense fallback={
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "100vh", backgroundColor: "var(--bg-primary)" }}>
        <p style={{ color: "var(--text-secondary)" }}>Loading...</p>
      </div>
    }>
      <PendingContent />
    </Suspense>
  );
}
