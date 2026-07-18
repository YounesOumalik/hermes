'use client';

import { ArrowUpRight, Bot, Check, Code2, MessageSquare, Plus, Save, Sparkles, Trash2, Wrench, X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Agent, api } from '../lib/api';

const presets = [
  { name: 'Architecte produit', description: 'Structure les idées, clarifie les besoins et propose une feuille de route.', color: 'violet' },
  { name: 'DevOps Sentinel', description: 'Inspecte les déploiements, les logs et les incidents avec méthode.', color: 'cyan' },
  { name: 'Researcher', description: 'Explore GitHub et transforme les sources en décisions actionnables.', color: 'amber' },
];

export default function AgentsPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [name, setName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function loadAgents() {
    try {
      const data = await api.get<{ agents: Agent[] }>('api/agents');
      setAgents(data.agents || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger les agents.');
    }
  }

  useEffect(() => { void loadAgents(); }, []);

  async function createAgent() {
    if (!name.trim()) return;
    setSaving(true);
    setError('');
    try {
      await api.post<Agent>('api/agents', { name: name.trim(), system_prompt: systemPrompt.trim() || 'Tu es un assistant précis et utile.', model: null, tools: [] });
      setName('');
      setSystemPrompt('');
      setOpen(false);
      await loadAgents();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Création impossible.');
    } finally {
      setSaving(false);
    }
  }

  async function deleteAgent(agentName: string) {
    try {
      await api.delete(`api/agents/${encodeURIComponent(agentName)}`);
      await loadAgents();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suppression impossible.');
    }
  }

  function startChat(agentName: string) {
    router.push(`/chat?agent=${encodeURIComponent(agentName)}`);
  }

  return <div className="page">
    <header className="page-header"><div><div className="eyebrow"><span className="eyebrow-line" /> CONFIGURATION</div><h1>Vos agents</h1><p className="page-subtitle">Donnez à chaque mission un cerveau, un ton et les bons outils.</p></div><button className="button button-primary" onClick={() => setOpen(true)}><Plus size={16} /> Nouvel agent</button></header>
    {error && <div className="alert error-alert">{error}<button onClick={() => setError('')}><X size={15} /></button></div>}
    <section className="agent-hero"><div><span className="hero-kicker"><Sparkles size={14} /> Agent builder</span><h2>Des assistants qui savent<br /><span>où aller ensuite.</span></h2><p>Créez un agent puis démarrez directement une conversation avec son instruction système.</p></div><div className="agent-stack-art"><span className="stack-card stack-back"><Code2 size={17} /> contexte</span><span className="stack-card stack-middle"><Wrench size={17} /> tools</span><span className="stack-card stack-front"><Bot size={18} /> agent</span></div></section>
    <section className="section-heading"><div><div className="eyebrow">VOS AGENTS</div><h2>{agents.length ? `${agents.length} agent${agents.length > 1 ? 's' : ''} configuré${agents.length > 1 ? 's' : ''}` : 'Commencez votre équipe'}</h2></div><span className="section-caption">Persistants dans votre workspace</span></section>
    <section className="agent-grid">{agents.map((agent, index) => <article className="agent-card" key={agent.name}><div className={`agent-card-icon ${['violet', 'cyan', 'amber'][index % 3]}`}><Bot size={20} /></div><div className="agent-card-body"><div className="card-overline"><span>AGENT PERSONNALISÉ</span><span className="status-tag"><span className="status-dot online" /> actif</span></div><h3>{agent.name}</h3><p>{agent.system_prompt}</p><div className="agent-card-footer"><span><Wrench size={13} /> {agent.tools.length || 0} outils</span><button className="text-link agent-chat-link" onClick={() => startChat(agent.name)}><MessageSquare size={13} /> Ouvrir le chat</button><button className="icon-button danger-button" onClick={() => deleteAgent(agent.name)} aria-label={`Supprimer ${agent.name}`}><Trash2 size={15} /></button></div></div></article>)}{!agents.length && <div className="empty-state"><span className="empty-icon"><Bot size={22} /></span><h3>Aucun agent pour le moment</h3><p>Créez votre premier agent ou partez d’un preset ci-dessous.</p><button className="button button-secondary" onClick={() => setOpen(true)}><Plus size={15} /> Créer mon premier agent</button></div>}</section>
    <section className="section-heading preset-heading"><div><div className="eyebrow">PRESETS</div><h2>Commencer plus vite</h2></div></section><section className="preset-grid">{presets.map((preset) => <button className="preset-card" key={preset.name} onClick={() => { setName(preset.name); setSystemPrompt(preset.description); setOpen(true); }}><span className={`preset-icon ${preset.color}`}><Sparkles size={16} /></span><span><strong>{preset.name}</strong><small>{preset.description}</small></span><ArrowUpRight size={15} /></button>)}</section>
    {open && <div className="modal-backdrop" onClick={() => setOpen(false)}><div className="modal" onClick={(event) => event.stopPropagation()}><div className="modal-heading"><div><div className="eyebrow">NOUVEL AGENT</div><h2>Créer un assistant</h2></div><button className="icon-button" onClick={() => setOpen(false)} aria-label="Fermer"><X size={18} /></button></div><label>Nom de l’agent<input value={name} onChange={(event) => setName(event.target.value)} placeholder="Ex. Analyste sécurité" autoFocus /></label><label>Instruction système<textarea value={systemPrompt} onChange={(event) => setSystemPrompt(event.target.value)} placeholder="Décrivez son rôle, son ton et sa méthode…" rows={6} /></label><div className="modal-actions"><button className="button button-secondary" onClick={() => setOpen(false)}>Annuler</button><button className="button button-primary" onClick={createAgent} disabled={saving || !name.trim()}>{saving ? 'Création…' : <><Save size={15} /> Créer l’agent</>}</button></div></div></div>}
  </div>;
}
