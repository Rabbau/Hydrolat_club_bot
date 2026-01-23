from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig


from alembic import context
from alembic.config import Config
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config


import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
env_path = project_root / '.env'
print(f"Ищем .env файл по пути: {env_path}")

if env_path.exists():
    print("✓ Файл .env найден")
    # Читаем .env файл вручную, чтобы не зависеть от python-dotenv
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
                    print(f"  Загружено: {key}=***")
                except ValueError:
                    print(f"  Ошибка в строке: {line}")
else:
    print("✗ Файл .env НЕ найден!")

db_url = os.getenv("DATABASE_URL")
if db_url:
    print(f"✓ DATABASE_URL загружен (первые 50 символов): {db_url[:50]}...")
else:
    print("✗ DATABASE_URL НЕ загружен!")

from src.database.database import Base
from src.database import models  # noqa: F401  (важно для регистрации моделей)


# Alembic Config object.
# Когда env.py запускается через команду `alembic`, Alembic прокидывает сюда
# `context.config`. Если env.py импортируют напрямую (например, при проверках),
# этого поля может не быть — тогда подхватываем `alembic.ini` из корня проекта.
config = context.config if hasattr(context, "config") else Config("alembic.ini")

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (needed for alembic migrations)")
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode (async engine)."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
