'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';

const DAEMON_URL = process.env.NEXT_PUBLIC_DAEMON_URL || 'http://localhost:8001';

export default function AgentsPage() {
  const [agents, setAgents] = useState<any[]>([]);
  const [name, setName] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const resp = await axios.get(`${DAEMON_URL}/api/agents`);
      setAgents(resp.data.agents || []);
    } catch (err) {
      console.error(err);
    }
  };

  const createAgent = async () => {
    if (!name.trim()) return;
    try {
      await axios.post(`${DAEMON_URL}/api/agents`, {
        name,
        system_prompt: systemPrompt,
        model: null,
        tools: [],
      });
      setName('');
      setSystemPrompt('');
      fetchAgents();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div>
      <h1>Agents</h1>
      <div className="card">
        <h2>Créer un agent</h2>
        <input
          placeholder="Nom de l'agent"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ marginBottom: '0.5rem' }}
        />
        <textarea
          placeholder="System prompt"
          value={systemPrompt}
          onChange={(e) => setSystemPrompt(e.target.value)}
          rows={4}
          style={{ marginBottom: '0.5rem' }}
        />
        <button className="btn" onClick={createAgent}>Créer</button>
      </div>
      <div className="card">
        <h2>Agents existants ({agents.length})</h2>
        {agents.length === 0 && <p style={{ color: 'var(--muted)' }}>Aucun agent pour l'instant.</p>}
        {agents.map((a, i) => (
          <div key={i} style={{ padding: '0.5rem 0', borderBottom: '1px solid var(--border)' }}>
            <strong>{a.name}</strong>
          </div>
        ))}
      </div>
    </div>
  );
}
