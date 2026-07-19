"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-07-19
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), unique=True, nullable=False, index=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("username", sa.String(100), unique=True, index=True),
        sa.Column("avatar_url", sa.Text),
        sa.Column("timezone", sa.String(50), server_default="UTC"),
        sa.Column("google_id", sa.String(200), unique=True, index=True),
        sa.Column("is_active", sa.Boolean, server_default="false", index=True),
        sa.Column("is_superadmin", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Sessions
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(512), nullable=False),
        sa.Column("device_info", sa.Text),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Workspaces
    op.create_table(
        "workspaces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("logo_url", sa.Text),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Workspace Members
    op.create_table(
        "workspace_members",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(20), server_default="member", nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Model Configs
    op.create_table(
        "model_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(300), nullable=False),
        sa.Column("context_window", sa.Integer, server_default="8192"),
        sa.Column("input_price_per_1m", sa.Float),
        sa.Column("output_price_per_1m", sa.Float),
        sa.Column("capabilities", postgresql.ARRAY(sa.String), server_default='{"text"}'),
        sa.Column("is_default", sa.Boolean, server_default="false"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Tools
    op.create_table(
        "tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), unique=True, nullable=False),
        sa.Column("slug", sa.String(200), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text),
        sa.Column("icon_name", sa.String(50), server_default="wrench"),
        sa.Column("category", sa.String(100), server_default="general"),
        sa.Column("cost_tier", sa.String(20), server_default="low"),
        sa.Column("is_builtin", sa.Boolean, server_default="true"),
        sa.Column("config_schema_json", postgresql.JSONB),
        sa.Column("enabled_globally", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Agents
    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("avatar_color", sa.String(7), server_default="#58a6ff"),
        sa.Column("system_prompt", sa.Text, server_default="You are a helpful assistant."),
        sa.Column("model_config_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("model_configs.id", ondelete="SET NULL")),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Agent Tools
    op.create_table(
        "agent_tools",
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tool_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tools.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("status", sa.String(20), server_default="off"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Conversations
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("last_message_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Messages
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text),
        sa.Column("metadata_json", postgresql.JSONB),
        sa.Column("tokens_used", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Chapters
    op.create_table(
        "chapters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("tags", postgresql.JSONB),
        sa.Column("status", sa.String(20), server_default="live"),
        sa.Column("start_message_id", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Attachments
    op.create_table(
        "attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id", ondelete="CASCADE"), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("mime_type", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Jobs
    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("cron_expression", sa.String(100)),
        sa.Column("next_run_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), server_default="active"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Job Runs
    op.create_table(
        "job_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("result_message_id", postgresql.UUID(as_uuid=True)),
        sa.Column("error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # API Keys
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(100), nullable=False, index=True),
        sa.Column("key_name", sa.String(300), nullable=False),
        sa.Column("encrypted_key", sa.Text, nullable=False),
        sa.Column("base_url", sa.String(1000)),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("added_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # User Quotas
    op.create_table(
        "user_quotas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("max_disk_bytes", sa.BigInteger, server_default="1073741824"),
        sa.Column("used_disk_bytes", sa.BigInteger, server_default="0"),
        sa.Column("max_monthly_llm_tokens", sa.BigInteger, server_default="1000000"),
        sa.Column("used_monthly_llm_tokens", sa.BigInteger, server_default="0"),
        sa.Column("quota_reset_at", sa.DateTime(timezone=True)),
        sa.Column("allowed_models", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("allowed_tools", postgresql.ARRAY(sa.String), server_default="{}"),
        sa.Column("notes_admin", sa.Text),
        sa.Column("updated_by_admin_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Admin Audit Log
    op.create_table(
        "admin_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("admin_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("target_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("details_json", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Memories
    op.create_table(
        "memories",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("usage_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Documents
    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("content_hash", sa.String(128)),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Mini Apps
    op.create_table(
        "mini_apps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("type", sa.String(100), server_default="custom"),
        sa.Column("html_content", sa.Text),
        sa.Column("config_json", postgresql.JSONB),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Integrations
    op.create_table(
        "integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("type", sa.String(100), nullable=False),
        sa.Column("config_json", postgresql.JSONB),
        sa.Column("status", sa.String(20), server_default="inactive"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Secrets
    op.create_table(
        "secrets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_name", sa.String(300), nullable=False),
        sa.Column("encrypted_value", sa.Text, nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Notification Channels
    op.create_table(
        "notification_channels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("config_json", postgresql.JSONB),
        sa.Column("is_connected", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Notification Rules
    op.create_table(
        "notification_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE")),
        sa.Column("event_type", sa.String(200), nullable=False),
        sa.Column("channel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("notification_channels.id"), nullable=False),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("notification_rules")
    op.drop_table("notification_channels")
    op.drop_table("secrets")
    op.drop_table("integrations")
    op.drop_table("mini_apps")
    op.drop_table("documents")
    op.drop_table("memories")
    op.drop_table("admin_audit_log")
    op.drop_table("user_quotas")
    op.drop_table("api_keys")
    op.drop_table("job_runs")
    op.drop_table("jobs")
    op.drop_table("attachments")
    op.drop_table("chapters")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("agent_tools")
    op.drop_table("agents")
    op.drop_table("tools")
    op.drop_table("model_configs")
    op.drop_table("workspace_members")
    op.drop_table("workspaces")
    op.drop_table("sessions")
    op.drop_table("users")