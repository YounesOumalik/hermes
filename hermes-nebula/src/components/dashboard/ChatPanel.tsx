"use client";

import { useState } from "react";
import { MessagesList } from "./MessagesList";
import { ChatInput } from "./ChatInput";
import { Button } from "@/components/ui";
import { apiFetch, apiPatch } from "@/lib/api";
import type { Agent, Conversation, Message, ModelConfig } from "@/lib/types";

interface ChatPanelProps {
  agent: Agent;
  conversation: Conversation | null;
  conversations: Conversation[];
  messages: Message[];
  availableModels: ModelConfig[];
  onSelectConversation: (c: Conversation) => void;
  onMessagesChange: (updater: (prev: Message[]) => Message[]) => void;
  onCreateConversation: () => void;
  onAgentChanged: (updated: Agent) => void;
}

/**
 * Panneau central de chat : header (agent + thread selector) + messages + input.
 * Gère le streaming SSE lui-même.
 */
export function ChatPanel({
  agent,
  conversation,
  conversations,
  messages,
  availableModels,
  onSelectConversation,
  onMessagesChange,
  onCreateConversation,
  onAgentChanged,
}: ChatPanelProps) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [isUpdatingModel, setIsUpdatingModel] = useState(false);

  /**
   * Change le modèle AI de l'agent à la volée.
   * Persisté en DB via PATCH /agents/{id}.
   */
  const handleModelChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModelId = e.target.value;
    if (!newModelId || newModelId === agent.model_config_id) return;
    setIsUpdatingModel(true);
    try {
      const updated = await apiPatch<Agent>(`/agents/${agent.id}`, {
        model_config_id: newModelId,
      });
      onAgentChanged(updated);
    } catch (err) {
      setStreamError(err instanceof Error ? err.message : "Failed to update model");
    } finally {
      setIsUpdatingModel(false);
    }
  };

  const handleSend = async (text: string) => {
    if (isStreaming) return;
    if (!conversation) {
      // Pas encore de conversation — le parent devrait en créer une à la volée.
      setStreamError("Initialisation de la conversation, réessayez dans 1s.");
      return;
    }

    setStreamError(null);
    setIsStreaming(true);

    // Ajout optimiste du message utilisateur
    const tempUserMsg: Message = {
      id: `temp-user-${Date.now()}`,
      role: "user",
      content: text,
      created_at: new Date().toISOString(),
    };
    onMessagesChange((prev) => [...prev, tempUserMsg]);

    const tempAgentId = `streaming-agent-${Date.now()}`;
    onMessagesChange((prev) => [
      ...prev,
      {
        id: tempAgentId,
        role: "assistant",
        content: "",
        created_at: new Date().toISOString(),
      },
    ]);

    try {
      const response = await apiFetch(
        `/conversations/${conversation.id}/messages`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content: text }),
        }
      );

      if (!response.ok) {
        throw new Error(await response.text());
      }

      // Parser SSE robuste : buffer les chunks jusqu'à voir \n\n,
      // puis parse les lignes "event:" et "data:".
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let agentText = "";
      let finished = false;

      while (!finished && reader) {
        const { value, done: readerDone } = await reader.read();
        if (readerDone) break;
        if (!value) continue;

        buffer += decoder.decode(value, { stream: true });

        // Découper en événements SSE (séparés par \n\n)
        let sepIdx: number;
        while ((sepIdx = buffer.indexOf("\n\n")) !== -1) {
          const rawEvent = buffer.slice(0, sepIdx);
          buffer = buffer.slice(sepIdx + 2);

          // Extraire event et data
          let eventName = "message";
          let dataStr = "";
          for (const line of rawEvent.split("\n")) {
            if (line.startsWith("event:")) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataStr += line.slice(5).trim();
            }
          }
          if (!dataStr) continue;

          try {
            const parsed = JSON.parse(dataStr);

            if (eventName === "chunk" && parsed.text) {
              agentText += parsed.text;
              onMessagesChange((prev) =>
                prev.map((m) =>
                  m.id === tempAgentId ? { ...m, content: agentText } : m
                )
              );
            } else if (eventName === "done" && parsed.content !== undefined) {
              agentText = parsed.content;
              onMessagesChange((prev) =>
                prev.map((m) =>
                  m.id === tempAgentId
                    ? { ...m, id: parsed.id || tempAgentId, content: agentText }
                    : m
                )
              );
              finished = true;
              break;
            } else if (eventName === "error") {
              throw new Error(parsed.detail || "Stream error from backend");
            }
          } catch (err) {
            if (err instanceof Error) throw err;
            // chunk partiel — on tolère
          }
        }
      }
    } catch (e) {
      const message = e instanceof Error ? e.message : "Stream error";
      setStreamError(message);
      // Nettoyer le message assistant vide en cas d'erreur
      onMessagesChange((prev) => prev.filter((m) => m.id !== tempAgentId));
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <section
      style={{ flex: 1, display: "flex", flexDirection: "column", height: "100vh" }}
    >
      {/* Header */}
      <header
        className="glass-panel"
        style={{
          padding: "16px 24px",
          borderRadius: "0",
          borderTop: "none",
          borderLeft: "none",
          borderRight: "none",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
          <div
            style={{
              width: "16px",
              height: "16px",
              borderRadius: "50%",
              backgroundColor: agent.avatar_color,
              flexShrink: 0,
            }}
          />
          <div style={{ minWidth: 0 }}>
            <h3 style={{ fontSize: "15px", fontWeight: "700" }}>{agent.name}</h3>
            <p
              style={{
                fontSize: "11px",
                color: "var(--text-secondary)",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
              }}
            >
              {agent.description || "Active session"}
            </p>
          </div>
        </div>

        {/* Thread selector + Model selector */}
        <div style={{ display: "flex", gap: "8px", flexShrink: 0, alignItems: "center" }}>
          <select
            value={agent.model_config_id || ""}
            onChange={handleModelChange}
            disabled={isUpdatingModel || availableModels.length === 0}
            className="input-field chat-panel-model-select"
            title="Change AI model"
            aria-label="AI model"
          >
            {availableModels.length === 0 && (
              <option value="">Loading models...</option>
            )}
            {availableModels.map((m) => (
              <option key={m.id} value={m.id}>
                {m.display_name}
              </option>
            ))}
          </select>
          <select
            value={conversation?.id || ""}
            onChange={(e) => {
              const c = conversations.find((conv) => conv.id === e.target.value);
              if (c) onSelectConversation(c);
            }}
            className="input-field"
            style={{ width: "180px", padding: "6px 12px", fontSize: "12px" }}
            aria-label="Select conversation thread"
          >
            {conversations.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title || "Chat session"}
              </option>
            ))}
          </select>
          <Button
            variant="secondary"
            size="sm"
            onClick={onCreateConversation}
            disabled={isStreaming}
          >
            New Thread
          </Button>
        </div>
      </header>

      {/* Messages */}
      <MessagesList
        messages={messages}
        isStreaming={isStreaming}
        agentName={agent.name}
        agentColor={agent.avatar_color}
      />

      {streamError && (
        <div
          role="alert"
          style={{
            margin: "0 24px",
            padding: "8px 12px",
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "8px",
            color: "var(--color-error)",
            fontSize: "12px",
          }}
        >
          {streamError}
        </div>
      )}

      {/* Input */}
      <ChatInput
        agentName={agent.name}
        disabled={!conversation}
        isStreaming={isStreaming}
        onSend={handleSend}
      />
    </section>
  );
}

export default ChatPanel;
