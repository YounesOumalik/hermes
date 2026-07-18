'use client';

import { ArrowUp, Bot, Check, ChevronDown, Copy, Paperclip, Plus, RotateCcw, Save, Settings2, SlidersHorizontal, Sparkles, Square, Terminal, UserRound, WandSparkles, X } from 'lucide-react';
import type { ComponentType } from 'react';
import { useEffect, useRef, useState } from 'react';
import { Agent, Conversation, ConversationMessage, Tool, api } from '../lib/api';

type ReasoningDetail = Record<string, unknown>;
type ChatMessage = ConversationMessage;
type ProviderStatus = { minimax_configured: boolean; model: string; mcp_ready: boolean };
type ChatResult = { content: string; model: string; agent_name?: string | null; reasoning_details?: ReasoningDetail[] | null };
type ConversationSettingsSnapshot = { model: string; tools: string[]; contextTokens: number };

const corePrompt = 'Tu es un orchestrateur précis. Décompose les demandes complexes et utilise les outils uniquement lorsque cela apporte une valeur claire.';
const coreTools = ['mcp_filesystem', 'mcp_github', 'n8n_webhook'];
const modelOptions = ['MiniMax-M3', 'MiniMax-M2.7', 'MiniMax-M2.7-highspeed', 'MiniMax-M2.5', 'MiniMax-M2.1', 'MiniMax-M2'];
const contextOptions = [
  { value: 128_000, label: '128K' },
  { value: 200_000, label: '200K' },
  { value: 512_000, label: '512K' },
  { value: 1_000_000, label: '1M' },
];

function greeting(agentName?: string): ChatMessage {
  return {
    role: 'assistant',
    content: agentName
      ? `Bonjour Younes. Je suis ${agentName}. Comment puis-je vous aider ?`
      : 'Bonjour Younes. Je suis Hermes, votre workspace d’orchestration. Que voulez-vous construire aujourd’hui ?',
    time: 'maintenant',
  };
}

function contextLabel(tokens: number) {
  return tokens >= 1_000_000 ? '1M' : `${Math.round(tokens / 1000)}K`;
}

function defaultContext(model?: string | null) {
  return model?.toLowerCase().includes('m3') ? 1_000_000 : 200_000;
}

function announceConversationsChanged() {
  window.dispatchEvent(new Event('hermes:conversations-changed'));
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState('');
  const [conversationTitle, setConversationTitle] = useState('Nouvelle conversation');
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [initialising, setInitialising] = useState(true);
  const [copied, setCopied] = useState<number | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [selectedAgentName, setSelectedAgentName] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedTools, setSelectedTools] = useState<string[]>(coreTools);
  const [contextTokens, setContextTokens] = useState(200_000);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsSnapshot, setSettingsSnapshot] = useState<ConversationSettingsSnapshot | null>(null);
  const [savingSettings, setSavingSettings] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const canSend = input.trim().length > 0 && !loading && !initialising;
  const activeAgent = agents.find((agent) => agent.name === selectedAgentName);
  const activeName = activeAgent?.name || 'Hermes Core';
  const activePrompt = activeAgent?.system_prompt || corePrompt;
  const activeModel = selectedModel || activeAgent?.model || providerStatus?.model || 'Modèle à configurer';
  const providerLabel = providerStatus?.minimax_configured ? 'MiniMax connecté' : 'MiniMax à configurer';

  useEffect(() => {
    let cancelled = false;
    async function initialise() {
      const params = new URLSearchParams(window.location.search);
      const requestedConversation = params.get('conversation');
      const requestedAgent = params.get('agent') || '';
      try {
        const [agentResult, toolResult, statusResult] = await Promise.all([
          api.get<{ agents: Agent[] }>('api/agents'),
          api.get<{ tools: Tool[] }>('api/tools'),
          api.get<ProviderStatus>('api/settings/status'),
        ]);
        if (cancelled) return;
        const loadedAgents = agentResult.agents || [];
        const loadedTools = toolResult.tools || [];
        setAgents(loadedAgents);
        setTools(loadedTools);
        setProviderStatus(statusResult);

        if (requestedConversation) {
          const conversation = await api.get<Conversation>(`api/conversations/${encodeURIComponent(requestedConversation)}`);
          if (cancelled) return;
          applyConversation(conversation);
        } else {
          const agent = loadedAgents.find((item) => item.name === requestedAgent);
          const initialContext = defaultContext(agent?.model || statusResult.model);
          const conversation = await api.post<Conversation>('api/conversations', {
            title: 'Nouvelle conversation',
            agent_name: agent?.name || null,
            model: null,
            tool_names: agent?.tools?.length ? agent.tools : coreTools,
            context_tokens: initialContext,
          });
          if (cancelled) return;
          applyConversation(conversation, agent?.name || '');
          window.history.replaceState(null, '', `/chat?conversation=${conversation.id}`);
          announceConversationsChanged();
        }
      } catch (error) {
        if (!cancelled) setMessages([{ role: 'assistant', content: error instanceof Error ? error.message : 'Impossible de charger la conversation.', time: 'erreur' }]);
      } finally {
        if (!cancelled) setInitialising(false);
      }
    }
    void initialise();
    return () => { cancelled = true; };
  }, []);

  function applyConversation(conversation: Conversation, fallbackAgent = '') {
    setConversationId(conversation.id);
    setConversationTitle(conversation.title);
    setSelectedAgentName(conversation.agent_name || fallbackAgent);
    setSelectedModel(conversation.model || '');
    setSelectedTools(conversation.tool_names || coreTools);
    setContextTokens(conversation.context_tokens || defaultContext(conversation.model));
    setMessages(conversation.messages?.length ? conversation.messages : [greeting(conversation.agent_name || fallbackAgent || undefined)]);
  }

  async function persistConversation(nextMessages: ChatMessage[], titleOverride?: string) {
    if (!conversationId) return;
    const firstUserMessage = nextMessages.find((message) => message.role === 'user');
    const nextTitle = titleOverride || (conversationTitle === 'Nouvelle conversation' && firstUserMessage ? firstUserMessage.content.slice(0, 64) : conversationTitle);
    setConversationTitle(nextTitle);
    await api.put<Conversation>(`api/conversations/${encodeURIComponent(conversationId)}`, {
      title: nextTitle,
      agent_name: selectedAgentName || null,
      model: selectedModel || null,
      tool_names: selectedTools,
      context_tokens: contextTokens,
      messages: nextMessages,
    });
    announceConversationsChanged();
  }

  async function requestCompletion(nextMessages: ChatMessage[]) {
    const controller = new AbortController();
    abortRef.current = controller;
    setMessages(nextMessages);
    setLoading(true);
    try {
      const response = await api.post<ChatResult>('api/chat', {
        messages: nextMessages.map(({ role, content, reasoning_details }) => ({ role, content, ...(reasoning_details?.length ? { reasoning_details } : {}) })),
        agent_name: selectedAgentName || undefined,
        model: selectedModel || undefined,
        tool_names: selectedTools,
        context_tokens: contextTokens,
      }, { signal: controller.signal });
      if (!controller.signal.aborted) {
        const assistantMessage: ChatMessage = { role: 'assistant', content: response.content, time: 'maintenant', ...(response.reasoning_details?.length ? { reasoning_details: response.reasoning_details } : {}) };
        const completedMessages = [...nextMessages, assistantMessage];
        setMessages(completedMessages);
        void persistConversation(completedMessages);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        const errorMessage: ChatMessage = { role: 'assistant', content: error instanceof Error ? error.message : 'Impossible de joindre Hermes. Réessayez dans un instant.', time: 'erreur' };
        const failedMessages = [...nextMessages, errorMessage];
        setMessages(failedMessages);
        void persistConversation(failedMessages);
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setLoading(false);
      }
    }
  }

  async function sendMessage() {
    if (!canSend) return;
    const content = input.trim();
    setInput('');
    await requestCompletion([...messages, { role: 'user', content, time: 'maintenant' }]);
  }

  function stopGeneration() {
    abortRef.current?.abort();
    abortRef.current = null;
    setLoading(false);
  }

  async function createNewConversation() {
    stopGeneration();
    const conversation = await api.post<Conversation>('api/conversations', {
      title: 'Nouvelle conversation',
      agent_name: selectedAgentName || null,
      model: selectedModel || null,
      tool_names: selectedTools,
      context_tokens: contextTokens,
    });
    applyConversation(conversation);
    window.history.replaceState(null, '', `/chat?conversation=${conversation.id}`);
    announceConversationsChanged();
  }

  async function chooseAgent(agentName: string) {
    const agent = agents.find((item) => item.name === agentName);
    const nextTools = agent?.tools?.length ? agent.tools : coreTools;
    const nextContext = defaultContext(agent?.model || activeModel);
    setSelectedAgentName(agentName);
    setSelectedModel('');
    setSelectedTools(nextTools);
    setContextTokens(nextContext);
    const url = new URL(window.location.href);
    if (agentName) url.searchParams.set('agent', agentName); else url.searchParams.delete('agent');
    window.history.replaceState(null, '', `${url.pathname}${url.search}`);
    if (conversationId) {
      await api.put(`api/conversations/${encodeURIComponent(conversationId)}`, { agent_name: agentName || null, model: null, tool_names: nextTools, context_tokens: nextContext });
      announceConversationsChanged();
    }
  }

  async function saveConversationSettings() {
    if (!conversationId) return;
    setSavingSettings(true);
    try {
      await api.put(`api/conversations/${encodeURIComponent(conversationId)}`, { agent_name: selectedAgentName || null, model: selectedModel || null, tool_names: selectedTools, context_tokens: contextTokens });
      setSettingsOpen(false);
      announceConversationsChanged();
    } finally {
      setSavingSettings(false);
    }
  }

  function toggleTool(toolName: string) {
    setSelectedTools((current) => current.includes(toolName) ? current.filter((name) => name !== toolName) : [...current, toolName]);
  }

  function openConversationSettings() {
    setSettingsSnapshot({ model: selectedModel, tools: selectedTools, contextTokens });
    setSettingsOpen(true);
  }

  function cancelConversationSettings() {
    if (settingsSnapshot) {
      setSelectedModel(settingsSnapshot.model);
      setSelectedTools(settingsSnapshot.tools);
      setContextTokens(settingsSnapshot.contextTokens);
    }
    setSettingsOpen(false);
  }

  async function regenerate() {
    if (loading) return;
    const lastUserIndex = [...messages].map((message) => message.role).lastIndexOf('user');
    if (lastUserIndex < 0) return;
    await requestCompletion(messages.slice(0, lastUserIndex + 1));
  }

  function copyMessage(index: number, content: string) {
    navigator.clipboard?.writeText(content);
    setCopied(index);
    window.setTimeout(() => setCopied(null), 1500);
  }

  return <div className="chat-layout page">
    <header className="chat-header">
      <div className="chat-title"><span className="agent-avatar"><Sparkles size={16} /></span><div><div className="eyebrow">CONVERSATION ACTIVE</div><label className="agent-picker"><span className="sr-only">Agent actif</span><select value={selectedAgentName} onChange={(event) => void chooseAgent(event.target.value)}><option value="">Hermes Core</option>{agents.map((agent) => <option key={agent.name} value={agent.name}>{agent.name}</option>)}</select><ChevronDown size={17} /></label></div></div>
      <div className="chat-header-actions"><button className="ghost-button" onClick={openConversationSettings}><Settings2 size={16} /> Conversation</button><button className="icon-button" onClick={() => void createNewConversation()} aria-label="Nouvelle conversation"><Plus size={18} /></button></div>
    </header>
    <div className="chat-body">
      <section className="messages-column">
        <div className="context-strip"><span><span className={`status-dot ${providerStatus?.minimax_configured ? 'online' : ''}`} /> {providerLabel}</span><span>{activeModel}</span><span>{contextLabel(contextTokens)} contexte</span></div>
        <div className="message-list">{initialising && <div className="loading-state">Chargement de la conversation…</div>}{messages.map((message, index) => <Message key={`${message.time}-${index}`} message={message} index={index} onCopy={copyMessage} onRegenerate={regenerate} copied={copied === index} />)}{loading && <div className="message assistant-message"><span className="message-avatar hermes-avatar"><Sparkles size={15} /></span><div className="message-content"><div className="message-meta"><strong>{activeName}</strong><span>réfléchit</span></div><div className="thinking"><span /><span /><span /></div></div></div>}</div>
        <div className="composer-wrap"><div className="suggestion-row"><button onClick={() => setInput('Analyse l’état de mon installation Hermes')}><WandSparkles size={14} /> Analyser mon installation</button><button onClick={() => setInput('Crée un agent spécialisé pour mon projet')}><Bot size={14} /> Créer un agent</button></div><form className="composer" onSubmit={(event) => { event.preventDefault(); void sendMessage(); }}><textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void sendMessage(); } }} placeholder={`Écrivez une instruction à ${activeName}…`} rows={2} aria-label="Message à Hermes" /><div className="composer-toolbar"><button className="icon-button" aria-label="Ajouter un fichier (bientôt disponible)" title="Pièces jointes bientôt disponibles" disabled><Paperclip size={17} /></button><span className="composer-hint">Entrée pour envoyer · ⇧ Entrée pour une nouvelle ligne</span><button className={`send-button ${canSend ? 'ready' : ''}`} type={loading ? 'button' : 'submit'} onClick={loading ? stopGeneration : undefined} disabled={!canSend && !loading} aria-label={loading ? 'Arrêter' : 'Envoyer'}>{loading ? <Square size={15} fill="currentColor" /> : <ArrowUp size={17} />}</button></div></form><p className="composer-disclaimer">Hermes peut faire des erreurs. Vérifiez les actions importantes.</p></div>
      </section>
      <aside className="context-panel"><div className="context-heading"><div><div className="eyebrow">CONTEXTE</div><h3>{conversationTitle}</h3></div><button className="icon-button" onClick={openConversationSettings} aria-label="Paramètres de la conversation"><SlidersHorizontal size={16} /></button></div><div className="context-agent"><span className="large-agent-avatar"><Sparkles size={20} /></span><div><strong>{activeName}</strong><small>{activeModel} · {contextLabel(contextTokens)}</small></div><Check size={16} className="text-success" /></div><div className="context-section"><div className="context-section-title"><span>Outils actifs</span><span className="count-badge">{selectedTools.length}</span></div>{selectedTools.map((tool, index) => <ContextTool icon={[Terminal, GitHubMark, WandSparkles][index % 3]} name={tool} status="Prêt" key={tool} />)}</div><div className="context-section"><div className="context-section-title"><span>Instructions</span><a className="text-link" href="/agents">Modifier</a></div><p className="context-note">{activePrompt}</p></div><div className="context-footer"><span className="status-dot online" /> Conversation synchronisée</div></aside>
    </div>
    {settingsOpen && <div className="modal-backdrop" onClick={cancelConversationSettings}><div className="modal modal-wide conversation-settings" onClick={(event) => event.stopPropagation()}><div className="modal-heading"><div><div className="eyebrow">PARAMÈTRES DE LA CONVERSATION</div><h2>Contrôler le contexte</h2></div><button className="icon-button" onClick={cancelConversationSettings} aria-label="Fermer"><X size={18} /></button></div><div className="conversation-config-grid"><label>Modèle MiniMax<input list="minimax-model-options" value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)} placeholder={activeAgent?.model || providerStatus?.model || 'MiniMax-M3'} /><small>Vide = modèle de l’agent, puis modèle global.</small><datalist id="minimax-model-options">{modelOptions.map((model) => <option value={model} key={model} />)}</datalist></label><label>Fenêtre de contexte<select value={contextTokens} onChange={(event) => setContextTokens(Number(event.target.value))}>{contextOptions.map((option) => <option value={option.value} key={option.value}>{option.label} tokens</option>)}</select><small>1M est disponible selon votre accès MiniMax M3.</small></label></div><div className="conversation-tools"><div className="tool-picker-heading"><div><strong>Outils de cette conversation</strong><small>Ces outils seront indiqués à Hermes pour cette session uniquement.</small></div><span className="count-badge">{selectedTools.length}</span></div><div className="tool-picker-grid">{tools.map((tool) => <label className={`tool-option ${selectedTools.includes(tool.name) ? 'selected' : ''}`} key={tool.name}><input type="checkbox" checked={selectedTools.includes(tool.name)} onChange={() => toggleTool(tool.name)} /><span><strong>{tool.name}</strong><small>{tool.description}</small></span></label>)}</div></div><div className="modal-actions"><button className="button button-secondary" onClick={cancelConversationSettings}>Annuler</button><button className="button button-primary" onClick={() => void saveConversationSettings()} disabled={savingSettings}>{savingSettings ? 'Enregistrement…' : <><Save size={15} /> Enregistrer</>}</button></div></div></div>}
  </div>;
}

function Message({ message, index, onCopy, onRegenerate, copied }: { message: ChatMessage; index: number; onCopy: (index: number, content: string) => void; onRegenerate: () => void; copied: boolean }) {
  const user = message.role === 'user';
  return <div className={`message ${user ? 'user-message' : 'assistant-message'}`}><span className={`message-avatar ${user ? 'user-avatar' : 'hermes-avatar'}`}>{user ? <UserRound size={15} /> : <Sparkles size={15} />}</span><div className="message-content"><div className="message-meta"><strong>{user ? 'Vous' : 'Hermes'}</strong><span>{message.time}</span></div><div className="message-text">{message.content}</div>{!user && <div className="message-actions"><button onClick={() => onCopy(index, message.content)}><Copy size={13} /> {copied ? 'Copié' : 'Copier'}</button><button onClick={onRegenerate}><RotateCcw size={13} /> Régénérer</button></div>}</div></div>;
}

function ContextTool({ icon: Icon, name, status }: { icon: ComponentType<{ size?: string | number }>; name: string; status: string }) {
  return <div className="context-tool"><span className="tool-mini-icon"><Icon size={14} /></span><span><strong>{name}</strong><small>{status}</small></span><span className="status-dot online" /></div>;
}

function GitHubMark({ size = 14 }: { size?: string | number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3.3-.4 6.8-1.6 6.8-7A5.5 5.5 0 0 0 19.3 4 5.1 5.1 0 0 0 19.2.4S18 0 15 2.1a13.4 13.4 0 0 0-6 0C6 .1 4.8.4 4.8.4A5.1 5.1 0 0 0 4.7 4a5.5 5.5 0 0 0-1.5 3.8c0 5.4 3.5 6.6 6.8 7A4.8 4.8 0 0 0 9 18v4" /><path d="M9 18c-4.5 2-5-2-7-2" /></svg>;
}
