"""Add configurable agents and tenant-scoped dashboard conversations."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0005_ai_agents_chat"
down_revision = "0004_embeddings_rag"
branch_labels = None
depends_on = None


def _policy(table: str, name: str, action: str, using: str | None = None, check: str | None = None) -> None:
    clauses = [f"CREATE POLICY {name} ON public.{table} FOR {action} TO authenticated"]
    if using:
        clauses.append(f"USING ({using})")
    if check:
        clauses.append(f"WITH CHECK ({check})")
    op.execute(sa.text(" ".join(clauses)))


def upgrade() -> None:
    uuid_type = sa.Uuid(as_uuid=True)
    now = sa.text("CURRENT_TIMESTAMP")
    json_type = sa.JSON().with_variant(JSONB(), "postgresql")
    member = "EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = {table}.organization_id AND m.user_id = auth.uid())"
    admin = "EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = {table}.organization_id AND m.user_id = auth.uid() AND m.role IN ('owner', 'admin'))"
    company_tenant = "EXISTS (SELECT 1 FROM public.companies c WHERE c.id = {table}.company_id AND c.organization_id = {table}.organization_id)"
    agent_tenant = "EXISTS (SELECT 1 FROM public.ai_agents a WHERE a.id = {table}.agent_id AND a.organization_id = {table}.organization_id AND a.company_id = {table}.company_id)"
    conversation_tenant = "EXISTS (SELECT 1 FROM public.conversations c WHERE c.id = {table}.conversation_id AND c.organization_id = {table}.organization_id AND c.company_id = {table}.company_id)"

    op.create_table(
        "ai_agents",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, nullable=False), sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(160), nullable=False), sa.Column("role", sa.String(160), nullable=False),
        sa.Column("description", sa.String(1000)), sa.Column("objective", sa.String(1000), nullable=False),
        sa.Column("tone", sa.String(120), nullable=False), sa.Column("language", sa.String(80), nullable=False),
        sa.Column("system_instructions", sa.Text, nullable=False), sa.Column("model", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("temperature", sa.Numeric(3, 2)), sa.Column("max_output_tokens", sa.Integer),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("status IN ('draft', 'active', 'disabled')", name="ck_ai_agents_status"),
        sa.CheckConstraint("temperature IS NULL OR (temperature >= 0 AND temperature <= 1)", name="ck_ai_agents_temperature"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "conversations",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, nullable=False), sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("agent_id", uuid_type, nullable=False), sa.Column("created_by", uuid_type),
        sa.Column("channel", sa.String(40), nullable=False, server_default="dashboard"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("last_message_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("status IN ('active', 'closed')", name="ck_conversations_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["ai_agents.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "messages",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, nullable=False), sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("conversation_id", uuid_type, nullable=False), sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=False), sa.Column("retrieved_chunk_ids", json_type), sa.Column("sources", json_type),
        sa.Column("provider", sa.String(80)), sa.Column("model", sa.String(120)), sa.Column("latency_ms", sa.Integer),
        sa.Column("input_tokens", sa.Integer), sa.Column("output_tokens", sa.Integer), sa.Column("status", sa.String(20), nullable=False, server_default="completed"),
        sa.Column("metadata", json_type), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="ck_messages_role"),
        sa.CheckConstraint("status IN ('completed', 'failed')", name="ck_messages_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
    )
    for table, columns in {
        "ai_agents": ["organization_id", "company_id", "status"],
        "conversations": ["organization_id", "company_id", "agent_id", "status"],
        "messages": ["organization_id", "company_id", "conversation_id", "created_at"],
    }.items():
        for column in columns:
            op.create_index(f"ix_{table}_{column}", table, [column])

    for table in ("ai_agents", "conversations", "messages"):
        op.execute(sa.text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"REVOKE ALL ON TABLE public.{table} FROM anon"))
    op.execute(sa.text("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.ai_agents TO authenticated"))
    op.execute(sa.text("GRANT SELECT, INSERT, UPDATE ON TABLE public.conversations TO authenticated"))
    op.execute(sa.text("GRANT SELECT, INSERT ON TABLE public.messages TO authenticated"))

    _policy("ai_agents", "ai_agents_select_member", "SELECT", member.format(table="public.ai_agents"))
    _policy("ai_agents", "ai_agents_insert_admin", "INSERT", check=f"{admin.format(table='public.ai_agents')} AND {company_tenant.format(table='public.ai_agents')}")
    _policy("ai_agents", "ai_agents_update_admin", "UPDATE", admin.format(table="public.ai_agents"), f"{admin.format(table='public.ai_agents')} AND {company_tenant.format(table='public.ai_agents')}")
    _policy("ai_agents", "ai_agents_delete_admin", "DELETE", admin.format(table="public.ai_agents"))
    _policy("conversations", "conversations_select_member", "SELECT", member.format(table="public.conversations"))
    _policy("conversations", "conversations_insert_member", "INSERT", check=f"{member.format(table='public.conversations')} AND {agent_tenant.format(table='public.conversations')}")
    _policy("conversations", "conversations_update_member", "UPDATE", member.format(table="public.conversations"), member.format(table="public.conversations"))
    _policy("messages", "messages_select_member", "SELECT", member.format(table="public.messages"))
    _policy("messages", "messages_insert_user", "INSERT", check=f"{member.format(table='public.messages')} AND role = 'user' AND {conversation_tenant.format(table='public.messages')}")


def downgrade() -> None:
    for table in ("messages", "conversations", "ai_agents"):
        for action in ("select_member", "insert_admin", "update_admin", "delete_admin", "insert_member", "update_member", "insert_user"):
            op.execute(sa.text(f"DROP POLICY IF EXISTS {table}_{action} ON public.{table}"))
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("ai_agents")
