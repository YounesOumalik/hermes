'use client';

import { Activity, ArrowUpRight, Bot, CheckCircle2, CircleDashed, Cpu, GitBranch, MessageSquare, Network, Sparkles, Wrench } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api, Agent, Tool } from './lib/api';

type Health = { status: string; service: string; version: string };
type SettingsStatus = { minimax_configured: boolean; mcp_ready: boolean; model: string };

const quickActions = [
  { href: '/chat', icon: MessageSquare, title: 'Démarrer un chat', text: 'Parler à Hermes et déléguer une tâche.' },
  { href: '/agents', icon: Bot, title: 'Créer un agent', text: 'Construire un assistant spécialisé.' },
  { href: '/tools', icon: Wrench, title: 'Explorer les outils', text: 'Connecter MCP, GitHub et n8n.' },
];

export default function HomePage() {
  const [health, setHealth] = useState<Health | null>(null);
  const [settings, setSettings] = useState<SettingsStatus | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);

  useEffect(() => {
    Promise.all([
      api.get<Health>('health').then(setHealth).catch(() => setHealth(null)),
      api.get<SettingsStatus>('api/settings/status').then(setSettings).catch(() => setSettings(null)),
      api.get<{ agents: Agent[] }>('api/agents').then((data) => setAgents(data.agents)).catch(() => undefined),
      api.get<{ tools: Tool[] }>('api/tools').then((data) => setTools(data.tools)).catch(() => undefined),
    ]);
  }, []);

  const online = Boolean(health);

  return (
    <div className="page dashboard-page">
      <header className="page-header dashboard-header">
        <div>
          <div className="eyebrow"><span className="eyebrow-line" /> HERMES WORKSPACE</div>
          <h1>Bonjour, Younes <span className="wave">✦</span></h1>
          <p className="page-subtitle">Votre centre de commande pour orchestrer des agents, des outils et des automatisations.</p>
        </div>
        <div className="header-actions"><span className="live-pill"><span className="status-dot online" /> Live</span><a className="button button-primary" href="/chat"><MessageSquare size={16} /> Ouvrir le chat</a></div>
      </header>

      <section className="hero-panel">
        <div className="hero-glow" />
        <div className="hero-copy">
          <div className="hero-kicker"><Sparkles size={15} /> Intelligence orchestrée</div>
          <h2>Une idée. Plusieurs agents.<br /><span>Un résultat qui avance.</span></h2>
          <p>Connectez vos modèles, donnez-leur les bons outils et laissez Hermes faire circuler le contexte au bon endroit.</p>
          <a className="button button-light" href="/chat">Commencer une conversation <ArrowUpRight size={16} /></a>
        </div>
        <div className="orbital-art" aria-hidden="true"><div className="orbit orbit-one" /><div className="orbit orbit-two" /><div className="orb-core"><Sparkles size={28} /></div><span className="orbit-node node-one"><Cpu size={15} /></span><span className="orbit-node node-two"><GitBranch size={15} /></span><span className="orbit-node node-three"><Network size={15} /></span></div>
      </section>

      <section className="section-heading"><div><div className="eyebrow">ACCÈS RAPIDE</div><h2>Construire avec Hermes</h2></div><a className="text-link" href="/settings">Gérer le workspace <ArrowUpRight size={14} /></a></section>
      <section className="quick-grid">
        {quickActions.map(({ href, icon: Icon, title, text }) => <a className="quick-card" href={href} key={href}><span className="quick-icon"><Icon size={19} /></span><span><strong>{title}</strong><small>{text}</small></span><ArrowUpRight size={16} className="quick-arrow" /></a>)}
      </section>

      <section className="overview-grid">
        <div className="panel health-panel"><div className="panel-heading"><div><div className="eyebrow">OBSERVABILITÉ</div><h3>Santé du workspace</h3></div><Activity size={18} className="muted-icon" /></div><div className="health-list"><HealthRow label="Hermes Daemon" detail={online ? 'API connectée' : 'Indisponible'} ok={online} /><HealthRow label="Minimax" detail={settings?.minimax_configured ? settings.model : 'Clé à configurer'} ok={Boolean(settings?.minimax_configured)} /><HealthRow label="MCP Server" detail={settings?.mcp_ready ? 'Prêt à recevoir des outils' : 'À vérifier'} ok={Boolean(settings?.mcp_ready)} /><HealthRow label="n8n" detail="Workflow engine" ok={online} /></div><a href="/settings" className="panel-link">Voir la configuration <ArrowUpRight size={14} /></a></div>
        <div className="panel stats-panel"><div className="panel-heading"><div><div className="eyebrow">VOTRE ESPACE</div><h3>En un coup d’œil</h3></div><CircleDashed size={18} className="muted-icon" /></div><div className="stat-row"><Stat label="Agents actifs" value={String(agents.length).padStart(2, '0')} icon={Bot} /><Stat label="Outils connectés" value={String(tools.length).padStart(2, '0')} icon={Wrench} /></div><div className="mini-chart"><span style={{ height: '35%' }} /><span style={{ height: '52%' }} /><span style={{ height: '45%' }} /><span style={{ height: '70%' }} /><span style={{ height: '58%' }} /><span style={{ height: '88%' }} /><span style={{ height: '78%' }} /><span style={{ height: '100%' }} /></div><small className="chart-caption">Activité récente · 7 derniers jours</small></div>
      </section>
    </div>
  );
}

function HealthRow({ label, detail, ok }: { label: string; detail: string; ok: boolean }) { return <div className="health-row"><span className={`health-icon ${ok ? 'ok' : 'pending'}`}>{ok ? <CheckCircle2 size={15} /> : <CircleDashed size={15} />}</span><span><strong>{label}</strong><small>{detail}</small></span><span className={`health-label ${ok ? 'text-success' : 'text-pending'}`}>{ok ? 'Opérationnel' : 'À configurer'}</span></div>; }
function Stat({ label, value, icon: Icon }: { label: string; value: string; icon: typeof Bot }) { return <div className="stat"><span className="stat-icon"><Icon size={16} /></span><div><strong>{value}</strong><small>{label}</small></div></div>; }
