"use client";

import { useState } from "react";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import { Modal, Input, Button } from "@/components/ui";

interface WorkspaceModalProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Modal de création de workspace.
 * Auto-suffisant : délègue la création au workspaceStore.
 */
export function WorkspaceModal({ open, onClose }: WorkspaceModalProps) {
  const createWorkspace = useWorkspaceStore((s) => s.createWorkspace);
  const [name, setName] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reset = () => {
    setName("");
    setError(null);
    setIsCreating(false);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || isCreating) return;
    setIsCreating(true);
    setError(null);
    try {
      await createWorkspace(name.trim());
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create workspace");
      setIsCreating(false);
    }
  };

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Create Workspace"
      description="Give your workspace a name to organize your agents."
      size="sm"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose} disabled={isCreating}>
            Cancel
          </Button>
          <Button
            type="submit"
            form="workspace-form"
            loading={isCreating}
            disabled={!name.trim()}
          >
            Create
          </Button>
        </>
      }
    >
      <form id="workspace-form" onSubmit={handleSubmit}>
        <Input
          label="Workspace Name"
          name="workspace-name"
          placeholder="e.g. Marketing Team"
          value={name}
          onChange={(e) => setName(e.target.value)}
          autoFocus
          error={error || undefined}
        />
      </form>
    </Modal>
  );
}

export default WorkspaceModal;
