from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.models.base import Base
from app.models import AIAgent, Company, Conversation, KnowledgeChunk, KnowledgeDocument, KnowledgeIngestionRun, KnowledgeSource, Lead, Message, Organization, OrganizationMember  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = get_settings().database_url
if database_url:
    migration_url = make_url(database_url)
    if migration_url.drivername in {"postgresql", "postgresql+asyncpg"}:
        migration_url = migration_url.set(drivername="postgresql+psycopg")
    config.set_main_option("sqlalchemy.url", migration_url.render_as_string(hide_password=False).replace("%", "%%"))

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("DATABASE_URL is required to run migrations")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    if not config.get_main_option("sqlalchemy.url"):
        raise RuntimeError("DATABASE_URL is required to run migrations")
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
