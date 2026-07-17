'use client';

import { Activity, ArrowUpRight, ChevronDown, Code2, ExternalLink, Search, Terminal, Wrench } from 'lucide-react';
import { useEffect, useState } from 'react';
import { api, Tool } from '../lib/api';

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  useEffect(() => { api.get<{ tools: Tool[] }>('api/tools').then((data) => setTools(data.tools || [])).catch(() => setTools([])).finally(() => setLoading(false)); }, []);
  const visible = tools.filter((tool) => `${tool.name} ${tool.description}`.toLowerCase().includes(query.toLowerCase()));
  return <div className="page"><header className="page-header"><div><div className="eyebrow"><span className="eyebrow-line" /> ÉCOSYSTÈME</div><h1>Outils & MCP</h1><p className="page-subtitle">Les capacités que Hermes peut activer pour transformer une intention en action.</p></div><div className="header-status"><span className="status-dot online" /> MCP Server opérationnel</div></header><section className="tools-summary"><div><span className="summary-icon"><Wrench size={20} /></span><div><strong>{tools.length || '—'}</strong><small>outils disponibles</small></div></div><div><span className="summary-icon cyan"><Activity size={20} /></span><div><strong>100%</strong><small>connectivité MCP</small></div></div><div className="summary-copy"><strong>Contrôlez chaque action</strong><small>Les outils sont affichés avant leur exécution et restent attachés à votre session.</small></div></section><div className="toolbar"><div className="search-field"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Rechercher un outil…" /></div><button className="filter-button">Tous les outils <ChevronDown size={15} /></button></div><section className="tools-grid">{loading && <div className="loading-state">Chargement des outils…</div>}{!loading && !visible.length && <div className="empty-state"><span className="empty-icon"><Search size={22} /></span><h3>Aucun outil trouvé</h3><p>Essayez une autre recherche.</p></div>}{visible.map((tool) => <article className="tool-card" key={tool.name}><div className="tool-card-top"><span className="tool-icon"><Terminal size={18} /></span><span className="status-tag"><span className="status-dot online" /> prêt</span></div><h3>{tool.name}</h3><p>{tool.description}</p><details><summary><Code2 size={14} /> Voir le schéma <ChevronDown size={14} /></summary><pre>{JSON.stringify(tool.parameters, null, 2)}</pre></details><div className="tool-footer"><span>via MCP</span><button className="text-link">Détails <ExternalLink size={13} /></button></div></article>)}</section></div>;
}
