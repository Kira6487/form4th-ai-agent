"""Add tenant-scoped knowledge ingestion pipeline tables and RLS."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003_knowledge_ingestion"
down_revision = "0002_multitenancy"
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

    op.create_table(
        "knowledge_sources",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000)),
        sa.Column("source_url", sa.String(2000)),
        sa.Column("storage_path", sa.String(1000)),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("last_error", sa.Text),
        sa.Column("last_indexed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", uuid_type),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("type IN ('website', 'manual', 'pdf')", name="ck_knowledge_sources_type"),
        sa.CheckConstraint("status IN ('pending', 'processing', 'ready', 'failed', 'disabled')", name="ck_knowledge_sources_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "knowledge_ingestion_runs",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("source_id", uuid_type, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("provider", sa.String(80)),
        sa.Column("external_job_id", sa.String(200)),
        sa.Column("documents_processed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("chunks_created", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(80)),
        sa.Column("error_message", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="ck_knowledge_ingestion_runs_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "knowledge_documents",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("source_id", uuid_type, nullable=False),
        sa.Column("ingestion_run_id", uuid_type),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_type", sa.String(40), nullable=False, server_default="text/markdown"),
        sa.Column("language", sa.String(20)),
        sa.Column("source_url", sa.String(2000)),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["knowledge_ingestion_runs.id"], ondelete="SET NULL"),
    )
    op.create_table(
        "knowledge_chunks",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("company_id", uuid_type, nullable=False),
        sa.Column("source_id", uuid_type, nullable=False),
        sa.Column("document_id", uuid_type, nullable=False),
        sa.Column("ingestion_run_id", uuid_type),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("approx_token_count", sa.Integer),
        sa.Column("metadata", json_type, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_id"], ["knowledge_sources.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ingestion_run_id"], ["knowledge_ingestion_runs.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_knowledge_sources_organization_id", "knowledge_sources", ["organization_id"])
    op.create_index("ix_knowledge_sources_company_id", "knowledge_sources", ["company_id"])
    op.create_index("ix_knowledge_sources_status", "knowledge_sources", ["status"])
    for table in ("knowledge_ingestion_runs", "knowledge_documents", "knowledge_chunks"):
        op.create_index(f"ix_{table}_organization_id", table, ["organization_id"])
        op.create_index(f"ix_{table}_company_id", table, ["company_id"])
    op.create_index("ix_knowledge_ingestion_runs_source_id", "knowledge_ingestion_runs", ["source_id"])
    op.create_index("ix_knowledge_ingestion_runs_status", "knowledge_ingestion_runs", ["status"])
    op.create_index("ix_knowledge_documents_source_id", "knowledge_documents", ["source_id"])
    op.create_index("ix_knowledge_documents_content_hash", "knowledge_documents", ["content_hash"])
    op.create_index("ix_knowledge_documents_is_active", "knowledge_documents", ["is_active"])
    op.create_index("ix_knowledge_chunks_source_id", "knowledge_chunks", ["source_id"])
    op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
    op.create_index("ix_knowledge_chunks_content_hash", "knowledge_chunks", ["content_hash"])
    op.create_index("ix_knowledge_chunks_is_active", "knowledge_chunks", ["is_active"])
    op.create_index("uq_knowledge_documents_active_hash", "knowledge_documents", ["source_id", "content_hash"], unique=True, postgresql_where=sa.text("is_active = true"))
    op.create_index("uq_knowledge_chunks_active_hash", "knowledge_chunks", ["source_id", "content_hash"], unique=True, postgresql_where=sa.text("is_active = true"))

    for table in ("knowledge_sources", "knowledge_ingestion_runs", "knowledge_documents", "knowledge_chunks"):
        op.execute(sa.text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"REVOKE ALL ON TABLE public.{table} FROM anon"))
        op.execute(sa.text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.{table} TO authenticated"))
    for table in ("knowledge_sources", "knowledge_ingestion_runs", "knowledge_documents", "knowledge_chunks"):
        _policy(table, f"{table}_select_member", "SELECT", member.format(table=f"public.{table}"))
        _policy(table, f"{table}_insert_admin", "INSERT", check=admin.format(table=f"public.{table}"))
        _policy(table, f"{table}_update_admin", "UPDATE", admin.format(table=f"public.{table}"), admin.format(table=f"public.{table}"))
        _policy(table, f"{table}_delete_admin", "DELETE", admin.format(table=f"public.{table}"))


def downgrade() -> None:
    for table in ("knowledge_chunks", "knowledge_documents", "knowledge_ingestion_runs", "knowledge_sources"):
        for action in ("select_member", "insert_admin", "update_admin", "delete_admin"):
            op.execute(sa.text(f"DROP POLICY IF EXISTS {table}_{action} ON public.{table}"))
    for table in ("knowledge_chunks", "knowledge_documents", "knowledge_ingestion_runs", "knowledge_sources"):
        op.drop_table(table)
