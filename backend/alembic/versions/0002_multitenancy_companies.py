"""Add organizations, memberships, companies and tenant RLS policies."""

from alembic import op
import sqlalchemy as sa

revision = "0002_multitenancy"
down_revision = "0001_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    uuid_type = sa.Uuid(as_uuid=True)
    now = sa.text("CURRENT_TIMESTAMP")

    op.create_table(
        "organizations",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("status IN ('active', 'suspended', 'archived')", name="ck_organizations_status"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_table(
        "organization_members",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("user_id", uuid_type, nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("role IN ('owner', 'admin', 'member')", name="ck_organization_members_role"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_organization_members_org_user"),
    )
    op.create_table(
        "profiles",
        sa.Column("id", uuid_type, primary_key=True),
        sa.Column("display_name", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.ForeignKeyConstraint(["id"], ["auth.users.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "companies",
        sa.Column("id", uuid_type, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", uuid_type, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("legal_name", sa.String(length=200), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("industry", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("timezone", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=now),
        sa.CheckConstraint("status IN ('active', 'inactive', 'archived')", name="ck_companies_status"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
    )

    op.create_index("ix_organization_members_organization_id", "organization_members", ["organization_id"])
    op.create_index("ix_organization_members_user_id", "organization_members", ["user_id"])
    op.create_index("ix_organization_members_role", "organization_members", ["role"])
    op.create_index("ix_companies_organization_id", "companies", ["organization_id"])

    for table in ("profiles", "organizations", "organization_members", "companies"):
        op.execute(sa.text(f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY"))

    op.execute(sa.text("REVOKE ALL ON TABLE public.profiles, public.organizations, public.organization_members, public.companies FROM anon"))
    op.execute(sa.text("GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.profiles, public.organizations, public.organization_members, public.companies TO authenticated"))

    op.execute(sa.text("""
        CREATE POLICY profiles_select_own ON public.profiles FOR SELECT TO authenticated
        USING (public.profiles.id = auth.uid())
    """))
    op.execute(sa.text("""
        CREATE POLICY profiles_insert_own ON public.profiles FOR INSERT TO authenticated
        WITH CHECK (public.profiles.id = auth.uid())
    """))
    op.execute(sa.text("""
        CREATE POLICY profiles_update_own ON public.profiles FOR UPDATE TO authenticated
        USING (public.profiles.id = auth.uid()) WITH CHECK (public.profiles.id = auth.uid())
    """))
    op.execute(sa.text("""
        CREATE POLICY organizations_select_member ON public.organizations FOR SELECT TO authenticated
        USING (EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = public.organizations.id AND m.user_id = auth.uid()))
    """))
    op.execute(sa.text("""
        CREATE POLICY organizations_insert_authenticated ON public.organizations FOR INSERT TO authenticated
        WITH CHECK (auth.uid() IS NOT NULL)
    """))
    op.execute(sa.text("""
        CREATE POLICY organizations_update_admin ON public.organizations FOR UPDATE TO authenticated
        USING (EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = public.organizations.id AND m.user_id = auth.uid() AND m.role IN ('owner', 'admin')))
        WITH CHECK (EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = public.organizations.id AND m.user_id = auth.uid() AND m.role IN ('owner', 'admin')))
    """))
    op.execute(sa.text("""
        CREATE POLICY organization_members_select_member ON public.organization_members FOR SELECT TO authenticated
        USING (public.organization_members.user_id = auth.uid())
    """))
    op.execute(sa.text("""
        CREATE POLICY organization_members_insert_denied ON public.organization_members FOR INSERT TO authenticated
        WITH CHECK (false)
    """))
    op.execute(sa.text("""
        CREATE POLICY organization_members_update_denied ON public.organization_members FOR UPDATE TO authenticated
        USING (false) WITH CHECK (false)
    """))
    op.execute(sa.text("""
        CREATE POLICY organization_members_delete_denied ON public.organization_members FOR DELETE TO authenticated
        USING (false)
    """))
    op.execute(sa.text("""
        CREATE POLICY companies_select_member ON public.companies FOR SELECT TO authenticated
        USING (EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = public.companies.organization_id AND m.user_id = auth.uid()))
    """))
    op.execute(sa.text("""
        CREATE POLICY companies_insert_admin ON public.companies FOR INSERT TO authenticated
        WITH CHECK (EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = public.companies.organization_id AND m.user_id = auth.uid() AND m.role IN ('owner', 'admin')))
    """))
    op.execute(sa.text("""
        CREATE POLICY companies_update_admin ON public.companies FOR UPDATE TO authenticated
        USING (EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = public.companies.organization_id AND m.user_id = auth.uid() AND m.role IN ('owner', 'admin')))
        WITH CHECK (EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = public.companies.organization_id AND m.user_id = auth.uid() AND m.role IN ('owner', 'admin')))
    """))
    op.execute(sa.text("""
        CREATE POLICY companies_delete_admin ON public.companies FOR DELETE TO authenticated
        USING (EXISTS (SELECT 1 FROM public.organization_members m WHERE m.organization_id = public.companies.organization_id AND m.user_id = auth.uid() AND m.role IN ('owner', 'admin')))
    """))


def downgrade() -> None:
    for table in ("companies", "organization_members", "organizations", "profiles"):
        op.execute(sa.text(f"DROP POLICY IF EXISTS {table}_select_member ON public.{table}"))
    op.drop_table("companies")
    op.drop_table("profiles")
    op.drop_table("organization_members")
    op.drop_table("organizations")
