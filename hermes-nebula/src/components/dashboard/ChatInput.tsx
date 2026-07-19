"use client";

import { useState, KeyboardEvent } from "react";
import { Send } from "lucide-react";
import { Button } from "@/components/ui";

interface ChatInputProps {
  agentName: string;
  disabled?: boolean;
  isStreaming: boolean;
  onSend: (text: string) => void;
}

/**
 * Input de chat avec bouton Send.
 * - Enter envoie, Shift+Enter = nouvelle ligne (à venir si on passe en textarea)
 * - Désactivé pendant le streaming
 */
export function ChatInput({
  agentName,
  disabled = false,
  isStreaming,
  onSend,
}: ChatInputProps) {
  const [text, setText] = useState("");

  const handleSubmit = () => {
    const trimmed = text.trim();
    if (!trimmed || disabled || isStreaming) return;
    onSend(trimmed);
    setText("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const canSend = text.trim().length > 0 && !disabled && !isStreaming;

  return (
    <footer
      style={{
        padding: "16px 24px",
        borderTop: "1px solid var(--border-glass)",
        backgroundColor: "var(--bg-primary)",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: "8px",
          alignItems: "flex-end",
        }}
      >
        <input
          type="text"
          placeholder={`Message ${agentName}…`}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          className="input-field"
          style={{
            flex: 1,
            minWidth: 0, /* permet au flex de shrink l'input */
          }}
          disabled={disabled || isStreaming}
          aria-label={`Message ${agentName}`}
        />
        <Button
          variant="primary"
          size="md"
          onClick={handleSubmit}
          disabled={!canSend}
          icon={<Send size={14} />}
          aria-label="Send message"
        >
          Send
        </Button>
      </div>
    </footer>
  );
}

export default ChatInput;
