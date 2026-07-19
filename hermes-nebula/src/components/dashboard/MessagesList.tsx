"use client";

import { useEffect, useRef } from "react";
import { Loader2 } from "lucide-react";
import type { Message } from "@/lib/types";

interface MessagesListProps {
  messages: Message[];
  isStreaming: boolean;
  agentName: string;
  agentColor: string;
}

/**
 * Liste des messages d'une conversation avec bulles user/assistant.
 * Auto-scroll en bas à chaque nouveau message.
 */
export function MessagesList({
  messages,
  isStreaming,
  agentName,
  agentColor,
}: MessagesListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  return (
    <div
      style={{
        flex: 1,
        padding: "24px",
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: "20px",
      }}
    >
      {messages.length === 0 && !isStreaming && (
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            color: "var(--text-muted)",
            textAlign: "center",
            gap: "8px",
          }}
        >
          <div
            style={{
              width: "40px",
              height: "40px",
              borderRadius: "50%",
              backgroundColor: agentColor,
              opacity: 0.6,
            }}
          />
          <p style={{ fontSize: "14px" }}>Start a conversation with {agentName}</p>
        </div>
      )}

      {messages.map((m) => {
        const isUser = m.role === "user";
        return (
          <div
            key={m.id}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: isUser ? "flex-end" : "flex-start",
              maxWidth: "80%",
              alignSelf: isUser ? "flex-end" : "flex-start",
              gap: "6px",
            }}
          >
            <span style={{ fontSize: "10px", color: "var(--text-muted)" }}>
              {isUser ? "You" : agentName}
            </span>

            <div
              className="glass-card"
              style={{
                padding: "16px",
                borderRadius: "var(--radius-md)",
                backgroundColor: isUser
                  ? "var(--bg-tertiary)"
                  : "rgba(255,255,255,0.02)",
                border: isUser
                  ? "1px solid rgba(255,255,255,0.1)"
                  : "1px solid var(--border-glass)",
                fontSize: "14px",
                lineHeight: "1.6",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {m.content || (isStreaming && !isUser ? "…" : "")}
            </div>
          </div>
        );
      })}

      {isStreaming && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            color: "var(--text-muted)",
            fontSize: "12px",
          }}
        >
          <Loader2 size={14} className="btn-spinner" />
          {agentName} is streaming response...
        </div>
      )}

      <div ref={endRef} />
    </div>
  );
}

export default MessagesList;
