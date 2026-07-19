"use client";

import { useState } from "react";
import { Modal, Input, Textarea, Button } from "@/components/ui";
import { CRON_PRESETS } from "./CronPresets";
import { apiPost } from "@/lib/api";
import type { Agent, Job } from "@/lib/types";

interface CreateJobModalProps {
  open: boolean;
  onClose: () => void;
  workspaceId: string;
  agents: Agent[];
  onCreated?: (job: Job) => void;
}

interface JobForm {
  agent_id: string;
  name: string;
  prompt: string;
  cron_expression: string;
}

const DEFAULT_FORM: JobForm = {
  agent_id: "",
  name: "",
  prompt: "",
  cron_expression: CRON_PRESETS[2].value, // "Every day at 9 AM"
};

/**
 * Modal de création de job récurrent.
 * - Sélecteur d'agent (parmi les agents du workspace)
 * - Presets cron + custom
 */
export function CreateJobModal({
  open,
  onClose,
  workspaceId,
  agents,
  onCreated,
}: CreateJobModalProps) {
  const [form, setForm] = useState<JobForm>(DEFAULT_FORM);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Pré-remplir l'agent si vide
  const effectiveAgentId = form.agent_id || agents[0]?.id || "";

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
    if (!form.name.trim() || !form.prompt.trim() || isCreating) return;

    setIsCreating(true);
    setError(null);
    try {
      const created = await apiPost<Job>(`/workspaces/${workspaceId}/jobs`, {
        ...form,
        agent_id: effectiveAgentId,
      });
      onCreated?.(created);
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create job");
      setIsCreating(false);
    }
  };

  const update = (key: keyof JobForm, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const canSubmit =
    form.name.trim().length > 0 &&
    form.prompt.trim().length > 0 &&
    effectiveAgentId.length > 0 &&
    !isCreating;

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Create Scheduled Job"
      description="Run an agent automatically on a recurring schedule."
      size="md"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose} disabled={isCreating}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="job-form"
            loading={isCreating}
            disabled={!canSubmit}
          >
            Create Job
          </Button>
        </>
      }
    >
      <form id="job-form" onSubmit={handleSubmit}>
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <Input
            label="Job Name"
            name="job-name"
            placeholder="e.g. Daily Standup Reporter"
            value={form.name}
            onChange={(e) => update("name", e.target.value)}
            autoFocus
          />

          <div className="input-wrapper">
            <label htmlFor="job-agent" className="input-label">
              Agent
            </label>
            <select
              id="job-agent"
              value={effectiveAgentId}
              onChange={(e) => update("agent_id", e.target.value)}
              className="input-field"
              disabled={agents.length === 0}
            >
              {agents.length === 0 && <option value="">No agent available</option>}
              {agents.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.name}
                </option>
              ))}
            </select>
          </div>

          <Textarea
            label="Prompt"
            name="job-prompt"
            placeholder="e.g. Summarize today's commits and open PRs, then post to Slack."
            rows={4}
            value={form.prompt}
            onChange={(e) => update("prompt", e.target.value)}
          />

          <div className="input-wrapper">
            <label className="input-label">Schedule (cron)</label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px", marginTop: "6px" }}>
              <select
                value={
                  CRON_PRESETS.some((p) => p.value === form.cron_expression)
                    ? form.cron_expression
                    : "__custom__"
                }
                onChange={(e) => {
                  if (e.target.value !== "__custom__") {
                    update("cron_expression", e.target.value);
                  }
                }}
                className="input-field"
                aria-label="Cron preset"
              >
                <option value="__custom__">Custom…</option>
                {CRON_PRESETS.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
              <input
                type="text"
                value={form.cron_expression}
                onChange={(e) => update("cron_expression", e.target.value)}
                className="input-field"
                placeholder="* * * * *"
                aria-label="Custom cron expression"
                style={{ fontFamily: "monospace" }}
              />
            </div>
            <span className="input-message">
              Format: minute hour day-of-month month day-of-week (e.g. <code>0 9 * * *</code> = daily at 9 AM)
            </span>
          </div>

          {error && <span className="input-message input-message-error">{error}</span>}
        </div>
      </form>
    </Modal>
  );
}

export default CreateJobModal;
