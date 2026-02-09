# bot/init_alembic.py
import os
import subprocess
import sys

def init_alembic():
    """Initialize Alembic environment"""
    print("Initializing Alembic...")
    
    # Создаем папку для миграций
    os.makedirs("alembic/versions", exist_ok=True)
    
    # Создаем alembic.ini если его нет
    alembic_ini = """[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://{user}:{password}@{host}:{port}/{dbname}

[post_write_hooks]
hooks = black

[loggers]
keys = root

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
    
    # Получаем параметры БД из переменных окружения
    db_config = {
        'user': os.getenv('DB_USER', 'tg_bot_user'),
        'password': os.getenv('DB_PASSWORD', 'tg_bot_password'),
        'host': os.getenv('DB_HOST', 'postgres'),
        'port': os.getenv('DB_PORT', '5432'),
        'dbname': os.getenv('DB_NAME', 'tg_bot_db')
    }
    
    with open('alembic.ini', 'w') as f:
        f.write(alembic_ini.format(**db_config))
    
    # Инициализируем Alembic
    subprocess.run([sys.executable, "-m", "alembic", "init", "alembic"], check=True)
    
    # Обновляем env.py
    env_py_path = "alembic/env.py"
    with open(env_py_path, 'r') as f:
        content = f.read()
    
    # Обновляем импорты и настройки
    new_content = '''import asyncio
import os
import sys
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Добавляем путь к проекту
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Импортируем модели
from src.db_components.models import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# set your target_metadata
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context."""
    
    # Получаем URL из переменных окружения или конфига
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
    
    with open(env_py_path, 'w') as f:
        f.write(new_content)
    
    print("✅ Alembic initialized successfully!")
    
    # Создаем первую миграцию
    print("Creating initial migration...")
    subprocess.run([sys.executable, "-m", "alembic", "revision", "--autogenerate", "-m", "Initial migration"], check=True)
    
    print("✅ Initial migration created!")

if __name__ == "__main__":
    init_alembic()