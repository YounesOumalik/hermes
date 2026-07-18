'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  Bot,
  Boxes,
  ChevronDown,
  ChevronRight,
  Command,
  Home,
  LogOut,
  MessageSquare,
  Monitor,
  Moon,
  MoreHorizontal,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Plus,
  Search,
  Settings,
  Sparkles,
  Sun,
  Trash2,
  Wrench,
  X,
} from 'lucide-react';
import {
  type ChangeEvent,
  type FormEvent,
  type KeyboardEvent as ReactKeyboardEvent,
  type MouseEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Agent, ConversationSummary, api } from '../lib/api';
import ConfirmDialog from './ConfirmDialog';
import { showToast } from './Toast';
import CommandPalette from './CommandPalette';

type AgentPalette = {
  id: string;
  gradient: string;
  text: string;
  ring: string;
  soft: string;
};

type SidebarMode = 'wide' | 'compact';

type ConversationMenuState = {
  conversationId: string;
  open: boolean;
} | null;

const navigation = [
  { href: '/', label: "Vue d'ensemble", icon: Home },
  { href: '/chat', label: 'Conversations', icon: MessageSquare },
  { href: '/agents', label: 'Agents', icon: Bot },
  { href: '/tools', label: 'Outils & MCP', icon: Wrench },
  { href: '/settings', label: 'Configuration', icon: Settings },
];

const SIDEBAR_MIN_WIDTH = 220;
const SIDEBAR_MAX_WIDTH = 520;
const SIDEBAR_DEFAULT_WIDTH = 300;
const SIDEBAR_WIDTH_STORAGE_KEY = 'hermes-sidebar-width';

const palette: AgentPalette[] = [
  { id: 'violet', gradient: 'linear-gradient(135deg, #bcb2ff, #7de7d7)', text: '#1a1530', ring: 'rgba(157,140,255,.45)', soft: 'rgba(157,140,255,.16)' },
  { id: 'cyan', gradient: 'linear-gradient(135deg, #7de7d7, #56b3ff)', text: '#06212e', ring: 'rgba(89,228,212,.45)', soft: 'rgba(89,228,212,.16)' },
  { id: 'amber', gradient: 'linear-gradient(135deg, #f8c96b, #ff9d72)', text: '#321a04', ring: 'rgba(248,201,107,.45)', soft: 'rgba(248,201,107,.16)' },
  { id: 'pink', gradient: 'linear-gradient(135deg, #ff9ec0, #c389ff)', text: '#311029', ring: 'rgba(255,130,151,.45)', soft: 'rgba(255,130,151,.16)' },
  { id: 'emerald', gradient: 'linear-gradient(135deg, #65e6aa, #59e4d4)', text: '#0a2418', ring: 'rgba(101,230,170,.45)', soft: 'rgba(101,230,170,.16)' },
  { id: 'indigo', gradient: 'linear-gradient(135deg, #a5b4ff, #6d5de7)', text: '#0d1238', ring: 'rgba(165,180,255,.45)', soft: 'rgba(165,180,255,.16)' },
];

function hashString(value: string): number {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function paletteFor(key: string): AgentPalette {
  if (!key) return palette[0];
  return palette[hashString(key) % palette.length];
}

function initials(value: string): string {
  if (!value) return '✦';
  const cleaned = value.replace(/[^a-zA-Z0-9À-ÿ ]/g, ' ').trim();
  const parts = cleaned.split(/\s+/).filter(Boolean);
  if (!parts.length) return value.slice(0, 2).toUpperCase();
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[1][0]).toUpperCase();
}

function formatRelativeDate(value: string): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const diffMs = Date.now() - date.getTime();
  const diffSec = Math.round(diffMs / 1000);
  if (diffSec < 60) return "à l'instant";
  const diffMin = Math.round(diffSec / 60);
  if (diffMin < 60) return `il y a ${diffMin} min`;
  const diffHour = Math.round(diffMin / 60);
  if (diffHour < 24) return `il y a ${diffHour} h`;
  const diffDay = Math.round(diffHour / 24);
  if (diffDay < 7) return `il y a ${diffDay} j`;
  return new Intl.DateTimeFormat('fr-FR', { day: '2-digit', month: '2-digit' }).format(date);
}

function contextLabel(tokens: number | null | undefined): string {
  if (!tokens) return '';
  if (tokens >= 1_000_000) return '1M';
  return `${Math.round(tokens / 1000)}K`;
}

function truncate(value: string, max: number): string {
  if (!value) return '';
  if (value.length <= max) return value;
  return `${value.slice(0, max - 1).trim()}…`;
}

function announceConversationsChanged() {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event('hermes:conversations-changed'));
}

function getActiveConversationIdFromPath(): string {
  if (typeof window === 'undefined') return '';
  const params = new URLSearchParams(window.location.search);
  return params.get('conversation') || '';
}

export default function WorkspaceShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [mode, setMode] = useState<SidebarMode>('wide');
  const [theme, setTheme] = useState<'dark' | 'light' | 'system'>('system');
  const [resolvedTheme, setResolvedTheme] = useState<'dark' | 'light'>('dark');
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [query, setQuery] = useState('');
  const [agentFilter, setAgentFilter] = useState<string>('all');
  const [collapsedGroups, setCollapsedGroups] = useState<Record<string, boolean>>({});
  const [menuState, setMenuState] = useState<ConversationMenuState>(null);
  const [renamingId, setRenamingId] = useState<string>('');
  const [renameDraft, setRenameDraft] = useState<string>('');
  const [busyId, setBusyId] = useState<string>('');
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null);
  const tooltipTimer = useRef<number | null>(null);
  const [sidebarWidth, setSidebarWidth] = useState<number>(SIDEBAR_DEFAULT_WIDTH);
  const resizeState = useRef<{ startX: number; startWidth: number } | null>(null);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<ConversationSummary | null>(null);

  const isLogin = pathname === '/login';
  const isChatPage = pathname === '/chat';
  const activeConversationId = getActiveConversationIdFromPath();
  const compact = mode === 'compact';

  // Drag-to-resize : on ajuste sidebarWidth en suivant le mouvement X de la souris.
  const beginResize = useCallback(
    (event: MouseEvent<HTMLDivElement>) => {
      if (compact) return;
      event.preventDefault();
      resizeState.current = { startX: event.clientX, startWidth: sidebarWidth };
      const onMove = (moveEvent: globalThis.MouseEvent) => {
        const state = resizeState.current;
        if (!state) return;
        const delta = moveEvent.clientX - state.startX;
        const next = Math.max(SIDEBAR_MIN_WIDTH, Math.min(SIDEBAR_MAX_WIDTH, state.startWidth + delta));
        setSidebarWidth(next);
      };
      const onUp = () => {
        resizeState.current = null;
        window.removeEventListener('mousemove', onMove);
        window.removeEventListener('mouseup', onUp);
        document.body.style.removeProperty('cursor');
        document.body.style.removeProperty('user-select');
      };
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
    },
    [compact, sidebarWidth],
  );

  const resetSidebarWidth = useCallback(() => {
    setSidebarWidth(SIDEBAR_DEFAULT_WIDTH);
    if (typeof window !== 'undefined') window.localStorage.removeItem(SIDEBAR_WIDTH_STORAGE_KEY);
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const savedMode = window.localStorage.getItem('hermes-sidebar-mode');
    setMode(savedMode === 'compact' ? 'compact' : 'wide');
    const savedThemeRaw = window.localStorage.getItem('hermes-theme');
    const initialTheme: 'dark' | 'light' | 'system' = savedThemeRaw === 'light' || savedThemeRaw === 'dark' || savedThemeRaw === 'system' ? savedThemeRaw : 'system';
    setTheme(initialTheme);
    const resolved = initialTheme === 'system'
      ? (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
      : initialTheme;
    setResolvedTheme(resolved);
    document.documentElement.dataset.theme = resolved;
    const savedWidth = Number(window.localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY));
    if (!Number.isNaN(savedWidth) && savedWidth >= SIDEBAR_MIN_WIDTH && savedWidth <= SIDEBAR_MAX_WIDTH) {
      setSidebarWidth(savedWidth);
    }
  }, []);

  // Applique le thème résolu à chaque changement + écoute le système si mode "system".
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const apply = (value: 'dark' | 'light') => {
      setResolvedTheme(value);
      document.documentElement.dataset.theme = value;
    };
    if (theme === 'system') {
      const media = window.matchMedia('(prefers-color-scheme: light)');
      apply(media.matches ? 'light' : 'dark');
      const handler = (event: MediaQueryListEvent) => apply(event.matches ? 'light' : 'dark');
      media.addEventListener('change', handler);
      window.localStorage.setItem('hermes-theme', 'system');
      return () => media.removeEventListener('change', handler);
    }
    apply(theme);
    window.localStorage.setItem('hermes-theme', theme);
    return undefined;
  }, [theme]);

  useEffect(() => {
    window.localStorage.setItem('hermes-sidebar-mode', mode);
  }, [mode]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    if (!compact) window.localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(sidebarWidth));
  }, [sidebarWidth, compact]);

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
    let cancelled = false;
    async function refresh() {
      try {
        const [conversationResult, agentResult] = await Promise.all([
          api.get<{ conversations: ConversationSummary[] }>('api/conversations'),
          api.get<{ agents: Agent[] }>('api/agents').catch(() => ({ agents: [] as Agent[] })),
        ]);
        if (cancelled) return;
        setConversations(conversationResult.conversations || []);
        setAgents(agentResult.agents || []);
      } catch {
        if (!cancelled) {
          setConversations([]);
          setAgents([]);
        }
      }
    }
    void refresh();
    window.addEventListener('hermes:conversations-changed', refresh);
    return () => {
      cancelled = true;
      window.removeEventListener('hermes:conversations-changed', refresh);
    };
  }, []);

  useEffect(() => {
    if (!menuState?.open) return undefined;
    function handle(event: globalThis.MouseEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.closest('[data-conversation-menu]') || target?.closest('[data-conversation-menu-button]')) return;
      setMenuState(null);
    }
    window.addEventListener('mousedown', handle);
    return () => window.removeEventListener('mousedown', handle);
  }, [menuState]);

  const agentByName = useMemo(() => {
    const map = new Map<string, Agent>();
    agents.forEach((agent) => map.set(agent.name, agent));
    return map;
  }, [agents]);

  const filteredConversations = useMemo(() => {
    const lowered = query.trim().toLowerCase();
    return conversations.filter((conversation) => {
      if (agentFilter !== 'all' && (conversation.agent_name || '') !== agentFilter) return false;
      if (!lowered) return true;
      return (
        conversation.title.toLowerCase().includes(lowered) ||
        (conversation.agent_name || '').toLowerCase().includes(lowered) ||
        (conversation.model || '').toLowerCase().includes(lowered)
      );
    });
  }, [agentFilter, conversations, query]);

  function getDateBucket(raw: string): string {
    if (!raw) return 'older';
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return 'older';
    const diffMs = Date.now() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return 'today';
    if (diffDays === 1) return 'yesterday';
    if (diffDays < 7) return 'week';
    if (diffDays < 30) return 'month';
    return 'older';
  }

  const bucketLabels: Record<string, string> = {
    today: 'Aujourd\'hui',
    yesterday: 'Hier',
    week: '7 derniers jours',
    month: '30 derniers jours',
    older: 'Plus ancien',
  };

  const groupedConversations = useMemo(() => {
    const buckets = new Map<string, ConversationSummary[]>();
    filteredConversations.forEach((conversation) => {
      const key = getDateBucket(conversation.updated_at);
      const list = buckets.get(key) || [];
      list.push(conversation);
      buckets.set(key, list);
    });
    const order = ['today', 'yesterday', 'week', 'month', 'older'];
    const agentByName = agents.reduce((map, a) => { map.set(a.name, a); return map; }, new Map<string, Agent>());
    return order
      .filter((key) => buckets.has(key))
      .map((key) => ({
        key,
        label: bucketLabels[key] || key,
        items: buckets.get(key)!,
        palette: palette[0],  // neutral palette for date groups
        agent: undefined,
        model: '',
        description: '',
      }));
  }, [agentByName, filteredConversations]);

  const compactRecent = useMemo(() => filteredConversations.slice(0, 3), [filteredConversations]);
  const totalConversations = conversations.length;
  const totalGroups = groupedConversations.length;

  if (isLogin) return <>{children}</>;

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

  function toggleMode() {
    setMode((value) => (value === 'wide' ? 'compact' : 'wide'));
  }

  function toggleGroup(key: string) {
    setCollapsedGroups((current) => ({ ...current, [key]: !current[key] }));
  }

  function openConversation(conversation: ConversationSummary, event: MouseEvent) {
    event.preventDefault();
    setMobileOpen(false);
    setMenuState(null);
    router.push(`/chat?conversation=${conversation.id}`);
  }

  function showTooltip(text: string, event: MouseEvent<HTMLElement> | React.FocusEvent<HTMLElement>) {
    if (tooltipTimer.current) window.clearTimeout(tooltipTimer.current);
    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    tooltipTimer.current = window.setTimeout(() => {
      setTooltip({ text, x: rect.right + 12, y: rect.top + rect.height / 2 });
    }, 350);
  }

  function hideTooltip() {
    if (tooltipTimer.current) window.clearTimeout(tooltipTimer.current);
    setTooltip(null);
  }

  function toggleMenu(conversationId: string, event: MouseEvent<HTMLButtonElement>) {
    event.stopPropagation();
    event.preventDefault();
    setMenuState((current) => {
      if (current && current.conversationId === conversationId && current.open) {
        return null;
      }
      return { conversationId, open: true };
    });
  }

  function deleteConversation(conversation: ConversationSummary) {
    setDeleteTarget(conversation);
  }

  async function confirmDelete() {
    const conversation = deleteTarget;
    if (!conversation) return;
    setBusyId(conversation.id);
    setDeleteTarget(null);
    try {
      await api.delete(`api/conversations/${encodeURIComponent(conversation.id)}`);
      setConversations((current) => current.filter((item) => item.id !== conversation.id));
      setMenuState(null);
      announceConversationsChanged();
      if (activeConversationId === conversation.id) router.push('/chat?new=1');
      showToast('success', `« ${conversation.title} » supprimée.`);
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : 'Suppression impossible.');
    } finally {
      setBusyId('');
    }
  }

  function beginRename(conversation: ConversationSummary) {
    setRenamingId(conversation.id);
    setRenameDraft(conversation.title);
    setMenuState(null);
  }

  async function commitRename(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = renameDraft.trim();
    if (!trimmed || !renamingId) {
      setRenamingId('');
      return;
    }
    setBusyId(renamingId);
    try {
      await api.put(`api/conversations/${encodeURIComponent(renamingId)}`, { title: trimmed });
      setConversations((current) =>
        current.map((item) => (item.id === renamingId ? { ...item, title: trimmed } : item)),
      );
      announceConversationsChanged();
      showToast('success', 'Conversation renommée.');
    } catch (error) {
      showToast('error', error instanceof Error ? error.message : 'Renommage impossible.');
    } finally {
      setRenamingId('');
      setBusyId('');
    }
  }

  function cancelRename() {
    setRenamingId('');
    setRenameDraft('');
  }

  function handleRenameKey(event: ReactKeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Escape') {
      event.preventDefault();
      cancelRename();
    }
  }

  function onSearchChange(event: ChangeEvent<HTMLInputElement>) {
    setQuery(event.target.value);
  }

  function onAgentFilterChange(event: ChangeEvent<HTMLSelectElement>) {
    setAgentFilter(event.target.value);
  }

  const showFullConversationList = isChatPage;
  const sidebarStyle = compact ? undefined : { width: `${sidebarWidth}px`, flexBasis: `${sidebarWidth}px` };

  return (
    <div className={`workspace-shell sidebar-mode-${mode}`}>
      <button className="mobile-menu-button" aria-label="Ouvrir le menu" onClick={() => setMobileOpen(true)}>
        <Command size={18} />
      </button>

      {mobileOpen && <button className="mobile-backdrop" aria-label="Fermer le menu" onClick={() => setMobileOpen(false)} />}
      <aside
        className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}
        style={sidebarStyle as React.CSSProperties}
      >
        <div className="brand-row">
          <Link href="/" className="brand" onClick={() => setMobileOpen(false)} title="Hermes Workspace" aria-label="Hermes Workspace">
            <span className="brand-mark"><Sparkles size={17} /></span>
            {!compact && (
              <span className="sidebar-label">
                Hermes<span className="brand-soft"> Workspace</span>
              </span>
            )}
          </Link>
          <div className="brand-actions">
            <button
              className="icon-button sidebar-toggle"
              onClick={toggleMode}
              aria-label={compact ? 'Déployer la barre latérale' : 'Rétracter la barre latérale'}
              title={compact ? 'Déployer' : 'Rétracter'}
              onMouseEnter={(event) => showTooltip(compact ? 'Déployer' : 'Rétracter', event)}
              onMouseLeave={hideTooltip}
              onFocus={(event) => showTooltip(compact ? 'Déployer' : 'Rétracter', event)}
              onBlur={hideTooltip}
            >
              {compact ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
            </button>
            <button
              className="icon-button"
              onClick={() => setPaletteOpen(true)}
              aria-label="Recherche rapide (⌘K)"
              title="Recherche rapide (⌘K)"
              onMouseEnter={(event) => showTooltip('Recherche rapide (⌘K)', event)}
              onMouseLeave={hideTooltip}
            >
              <Search size={16} />
            </button>
            <button className="icon-button mobile-close" onClick={() => setMobileOpen(false)} aria-label="Fermer le menu">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* CONVERSATIONS EN HAUT — c'est la zone principale de la sidebar. */}
        <div className="sidebar-conversations-top">
          <div className="sidebar-section-label conversations-header sidebar-label">
            <span>{showFullConversationList ? 'Conversations' : 'Récents'}</span>
            {!compact && showFullConversationList && (
              <span className="sidebar-section-count">
                {totalGroups} agent{totalGroups > 1 ? 's' : ''} · {filteredConversations.length} conv.
              </span>
            )}
          </div>

          {!compact && (
            <Link
              href="/chat"
              className="new-chat"
              onClick={startNewConversation}
              aria-label="Nouvelle conversation"
              onMouseEnter={(event) => showTooltip('Nouvelle conversation (⌘K)', event)}
              onMouseLeave={hideTooltip}
              onFocus={(event) => showTooltip('Nouvelle conversation (⌘K)', event)}
              onBlur={hideTooltip}
            >
              <Plus size={17} />
              <span className="sidebar-label">Nouvelle conversation</span>
              <span className="shortcut sidebar-label">⌘ K</span>
            </Link>
          )}

          {compact && (
            <Link
              href="/chat"
              className="new-chat compact-new-chat"
              onClick={startNewConversation}
              aria-label="Nouvelle conversation"
              title="Nouvelle conversation"
            >
              <Plus size={18} />
            </Link>
          )}

          {!compact && showFullConversationList && (
            <>
              <div className="sidebar-search-row">
                <div className="sidebar-search">
                  <Search size={14} />
                  <input value={query} onChange={onSearchChange} placeholder="Rechercher…" aria-label="Rechercher une conversation" />
                  {query && (
                    <button className="search-clear" onClick={() => setQuery('')} aria-label="Effacer la recherche" type="button">
                      <X size={12} />
                    </button>
                  )}
                </div>
                <label className="sidebar-agent-filter">
                  <span className="sr-only">Filtrer par agent</span>
                  <select value={agentFilter} onChange={onAgentFilterChange}>
                    <option value="all">Tous ({totalConversations})</option>
                    {Array.from(
                      new Set([
                        ...agents.map((agent) => agent.name),
                        ...filteredConversations
                          .map((conversation) => conversation.agent_name || '')
                          .filter((value) => !agents.some((agent) => agent.name === value)),
                      ]),
                    )
                      .filter(Boolean)
                      .map((name) => (
                        <option key={name} value={name}>
                          {name}
                        </option>
                      ))}
                    <option value="">Hermes Core</option>
                  </select>
                  <ChevronDown size={12} />
                </label>
              </div>
            </>
          )}

          {!compact && showFullConversationList && groupedConversations.length === 0 && (
            <div className="history-empty">
              {conversations.length === 0
                ? 'Aucune conversation. Lancez-en une avec « Nouvelle conversation ».'
                : 'Aucun résultat pour cette recherche.'}
            </div>
          )}

          <div className={`sidebar-conversation-scroll ${showFullConversationList ? 'full' : 'compact'}`}>
            {!compact && showFullConversationList &&
              groupedConversations.map((group) => {
                const isCollapsed = collapsedGroups[group.key] === true;
                return (
                  <section key={group.key} className={`agent-group ${isCollapsed ? 'collapsed' : ''}`}>
                    <button
                      className="agent-group-header"
                      aria-expanded={!isCollapsed}
                      onClick={() => toggleGroup(group.key)}
                      onMouseEnter={(event) => showTooltip(isCollapsed ? 'Déplier le groupe' : 'Replier le groupe', event)}
                      onMouseLeave={hideTooltip}
                    >
                      <span
                        className="agent-avatar-bubble"
                        style={{ background: group.palette.gradient, color: group.palette.text, boxShadow: `inset 0 0 0 1px ${group.palette.ring}` }}
                      >
                        {initials(group.label)}
                      </span>
                      <span className="agent-group-meta">
                        <strong>{group.label}</strong>
                        <small>{group.model}</small>
                      </span>
                      <span className="agent-group-count">{group.items.length}</span>
                      <span className="agent-group-caret">{isCollapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}</span>
                    </button>
                    {!isCollapsed && (
                      <div className="agent-group-conversations">
                        {group.items.map((conversation) => (
                          <ConversationCard
                            key={conversation.id}
                            conversation={conversation}
                            agent={group.agent}
                            paletteEntry={group.palette}
                            active={conversation.id === activeConversationId}
                            menuOpen={menuState?.conversationId === conversation.id && menuState.open}
                            renaming={renamingId === conversation.id}
                            renameDraft={renameDraft}
                            busy={busyId === conversation.id}
                            onOpen={openConversation}
                            onToggleMenu={toggleMenu}
                            onRename={beginRename}
                            onRenameChange={setRenameDraft}
                            onRenameSubmit={commitRename}
                            onRenameCancel={cancelRename}
                            onRenameKey={handleRenameKey}
                            onDelete={deleteConversation}
                            onShowTooltip={showTooltip}
                            onHideTooltip={hideTooltip}
                          />
                        ))}
                      </div>
                    )}
                  </section>
                );
              })}

            {!compact && !showFullConversationList &&
              (compactRecent.length === 0 ? (
                <div className="history-empty">
                  {conversations.length === 0
                    ? 'Aucune conversation.'
                    : 'Aucun résultat pour cette recherche.'}
                </div>
              ) : (
                <>
                  {compactRecent.map((conversation) => (
                    <CompactConversationRow
                      key={conversation.id}
                      conversation={conversation}
                      active={conversation.id === activeConversationId}
                      onOpen={openConversation}
                    />
                  ))}
                  {conversations.length > compactRecent.length && (
                    <Link href="/chat" className="sidebar-show-all" onClick={() => setMobileOpen(false)}>
                      Voir toutes les conversations ({conversations.length})
                      <ChevronRight size={13} />
                    </Link>
                  )}
                </>
              ))}
          </div>
        </div>

        {/* NAVIGATION — sous les conversations. */}
        {!compact && <div className="sidebar-section-label nav-header sidebar-label">Workspace</div>}
        {!compact && (
          <nav className="sidebar-nav" aria-label="Navigation principale">
            {navigation.map(({ href, label, icon: Icon }) => {
              const active = pathname === href || (href === '/chat' && Boolean(pathname?.startsWith('/chat')));
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  className={active ? 'nav-link active' : 'nav-link'}
                  onMouseEnter={(event) => showTooltip(label, event)}
                  onMouseLeave={hideTooltip}
                  onFocus={(event) => showTooltip(label, event)}
                  onBlur={hideTooltip}
                >
                  <Icon size={17} strokeWidth={1.8} />
                  {!compact && <span className="sidebar-label">{label}</span>}
                  {!compact && href === '/chat' && <span className="nav-badge">{totalConversations || ''}</span>}
                  {compact && href === '/chat' && <span className="nav-badge-compact">{totalConversations || ''}</span>}
                </Link>
              );
            })}
          </nav>
        )}

        {/* Bouton "Nouvelle conversation" réduit, près de la nav. */}

        <div className="sidebar-footer">
          {!compact && (
            <div className="connection-card">
              <span className="status-dot online" />
              <div className="sidebar-label">
                <strong>Hermes opérationnel</strong>
                <small>Daemon · MCP · n8n</small>
              </div>
              <ChevronDown size={14} className="muted-icon" />
            </div>
          )}
          <div className="user-row">
            <span className="avatar">YO</span>
            {!compact && (
              <span className="sidebar-label">
                <strong>Younes</strong>
                <small>Workspace privé</small>
              </span>
            )}
            <button
              className="icon-button theme-toggle"
              onClick={() => setTheme((value) => (value === 'dark' ? 'light' : value === 'light' ? 'system' : 'dark'))}
              aria-label={theme === 'dark' ? 'Activer le mode clair' : theme === 'light' ? 'Activer le mode système' : 'Activer le mode sombre'}
              title={theme === 'dark' ? 'Mode sombre' : theme === 'light' ? 'Mode clair' : 'Mode système'}
              onMouseEnter={(event) => showTooltip(theme === 'dark' ? 'Mode sombre → clair' : theme === 'light' ? 'Mode clair → système' : 'Mode système → sombre', event)}
              onMouseLeave={hideTooltip}
              onFocus={(event) => showTooltip(theme === 'dark' ? 'Mode sombre → clair' : theme === 'light' ? 'Mode clair → système' : 'Mode système → sombre', event)}
              onBlur={hideTooltip}
            >
              {theme === 'dark' ? <Moon size={15} /> : theme === 'light' ? <Sun size={15} /> : <Monitor size={15} />}
            </button>
            {!compact && (
              <button
                className="icon-button sidebar-label"
                onClick={logout}
                aria-label="Se déconnecter"
                title="Se déconnecter"
                onMouseEnter={(event) => showTooltip('Se déconnecter', event)}
                onMouseLeave={hideTooltip}
                onFocus={(event) => showTooltip('Se déconnecter', event)}
                onBlur={hideTooltip}
              >
                <LogOut size={15} />
              </button>
            )}
            {!compact && <Boxes size={15} className="muted-icon sidebar-label" />}
          </div>
        </div>

        {!compact && (
          <div
            className="sidebar-resize-handle"
            role="separator"
            aria-orientation="vertical"
            aria-label="Redimensionner la barre latérale"
            aria-valuenow={sidebarWidth}
            aria-valuemin={SIDEBAR_MIN_WIDTH}
            aria-valuemax={SIDEBAR_MAX_WIDTH}
            title="Glisser pour redimensionner · Double-clic pour réinitialiser"
            onMouseDown={beginResize}
            onDoubleClick={resetSidebarWidth}
          >
            <span className="sidebar-resize-grip" aria-hidden="true" />
          </div>
        )}
      </aside>

      <main className="workspace-main">{children}</main>

      {tooltip && (
        <div className="sidebar-tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
          {tooltip.text}
        </div>
      )}

      {deleteTarget && (
        <ConfirmDialog
          open
          variant="danger"
          title="Supprimer la conversation"
          message={`Supprimer définitivement « ${deleteTarget.title} » ? Cette action est irréversible.`}
          confirmLabel="Supprimer"
          cancelLabel="Annuler"
          loading={busyId === deleteTarget.id}
          onClose={() => setDeleteTarget(null)}
          onConfirm={() => void confirmDelete()}
        />
      )}

      {paletteOpen && (
        <CommandPalette
          conversations={conversations.map((c) => ({ id: c.id, title: c.title }))}
          onNewConversation={() => { setPaletteOpen(false); window.location.assign('/chat?new=1'); }}
          onClose={() => setPaletteOpen(false)}
        />
      )}
    </div>
  );
}

type ConversationCardProps = {
  conversation: ConversationSummary;
  agent: Agent | undefined;
  paletteEntry: AgentPalette;
  active: boolean;
  menuOpen: boolean;
  renaming: boolean;
  renameDraft: string;
  busy: boolean;
  onOpen: (conversation: ConversationSummary, event: MouseEvent) => void;
  onToggleMenu: (conversationId: string, event: MouseEvent<HTMLButtonElement>) => void;
  onRename: (conversation: ConversationSummary) => void;
  onRenameChange: (value: string) => void;
  onRenameSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onRenameCancel: () => void;
  onRenameKey: (event: ReactKeyboardEvent<HTMLInputElement>) => void;
  onDelete: (conversation: ConversationSummary) => void;
  onShowTooltip: (text: string, event: MouseEvent<HTMLElement> | React.FocusEvent<HTMLElement>) => void;
  onHideTooltip: () => void;
};

function ConversationCard(props: ConversationCardProps) {
  const {
    conversation,
    agent,
    paletteEntry,
    active,
    menuOpen,
    renaming,
    renameDraft,
    busy,
    onOpen,
    onToggleMenu,
    onRename,
    onRenameChange,
    onRenameSubmit,
    onRenameCancel,
    onRenameKey,
    onDelete,
    onShowTooltip,
    onHideTooltip,
  } = props;

  const agentName = conversation.agent_name || 'Hermes Core';
  const modelLabel = conversation.model || agent?.model || 'Modèle global';
  const contextValue = contextLabel(conversation.context_tokens);
  const updatedRelative = formatRelativeDate(conversation.updated_at);
  const toolCount = conversation.tool_names?.length || 0;
  const [expanded, setExpanded] = useState(false);

  const cardClasses = `conversation-card ${active ? 'is-active' : ''} ${busy ? 'is-busy' : ''} ${expanded ? 'is-expanded' : 'is-collapsed'}`;

  function toggleExpanded(event: MouseEvent<HTMLButtonElement>) {
    event.stopPropagation();
    event.preventDefault();
    setExpanded((value) => !value);
  }

  return (
    <article className={cardClasses} data-active={active} data-expanded={expanded}>
      <button
        type="button"
        className="conversation-card-main"
        onClick={(event) => onOpen(conversation, event as unknown as MouseEvent)}
        aria-label={`Ouvrir « ${conversation.title} » avec ${agentName}`}
      >
        <span
          className="agent-avatar-bubble small"
          style={{ background: paletteEntry.gradient, color: paletteEntry.text, boxShadow: `inset 0 0 0 1px ${paletteEntry.ring}` }}
          aria-hidden="true"
        >
          {initials(agentName)}
        </span>
        <span className="conversation-card-body">
          {renaming ? (
            <form className="conversation-rename" onSubmit={onRenameSubmit}>
              <input
                autoFocus
                value={renameDraft}
                onChange={(event) => onRenameChange(event.target.value)}
                onKeyDown={onRenameKey}
                onClick={(event) => event.stopPropagation()}
                onBlur={onRenameCancel}
                aria-label="Nouveau titre"
              />
            </form>
          ) : (
            <span className="conversation-card-title">
              {truncate(conversation.title, 60)}
            </span>
          )}
          <span className="conversation-card-meta">
            <span className="meta-agent">{agentName}</span>
            <span className="meta-dot" aria-hidden="true">·</span>
            <span className="meta-relative">{updatedRelative}</span>
          </span>
          <div className="conversation-card-details">
            <span className="conversation-card-preview placeholder">{contextValue ? `${modelLabel} · ${contextValue}` : modelLabel}</span>
            <span className="conversation-card-footer">
              <span className="meta-model">{modelLabel}</span>
              {contextValue && (
                <>
                  <span className="meta-dot" aria-hidden="true">·</span>
                  <span className="meta-context">{contextValue}</span>
                </>
              )}
              {toolCount > 0 && (
                <>
                  <span className="meta-dot" aria-hidden="true">·</span>
                  <span className="meta-tools" aria-label={`${toolCount} outil${toolCount > 1 ? 's' : ''}`}>
                    {toolCount} outil{toolCount > 1 ? 's' : ''}
                  </span>
                </>
              )}
              {active && <span className="meta-active">Active</span>}
            </span>
          </div>
        </span>
      </button>
      <button
        type="button"
        className="conversation-expand-button"
        aria-label={expanded ? 'Réduire les détails' : 'Voir les détails'}
        aria-expanded={expanded}
        title={expanded ? 'Réduire' : 'Détails'}
        onClick={toggleExpanded}
        onMouseEnter={(event) => onShowTooltip(expanded ? 'Réduire' : 'Détails', event)}
        onMouseLeave={onHideTooltip}
      >
        <ChevronDown size={14} className="conversation-expand-icon" />
      </button>
      <button
        type="button"
        className="conversation-menu-button"
        data-conversation-menu-button
        onClick={(event) => onToggleMenu(conversation.id, event)}
        aria-label="Actions de la conversation"
        onMouseEnter={(event) => onShowTooltip('Actions', event)}
        onMouseLeave={onHideTooltip}
      >
        <MoreHorizontal size={15} />
      </button>
      {menuOpen && (
        <div className="conversation-menu" data-conversation-menu role="menu">
          <button
            type="button"
            role="menuitem"
            onClick={(event) => {
              event.preventDefault();
              onRename(conversation);
            }}
          >
            <Pencil size={13} /> Renommer
          </button>
          <Link
            href={`/agents?name=${encodeURIComponent(agentName)}`}
            role="menuitem"
            onClick={(event) => event.stopPropagation()}
          >
            <Bot size={13} /> Paramètres de l’agent
          </Link>
          <button
            type="button"
            role="menuitem"
            className="danger"
            onClick={(event) => {
              event.preventDefault();
              void onDelete(conversation);
            }}
            disabled={busy}
          >
            <Trash2 size={13} /> Supprimer
          </button>
        </div>
      )}
    </article>
  );
}

type CompactRowProps = {
  conversation: ConversationSummary;
  active: boolean;
  onOpen: (conversation: ConversationSummary, event: MouseEvent) => void;
};

function CompactConversationRow({ conversation, active, onOpen }: CompactRowProps) {
  const agentName = conversation.agent_name || 'Hermes Core';
  const paletteEntry = paletteFor(agentName);
  return (
    <button
      type="button"
      className={`compact-row ${active ? 'is-active' : ''}`}
      onClick={(event) => onOpen(conversation, event as unknown as MouseEvent)}
      aria-label={`Ouvrir « ${conversation.title} » avec ${agentName}`}
    >
      <span
        className="agent-avatar-bubble tiny"
        style={{ background: paletteEntry.gradient, color: paletteEntry.text, boxShadow: `inset 0 0 0 1px ${paletteEntry.ring}` }}
        aria-hidden="true"
      >
        {initials(agentName)}
      </span>
      <span className="compact-row-meta">
        <strong>{truncate(conversation.title, 32)}</strong>
        <small><span className="compact-agent-name">{agentName}</span><span aria-hidden="true"> · </span>{formatRelativeDate(conversation.updated_at)}</small>
      </span>
    </button>
  );
}
