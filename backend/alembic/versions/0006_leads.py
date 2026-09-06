"""Add tenant-scoped commercial leads and qualification state."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0006_leads"
down_revision = "0005_ai_agents_chat"
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
    json_type = sa.JSON().with_variant(JSONB(), "postgresql")
    now = sa.text("CURRENT_TIMESTAMP")

    op.create_table(
        "leads",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("agent_id", uuid_type),
        sa.Column("conversation_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(200)),
        sa.Column("email", sa.String(320)),
        sa.Column("phone", sa.String(32)),
        sa.Column("interest", sa.Text),
        sa.Column("intent", sa.String(40), nullable=False),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("source", sa.String(40), nullable=False, server_default="dashboard_test"),
        sa.Column("consent_to_contact", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("qualified_at", sa.DateTime(timezone=True)),
        sa.Column("last_user_message_id", uuid_type),
        sa.Column("metadata", json_type),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("intent IN ('general_inquiry', 'purchase_interest', 'request_quote', 'request_demo', 'contact_request', 'appointment_interest', 'other_commercial')", name="ck_leads_intent"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_leads_confidence"),
        sa.CheckConstraint("status IN ('new', 'qualified', 'contacted', 'converted', 'lost')", name="ck_leads_status"),
        sa.CheckConstraint("source IN ('dashboard_test', 'widget', 'whatsapp', 'email', 'api')", name="ck_leads_source"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["ai_agents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_user_message_id"], ["messages.id"], ondelete="SET NULL"),
    )
    for column in ("organization_id", "company_id", "status", "intent", "source"):
        op.create_index(f"ix_leads_{column}", "leads", [column])
    op.create_index("ux_leads_conversation_id", "leads", ["conversation_id"], unique=True)

    op.execute(sa.text("ALTER TABLE public.leads ENABLE ROW LEVEL SECURITY"))
    op.execute(sa.text("REVOKE ALL ON TABLE public.leads FROM anon"))
    op.execute(sa.text("GRANT SELECT, UPDATE ON TABLE public.leads TO authenticated"))

    member = "EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = public.leads.organization_id AND m.user_id = auth.uid())"
    admin = "EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = public.leads.organization_id AND m.user_id = auth.uid() AND m.role IN ('owner', 'admin'))"
    tenant = "EXISTS (SELECT 1 FROM public.companies c WHERE c.id = public.leads.company_id AND c.organization_id = public.leads.organization_id) AND EXISTS (SELECT 1 FROM public.conversations cv WHERE cv.id = public.leads.conversation_id AND cv.organization_id = public.leads.organization_id AND cv.company_id = public.leads.company_id) AND (public.leads.agent_id IS NULL OR EXISTS (SELECT 1 FROM public.ai_agents a WHERE a.id = public.leads.agent_id AND a.organization_id = public.leads.organization_id AND a.company_id = public.leads.company_id))"
    _policy("leads", "leads_select_member", "SELECT", member)
    _policy("leads", "leads_update_admin", "UPDATE", f"{admin} AND {tenant}", f"{admin} AND {tenant}")


def downgrade() -> None:
    op.execute(sa.text("DROP POLICY IF EXISTS leads_select_member ON public.leads"))
    op.execute(sa.text("DROP POLICY IF EXISTS leads_update_admin ON public.leads"))
    op.drop_index("ux_leads_conversation_id", table_name="leads")
    for column in ("organization_id", "company_id", "status", "intent", "source"):
        op.drop_index(f"ix_leads_{column}", table_name="leads")
    op.drop_table("leads")
