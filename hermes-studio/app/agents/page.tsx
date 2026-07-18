'use client';

import { ArrowUpRight, Bot, Code2, MessageSquare, Plus, Save, Settings2, Sparkles, Trash2, Wrench, X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Agent, Tool, api } from '../lib/api';

const presets = [
  { name: 'Architecte produit', description: 'Structure les idées, clarifie les besoins et propose une feuille de route.', color: 'violet' },
  { name: 'DevOps Sentinel', description: 'Inspecte les déploiements, les logs et les incidents avec méthode.', color: 'cyan' },
  { name: 'Researcher', description: 'Explore GitHub et transforme les sources en décisions actionnables.', color: 'amber' },
];

type AgentDraft = {
  originalName: string;
  name: string;
  description: string;
  systemPrompt: string;
  model: string;
  temperature: string;
  maxTokens: string;
  tools: string[];
};

const blankDraft = (preset?: { name: string; description: string }): AgentDraft => ({
  originalName: '',
  name: preset?.name || '',
  description: preset?.description || '',
  systemPrompt: preset ? `Tu es ${preset.name}. ${preset.description} Sois précis, structuré et propose toujours une prochaine action utile.` : '',
  model: '',
  temperature: '0.7',
  maxTokens: '2000',
  tools: [],
});

export default function AgentsPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [draft, setDraft] = useState<AgentDraft>(blankDraft());
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  async function loadWorkspace() {
    setLoading(true);
    try {
      const [agentResult, toolResult] = await Promise.all([
        api.get<{ agents: Agent[] }>('api/agents'),
        api.get<{ tools: Tool[] }>('api/tools'),
      ]);
      setAgents(agentResult.agents || []);
      setTools(toolResult.tools || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Impossible de charger les agents.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void loadWorkspace(); }, []);

  function updateDraft<K extends keyof AgentDraft>(field: K, value: AgentDraft[K]) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  function openCreate(preset?: { name: string; description: string }) {
    setDraft(blankDraft(preset));
    setError('');
    setOpen(true);
  }

  function openEdit(agent: Agent) {
    setDraft({
      originalName: agent.name,
      name: agent.name,
      description: agent.description || '',
      systemPrompt: agent.system_prompt,
      model: agent.model || '',
      temperature: String(agent.temperature ?? 0.7),
      maxTokens: String(agent.max_tokens ?? 2000),
      tools: agent.tools || [],
    });
    setError('');
    setOpen(true);
  }

  async function saveAgent() {
    if (!draft.name.trim() || !draft.systemPrompt.trim()) return;
    setSaving(true);
    setError('');
    const payload = {
      name: draft.name.trim(),
      description: draft.description.trim(),
      system_prompt: draft.systemPrompt.trim(),
      model: draft.model.trim() || null,
      temperature: Number(draft.temperature),
      max_tokens: Number(draft.maxTokens),
      tools: draft.tools,
    };
    try {
      if (draft.originalName) {
        await api.put<Agent>(`api/agents/${encodeURIComponent(draft.originalName)}`, payload);
      } else {
        await api.post<Agent>('api/agents', payload);
      }
      setOpen(false);
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Enregistrement impossible.');
    } finally {
      setSaving(false);
    }
  }

  async function deleteAgent(agentName: string) {
    if (!window.confirm(`Supprimer l’agent « ${agentName} » ?`)) return;
    try {
      await api.delete(`api/agents/${encodeURIComponent(agentName)}`);
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Suppression impossible.');
    }
  }

  function startChat(agentName: string) {
    router.push(`/chat?agent=${encodeURIComponent(agentName)}`);
  }

  function toggleTool(toolName: string) {
    setDraft((current) => ({
      ...current,
      tools: current.tools.includes(toolName) ? current.tools.filter((name) => name !== toolName) : [...current.tools, toolName],
    }));
  }

  return <div className="page">
    <header className="page-header"><div><div className="eyebrow"><span className="eyebrow-line" /> CONFIGURATION</div><h1>Vos agents</h1><p className="page-subtitle">Donnez à chaque mission un cerveau, un modèle et les bons outils.</p></div><button className="button button-primary" onClick={() => openCreate()}><Plus size={16} /> Nouvel agent</button></header>
    {error && <div className="alert error-alert">{error}<button onClick={() => setError('')} aria-label="Fermer l’erreur"><X size={15} /></button></div>}
    <section className="agent-hero"><div><span className="hero-kicker"><Sparkles size={14} /> Agent builder</span><h2>Des assistants qui savent<br /><span>où aller ensuite.</span></h2><p>Créez un agent, choisissez son modèle MiniMax, ajustez son comportement et connectez ses outils.</p></div><div className="agent-stack-art"><span className="stack-card stack-back"><Code2 size={17} /> contexte</span><span className="stack-card stack-middle"><Wrench size={17} /> tools</span><span className="stack-card stack-front"><Bot size={18} /> agent</span></div></section>
    <section className="section-heading"><div><div className="eyebrow">VOS AGENTS</div><h2>{agents.length ? `${agents.length} agent${agents.length > 1 ? 's' : ''} configuré${agents.length > 1 ? 's' : ''}` : 'Commencez votre équipe'}</h2></div><span className="section-caption">Persistants dans votre workspace</span></section>
    <section className="agent-grid">{loading && <div className="loading-state">Chargement de vos agents…</div>}{!loading && agents.map((agent, index) => <article className="agent-card" key={agent.name}><div className={`agent-card-icon ${['violet', 'cyan', 'amber'][index % 3]}`}><Bot size={20} /></div><div className="agent-card-body"><div className="card-overline"><span>AGENT PERSONNALISÉ</span><span className="status-tag"><span className="status-dot online" /> actif</span></div><h3>{agent.name}</h3><p>{agent.description || agent.system_prompt}</p><div className="agent-card-meta"><span>{agent.model || 'Modèle global'}</span><span>{agent.temperature ?? 0.7} température</span></div><div className="agent-card-footer"><span><Wrench size={13} /> {agent.tools.length || 0} outils</span><button className="text-link agent-edit-button" onClick={() => openEdit(agent)}><Settings2 size={13} /> Modifier</button><button className="text-link agent-chat-link" onClick={() => startChat(agent.name)}><MessageSquare size={13} /> Ouvrir le chat</button><button className="icon-button danger-button" onClick={() => void deleteAgent(agent.name)} aria-label={`Supprimer ${agent.name}`}><Trash2 size={15} /></button></div></div></article>)}{!loading && !agents.length && <div className="empty-state"><span className="empty-icon"><Bot size={22} /></span><h3>Aucun agent pour le moment</h3><p>Créez votre premier agent ou partez d’un preset ci-dessous.</p><button className="button button-secondary" onClick={() => openCreate()}><Plus size={15} /> Créer mon premier agent</button></div>}</section>
    <section className="section-heading preset-heading"><div><div className="eyebrow">PRESETS</div><h2>Commencer plus vite</h2></div></section><section className="preset-grid">{presets.map((preset) => <button className="preset-card" key={preset.name} onClick={() => openCreate(preset)}><span className={`preset-icon ${preset.color}`}><Sparkles size={16} /></span><span><strong>{preset.name}</strong><small>{preset.description}</small></span><ArrowUpRight size={15} /></button>)}</section>
    {open && <div className="modal-backdrop" onClick={() => setOpen(false)}><div className="modal modal-wide agent-modal" onClick={(event) => event.stopPropagation()}><div className="modal-heading"><div><div className="eyebrow">{draft.originalName ? 'PARAMÈTRES AGENT' : 'NOUVEL AGENT'}</div><h2>{draft.originalName ? 'Modifier l’agent' : 'Créer un assistant'}</h2></div><button className="icon-button" onClick={() => setOpen(false)} aria-label="Fermer"><X size={18} /></button></div><div className="agent-form-grid"><label>Nom de l’agent<input value={draft.name} onChange={(event) => updateDraft('name', event.target.value)} placeholder="Ex. Analyste sécurité" autoFocus /></label><label>Modèle MiniMax<input value={draft.model} onChange={(event) => updateDraft('model', event.target.value)} placeholder="Vide = modèle global" /><small>Ex. MiniMax-M2.7. Le champ vide utilise le modèle de Configuration.</small></label><label className="field-span-2">Résumé court<input value={draft.description} onChange={(event) => updateDraft('description', event.target.value)} placeholder="À quoi sert cet agent ?" /></label><label className="field-span-2">Instruction système<textarea value={draft.systemPrompt} onChange={(event) => updateDraft('systemPrompt', event.target.value)} placeholder="Décrivez son rôle, son ton et sa méthode…" rows={5} /></label><label>Température<input type="number" min="0" max="2" step="0.1" value={draft.temperature} onChange={(event) => updateDraft('temperature', event.target.value)} /><small>0 = précis · 2 = créatif</small></label><label>Maximum de tokens<input type="number" min="256" max="16000" step="256" value={draft.maxTokens} onChange={(event) => updateDraft('maxTokens', event.target.value)} /><small>Limite de réponse du modèle</small></label></div><div className="tool-picker"><div className="tool-picker-heading"><div><strong>Compétences & outils</strong><small>Sélectionnez les outils que cet agent peut utiliser dans sa mission.</small></div><span className="count-badge">{draft.tools.length}</span></div><div className="tool-picker-grid">{tools.map((tool) => <label className={`tool-option ${draft.tools.includes(tool.name) ? 'selected' : ''}`} key={tool.name}><input type="checkbox" checked={draft.tools.includes(tool.name)} onChange={() => toggleTool(tool.name)} /><span><strong>{tool.name}</strong><small>{tool.description}</small></span></label>)}{!tools.length && <small className="agent-modal-note">Aucun outil disponible. Vérifiez la connexion MCP.</small>}</div></div><div className="modal-actions"><button className="button button-secondary" onClick={() => setOpen(false)}>Annuler</button><button className="button button-primary" onClick={() => void saveAgent()} disabled={saving || !draft.name.trim() || !draft.systemPrompt.trim()}>{saving ? 'Enregistrement…' : <><Save size={15} /> {draft.originalName ? 'Enregistrer les changements' : 'Créer l’agent'}</>}</button></div></div></div>}
  </div>;
}
