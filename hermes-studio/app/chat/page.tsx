'use client';

import { Sparkles, Terminal, Bot, WandSparkles, ChevronDown, X, Save } from 'lucide-react';
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Agent, Attachment, Conversation, ConversationMessage, Tool, api } from '../lib/api';
import Markdown from './components/Markdown';
import { useChatStream } from './useChatStream';
import ToolCallCard from './components/ToolCallCard';
import ReasoningBlock from './components/ReasoningBlock';
import MessageBubble from './components/MessageBubble';
import Composer from './components/Composer';
import ChatHeader from './components/ChatHeader';

type ChatMessage = ConversationMessage;
type ProviderStatus = { minimax_configured: boolean; model: string; mcp_ready: boolean };
type ConversationSettingsSnapshot = { model: string; tools: string[]; contextTokens: number };

const corePrompt = 'Tu es un orchestrateur précis. Décompose les demandes complexes, utilise web_search/web_fetch pour les informations récentes et mcp_terminal pour diagnostiquer le workspace. N’exécute jamais une action sensible sans demander une confirmation explicite.';
const coreTools = ['mcp_filesystem', 'mcp_github', 'mcp_terminal', 'n8n_webhook', 'server_diagnostics', 'web_search', 'web_fetch'];
const modelOptions = ['MiniMax-M3', 'MiniMax-M2.7', 'MiniMax-M2.7-highspeed', 'MiniMax-M2.5', 'MiniMax-M2.1', 'MiniMax-M2'];
const contextOptions = [
  { value: 128_000, label: '128K' },
  { value: 200_000, label: '200K' },
  { value: 512_000, label: '512K' },
  { value: 1_000_000, label: '1M' },
];

const suggestions = [
  { icon: Terminal, label: 'Analyse l’état de mon installation Hermes', hint: 'Système' },
  { icon: Bot, label: 'Crée un agent spécialisé DevOps', hint: 'Agents' },
  { icon: Sparkles, label: 'Explique-moi l’architecture du workspace', hint: 'Doc' },
  { icon: WandSparkles, label: 'Planifie mon sprint de la semaine', hint: 'Plan' },
];

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
  const [initialising, setInitialising] = useState(true);
  const [copied, setCopied] = useState<number | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tools, setTools] = useState<Tool[]>([]);
  const [selectedAgentName, setSelectedAgentName] = useState('');
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedTools, setSelectedTools] = useState<string[]>(coreTools);
  const [pendingAttachments, setPendingAttachments] = useState<Attachment[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [contextTokens, setContextTokens] = useState(200_000);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settingsSnapshot, setSettingsSnapshot] = useState<ConversationSettingsSnapshot | null>(null);
  const [savingSettings, setSavingSettings] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesListRef = useRef<HTMLDivElement>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const [isPinnedToBottom, setIsPinnedToBottom] = useState(true);
  const [showJumpToBottom, setShowJumpToBottom] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [pendingUserMessage, setPendingUserMessage] = useState<ChatMessage | null>(null);
  const [pendingApprovals, setPendingApprovals] = useState<number[]>([]);

  const { streamState, startStream, stopStream, resumeAfterApproval } = useChatStream({
    onDone: (content, model) => {
      if (pendingUserMessage) {
        const completed = [...messages, pendingUserMessage, { role: 'assistant' as const, content, time: 'maintenant' }];
        setMessages(completed);
        setPendingUserMessage(null);
        void persistConversation(completed);
      }
    },
    onError: (message) => {
      if (pendingUserMessage) {
        const failed = [...messages, pendingUserMessage, { role: 'assistant' as const, content: message, time: 'erreur' }];
        setMessages(failed);
        setPendingUserMessage(null);
        void persistConversation(failed);
      }
    },
    onApprovalRequired: (approvalIds) => {
      // Stocke les approval IDs pour les boutons inline dans ToolCallCard
      setPendingApprovals(approvalIds);
    },
  });

  const canSend = (input.trim().length > 0 || pendingAttachments.length > 0) && !streamState.isStreaming && !initialising;
  const isLoading = streamState.isStreaming;
  const activeAgent = agents.find((agent) => agent.name === selectedAgentName);
  const activeName = activeAgent?.name || 'Hermes Core';
  const activeModel = selectedModel || activeAgent?.model || providerStatus?.model || 'Modèle à configurer';

  useEffect(() => {
    if (!isPinnedToBottom) return;
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages, isLoading, isPinnedToBottom, streamState.content]);

  const resizeComposer = useCallback(() => {
    const textarea = composerRef.current;
    if (!textarea) return;
    textarea.style.height = 'auto';
    const next = Math.min(textarea.scrollHeight, 240);
    textarea.style.height = `${next}px`;
  }, []);

  useLayoutEffect(() => {
    resizeComposer();
  }, [input, resizeComposer]);

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
          const existing = await api.get<{ conversations: Conversation[] }>('api/conversations');
          if (cancelled) return;
          const recent = (existing.conversations || []).find((conv) => {
            if (conv.title !== 'Nouvelle conversation') return false;
            const updated = new Date(conv.updated_at).getTime();
            if (Number.isNaN(updated) || Date.now() - updated > 60 * 60 * 1000) return false;
            if (requestedAgent && (conv.agent_name || '') !== requestedAgent) return false;
            return true;
          });
          if (recent) {
            const full = await api.get<Conversation>(`api/conversations/${encodeURIComponent(recent.id)}`);
            if (cancelled) return;
            const hasUserMessage = (full.messages || []).some((msg) => msg.role === 'user');
            if (!hasUserMessage) {
              applyConversation(full, agent?.name || '');
              window.history.replaceState(null, '', `/chat?conversation=${full.id}`);
              return;
            }
          }
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
    setPendingAttachments([]);
    setMessages(conversation.messages || []);
    setIsPinnedToBottom(true);
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

  async function uploadFiles(fileList: FileList | File[]) {
    if (!conversationId || initialising) return;
    const files = Array.from(fileList);
    if (!files.length) return;
    setUploading(true);
    setUploadError('');
    try {
      const uploaded: Attachment[] = [];
      for (const file of files) {
        uploaded.push(await api.upload<Attachment>(`api/conversations/${encodeURIComponent(conversationId)}/attachments`, file));
      }
      setPendingAttachments((current) => [...current, ...uploaded]);
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Upload impossible.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  }

  function removePendingAttachment(id: string) {
    setPendingAttachments((current) => current.filter((attachment) => attachment.id !== id));
    void api.delete(`api/conversations/${encodeURIComponent(conversationId)}/attachments/${id}`).catch(() => undefined);
  }

  async function sendMessage() {
    if (!canSend) return;
    const content = input.trim();
    setInput('');
    const attachments = pendingAttachments.length ? pendingAttachments : undefined;
    setPendingAttachments([]);

    const userMessage: ChatMessage = { role: 'user', content, time: 'maintenant', ...(attachments ? { attachments } : {}) };
    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setPendingUserMessage(userMessage);
    setStopping(false);

    const activeAgentId = agents.find((a) => a.name === selectedAgentName)?.id;
    void startStream({
      messages: nextMessages.map(({ role, content: c, reasoning_details, attachments: atts }) => ({ role, content: c, ...(reasoning_details?.length ? { reasoning_details } : {}), ...(atts?.length ? { attachments: atts } : {}) })),
      agent_id: activeAgentId,
      agent_name: selectedAgentName || undefined,
      model: selectedModel || undefined,
      conversation_id: conversationId ? Number(conversationId) : undefined,
      tools_schema: undefined, // MVP : schéma déduit côté serveur depuis tool_names
      tool_names: selectedTools,
      context_tokens: contextTokens,
    });
  }

  async function resolveApproval(approvalId: number, decision: 'approve' | 'reject') {
    try {
      await api.post(`api/approvals/${approvalId}/resolve`, { decision });
      setPendingApprovals((current) => current.filter((id) => id !== approvalId));
      // Le tool_result arrivera via le events bus (Phase 7) ou via re-stream si on relance un tour
      // Pour MVP, on notifie et on attend que l'utilisateur relance
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : 'Approbation échouée.');
    }
  }

  function stopGeneration() {
    if (!streamState.isStreaming) return;
    setStopping(true);
    stopStream();
    if (pendingUserMessage) {
      const interrupted = [...messages, pendingUserMessage, { role: 'assistant' as const, content: '⏹ Génération interrompue.', time: 'interrompu' }];
      setMessages(interrupted);
      setPendingUserMessage(null);
      void persistConversation(interrupted);
    }
    setStopping(false);
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
    if (streamState.isStreaming) return;
    const lastUserIndex = [...messages].map((message) => message.role).lastIndexOf('user');
    if (lastUserIndex < 0) return;
    const sliced = messages.slice(0, lastUserIndex + 1);
    const userMsg = sliced[sliced.length - 1];
    setMessages(sliced);
    setPendingUserMessage(userMsg);
    setStopping(false);
    void startStream({
      messages: sliced.map(({ role, content: c, reasoning_details, attachments: atts }) => ({ role, content: c, ...(reasoning_details?.length ? { reasoning_details } : {}), ...(atts?.length ? { attachments: atts } : {}) })),
      agent_name: selectedAgentName || undefined,
      model: selectedModel || undefined,
      tool_names: selectedTools,
      context_tokens: contextTokens,
    });
  }

  function copyMessage(index: number, content: string) {
    navigator.clipboard?.writeText(content);
    setCopied(index);
    window.setTimeout(() => setCopied(null), 1500);
  }

  return (
    <div className="chat-layout">
      <ChatHeader 
        agents={agents}
        selectedAgentName={selectedAgentName}
        onChooseAgent={(name) => void chooseAgent(name)}
        onOpenSettings={openConversationSettings}
        onNewConversation={() => void createNewConversation()}
      />
      
      <div className="chat-body">
        <section className="messages-column">
          <div
            className="message-list"
            ref={messagesListRef}
            onScroll={(event) => {
              const el = event.currentTarget;
              const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
              const nearBottom = distanceFromBottom < 120;
              setIsPinnedToBottom(nearBottom);
              setShowJumpToBottom(!nearBottom && messages.length > 2);
            }}
          >
            {initialising && <div className="loading-state">Chargement de la conversation…</div>}
            
            {!initialising && messages.length === 0 && (
              <div className="chat-empty-state">
                <span className="empty-mark"><Sparkles size={24} /></span>
                <h2>Que voulez-vous construire ?</h2>
                <div className="empty-suggestions">
                  {suggestions.map((s) => (
                    <button key={s.label} type="button" className="empty-suggestion" onClick={() => { setInput(s.label); composerRef.current?.focus(); }}>
                      <span className="empty-suggestion-icon"><s.icon size={15} /></span>
                      <span><strong>{s.label}</strong><small>{s.hint}</small></span>
                    </button>
                  ))}
                </div>
              </div>
            )}
            
            {messages.map((message, index) => (
              <MessageBubble 
                key={`${message.time}-${index}`} 
                message={message} 
                index={index} 
                onCopy={copyMessage} 
                onRegenerate={regenerate} 
                copied={copied === index} 
              />
            ))}
            
            {isLoading && (
              <div className="message assistant-message">
                <span className="message-avatar hermes-avatar"><Sparkles size={15} /></span>
                <div className="message-content">
                  <div className="message-meta"><strong>{activeName}</strong><span>{stopping ? 'arrêt en cours…' : 'répond'}</span></div>
                  {streamState.reasoning.length > 0 && <ReasoningBlock details={streamState.reasoning} />}
                  {streamState.tools.map((t, i) => (
                    <ToolCallCard
                      key={i}
                      tool={t.tool}
                      status={t.status}
                      args={t.args}
                      result={t.result}
                      {...(t.approval_id !== undefined ? { approval_id: t.approval_id } : {})}
                      onApprove={(aid) => void resolveApproval(aid, 'approve')}
                      onReject={(aid) => void resolveApproval(aid, 'reject')}
                    />
                  ))}
                  {streamState.content ? (
                    <div className="message-text"><Markdown>{streamState.content}</Markdown></div>
                  ) : (
                    <div className="thinking"><span /><span /><span /></div>
                  )}
                  {streamState.isStreaming && <span className="streaming-cursor" aria-hidden="true" />}
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} className="messages-end-spacer" />
          </div>
          
          {showJumpToBottom && (
            <button
              type="button"
              className="jump-to-bottom"
              aria-label="Aller en bas"
              onClick={() => {
                setIsPinnedToBottom(true);
                messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
              }}
            >
              <ChevronDown size={16} />
            </button>
          )}
          
          <Composer 
            input={input}
            setInput={setInput}
            isLoading={isLoading}
            canSend={canSend}
            onSend={() => void sendMessage()}
            onStop={stopGeneration}
            composerRef={composerRef}
            fileInputRef={fileInputRef}
            pendingAttachments={pendingAttachments}
            uploading={uploading}
            uploadError={uploadError}
            onUpload={(files) => void uploadFiles(files)}
            onRemoveAttachment={removePendingAttachment}
            activeName={activeName}
          />
        </section>
      </div>

      {/* Settings Modal */}
      {settingsOpen && (
        <div className="modal-backdrop" onClick={cancelConversationSettings}>
          <div className="modal modal-wide conversation-settings" onClick={(event) => event.stopPropagation()}>
            <div className="modal-heading">
              <div>
                <div className="eyebrow">PARAMÈTRES DE LA CONVERSATION</div>
                <h2>Contrôler le contexte</h2>
              </div>
              <button className="icon-button" onClick={cancelConversationSettings} aria-label="Fermer"><X size={18} /></button>
            </div>
            
            <div className="conversation-config-grid">
              <label>
                Modèle
                <input list="minimax-model-options" value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)} placeholder={activeAgent?.model || providerStatus?.model || 'MiniMax-M3'} />
                <small>Vide = modèle de l’agent, puis modèle global.</small>
                <datalist id="minimax-model-options">
                  {modelOptions.map((model) => <option value={model} key={model} />)}
                </datalist>
              </label>
              <label>
                Fenêtre de contexte
                <select value={contextTokens} onChange={(event) => setContextTokens(Number(event.target.value))}>
                  {contextOptions.map((option) => <option value={option.value} key={option.value}>{option.label} tokens</option>)}
                </select>
                <small>1M est disponible selon votre accès.</small>
              </label>
            </div>
            
            <div className="conversation-tools">
              <div className="tool-picker-heading">
                <div>
                  <strong>Outils de cette conversation</strong>
                  <small>Ces outils seront indiqués à Hermes pour cette session uniquement.</small>
                </div>
                <span className="count-badge">{selectedTools.length}</span>
              </div>
              <div className="tool-picker-grid">
                {tools.map((tool) => (
                  <label className={`tool-option ${selectedTools.includes(tool.name) ? 'selected' : ''}`} key={tool.name}>
                    <input type="checkbox" checked={selectedTools.includes(tool.name)} onChange={() => toggleTool(tool.name)} />
                    <span><strong>{tool.name}</strong><small>{tool.description}</small></span>
                  </label>
                ))}
              </div>
            </div>
            
            <div className="modal-actions">
              <button className="button button-secondary" onClick={cancelConversationSettings}>Annuler</button>
              <button className="button button-primary" onClick={() => void saveConversationSettings()} disabled={savingSettings}>
                {savingSettings ? 'Enregistrement…' : <><Save size={15} /> Enregistrer</>}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
