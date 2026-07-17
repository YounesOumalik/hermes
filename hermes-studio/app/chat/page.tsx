'use client';

import { ArrowUp, Bot, Check, ChevronDown, Copy, Paperclip, Plus, RotateCcw, SlidersHorizontal, Sparkles, Square, Terminal, UserRound, WandSparkles } from 'lucide-react';
import type { ComponentType } from 'react';
import { useMemo, useState } from 'react';
import { api } from '../lib/api';

type ChatMessage = { role: 'user' | 'assistant'; content: string; time: string };

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([{ role: 'assistant', content: 'Bonjour Younes. Je suis Hermes, votre workspace d’orchestration. Que voulez-vous construire aujourd’hui ?', time: 'maintenant' }]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState<number | null>(null);

  const canSend = input.trim().length > 0 && !loading;
  const transcript = useMemo(() => messages.map(({ role, content }) => ({ role, content })), [messages]);

  async function sendMessage() {
    if (!canSend) return;
    const content = input.trim();
    const next = [...messages, { role: 'user' as const, content, time: 'maintenant' }];
    setMessages(next);
    setInput('');
    setLoading(true);
    try {
      const response = await api.post<{ content: string }>('api/chat', { messages: next.map(({ role, content: text }) => ({ role, content: text })) });
      setMessages([...next, { role: 'assistant', content: response.content, time: 'maintenant' }]);
    } catch (error) {
      setMessages([...next, { role: 'assistant', content: `Je n’ai pas pu joindre le daemon. ${error instanceof Error ? error.message : 'Réessayez dans un instant.'}`, time: 'erreur' }]);
    } finally { setLoading(false); }
  }

  function copyMessage(index: number, content: string) { navigator.clipboard?.writeText(content); setCopied(index); window.setTimeout(() => setCopied(null), 1500); }

  return <div className="chat-layout page"><header className="chat-header"><div className="chat-title"><span className="agent-avatar"><Sparkles size={16} /></span><div><div className="eyebrow">CONVERSATION ACTIVE</div><h1>Hermes Core <ChevronDown size={17} /></h1></div></div><div className="chat-header-actions"><button className="ghost-button"><SlidersHorizontal size={16} /> Paramètres</button><button className="icon-button"><Plus size={18} /></button></div></header>
    <div className="chat-body"><section className="messages-column"><div className="context-strip"><span><span className="status-dot online" /> Minimax connecté</span><span>abab6.5s-chat</span><span>Contexte 8k</span></div><div className="message-list">{messages.map((message, index) => <Message key={`${message.time}-${index}`} message={message} index={index} onCopy={copyMessage} copied={copied === index} />)}{loading && <div className="message assistant-message"><span className="message-avatar hermes-avatar"><Sparkles size={15} /></span><div className="message-content"><div className="message-meta"><strong>Hermes</strong><span>réfléchit</span></div><div className="thinking"><span /><span /><span /></div></div></div>}</div><div className="composer-wrap"><div className="suggestion-row"><button onClick={() => setInput('Analyse l’état de mon installation Hermes')}><WandSparkles size={14} /> Analyser mon installation</button><button onClick={() => setInput('Crée un agent spécialisé pour mon projet')}><Bot size={14} /> Créer un agent</button></div><div className="composer"><textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); sendMessage(); } }} placeholder="Écrivez une instruction à Hermes…" rows={1} aria-label="Message à Hermes" /><div className="composer-toolbar"><button className="icon-button" aria-label="Ajouter un fichier"><Paperclip size={17} /></button><span className="composer-hint">Entrée pour envoyer · ⇧ Entrée pour une nouvelle ligne</span><button className={`send-button ${canSend ? 'ready' : ''}`} onClick={loading ? () => setLoading(false) : sendMessage} disabled={!canSend && !loading} aria-label={loading ? 'Arrêter' : 'Envoyer'}>{loading ? <Square size={15} fill="currentColor" /> : <ArrowUp size={17} />}</button></div></div><p className="composer-disclaimer">Hermes peut faire des erreurs. Vérifiez les actions importantes.</p></div></section><aside className="context-panel"><div className="context-heading"><div><div className="eyebrow">CONTEXTE</div><h3>Session Hermes</h3></div><button className="icon-button"><SlidersHorizontal size={16} /></button></div><div className="context-agent"><span className="large-agent-avatar"><Sparkles size={20} /></span><div><strong>Hermes Core</strong><small>Orchestrateur généraliste</small></div><Check size={16} className="text-success" /></div><div className="context-section"><div className="context-section-title"><span>Outils actifs</span><span className="count-badge">3</span></div><ContextTool icon={Terminal} name="mcp_filesystem" status="Prêt" /><ContextTool icon={GitHubMark} name="mcp_github" status="Prêt" /><ContextTool icon={WandSparkles} name="n8n_webhook" status="Prêt" /></div><div className="context-section"><div className="context-section-title"><span>Instructions</span><button className="text-link">Modifier</button></div><p className="context-note">Tu es un orchestrateur précis. Décompose les demandes complexes et utilise les outils uniquement lorsque cela apporte une valeur claire.</p></div><div className="context-footer"><span className="status-dot online" /> Tout est synchronisé</div></aside></div></div>;
}

function Message({ message, index, onCopy, copied }: { message: ChatMessage; index: number; onCopy: (index: number, content: string) => void; copied: boolean }) { const user = message.role === 'user'; return <div className={`message ${user ? 'user-message' : 'assistant-message'}`}><span className={`message-avatar ${user ? 'user-avatar' : 'hermes-avatar'}`}>{user ? <UserRound size={15} /> : <Sparkles size={15} />}</span><div className="message-content"><div className="message-meta"><strong>{user ? 'Vous' : 'Hermes'}</strong><span>{message.time}</span></div><div className="message-text">{message.content}</div>{!user && <div className="message-actions"><button onClick={() => onCopy(index, message.content)}><Copy size={13} /> {copied ? 'Copié' : 'Copier'}</button><button><RotateCcw size={13} /> Régénérer</button></div>}</div></div>; }
function ContextTool({ icon: Icon, name, status }: { icon: ComponentType<{ size?: string | number }>; name: string; status: string }) { return <div className="context-tool"><span className="tool-mini-icon"><Icon size={14} /></span><span><strong>{name}</strong><small>{status}</small></span><span className="status-dot online" /></div>; }
function GitHubMark({ size = 14 }: { size?: string | number }) { return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3.3-.4 6.8-1.6 6.8-7A5.5 5.5 0 0 0 19.3 4 5.1 5.1 0 0 0 19.2.4S18 0 15 2.1a13.4 13.4 0 0 0-6 0C6 .1 4.8.4 4.8.4A5.1 5.1 0 0 0 4.7 4a5.5 5.5 0 0 0-1.5 3.8c0 5.4 3.5 6.6 6.8 7A4.8 4.8 0 0 0 9 18v4" /><path d="M9 18c-4.5 2-5-2-7-2" /></svg>; }
