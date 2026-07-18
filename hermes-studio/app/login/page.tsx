'use client';

import { FormEvent, useState } from 'react';
import { ArrowRight, LockKeyhole, Sparkles } from 'lucide-react';

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

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const response = await fetch('/api/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username, password }) });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail || 'Connexion impossible');
      }
      window.location.assign(getSafeNext());
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Connexion impossible');
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-glow login-glow-one" />
      <div className="login-glow login-glow-two" />
      <section className="login-card" aria-labelledby="login-title">
        <div className="login-brand"><span className="brand-mark"><Sparkles size={18} /></span><span>Hermes<span className="brand-soft"> Workspace</span></span></div>
        <div className="login-heading"><span className="login-lock"><LockKeyhole size={19} /></span><div><div className="eyebrow">ESPACE PRIVÉ</div><h1 id="login-title">Bon retour.</h1></div></div>
        <p className="login-intro">Connectez-vous pour accéder à vos agents, outils et conversations.</p>
        {error && <div className="alert" role="alert">{error}</div>}
        <form className="login-form" onSubmit={submit}>
          <label>Identifiant<input autoFocus required autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} /></label>
          <label>Mot de passe<input required type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <button className="button button-primary login-submit" type="submit" disabled={loading}>{loading ? 'Connexion…' : 'Se connecter'} {!loading && <ArrowRight size={16} />}</button>
        </form>
        <div className="login-footer"><span className="status-dot online" /> Connexion chiffrée · Session privée</div>
      </section>
    </main>
  );
}
