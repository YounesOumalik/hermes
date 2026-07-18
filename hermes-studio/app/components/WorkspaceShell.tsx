'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bot, Boxes, ChevronDown, Command, Home, LogOut, MessageSquare, Plus, Settings, Sparkles, Wrench, X } from 'lucide-react';
import { type MouseEvent, useState } from 'react';

const navigation = [
  { href: '/', label: 'Vue d’ensemble', icon: Home },
  { href: '/chat', label: 'Conversations', icon: MessageSquare },
  { href: '/agents', label: 'Agents', icon: Bot },
  { href: '/tools', label: 'Outils & MCP', icon: Wrench },
  { href: '/settings', label: 'Configuration', icon: Settings },
];

export default function WorkspaceShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

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

  return (
    <div className="workspace-shell">
      <button className="mobile-menu-button" aria-label="Ouvrir le menu" onClick={() => setMobileOpen(true)}>
        <Command size={18} />
      </button>

      {mobileOpen && <button className="mobile-backdrop" aria-label="Fermer le menu" onClick={() => setMobileOpen(false)} />}
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand-row">
          <Link href="/" className="brand" onClick={() => setMobileOpen(false)}>
            <span className="brand-mark"><Sparkles size={17} /></span>
            <span>Hermes<span className="brand-soft"> Workspace</span></span>
          </Link>
          <button className="icon-button mobile-close" onClick={() => setMobileOpen(false)} aria-label="Fermer le menu"><X size={18} /></button>
        </div>

        <Link href="/chat" className="new-chat" onClick={startNewConversation}>
          <Plus size={17} /> Nouvelle conversation
          <span className="shortcut">⌘ K</span>
        </Link>

        <div className="sidebar-section-label">Workspace</div>
        <nav className="sidebar-nav" aria-label="Navigation principale">
          {navigation.map(({ href, label, icon: Icon }) => (
            <Link key={href} href={href} onClick={() => setMobileOpen(false)} className={pathname === href ? 'nav-link active' : 'nav-link'}>
              <Icon size={17} strokeWidth={1.8} />
              <span>{label}</span>
              {href === '/chat' && <span className="nav-badge">3</span>}
            </Link>
          ))}
        </nav>

        <div className="sidebar-section-label history-label">Récent</div>
        <div className="history-list">
          <Link href="/chat" className="history-item"><span className="history-dot" />Audit de l’installation</Link>
          <Link href="/chat" className="history-item"><span className="history-dot" />Workflow GitHub</Link>
          <Link href="/chat" className="history-item"><span className="history-dot" />Optimiser Hermes Studio</Link>
        </div>

        <div className="sidebar-footer">
          <div className="connection-card">
            <span className="status-dot online" />
            <div><strong>Hermes opérationnel</strong><small>Daemon · MCP · n8n</small></div>
            <ChevronDown size={14} className="muted-icon" />
          </div>
          <div className="user-row"><span className="avatar">YO</span><span><strong>Younes</strong><small>Workspace privé</small></span><button className="icon-button" onClick={logout} aria-label="Se déconnecter" title="Se déconnecter"><LogOut size={15} /></button><Boxes size={15} className="muted-icon" /></div>
        </div>
      </aside>

      <main className="workspace-main">{children}</main>
    </div>
  );
}
