'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';

const DAEMON_URL = process.env.NEXT_PUBLIC_DAEMON_URL || 'http://localhost:8001';

export default function SettingsPage() {
  const [minimaxKey, setMinimaxKey] = useState('');
  const [telegramToken, setTelegramToken] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');

  useEffect(() => {
    fetchStatus();
  }, []);

  const fetchStatus = async () => {
    try {
      const resp = await axios.get(`${DAEMON_URL}/api/settings/status`);
      setStatus(resp.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const saveKeys = async () => {
    setSaving(true);
    setMessage('');
    try {
      const body: any = {};
      if (minimaxKey) body.minimax_api_key = minimaxKey;
      if (telegramToken) body.telegram_bot_token = telegramToken;
      if (githubToken) body.github_token = githubToken;

      const resp = await axios.post(`${DAEMON_URL}/api/settings/update`, body);
      setMessage(`✅ ${resp.data.message}`);
      setMinimaxKey('');
      setTelegramToken('');
      setGithubToken('');
      fetchStatus();
    } catch (err: any) {
      setMessage(`❌ Erreur: ${err.response?.data?.detail || String(err)}`);
    } finally {
      setSaving(false);
    }
  };

  const testMinimax = async () => {
    setMessage('Test en cours…');
    try {
      const resp = await axios.post(`${DAEMON_URL}/api/settings/test/minimax`);
      setMessage(`✅ Minimax OK (HTTP ${resp.data.code})`);
    } catch (err: any) {
      setMessage(`❌ ${err.response?.data?.detail || String(err)}`);
    }
  };

  return (
    <div>
      <h1>Settings</h1>

      {loading && <p style={{ color: 'var(--muted)' }}>Chargement…</p>}

      {status && (
        <div className="card">
          <h2>État actuel</h2>
          <table style={{ width: '100%' }}>
            <tbody>
              <tr>
                <td>Minimax ({status.model})</td>
                <td>{status.minimax_configured ? '🟢 Configurée' : '🔴 Manquante'}</td>
              </tr>
              <tr>
                <td>Telegram Bot</td>
                <td>{status.telegram_configured ? '🟢 Configuré' : '🔴 Manquant'}</td>
              </tr>
              <tr>
                <td>GitHub Token</td>
                <td>{status.github_configured ? '🟢 Configuré' : '🔴 Manquant'}</td>
              </tr>
            </tbody>
          </table>
          <div style={{ marginTop: '1rem' }}>
            <button className="btn btn-secondary" onClick={fetchStatus}>🔄 Rafraîchir</button>
            {status.minimax_configured && (
              <button className="btn btn-secondary" onClick={testMinimax} style={{ marginLeft: '0.5rem' }}>
                🧪 Tester Minimax
              </button>
            )}
          </div>
        </div>
      )}

      <div className="card">
        <h2>Ajouter / remplacer une clé</h2>
        <p style={{ color: 'var(--muted)', marginBottom: '1rem' }}>
          Les clés sont stockées côté serveur (volume Docker persistant <code>/data/hermes.env</code>).
          Aucune clé n'est jamais renvoyée au frontend.
        </p>

        <label>Minimax API Key</label>
        <input
          type="password"
          value={minimaxKey}
          onChange={(e) => setMinimaxKey(e.target.value)}
          placeholder="MiniMax-xxx…"
          style={{ marginBottom: '1rem' }}
        />

        <label>Telegram Bot Token</label>
        <input
          type="password"
          value={telegramToken}
          onChange={(e) => setTelegramToken(e.target.value)}
          placeholder="123456:ABC-DEF…"
          style={{ marginBottom: '1rem' }}
        />

        <label>GitHub Token</label>
        <input
          type="password"
          value={githubToken}
          onChange={(e) => setGithubToken(e.target.value)}
          placeholder="ghp_xxx…"
          style={{ marginBottom: '1rem' }}
        />

        <button className="btn" onClick={saveKeys} disabled={saving}>
          {saving ? 'Sauvegarde…' : '💾 Sauvegarder côté serveur'}
        </button>

        {message && (
          <p style={{ marginTop: '1rem', padding: '0.5rem', background: 'var(--bg)', borderRadius: '6px' }}>
            {message}
          </p>
        )}
      </div>

      <div className="card">
        <h2>Comment obtenir les clés</h2>
        <ul>
          <li><strong>Minimax</strong> : <a href="https://platform.minimax.chat/" target="_blank" rel="noreferrer">platform.minimax.chat</a></li>
          <li><strong>Telegram</strong> : parle à <a href="https://t.me/BotFather" target="_blank" rel="noreferrer">@BotFather</a> sur Telegram</li>
          <li><strong>GitHub</strong> : <a href="https://github.com/settings/tokens/new" target="_blank" rel="noreferrer">github.com/settings/tokens/new</a> (cocher <code>repo</code>)</li>
        </ul>
      </div>
    </div>
  );
}

        <h2>Note de sécurité</h2>
        <p style={{ color: 'var(--muted)' }}>
          Les clés API doivent être stockées côté serveur (Hermes Daemon) et
          injectées via variables d'environnement. Ne les exposez jamais côté client.
        </p>
      </div>
    </div>
  );
}
