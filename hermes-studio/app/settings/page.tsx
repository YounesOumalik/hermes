'use client';

import { CheckCircle2, ExternalLink, KeyRound, RefreshCw, Save, ShieldCheck, TestTube2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api } from '../lib/api';

type Status = {
  minimax_configured: boolean;
  telegram_configured: boolean;
  telegram_chat_configured: boolean;
  telegram_running: boolean;
  telegram_bot_username?: string | null;
  telegram_last_error?: string | null;
  github_configured: boolean;
  model: string;
  minimax_base_url: string;
  mcp_ready: boolean;
};

type TelegramTest = {
  bot_username?: string | null;
  webhook_configured: boolean;
  pending_updates: number;
  allowed_chat_configured: boolean;
};

export default function SettingsPage() {
  const [status, setStatus] = useState<Status | null>(null);
  const [minimaxKey, setMinimaxKey] = useState('');
  const [minimaxBaseUrl, setMinimaxBaseUrl] = useState('');
  const [minimaxModel, setMinimaxModel] = useState('');
  const [telegramToken, setTelegramToken] = useState('');
  const [allowedChatId, setAllowedChatId] = useState('');
  const [githubToken, setGithubToken] = useState('');
  const [message, setMessage] = useState('');
  const [messageKind, setMessageKind] = useState<'success' | 'error'>('success');
  const [saving, setSaving] = useState(false);
  const [testingMinimax, setTestingMinimax] = useState(false);
  const [testingTelegram, setTestingTelegram] = useState(false);

  async function loadStatus() {
    try {
      const nextStatus = await api.get<Status>('api/settings/status');
      setStatus(nextStatus);
      setMinimaxBaseUrl((current) => current || nextStatus.minimax_base_url);
      setMinimaxModel((current) => current || nextStatus.model);
    } catch (error) {
      setMessageKind('error');
      setMessage(error instanceof Error ? error.message : 'Impossible de charger la configuration.');
    }
  }

  useEffect(() => { void loadStatus(); }, []);

  async function saveKeys() {
    setSaving(true);
    setMessage('');
    try {
      const body: Record<string, string> = {};
      if (minimaxKey) body.minimax_api_key = minimaxKey;
      if (minimaxBaseUrl) body.minimax_base_url = minimaxBaseUrl;
      if (minimaxModel) body.minimax_model = minimaxModel;
      if (telegramToken) body.telegram_bot_token = telegramToken;
      if (allowedChatId) body.allowed_chat_id = allowedChatId;
      if (githubToken) body.github_token = githubToken;
      await api.post('api/settings/update', body);
      setMinimaxKey('');
      setTelegramToken('');
      setAllowedChatId('');
      setGithubToken('');
      setMessageKind('success');
      setMessage('Paramètres enregistrés. Telegram détecte les nouveaux réglages en moins de 30 secondes.');
      await loadStatus();
    } catch (error) {
      setMessageKind('error');
      setMessage(error instanceof Error ? error.message : 'Enregistrement impossible.');
    } finally {
      setSaving(false);
    }
  }

  async function testMinimax() {
    setTestingMinimax(true);
    setMessage('Test MiniMax en cours…');
    try {
      const response = await api.post<{ code: number; model: string }>('api/settings/test/minimax', {});
      setMessageKind('success');
      setMessage(`MiniMax répond correctement avec ${response.model} (HTTP ${response.code}).`);
    } catch (error) {
      setMessageKind('error');
      setMessage(error instanceof Error ? error.message : 'Test impossible.');
    } finally {
      setTestingMinimax(false);
    }
  }

  async function testTelegram() {
    setTestingTelegram(true);
    setMessage('Test Telegram en cours…');
    try {
      const response = await api.post<TelegramTest>('api/settings/test/telegram', {});
      const botName = response.bot_username ? `@${response.bot_username}` : 'Le bot Telegram';
      if (response.webhook_configured) {
        setMessageKind('error');
        setMessage(`${botName} est valide, mais un webhook externe bloque le polling Hermes.`);
      } else if (!response.allowed_chat_configured) {
        setMessageKind('success');
        setMessage(`${botName} est valide. Envoyez-lui un message : il vous donnera votre Chat ID à autoriser ci-dessous.`);
      } else {
        setMessageKind('success');
        setMessage(`${botName} est prêt et le chat autorisé est configuré (${response.pending_updates} message(s) en attente).`);
      }
      await loadStatus();
    } catch (error) {
      setMessageKind('error');
      setMessage(error instanceof Error ? error.message : 'Test Telegram impossible.');
    } finally {
      setTestingTelegram(false);
    }
  }

  const telegramValue = status?.telegram_running
    ? status.telegram_bot_username ? `@${status.telegram_bot_username}` : 'Bot actif'
    : status?.telegram_configured ? 'À autoriser' : 'À configurer';
  const telegramMeta = status?.telegram_last_error || (status?.telegram_chat_configured ? 'Chat privé autorisé' : 'Ajoutez un Chat ID pour répondre');

  return <div className="page">
    <header className="page-header"><div><div className="eyebrow"><span className="eyebrow-line" /> WORKSPACE</div><h1>Configuration</h1><p className="page-subtitle">Connectez les services qui donnent de la profondeur à Hermes.</p></div><button className="ghost-button" onClick={() => void loadStatus()}><RefreshCw size={15} /> Actualiser</button></header>
    <section className="settings-status-grid"><StatusCard label="MiniMax" value={status?.minimax_configured ? 'Clé présente' : 'À configurer'} ok={Boolean(status?.minimax_configured)} meta={status?.minimax_configured ? 'Testez la clé avant utilisation' : 'Ajoutez une clé API'} /><StatusCard label="Telegram" value={telegramValue} ok={Boolean(status?.telegram_running)} meta={telegramMeta} /><StatusCard label="MCP Server" value={status?.mcp_ready ? 'Prêt' : 'À vérifier'} ok={Boolean(status?.mcp_ready)} meta="Outils et contexte" /><StatusCard label="Sécurité" value="Serveur privé" ok meta="Clés jamais renvoyées" /></section>
    <div className="settings-layout"><section className="panel settings-panel"><div className="panel-heading"><div><div className="eyebrow">SECRETS SERVEUR</div><h2>Clés & intégrations</h2></div><span className="secure-badge"><ShieldCheck size={14} /> Accès restreint</span></div><p className="panel-intro">Les secrets restent côté serveur. Une clé ou un modèle enregistré ici est utilisé immédiatement par Hermes, sans redémarrage.</p><KeyField label="MiniMax API Key" value={minimaxKey} onChange={setMinimaxKey} placeholder={status?.minimax_configured ? 'Clé déjà configurée · saisir pour remplacer' : 'Clé créée dans MiniMax Platform'} /><TextField label="MiniMax Base URL" value={minimaxBaseUrl} onChange={setMinimaxBaseUrl} placeholder="https://api.minimax.io/v1" /><TextField label="MiniMax Model" value={minimaxModel} onChange={setMinimaxModel} placeholder="MiniMax-M2.7" /><KeyField label="Telegram Bot Token" value={telegramToken} onChange={setTelegramToken} placeholder={status?.telegram_configured ? 'Token déjà configuré · saisir pour remplacer' : '123456:ABC-DEF…'} /><TextField label="Telegram Chat ID autorisé" value={allowedChatId} onChange={setAllowedChatId} placeholder={status?.telegram_chat_configured ? 'Un chat est déjà autorisé · saisir pour remplacer' : 'Envoyez un message au bot pour recevoir votre ID'} /><small className="field-help">Seul ce chat peut demander des réponses à Hermes. Sans cet ID, le bot vous le communique mais ne consomme pas MiniMax.</small><KeyField label="GitHub Token" value={githubToken} onChange={setGithubToken} placeholder={status?.github_configured ? 'Token déjà configuré · saisir pour remplacer' : 'ghp_…'} /><div className="form-actions"><button className="button button-primary" onClick={() => void saveKeys()} disabled={saving}><Save size={15} /> {saving ? 'Enregistrement…' : 'Enregistrer les changements'}</button><button className="button button-secondary" onClick={() => void testMinimax()} disabled={testingMinimax || !status?.minimax_configured}><TestTube2 size={15} /> {testingMinimax ? 'Test…' : 'Tester MiniMax'}</button><button className="button button-secondary" onClick={() => void testTelegram()} disabled={testingTelegram || !status?.telegram_configured}><TestTube2 size={15} /> {testingTelegram ? 'Test…' : 'Tester Telegram'}</button></div>{message && <div className={`form-message ${messageKind === 'error' ? 'form-error' : ''}`}><CheckCircle2 size={15} /> {message}</div>}</section><aside className="settings-side"><div className="panel"><div className="panel-heading"><div><div className="eyebrow">GUIDES</div><h3>Obtenir vos clés</h3></div><KeyRound size={18} className="muted-icon" /></div><a className="resource-link" href="https://platform.minimax.io/" target="_blank" rel="noreferrer"><span>MiniMax Platform</span><ExternalLink size={14} /></a><a className="resource-link" href="https://t.me/BotFather" target="_blank" rel="noreferrer"><span>Telegram BotFather</span><ExternalLink size={14} /></a><a className="resource-link" href="https://github.com/settings/tokens/new" target="_blank" rel="noreferrer"><span>GitHub Developer Settings</span><ExternalLink size={14} /></a></div><div className="panel privacy-panel"><ShieldCheck size={20} /><strong>Activer Telegram en sécurité</strong><p>Enregistrez le token, envoyez un message au bot pour recevoir votre Chat ID, puis collez cet ID ici. Le bot répond alors uniquement à votre chat.</p></div></aside></div>
  </div>;
}

function StatusCard({ label, value, meta, ok }: { label: string; value: string; meta: string; ok: boolean }) { return <div className="status-card"><span className={`status-card-icon ${ok ? 'success' : 'pending'}`}>{ok ? <CheckCircle2 size={18} /> : <KeyRound size={18} />}</span><span><small>{label}</small><strong>{value}</strong><em>{meta}</em></span></div>; }
function KeyField({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder: string }) { return <label className="key-field"><span>{label}</span><input type="password" value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} autoComplete="new-password" /></label>; }
function TextField({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder: string }) { return <label className="key-field"><span>{label}</span><input type="text" value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} autoComplete="off" /></label>; }
