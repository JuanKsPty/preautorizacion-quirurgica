"""
Configuracion de Alembic.

La URL de la base sale de DATABASE_URL (el .env de la raiz), no de alembic.ini,
para que no haya dos sitios donde configurar lo mismo.

Mientras AUTO_CREATE_TABLES=true la API crea las tablas al arrancar y Alembic
no hace falta. Cuando el esquema tenga que evolucionar sin perder datos:

    1. pon AUTO_CREATE_TABLES=false en el .env
    2. pnpm run db:revision "describe el cambio"
    3. pnpm run db:migrate
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import app.models  # noqa: F401  (registra las tablas en SQLModel.metadata)
from alembic import context
from app.core.config import settings

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            # SQLite necesita reconstruir la tabla para alterar columnas.
            render_as_batch=settings.database_kind == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
