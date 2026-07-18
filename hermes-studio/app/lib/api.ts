export type ApiError = Error & { status?: number };

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/hermes/${path.replace(/^\//, '')}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    cache: 'no-store',
  });

  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json() : await response.text();

  if (!response.ok) {
    const message = typeof data === 'object' && data?.detail ? data.detail : `Erreur HTTP ${response.status}`;
    const error = new Error(message) as ApiError;
    error.status = response.status;
    throw error;
  }

  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body: unknown, options: Omit<RequestInit, 'method' | 'body'> = {}) => request<T>(path, { ...options, method: 'POST', body: JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: 'DELETE' }),
};

export type Agent = {
  name: string;
  system_prompt: string;
  description?: string;
  model?: string | null;
  temperature?: number;
  max_tokens?: number;
  tools: string[];
};

export type ConversationMessage = {
  role: 'user' | 'assistant';
  content: string;
  time: string;
  reasoning_details?: Record<string, unknown>[];
};

export type Conversation = {
  id: string;
  title: string;
  agent_name?: string | null;
  model?: string | null;
  tool_names: string[];
  context_tokens: number;
  messages: ConversationMessage[];
  created_at: string;
  updated_at: string;
};

export type ConversationSummary = Omit<Conversation, 'messages'>;

export type Tool = {
  name: string;
  description: string;
  parameters: Record<string, unknown>;
};
