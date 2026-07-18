'use client';

import { ArrowUp, Bot, Check, ChevronDown, Copy, Paperclip, Plus, RotateCcw, SlidersHorizontal, Sparkles, Square, Terminal, UserRound, WandSparkles } from 'lucide-react';
import type { ComponentType } from 'react';
import { useEffect, useRef, useState } from 'react';
import { Agent, api } from '../lib/api';

type ReasoningDetail = Record<string, unknown>;
type ChatMessage = { role: 'user' | 'assistant'; content: string; time: string; reasoning_details?: ReasoningDetail[] };
type ProviderStatus = { minimax_configured: boolean; model: string; mcp_ready: boolean };
type ChatResult = { content: string; model: string; agent_name?: string | null; reasoning_details?: ReasoningDetail[] | null };

const corePrompt = 'Tu es un orchestrateur précis. Décompose les demandes complexes et utilise les outils uniquement lorsque cela apporte une valeur claire.';
const coreTools = ['mcp_filesystem', 'mcp_github', 'n8n_webhook'];

function greeting(agentName?: string) {
  return {
    role: 'assistant' as const,
    content: agentName
      ? `Bonjour Younes. Je suis ${agentName}. Comment puis-je vous aider ?`
      : 'Bonjour Younes. Je suis Hermes, votre workspace d’orchestration. Que voulez-vous construire aujourd’hui ?',
    time: 'maintenant',
  };
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([greeting()]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState<number | null>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentName, setSelectedAgentName] = useState('');
  const [providerStatus, setProviderStatus] = useState<ProviderStatus | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const canSend = input.trim().length > 0 && !loading;
  const activeAgent = agents.find((agent) => agent.name === selectedAgentName);
  const activeName = activeAgent?.name || 'Hermes Core';
  const activePrompt = activeAgent?.system_prompt || corePrompt;
  const activeTools = activeAgent ? activeAgent.tools : coreTools;
  const activeModel = activeAgent?.model || providerStatus?.model || 'Modèle à configurer';
  const providerLabel = providerStatus?.minimax_configured ? 'Clé Minimax à vérifier' : 'Minimax à configurer';

  useEffect(() => {
    async function loadWorkspace() {
      const [agentResult, statusResult] = await Promise.allSettled([
        api.get<{ agents: Agent[] }>('api/agents'),
        api.get<ProviderStatus>('api/settings/status'),
      ]);
      if (agentResult.status === 'fulfilled') setAgents(agentResult.value.agents || []);
      if (statusResult.status === 'fulfilled') setProviderStatus(statusResult.value);
    }
    void loadWorkspace();
  }, []);

  useEffect(() => {
    const requestedAgent = new URLSearchParams(window.location.search).get('agent');
    if (requestedAgent && agents.some((agent) => agent.name === requestedAgent)) {
      setSelectedAgentName(requestedAgent);
      setMessages([greeting(requestedAgent)]);
    }
  }, [agents]);

  async function requestCompletion(nextMessages: ChatMessage[]) {
    const controller = new AbortController();
    abortRef.current = controller;
    setMessages(nextMessages);
    setLoading(true);

    try {
      const response = await api.post<ChatResult>(
        'api/chat',
        {
          messages: nextMessages.map(({ role, content, reasoning_details }) => ({
            role,
            content,
            ...(reasoning_details?.length ? { reasoning_details } : {}),
          })),
          agent_name: selectedAgentName || undefined,
        },
        { signal: controller.signal },
      );
      if (!controller.signal.aborted) {
        setMessages([...nextMessages, {
          role: 'assistant',
          content: response.content,
          time: 'maintenant',
          ...(response.reasoning_details?.length ? { reasoning_details: response.reasoning_details } : {}),
        }]);
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        setMessages([...nextMessages, {
          role: 'assistant',
          content: error instanceof Error ? error.message : 'Impossible de joindre Hermes. Réessayez dans un instant.',
          time: 'erreur',
        }]);
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

  function resetConversation(agentName = selectedAgentName) {
    stopGeneration();
    setInput('');
    setMessages([greeting(agentName || undefined)]);
  }

  function chooseAgent(agentName: string) {
    setSelectedAgentName(agentName);
    const url = new URL(window.location.href);
    if (agentName) url.searchParams.set('agent', agentName);
    else url.searchParams.delete('agent');
    window.history.replaceState(null, '', `${url.pathname}${url.search}`);
    resetConversation(agentName);
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
      <div className="chat-title">
        <span className="agent-avatar"><Sparkles size={16} /></span>
        <div>
          <div className="eyebrow">CONVERSATION ACTIVE</div>
          <label className="agent-picker"><span className="sr-only">Agent actif</span><select value={selectedAgentName} onChange={(event) => chooseAgent(event.target.value)}><option value="">Hermes Core</option>{agents.map((agent) => <option key={agent.name} value={agent.name}>{agent.name}</option>)}</select><ChevronDown size={17} /></label>
        </div>
      </div>
      <div className="chat-header-actions"><a className="ghost-button" href="/settings"><SlidersHorizontal size={16} /> Paramètres</a><button className="icon-button" onClick={() => resetConversation()} aria-label="Nouvelle conversation"><Plus size={18} /></button></div>
    </header>
    <div className="chat-body">
      <section className="messages-column">
        <div className="context-strip"><span><span className={`status-dot ${providerStatus?.minimax_configured ? 'online' : ''}`} /> {providerLabel}</span><span>{activeModel}</span><span>{activeAgent ? `${activeAgent.max_tokens || 2000} tokens max` : 'Contexte 8k'}</span></div>
        <div className="message-list">{messages.map((message, index) => <Message key={`${message.time}-${index}`} message={message} index={index} onCopy={copyMessage} onRegenerate={regenerate} copied={copied === index} />)}{loading && <div className="message assistant-message"><span className="message-avatar hermes-avatar"><Sparkles size={15} /></span><div className="message-content"><div className="message-meta"><strong>{activeName}</strong><span>réfléchit</span></div><div className="thinking"><span /><span /><span /></div></div></div>}</div>
        <div className="composer-wrap">
          <div className="suggestion-row"><button onClick={() => setInput('Analyse l’état de mon installation Hermes')}><WandSparkles size={14} /> Analyser mon installation</button><button onClick={() => setInput('Crée un agent spécialisé pour mon projet')}><Bot size={14} /> Créer un agent</button></div>
          <form className="composer" onSubmit={(event) => { event.preventDefault(); void sendMessage(); }}>
            <textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void sendMessage(); } }} placeholder={`Écrivez une instruction à ${activeName}…`} rows={1} aria-label="Message à Hermes" />
            <div className="composer-toolbar"><button className="icon-button" aria-label="Ajouter un fichier (bientôt disponible)" title="Pièces jointes bientôt disponibles" disabled><Paperclip size={17} /></button><span className="composer-hint">Entrée pour envoyer · ⇧ Entrée pour une nouvelle ligne</span><button className={`send-button ${canSend ? 'ready' : ''}`} type={loading ? 'button' : 'submit'} onClick={loading ? stopGeneration : undefined} disabled={!canSend && !loading} aria-label={loading ? 'Arrêter' : 'Envoyer'}>{loading ? <Square size={15} fill="currentColor" /> : <ArrowUp size={17} />}</button></div>
          </form>
          <p className="composer-disclaimer">Hermes peut faire des erreurs. Vérifiez les actions importantes.</p>
        </div>
      </section>
      <aside className="context-panel">
        <div className="context-heading"><div><div className="eyebrow">CONTEXTE</div><h3>Session Hermes</h3></div><a className="icon-button" href="/agents" aria-label="Gérer les agents"><SlidersHorizontal size={16} /></a></div>
        <div className="context-agent"><span className="large-agent-avatar"><Sparkles size={20} /></span><div><strong>{activeName}</strong><small>{activeAgent ? 'Agent personnalisé' : 'Orchestrateur généraliste'}</small></div><Check size={16} className="text-success" /></div>
        <div className="context-section"><div className="context-section-title"><span>Outils actifs</span><span className="count-badge">{activeTools.length}</span></div>{activeTools.map((tool, index) => <ContextTool icon={[Terminal, GitHubMark, WandSparkles][index % 3]} name={tool} status="Prêt" key={tool} />)}</div>
        <div className="context-section"><div className="context-section-title"><span>Instructions</span><a className="text-link" href="/agents">Modifier</a></div><p className="context-note">{activePrompt}</p></div>
        <div className="context-footer"><span className="status-dot online" /> Session synchronisée</div>
      </aside>
    </div>
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
