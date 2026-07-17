'use client';

import { useState, useEffect } from 'react';
import axios from 'axios';

const DAEMON_URL = process.env.NEXT_PUBLIC_DAEMON_URL || 'http://localhost:8001';

export default function ToolsPage() {
  const [tools, setTools] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTools();
  }, []);

  const fetchTools = async () => {
    try {
      const resp = await axios.get(`${DAEMON_URL}/api/tools`);
      setTools(resp.data.tools || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Tools</h1>
      {loading && <p style={{ color: 'var(--muted)' }}>Chargement…</p>}
      {tools.map((t, i) => (
        <div key={i} className="card">
          <h3>{t.name}</h3>
          <p style={{ color: 'var(--muted)' }}>{t.description}</p>
          <details>
            <summary>Schéma JSON</summary>
            <pre style={{ overflow: 'auto', fontSize: '0.8rem' }}>
              {JSON.stringify(t.parameters, null, 2)}
            </pre>
          </details>
        </div>
      ))}
    </div>
  );
}
