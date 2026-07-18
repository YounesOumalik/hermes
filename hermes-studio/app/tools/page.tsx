'use client';

import { Activity, ChevronDown, Code2, Search, Terminal, Wrench } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { api, Tool } from '../lib/api';

type ToolFilter = 'all' | 'mcp' | 'webhook';
type SettingsStatus = { mcp_ready: boolean };

function belongsToFilter(tool: Tool, filter: ToolFilter) {
  if (filter === 'all') return true;
  if (filter === 'webhook') return tool.name.includes('webhook');
  return tool.name.startsWith('mcp_');
}

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [mcpReady, setMcpReady] = useState(false);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<ToolFilter>('all');
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.get<{ tools: Tool[] }>('api/tools'),
      api.get<SettingsStatus>('api/settings/status'),
    ]).then(([toolsResult, statusResult]) => {
      if (!active) return;
      if (toolsResult.status === 'fulfilled') setTools(toolsResult.value.tools || []);
      else setError('Impossible de charger le registre des outils.');
      if (statusResult.status === 'fulfilled') setMcpReady(statusResult.value.mcp_ready);
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const visible = useMemo(() => tools.filter((tool) => belongsToFilter(tool, filter) && `${tool.name} ${tool.description}`.toLowerCase().includes(query.toLowerCase())), [filter, query, tools]);
  const mcpLabel = loading ? 'Vérification du MCP…' : mcpReady ? 'MCP Server prêt' : 'MCP à vérifier';

  return <div className="page">
    <header className="page-header"><div><div className="eyebrow"><span className="eyebrow-line" /> ÉCOSYSTÈME</div><h1>Outils & MCP</h1><p className="page-subtitle">Les capacités que Hermes peut activer pour transformer une intention en action.</p></div><div className="header-status"><span className={`status-dot ${mcpReady ? 'online' : ''}`} /> {mcpLabel}</div></header>
    {error && <div className="alert error-alert">{error}</div>}
    <section className="tools-summary"><div><span className="summary-icon"><Wrench size={20} /></span><div><strong>{loading ? '—' : tools.length}</strong><small>outils disponibles</small></div></div><div><span className="summary-icon cyan"><Activity size={20} /></span><div><strong>{loading ? '…' : mcpReady ? 'Prêt' : 'À vérifier'}</strong><small>connectivité MCP</small></div></div><div className="summary-copy"><strong>Contrôlez chaque action</strong><small>Les outils sont affichés avant leur exécution et restent attachés à votre session.</small></div></section>
    <div className="toolbar"><div className="search-field"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Rechercher un outil…" /></div><label className="filter-button tool-filter"><span className="sr-only">Filtrer les outils</span><select value={filter} onChange={(event) => setFilter(event.target.value as ToolFilter)}><option value="all">Tous les outils</option><option value="mcp">Outils MCP</option><option value="webhook">Webhooks n8n</option></select><ChevronDown size={15} /></label></div>
    <section className="tools-grid">{loading && <div className="loading-state">Chargement des outils…</div>}{!loading && !visible.length && <div className="empty-state"><span className="empty-icon"><Search size={22} /></span><h3>Aucun outil trouvé</h3><p>Essayez une autre recherche ou un autre filtre.</p></div>}{visible.map((tool) => <article className="tool-card" key={tool.name}><div className="tool-card-top"><span className="tool-icon"><Terminal size={18} /></span><span className="status-tag"><span className={`status-dot ${mcpReady ? 'online' : ''}`} /> {mcpReady ? 'prêt' : 'à vérifier'}</span></div><h3>{tool.name}</h3><p>{tool.description}</p><details><summary><Code2 size={14} /> Voir le schéma <ChevronDown size={14} /></summary><pre>{JSON.stringify(tool.parameters, null, 2)}</pre></details><div className="tool-footer"><span>via MCP</span></div></article>)}</section>
  </div>;
}
