'use client';

import { useState } from 'react';

export default function SettingsPage() {
  const [minimaxKey, setMinimaxKey] = useState('');
  const [telegramToken, setTelegramToken] = useState('');
  const [githubToken, setGithubToken] = useState('');

  const saveSettings = () => {
    // En production, ceci devrait être envoyé au backend de manière sécurisée
    // Pour l'instant, on stocke dans localStorage (à remplacer par API backend)
    localStorage.setItem('MINIMAX_API_KEY', minimaxKey);
    localStorage.setItem('TELEGRAM_BOT_TOKEN', telegramToken);
    localStorage.setItem('GITHUB_TOKEN', githubToken);
    alert('Paramètres sauvegardés localement (à synchroniser avec le backend)');
  };

  return (
    <div>
      <h1>Settings</h1>
      <div className="card">
        <h2>Clés API</h2>
        <label>Minimax API Key</label>
        <input
          type="password"
          value={minimaxKey}
          onChange={(e) => setMinimaxKey(e.target.value)}
          placeholder="MiniMax-xxx"
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
          placeholder="ghp_xxx"
          style={{ marginBottom: '1rem' }}
        />
        <button className="btn" onClick={saveSettings}>Sauvegarder</button>
      </div>
      <div className="card">
        <h2>Note de sécurité</h2>
        <p style={{ color: 'var(--muted)' }}>
          Les clés API doivent être stockées côté serveur (Hermes Daemon) et
          injectées via variables d'environnement. Ne les exposez jamais côté client.
        </p>
      </div>
    </div>
  );
}
