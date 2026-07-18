'use client';

import { useState, type MouseEvent } from 'react';
import { ChevronDown, Terminal, Wrench, Globe, Zap } from 'lucide-react';

type ToolCallCardProps = {
  tool: string;
  status: 'running' | 'success' | 'error';
  args?: Record<string, unknown>;
  result?: Record<string, unknown>;
};

function toolIcon(tool: string) {
  if (tool.startsWith('web_')) return Globe;
  if (tool.startsWith('mcp_')) return Terminal;
  if (tool.includes('webhook')) return Zap;
  return Wrench;
}

export default function ToolCallCard({ tool, status, args, result }: ToolCallCardProps) {
  const [open, setOpen] = useState(false);

  function toggle(event: MouseEvent<HTMLButtonElement>) {
    event.stopPropagation();
    setOpen((v) => !v);
  }

  const Icon = toolIcon(tool);
  const statusIcon = status === 'running' ? '✦' : status === 'success' ? '✓' : '✗';

  return (
    <div className={`tool-call-card ${status === 'running' ? 'is-running' : ''}`}>
      <div className="tool-call-header">
        <span className="tool-call-icon"><Icon size={13} /></span>
        <span className="tool-call-name">{tool}</span>
        <span className={`tool-call-status tool-call-status-${status}`}>{statusIcon} {status === 'running' ? 'En cours' : status === 'success' ? 'OK' : 'Erreur'}</span>
        {(args || result) && (
          <button type="button" className="tool-call-toggle" onClick={toggle} aria-label={open ? 'Masquer les détails' : 'Voir les détails'}>
            <ChevronDown size={13} className={`tool-call-toggle-icon ${open ? 'is-open' : ''}`} />
          </button>
        )}
      </div>
      {open && (
        <div className="tool-call-body">
          {args && (
            <div className="tool-call-section">
              <span className="tool-call-label">Arguments</span>
              <pre className="tool-call-pre">{JSON.stringify(args, null, 2)}</pre>
            </div>
          )}
          {result && (
            <div className="tool-call-section">
              <span className="tool-call-label">Résultat</span>
              <pre className="tool-call-pre">{JSON.stringify(result, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
