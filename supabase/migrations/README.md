# Supabase migrations

The migration chain is under `backend/alembic/`. Phase 3 adds the knowledge
source/run/document/chunk tables and RLS in `0003_knowledge_ingestion`; it
intentionally does not enable or query vector/embedding features. Do not
enable extensions or create domain tables manually from application startup.
