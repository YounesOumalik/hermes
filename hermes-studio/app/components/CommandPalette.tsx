'use client';

import { Home, MessageSquare, Bot, Wrench, Settings, Search } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { type KeyboardEvent as ReactKeyboardEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';

type PaletteItem = {
  id: string;
  label: string;
  subtitle: string;
  icon: typeof MessageSquare;
  href: string;
  shortcut?: string;
};

const staticItems: PaletteItem[] = [
  { id: 'overview', label: "Vue d'ensemble", subtitle: 'Dashboard', icon: Home, href: '/' },
  { id: 'chat', label: 'Conversations', subtitle: 'Chat avec vos agents', icon: MessageSquare, href: '/chat', shortcut: '⌃G' },
  { id: 'agents', label: 'Agents', subtitle: 'Créer et gérer vos agents', icon: Bot, href: '/agents' },
  { id: 'tools', label: 'Outils & MCP', subtitle: 'Explorer les capacités', icon: Wrench, href: '/tools' },
  { id: 'settings', label: 'Configuration', subtitle: 'API keys, secrets, connecteurs', icon: Settings, href: '/settings' },
];

type CommandPaletteProps = {
  conversations: { id: string; title: string }[];
  onNewConversation: () => void;
  onClose: () => void;
};

export default function CommandPalette({ conversations, onNewConversation, onClose }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // ⌘K = nouvelle conversation
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const conversationItems: PaletteItem[] = useMemo(
    () =>
      conversations
        .filter((c) => !query || c.title.toLowerCase().includes(query.toLowerCase()))
        .slice(0, 8)
        .map((c) => ({
          id: c.id,
          label: c.title,
          subtitle: 'Conversation',
          icon: MessageSquare,
          href: `/chat?conversation=${c.id}`,
        })),
    [conversations, query],
  );

  const allItems: PaletteItem[] = useMemo(() => {
    const filtered = query
      ? staticItems.filter((i) => i.label.toLowerCase().includes(query.toLowerCase()) || i.subtitle.toLowerCase().includes(query.toLowerCase()))
      : staticItems;
    const combined = conversationItems.length
      ? [
          ...conversationItems,
          ...filtered.filter((si) => !conversationItems.some((ci) => ci.id === si.id)),
        ]
      : filtered;
    return combined;
  }, [conversationItems, query]);

  // Clamp selected index
  const safeIdx = Math.min(selectedIdx, Math.max(0, allItems.length - 1));

  const execute = useCallback(
    (item?: PaletteItem) => {
      const target = item || allItems[safeIdx];
      if (!target) return;
      onClose();
      if (target.href === '/chat' && target.id === 'chat') onNewConversation();
      else router.push(target.href);
    },
    [allItems, safeIdx, onClose, onNewConversation, router],
  );

  const handleKeyDown = (event: ReactKeyboardEvent) => {
    if (event.key === 'ArrowDown') { event.preventDefault(); setSelectedIdx((i) => Math.min(i + 1, allItems.length - 1)); }
    else if (event.key === 'ArrowUp') { event.preventDefault(); setSelectedIdx((i) => Math.max(i - 1, 0)); }
    else if (event.key === 'Enter') { event.preventDefault(); execute(); }
    else if (event.key === 'Escape') onClose();
  };

  return (
    <div
      className="command-palette-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="Recherche rapide"
      onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}
    >
      <div className="command-palette" onKeyDown={handleKeyDown}>
        <div className="command-palette-input">
          <Search size={17} className="muted-icon" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => { setQuery(event.target.value); setSelectedIdx(0); }}
            placeholder="Rechercher une conversation ou une page…"
            aria-label="Rechercher"
          />
          <span className="command-palette-hint">esc</span>
        </div>
        <div className="command-palette-results">
          {allItems.map((item, idx) => (
            <button
              key={item.id}
              type="button"
              className="command-palette-item"
              onClick={() => execute(item)}
              aria-selected={idx === safeIdx}
            >
              <span className="command-palette-item-icon"><item.icon size={15} /></span>
              <span className="command-palette-item-body">
                <strong>{item.label}</strong>
                <small>{item.subtitle}</small>
              </span>
              {item.shortcut && <span className="command-palette-item-shortcut">{item.shortcut}</span>}
            </button>
          ))}
          {query && allItems.length === 0 && (
            <div className="history-empty">Aucun résultat pour « {query} ».</div>
          )}
        </div>
      </div>
    </div>
  );
}
