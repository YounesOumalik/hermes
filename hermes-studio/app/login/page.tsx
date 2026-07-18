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
      const response = await fetch('/api/auth/login', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' }, 
        body: JSON.stringify({ username, password }) 
      });
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
    <main className="login-container">
      <div className="login-background-glow" />
      <section className="login-glass" aria-labelledby="login-title">
        <div className="login-brand">
          <span className="brand-mark"><Sparkles size={24} /></span>
          <span className="brand-text">Hermes</span>
        </div>
        
        <div className="login-heading">
          <h1 id="login-title">Content de vous revoir</h1>
          <p className="login-intro">Connectez-vous pour accéder à votre espace de travail.</p>
        </div>
        
        {error && <div className="alert alert-error" role="alert">{error}</div>}
        
        <form className="login-form" onSubmit={submit}>
          <label>
            Identifiant
            <input 
              autoFocus 
              required 
              autoComplete="username" 
              value={username} 
              onChange={(event) => setUsername(event.target.value)} 
              placeholder="Entrez votre identifiant"
            />
          </label>
          <label>
            Mot de passe
            <input 
              required 
              type="password" 
              autoComplete="current-password" 
              value={password} 
              onChange={(event) => setPassword(event.target.value)} 
              placeholder="Entrez votre mot de passe"
            />
          </label>
          <button className="button button-primary login-submit" type="submit" disabled={loading}>
            {loading ? 'Connexion en cours…' : 'Se connecter'} 
            {!loading && <ArrowRight size={16} />}
          </button>
        </form>
        <div className="login-footer">
          <LockKeyhole size={12} className="text-muted" /> 
          <span>Connexion sécurisée</span>
        </div>
      </section>
    </main>
  );
}
