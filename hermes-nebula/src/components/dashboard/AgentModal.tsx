"use client";

import { useEffect, useState } from "react";
import { Modal, Input, Textarea, Button } from "@/components/ui";
import { apiPost, apiGet } from "@/lib/api";
import type { Agent, ModelConfig } from "@/lib/types";

interface AgentModalProps {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
  onCreated?: (agent: Agent) => void;
}

const AVATAR_COLORS: { value: string; label: string }[] = [
  { value: "#5e5af6", label: "Purple Glow" },
  { value: "#00d2ff", label: "Ocean Blue" },
  { value: "#10b981", label: "Emerald" },
  { value: "#f59e0b", label: "Amber" },
  { value: "#ef4444", label: "Rose Red" },
];

interface AgentForm {
  name: string;
  description: string;
  avatar_color: string;
  system_prompt: string;
  model_config_id: string;
  tools: string[];
}

const DEFAULT_FORM: AgentForm = {
  name: "",
  description: "",
  avatar_color: "#5e5af6",
  system_prompt: "You are a helpful assistant.",
  model_config_id: "",
  tools: [],
};

/**
 * Modal de création d'agent autonome.
 * Charge lui-même la liste des modèles disponibles.
 */
export function AgentModal({
  open,
  onClose,
  workspaceId,
  onCreated,
}: AgentModalProps) {
  const [form, setForm] = useState<AgentForm>(DEFAULT_FORM);
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Charger les modèles quand le modal s'ouvre
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    (async () => {
      try {
        const data = await apiGet<ModelConfig[]>("/models");
        if (cancelled) return;
        setModels(data);
        if (data.length > 0 && !form.model_config_id) {
          setForm((prev) => ({ ...prev, model_config_id: data[0].id }));
        }
      } catch (e) {
        if (!cancelled) {
          setError(
            e instanceof Error ? e.message : "Failed to load models"
          );
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const reset = () => {
    setForm(DEFAULT_FORM);
    setError(null);
    setIsCreating(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || isCreating) return;
    setIsCreating(true);
    setError(null);
    try {
      const created = await apiPost<Agent>(
        `/workspaces/${workspaceId}/agents`,
        form
      );
      onCreated?.(created);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create agent");
      setIsCreating(false);
    }
  };

  const update = (key: keyof AgentForm, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Create Autonomous Agent"
      description="Configure a specialized AI agent for this workspace."
      size="md"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose} disabled={isCreating}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="agent-form"
            loading={isCreating}
            disabled={!form.name.trim()}
          >
            Deploy Agent
          </Button>
        </>
      }
    >
      <form id="agent-form" onSubmit={handleSubmit}>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <Input
            label="Agent Name"
            name="agent-name"
            placeholder="e.g. Researcher Bot"
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            autoFocus
          />

          <Input
            label="Description"
            name="agent-description"
            placeholder="What is this agent specialized in?"
            value={form.description}
            onChange={(e) => update("description", e.target.value)}
          />

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "12px",
            }}
          >
            <div className="input-wrapper">
              <label htmlFor="agent-avatar-color" className="input-label">
                Avatar Theme Color
              </label>
              <select
                id="agent-avatar-color"
                value={form.avatar_color}
                onChange={(e) => update("avatar_color", e.target.value)}
                className="input-field"
              >
                {AVATAR_COLORS.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="input-wrapper">
              <label htmlFor="agent-model" className="input-label">
                LLM Model
              </label>
              <select
                id="agent-model"
                value={form.model_config_id}
                onChange={(e) => update("model_config_id", e.target.value)}
                className="input-field"
              >
                {models.length === 0 && <option value="">Loading...</option>}
                {models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.display_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <Textarea
            label="System Instructions / Prompt"
            name="agent-system-prompt"
            rows={4}
            value={form.system_prompt}
            onChange={(e) => update("system_prompt", e.target.value)}
          />

          {error && <span className="input-message input-message-error">{error}</span>}
        </div>
      </form>
    </Modal>
  );
}

export default AgentModal;
