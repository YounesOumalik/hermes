'use client';

import { useCallback, useRef, useState } from 'react';

type StreamEvent =
  | { event: 'delta'; content: string }
  | { event: 'reasoning'; details: Record<string, unknown>[] }
  | { event: 'tool_call'; tool: string; args: Record<string, unknown> }
  | { event: 'tool_result'; tool: string; status: string; result: Record<string, unknown> }
  | { event: 'tool_calls_detected'; count: number }
  | { event: 'done'; content: string; model: string; finish_reason: string }
  | { event: 'error'; message: string };

type ToolEvent = {
  tool: string;
  status: 'running' | 'success' | 'error';
  args?: Record<string, unknown>;
  result?: Record<string, unknown>;
};

type StreamState = {
  content: string;
  reasoning: Record<string, unknown>[];
  tools: ToolEvent[];
  isStreaming: boolean;
  isDone: boolean;
  model: string;
  finishReason: string;
  error: string | null;
};

const EMPTY_STATE: StreamState = {
  content: '',
  reasoning: [],
  tools: [],
  isStreaming: false,
  isDone: false,
  model: '',
  finishReason: '',
  error: null,
};

type UseChatStreamOptions = {
  onDone?: (content: string, model: string) => void;
  onError?: (message: string) => void;
};

export function useChatStream({ onDone, onError }: UseChatStreamOptions = {}) {
  const [streamState, setStreamState] = useState<StreamState>(EMPTY_STATE);
  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(
    async (payload: Record<string, unknown>) => {
      // Reset
      setStreamState(EMPTY_STATE);
      const controller = new AbortController();
      abortRef.current = controller;

      setStreamState((prev) => ({ ...prev, isStreaming: true }));

      try {
        const response = await fetch('/api/hermes/api/chat/stream', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
          signal: controller.signal,
          cache: 'no-store',
        });

        if (!response.ok) {
          const text = await response.text();
          let detail = `Erreur HTTP ${response.status}`;
          try { const parsed = JSON.parse(text); detail = parsed.detail || detail; } catch { /* raw */ }
          setStreamState((prev) => ({ ...prev, isStreaming: false, error: detail }));
          onError?.(detail);
          return;
        }

        const reader = response.body?.getReader();
        if (!reader) {
          setStreamState((prev) => ({ ...prev, isStreaming: false, error: 'Aucun flux de réponse.' }));
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line || !line.startsWith('data: ')) continue;
            const jsonStr = line.slice(6);
            let event: StreamEvent;
            try {
              event = JSON.parse(jsonStr) as StreamEvent;
            } catch {
              continue;
            }

            setStreamState((prev) => {
              const next = { ...prev };
              switch (event.event) {
                case 'delta':
                  next.content = prev.content + event.content;
                  break;
                case 'reasoning':
                  next.reasoning = [...prev.reasoning, ...(event.details || [])];
                  break;
                case 'tool_call':
                  next.tools = [...prev.tools, { tool: event.tool, args: event.args, status: 'running' as const }];
                  break;
                case 'tool_result':
                  next.tools = prev.tools.map((t) => {
                    if (t.tool === event.tool && t.status === 'running') {
                      const s: ToolEvent['status'] = event.status === 'success' ? 'success' : 'error';
                      return { ...t, status: s, result: event.result };
                    }
                    return t;
                  });
                  break;
                case 'tool_calls_detected':
                  // déjà couvert par tool_call individuel
                  break;
                case 'done':
                  next.content = event.content;
                  next.model = event.model;
                  next.finishReason = event.finish_reason;
                  next.isDone = true;
                  next.isStreaming = false;
                  break;
                case 'error':
                  next.error = event.message;
                  next.isStreaming = false;
                  break;
              }
              return next;
            });

            if (event.event === 'done') {
              onDone?.(event.content, event.model);
              return;
            }
            if (event.event === 'error') {
              onError?.(event.message);
              return;
            }
          }
        }

        // Si le stream s'arrête sans événement 'done'
        setStreamState((prev) => {
          if (prev.isDone || prev.error) return prev;
          return { ...prev, isStreaming: false, error: 'Le flux s\'est interrompu.' };
        });
      } catch (error) {
        if (controller.signal.aborted) {
          setStreamState((prev) => ({ ...prev, isStreaming: false }));
          return;
        }
        const message = error instanceof Error ? error.message : 'Erreur de connexion.';
        setStreamState((prev) => ({ ...prev, isStreaming: false, error: message }));
        onError?.(message);
      }
    },
    [onDone, onError],
  );

  const stopStream = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStreamState((prev) => ({ ...prev, isStreaming: false }));
  }, []);

  const resetStream = useCallback(() => {
    setStreamState(EMPTY_STATE);
    abortRef.current = null;
  }, []);

  return { streamState, startStream, stopStream, resetStream };
}
