'use client';

import { useCallback, useRef, useState } from 'react';

// Wire format aligné sur l'executor hermes-core (orchestrator/executor.py).
type ExecutorEvent =
  | { type: 'delta'; content: string }
  | { type: 'reasoning'; content: string }
  | { type: 'tool_call'; tool_call_id?: number; tool: string; args: Record<string, unknown>; requires_approval?: boolean; approval_id?: number }
  | { type: 'tool_result'; tool: string; status: string; result?: Record<string, unknown> }
  | { type: 'tool_calls_detected'; count: number; approval_ids: number[] }
  | { type: 'done'; content: string; model: string; finish_reason: string; run_id?: number; message_id?: number }
  | { type: 'error'; message: string };

type ToolEvent = {
  id?: number;
  tool: string;
  status: 'running' | 'success' | 'error' | 'awaiting_approval' | 'rejected';
  args?: Record<string, unknown>;
  result?: Record<string, unknown>;
  approval_id?: number;
  requires_approval?: boolean;
};

type StreamState = {
  content: string;
  reasoning: string;
  tools: ToolEvent[];
  isStreaming: boolean;
  isDone: boolean;
  model: string;
  finishReason: string;
  error: string | null;
  runId: number | null;
  pendingApprovals: number[];
};

const EMPTY_STATE: StreamState = {
  content: '',
  reasoning: '',
  tools: [],
  isStreaming: false,
  isDone: false,
  model: '',
  finishReason: '',
  error: null,
  runId: null,
  pendingApprovals: [],
};

type UseChatStreamOptions = {
  onDone?: (content: string, model: string, runId?: number) => void;
  onError?: (message: string) => void;
  onApprovalRequired?: (approvalIds: number[]) => void;
};

export function useChatStream({ onDone, onError, onApprovalRequired }: UseChatStreamOptions = {}) {
  const [streamState, setStreamState] = useState<StreamState>(EMPTY_STATE);
  const abortRef = useRef<AbortController | null>(null);

  const startStream = useCallback(
    async (payload: Record<string, unknown>) => {
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
          try {
            const parsed = JSON.parse(text);
            detail = parsed.detail || detail;
          } catch {
            /* raw */
          }
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
            let event: ExecutorEvent;
            try {
              event = JSON.parse(jsonStr) as ExecutorEvent;
            } catch {
              continue;
            }

            setStreamState((prev) => {
              const next = { ...prev };
              switch (event.type) {
                case 'delta':
                  next.content = prev.content + (event.content || '');
                  break;
                case 'reasoning':
                  next.reasoning = prev.reasoning + (event.content || '');
                  break;
                case 'tool_call': {
                  const tc: ToolEvent = {
                    id: event.tool_call_id,
                    tool: event.tool,
                    args: event.args,
                    status: event.requires_approval ? 'awaiting_approval' : 'running',
                    approval_id: event.approval_id,
                    requires_approval: event.requires_approval,
                  };
                  next.tools = [...prev.tools, tc];
                  break;
                }
                case 'tool_result': {
                  next.tools = prev.tools.map((t) =>
                    t.tool === event.tool && (t.status === 'running' || t.status === 'awaiting_approval')
                      ? {
                          ...t,
                          status:
                            event.status === 'success'
                              ? 'success'
                              : event.status === 'rejected'
                                ? 'rejected'
                                : 'error',
                          result: event.result,
                        }
                      : t,
                  );
                  break;
                }
                case 'tool_calls_detected':
                  next.pendingApprovals = Array.from(
                    new Set([...prev.pendingApprovals, ...(event.approval_ids || [])]),
                  );
                  break;
                case 'done':
                  next.content = event.content || prev.content;
                  next.model = event.model;
                  next.finishReason = event.finish_reason;
                  next.runId = event.run_id ?? prev.runId;
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

            if (event.type === 'tool_calls_detected' && event.approval_ids?.length) {
              onApprovalRequired?.(event.approval_ids);
            }
            if (event.type === 'done') {
              onDone?.(event.content, event.model, event.run_id);
              return;
            }
            if (event.type === 'error') {
              onError?.(event.message);
              return;
            }
          }
        }

        setStreamState((prev) => {
          if (prev.isDone || prev.error) return prev;
          return { ...prev, isStreaming: false, error: "Le flux s'est interrompu." };
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
    [onDone, onError, onApprovalRequired],
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

  const resumeAfterApproval = useCallback(
    async (payload: Record<string, unknown>) => startStream(payload),
    [startStream],
  );

  return {
    streamState,
    startStream,
    stopStream,
    resetStream,
    resumeAfterApproval,
  };
}
