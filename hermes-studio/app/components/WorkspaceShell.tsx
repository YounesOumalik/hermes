'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bot, Boxes, ChevronDown, Command, Home, LogOut, MessageSquare, Moon, PanelLeftClose, PanelLeftOpen, Plus, Settings, Sparkles, Sun, Wrench, X } from 'lucide-react';
import { type MouseEvent, useEffect, useState } from 'react';
import { ConversationSummary, api } from '../lib/api';

const navigation = [
  { href: '/', label: 'Vue d’ensemble', icon: Home },
  { href: '/chat', label: 'Conversations', icon: MessageSquare },
  { href: '/agents', label: 'Agents', icon: Bot },
  { href: '/tools', label: 'Outils & MCP', icon: Wrench },
  { href: '/settings', label: 'Configuration', icon: Settings },
];

function formatConversationDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: '2-digit' }).format(date);
}

export default function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);

  useEffect(() => {
    const savedCollapsed = window.localStorage.getItem('hermes-sidebar-collapsed') === 'true';
    const savedTheme = window.localStorage.getItem('hermes-theme') === 'light' ? 'light' : 'dark';
    setCollapsed(savedCollapsed);
    setTheme(savedTheme);
    document.documentElement.dataset.theme = savedTheme;
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem('hermes-theme', theme);
  }, [theme]);

  useEffect(() => {
    async function loadConversations() {
      try {
        const data = await api.get<{ conversations: ConversationSummary[] }>('api/conversations');
        setConversations(data.conversations || []);
      } catch {
        setConversations([]);
      }
    }
    void loadConversations();
    window.addEventListener('hermes:conversations-changed', loadConversations);
    return () => window.removeEventListener('hermes:conversations-changed', loadConversations);
  }, []);

  if (pathname === '/login') return <>{children}</>;

  async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.assign('/login');
  }

  function startNewConversation(event: MouseEvent<HTMLAnchorElement>) {
    setMobileOpen(false);
    if (pathname === '/chat') {
      event.preventDefault();
      window.location.assign(`/chat?new=${Date.now()}`);
    }
  }

  function toggleCollapsed() {
    setCollapsed((value) => {
      const next = !value;
      window.localStorage.setItem('hermes-sidebar-collapsed', String(next));
      return next;
    });
  }

  return (
    <div className={`workspace-shell ${collapsed ? 'sidebar-is-collapsed' : ''}`}>
      <button className="mobile-menu-button" aria-label="Ouvrir le menu" onClick={() => setMobileOpen(true)}>
        <Command size={18} />
      </button>

      {mobileOpen && <button className="mobile-backdrop" aria-label="Fermer le menu" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand-row">
          <Link href="/" className="brand" onClick={() => setMobileOpen(false)} title="Hermes Workspace">
            <span className="brand-mark"><Sparkles size={17} /></span>
            <span className="sidebar-label">Hermes<span className="brand-soft"> Workspace</span></span>
          </Link>
          <button className="icon-button sidebar-toggle" onClick={toggleCollapsed} aria-label={collapsed ? 'Déployer la barre latérale' : 'Rétracter la barre latérale'} title={collapsed ? 'Déployer la barre latérale' : 'Rétracter la barre latérale'}>{collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}</button>
          <button className="icon-button mobile-close" onClick={() => setMobileOpen(false)} aria-label="Fermer le menu"><X size={18} /></button>
        </div>

        <Link href="/chat" className="new-chat" onClick={startNewConversation} title="Nouvelle conversation">
          <Plus size={17} /><span className="sidebar-label">Nouvelle conversation</span>
          <span className="shortcut sidebar-label">⌘ K</span>
        </Link>

        <div className="sidebar-section-label sidebar-label">Workspace</div>
        <nav className="sidebar-nav" aria-label="Navigation principale">
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} onClick={() => setMobileOpen(false)} title={label} className={pathname === href ? 'nav-link active' : 'nav-link'}>
              <Icon size={17} strokeWidth={1.8} />
              <span className="sidebar-label">{label}</span>
              {href === '/chat' && <span className="nav-badge">{conversations.length || ''}</span>}
            </Link>
          ))}
        </nav>

        <div className="sidebar-section-label history-label sidebar-label">Récent</div>
        <div className="history-list">
          {conversations.slice(0, 8).map((conversation) => <Link href={`/chat?conversation=${conversation.id}`} className="history-item" key={conversation.id} title={conversation.title} onClick={(event) => { event.preventDefault(); window.location.assign(`/chat?conversation=${conversation.id}`); }}><span className="history-dot" /><span className="history-title sidebar-label">{conversation.title}</span><small className="history-date sidebar-label">{formatConversationDate(conversation.updated_at)}</small></Link>)}
          {!conversations.length && <span className="history-empty sidebar-label">Aucune conversation</span>}
        </div>

        <div className="sidebar-footer">
          <div className="connection-card" title="Hermes opérationnel">
            <span className="status-dot online" />
            <div className="sidebar-label"><strong>Hermes opérationnel</strong><small>Daemon · MCP · n8n</small></div>
            <ChevronDown size={14} className="muted-icon" />
          </div>
          <div className="user-row"><span className="avatar">YO</span><span className="sidebar-label"><strong>Younes</strong><small>Workspace privé</small></span><button className="icon-button theme-toggle" onClick={() => setTheme((value) => value === 'dark' ? 'light' : 'dark')} aria-label={theme === 'dark' ? 'Activer le mode clair' : 'Activer le mode sombre'} title={theme === 'dark' ? 'Mode clair' : 'Mode sombre'}>{theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}</button><button className="icon-button sidebar-label" onClick={logout} aria-label="Se déconnecter" title="Se déconnecter"><LogOut size={15} /></button><Boxes size={15} className="muted-icon sidebar-label" /></div>
        </div>
      </aside>

      <main className="workspace-main">{children}</main>
    </div>
  );
}
