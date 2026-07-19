/**
 * Types partagés du domaine AgentAI (frontend).
 * Alignés sur les schémas Pydantic du backend (hermes-nebula-api).
 */

export interface User {
  id: string;
  email: string;
  display_name: string;
  username: string | null;
  avatar_url: string | null;
  is_active: boolean;
  is_superadmin: boolean;
  created_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  logo_url: string | null;
  owner_id: string;
}

export interface Agent {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  avatar_color: string;
  system_prompt: string;
  model_config_id: string | null;
  status: string;
}

export interface Conversation {
  id: string;
  agent_id: string;
  title: string | null;
}

export interface Message {
  id: string;
  role: string;
  content: string;
  created_at: string;
  attachments?: Attachment[];
}

export interface Attachment {
  id: string;
  filename: string;
  mime_type: string;
  size: number;
  url: string;
}

export interface ModelConfig {
  id: string;
  display_name: string;
  provider: string;
}

export interface ToolItem {
  id: string;
  name: string;
  slug: string;
  description: string;
  icon_name: string;
}

export interface Job {
  id: string;
  workspace_id: string;
  agent_id: string;
  name: string;
  prompt: string;
  cron_expression: string;
  next_run_at: string | null;
  status: "active" | "paused" | "draft";
  created_by: string;
  created_at: string;
}

export interface JobRun {
  id: string;
  job_id: string;
  started_at: string | null;
  finished_at: string | null;
  status: "pending" | "running" | "success" | "failed";
  result_message_id: string | null;
  error: string | null;
}

export interface NotificationChannel {
  id: string;
  type: "email" | "webhook" | "slack" | "discord";
  label: string;
  config: Record<string, unknown>;
  is_active: boolean;
}
