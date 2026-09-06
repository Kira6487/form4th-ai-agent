# RLS tests — Phase 2

These checks require a real Supabase project with migration
`0002_multitenancy` applied. They are not part of local pytest and must not be
reported as passed without a configured Supabase environment.

Recommended reproducible flow:

1. Install Supabase CLI and link the project with
   `supabase link --project-ref <project-ref>`.
2. Run `supabase db push` to apply pending migrations.
3. Create two test users in Supabase Auth and record their UUIDs. Do not store
   their passwords in this repository.
4. Insert one organization, owner membership and company per user using a
   temporary administrative session.
5. Query with each user's JWT and verify that each user only sees its own
   organization/company, non-members cannot read or modify tenant data,
   anonymous users cannot read private data, and `member` cannot mutate
   companies.

FastAPI authorization is tested without Internet in
`backend/tests/test_tenant_isolation.py`; these checks are the second RLS
layer and must run against PostgreSQL/Supabase.

## Phase 3 knowledge checks

After `0003_knowledge_ingestion` is applied, repeat the same two-user setup
with one company and source per organization. Verify that members can read
only their tenant's sources, documents and chunks; owner/admin can mutate;
non-members and `anon` cannot read or write; and direct UUID access cannot
cross organization or company boundaries. The local suite does not validate
PostgreSQL RLS because no Supabase project is configured in this repository.
