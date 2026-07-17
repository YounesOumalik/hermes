'use client';

import { useState } from 'react';
import axios from 'axios';

const DAEMON_URL = process.env.NEXT_PUBLIC_DAEMON_URL || 'http://localhost:8001';

export default function ChatPage() {
  const [messages, setMessages] = useState<{role: string; content: string}[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;
    const newMessages = [...messages, { role: 'user', content: input }];
    setMessages(newMessages);
    setInput('');
    setLoading(true);

    try {
      const resp = await axios.post(`${DAEMON_URL}/api/chat`, {
        messages: newMessages,
      });
      setMessages([...newMessages, { role: 'assistant', content: resp.data.content }]);
    } catch (err) {
      setMessages([...newMessages, { role: 'assistant', content: 'Erreur: ' + String(err) }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Chat</h1>
      <div className="card" style={{ minHeight: '400px' }}>
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: '1rem' }}>
            <strong>{m.role}:</strong> {m.content}
          </div>
        ))}
        {loading && <p style={{ color: 'var(--muted)' }}>…</p>}
      </div>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Tapez votre message…"
        />
        <button className="btn" onClick={sendMessage} disabled={loading}>
          Envoyer
        </button>
      </div>
    </div>
  );
}
