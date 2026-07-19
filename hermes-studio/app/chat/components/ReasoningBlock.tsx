'use client';

import { useState, type MouseEvent } from 'react';
import { ChevronDown, Brain } from 'lucide-react';

type ReasoningBlockProps = {
  details: string | Record<string, unknown>[];
};

export default function ReasoningBlock({ details }: ReasoningBlockProps) {
  const [open, setOpen] = useState(false);

  function toggle(event: MouseEvent<HTMLButtonElement>) {
    event.stopPropagation();
    setOpen((v) => !v);
  }

  const isString = typeof details === 'string';
  const hasContent = isString ? (details as string).length > 0 : (details as Record<string, unknown>[]).length > 0;
  if (!hasContent) return null;

  return (
    <div className="reasoning-block">
      <button type="button" className="reasoning-toggle" onClick={toggle} aria-expanded={open}>
        <span className="reasoning-icon"><Brain size={13} /></span>
        <span className="reasoning-label">Raisonnement</span>
        <ChevronDown size={13} className={`reasoning-caret ${open ? 'is-open' : ''}`} />
      </button>
      {open && (
        <div className="reasoning-content">
          {isString ? (
            <p className="reasoning-line">{details}</p>
          ) : (
            (details as Record<string, unknown>[]).map((d, i) => (
              <p key={i} className="reasoning-line">
                {typeof d === 'object' && d !== null && 'text' in d
                  ? String((d as Record<string, unknown>).text)
                  : JSON.stringify(d)}
              </p>
            ))
          )}
        </div>
      )}
    </div>
  );
}
