'use client';

import { FormEvent, useEffect, useState } from 'react';
import { ArrowRight, Fingerprint, LockKeyhole, ScanLine, ShieldCheck, Sparkles, Zap } from 'lucide-react';

function getSafeNext() {
  if (typeof window === 'undefined') return '/';
  const next = new URLSearchParams(window.location.search).get('next');
  return next && next.startsWith('/') && !next.startsWith('//') ? next : '/';
}

export default function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [scanning, setScanning] = useState(true);
  const [authStep, setAuthStep] = useState<'idle' | 'handshake' | 'authenticate' | 'success'>('idle');
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const timer = window.setTimeout(() => setScanning(false), 1600);
    return () => window.clearTimeout(timer);
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setLoading(true);
    setAuthStep('handshake');
    setProgress(15);

    try {
      await new Promise((r) => window.setTimeout(r, 350));
      setProgress(45);
      setAuthStep('authenticate');

      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      setProgress(85);

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || 'Identifiants rejetés');
      }

      setProgress(100);
      setAuthStep('success');
      await new Promise((r) => window.setTimeout(r, 450));
      window.location.assign(getSafeNext());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Connexion impossible');
      setLoading(false);
      setAuthStep('idle');
      setProgress(0);
    }
  }

  const statusLabel =
    authStep === 'handshake' ? 'Établissement du canal sécurisé…'
    : authStep === 'authenticate' ? 'Vérification des identifiants…'
    : authStep === 'success' ? 'Authentification validée'
    : null;

  return (
    <main className="login-hud">
      {/* Background animé */}
      <div className="login-bg">
        <div className="login-grid" />
        <div className="login-scanlines" />
        <div className="login-orb login-orb-1" />
        <div className="login-orb login-orb-2" />
        <div className="login-orb login-orb-3" />
        <div className="login-noise" />
      </div>

      {/* HUD périphérique */}
      <div className="login-corner login-corner-tl">
        <span className="login-corner-dot" />
        <span className="login-corner-text">SYS · HERMES-V3 · 2026</span>
      </div>
      <div className="login-corner login-corner-tr">
        <span className="login-corner-dot login-corner-dot-pulse" />
        <span className="login-corner-text">SECURE CHANNEL · TLS 1.3</span>
      </div>
      <div className="login-corner login-corner-bl">
        <span className="login-corner-text">NODE prod-01 · 169.58.30.70</span>
      </div>
      <div className="login-corner login-corner-br">
        <span className="login-corner-text">UPTIME 32d 14h 09m</span>
      </div>

      <section className={`login-panel ${scanning ? 'is-scanning' : ''}`} aria-labelledby="login-title">
        <div className="login-panel-border" aria-hidden="true" />

        <header className="login-panel-header">
          <div className="login-brand">
            <div className="login-brand-mark">
              <Sparkles size={20} strokeWidth={2.4} />
              <div className="login-brand-pulse" />
            </div>
            <div className="login-brand-text">
              <span className="login-brand-name">HERMES</span>
              <span className="login-brand-sub">STUDIO · MULTI-AGENT ORCHESTRATOR</span>
            </div>
          </div>
          <div className="login-status">
            <ShieldCheck size={14} />
            <span>ENCRYPTED</span>
          </div>
        </header>

        <div className="login-panel-intro">
          <h1 id="login-title">
            <span className="login-title-line">Authentification</span>
            <span className="login-title-line login-title-dim">requise.</span>
          </h1>
          <p className="login-intro">
            Présentez vos identifiants pour accéder à votre espace d'orchestration agentique.
          </p>
        </div>

        {error && (
          <div className="login-alert" role="alert">
            <Zap size={14} />
            <span>{error}</span>
          </div>
        )}

        <form className="login-form" onSubmit={submit} noValidate>
          <div className="login-field">
            <label htmlFor="username">
              <Fingerprint size={13} />
              <span>Identifiant</span>
            </label>
            <div className="login-input-wrap">
              <input
                id="username"
                autoFocus
                required
                autoComplete="username"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="operator"
                spellCheck={false}
                disabled={loading}
              />
              <span className="login-input-bar" />
            </div>
          </div>

          <div className="login-field">
            <label htmlFor="password">
              <LockKeyhole size={13} />
              <span>Clé d'accès</span>
            </label>
            <div className="login-input-wrap">
              <input
                id="password"
                required
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="••••••••••••"
                disabled={loading}
              />
              <span className="login-input-bar" />
            </div>
          </div>

          <button
            type="submit"
            className={`login-submit ${authStep !== 'idle' ? 'is-active' : ''} ${authStep === 'success' ? 'is-success' : ''}`}
            disabled={loading}
            aria-busy={loading}
          >
            <span className="login-submit-bg" aria-hidden="true" />
            <span className="login-submit-content">
              {authStep === 'success' ? (
                <>
                  <ShieldCheck size={16} />
                  <span>Accès autorisé</span>
                </>
              ) : loading ? (
                <>
                  <ScanLine size={16} className="login-submit-icon-spin" />
                  <span>Authentification…</span>
                </>
              ) : (
                <>
                  <span>Initier la session</span>
                  <ArrowRight size={16} />
                </>
              )}
            </span>
            {loading && (
              <span
                className="login-submit-progress"
                style={{ width: `${progress}%` }}
                aria-hidden="true"
              />
            )}
          </button>
        </form>

        <footer className="login-panel-footer">
          <div className="login-footer-row">
            <span className="login-footer-item">
              <span className="login-footer-dot" />
              JWT-HS256
            </span>
            <span className="login-footer-item">
              <span className="login-footer-dot login-footer-dot-amber" />
              SESSION 8H
            </span>
            <span className="login-footer-item">
              <span className="login-footer-dot login-footer-dot-cyan" />
              HTTPONLY
            </span>
          </div>
          {statusLabel && (
            <div className="login-footer-status" aria-live="polite">
              <span className="login-footer-status-dot" />
              {statusLabel}
            </div>
          )}
        </footer>
      </section>
    </main>
  );
}