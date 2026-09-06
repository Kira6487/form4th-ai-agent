# Supabase migrations

Phase 1 keeps the migration chain under `backend/alembic/`. Domain tables and
the optional `vector` extension belong to later phases, after their schemas and
compatibility requirements are defined. Do not enable extensions or create
domain tables manually from application startup.
