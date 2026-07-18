'use client';

import { ReactNode, useState, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import Sidebar from './sidebar/Sidebar';
import { api, ConversationSummary } from '../lib/api';
import ToastContainer from './Toast';
import CommandPalette from './CommandPalette';

export default function WorkspaceShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [query, setQuery] = useState('');
  const [activeId, setActiveId] = useState('');
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Cmd+K / Ctrl+K → pallette de recherche
  useEffect(() => {
    if (typeof window === 'undefined') return;
    function handle(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
        event.preventDefault();
        setPaletteOpen((v) => !v);
      }
    }
    window.addEventListener('keydown', handle);
    return () => window.removeEventListener('keydown', handle);
  }, []);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      setActiveId(params.get('conversation') || '');
    }
  }, [pathname]);

  useEffect(() => {
    const savedTheme = localStorage.getItem('hermes-theme') as 'dark' | 'light' | null;
    if (savedTheme) {
      setTheme(savedTheme);
      document.documentElement.setAttribute('data-theme', savedTheme);
    } else {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('hermes-theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  useEffect(() => {
    const loadConversations = async () => {
      try {
        const data = await api.get<{ conversations: ConversationSummary[] }>('api/conversations');
        setConversations(data.conversations || []);
      } catch (err) {
        if ((err as Error).message !== 'Authentification requise' && (err as any).status !== 401) {
          console.error('Failed to load conversations', err);
        }
      }
    };
    loadConversations();

    const handleConversationsChanged = () => {
      loadConversations();
    };

    window.addEventListener('hermes:conversations-changed', handleConversationsChanged);
    
    const handleToggleSidebar = () => {
      setMobileOpen(prev => !prev);
    };
    window.addEventListener('hermes:toggle-sidebar', handleToggleSidebar);
    
    return () => {
      window.removeEventListener('hermes:conversations-changed', handleConversationsChanged);
      window.removeEventListener('hermes:toggle-sidebar', handleToggleSidebar);
    };
  }, []);

  const isLogin = pathname === '/login';

  if (isLogin) {
    return (
      <>
        {children}
        <ToastContainer />
      </>
    );
  }

  const filteredConversations = conversations.filter(c => 
    c.title?.toLowerCase().includes(query.toLowerCase()) || !query
  );

  return (
    <div className="app-container">
      <Sidebar
        isOpen={mobileOpen}
        toggleSidebar={() => setMobileOpen(!mobileOpen)}
        query={query}
        setQuery={setQuery}
        conversations={filteredConversations}
        activeId={activeId}
        theme={theme}
        toggleTheme={toggleTheme}
      />
      <main className="main-content">
        {children}
      </main>
      <ToastContainer />
      {paletteOpen && (
        <CommandPalette 
          conversations={conversations} 
          onNewConversation={() => {
            setPaletteOpen(false);
            router.push('/chat');
          }}
          onClose={() => setPaletteOpen(false)}
        />
      )}
    </div>
  );
}
