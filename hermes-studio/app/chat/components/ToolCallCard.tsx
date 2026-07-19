'use client';

import { useState, type MouseEvent } from 'react';
import { ChevronDown, Terminal, Wrench, Globe, Zap } from 'lucide-react';

type ToolStatus = 'running' | 'success' | 'error' | 'awaiting_approval' | 'rejected';

type ToolCallCardProps = {
  tool: string;
  status: ToolStatus;
  args?: Record<string, unknown>;
  result?: Record<string, unknown>;
  approval_id?: number;
  onApprove?: (approvalId: number) => void;
  onReject?: (approvalId: number) => void;
};

function toolIcon(tool: string) {
  if (tool.startsWith('web_')) return Globe;
  if (tool.startsWith('mcp_')) return Terminal;
  if (tool.includes('webhook')) return Zap;
  return Wrench;
}

const STATUS_LABEL: Record<ToolStatus, string> = {
  running: 'En cours',
  success: 'OK',
  error: 'Erreur',
  awaiting_approval: 'Approbation requise',
  rejected: 'Rejeté',
};

const STATUS_ICON: Record<ToolStatus, string> = {
  running: '✦',
  success: '✓',
  error: '✗',
  awaiting_approval: '⚠',
  rejected: '⊘',
};

export default function ToolCallCard({ tool, status, args, result, approval_id, onApprove, onReject }: ToolCallCardProps) {
  const [open, setOpen] = useState(false);

  function toggle(event: MouseEvent<HTMLButtonElement>) {
    event.stopPropagation();
    setOpen((v) => !v);
  }

  const Icon = toolIcon(tool);

  return (
    <div className={`tool-call-card ${status === 'running' ? 'is-running' : ''} tool-call-${status}`}>
      <div className="tool-call-header">
        <span className="tool-call-icon"><Icon size={13} /></span>
        <span className="tool-call-name">{tool}</span>
        <span className={`tool-call-status tool-call-status-${status}`}>{STATUS_ICON[status]} {STATUS_LABEL[status]}</span>
        {status === 'awaiting_approval' && approval_id !== undefined && (
          <>
            <button
              type="button"
              className="tool-call-approve"
              onClick={(e) => { e.stopPropagation(); onApprove?.(approval_id); }}
              aria-label="Approuver"
            >
              ✓ Approuver
            </button>
            <button
              type="button"
              className="tool-call-reject"
              onClick={(e) => { e.stopPropagation(); onReject?.(approval_id); }}
              aria-label="Rejeter"
            >
              ✗ Rejeter
            </button>
          </>
        )}
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
