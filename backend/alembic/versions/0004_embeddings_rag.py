"""Add Gemini embeddings and pgvector indexes for tenant-scoped RAG."""

from alembic import op
import sqlalchemy as sa

revision = "0004_embeddings_rag"
down_revision = "0003_knowledge_ingestion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("CREATE EXTENSION IF NOT EXISTS vector"))
    op.execute(sa.text("ALTER TABLE public.knowledge_chunks ADD COLUMN embedding vector(768)"))
    op.add_column("knowledge_chunks", sa.Column("embedding_model", sa.String(120), nullable=True))
    op.add_column("knowledge_chunks", sa.Column("embedding_dimensions", sa.Integer, nullable=True))
    op.add_column("knowledge_chunks", sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("knowledge_chunks", sa.Column("embedding_status", sa.String(20), nullable=False, server_default="pending"))
    op.add_column("knowledge_chunks", sa.Column("embedding_error", sa.Text, nullable=True))
    op.create_check_constraint("ck_knowledge_chunks_embedding_status", "knowledge_chunks", "embedding_status IN ('pending', 'processing', 'ready', 'failed')")
    op.create_index("ix_knowledge_chunks_embedding_status", "knowledge_chunks", ["embedding_status"])
    op.execute(sa.text("CREATE INDEX ix_knowledge_chunks_embedding_hnsw ON public.knowledge_chunks USING hnsw (embedding vector_cosine_ops)"))


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS public.ix_knowledge_chunks_embedding_hnsw"))
    op.drop_constraint("ck_knowledge_chunks_embedding_status", "knowledge_chunks", type_="check")
    op.drop_index("ix_knowledge_chunks_embedding_status", table_name="knowledge_chunks")
    op.drop_column("knowledge_chunks", "embedding_error")
    op.drop_column("knowledge_chunks", "embedding_status")
    op.drop_column("knowledge_chunks", "embedded_at")
    op.drop_column("knowledge_chunks", "embedding_dimensions")
    op.drop_column("knowledge_chunks", "embedding_model")
    op.execute(sa.text("ALTER TABLE public.knowledge_chunks DROP COLUMN embedding"))
