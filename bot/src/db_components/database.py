# bot/src/db_components/database.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from contextlib import asynccontextmanager
import os
from typing import AsyncGenerator
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# Database URL
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'tg_bot_db')
DB_USER = os.getenv('DB_USER', 'tg_bot_user')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'tg_bot_password')

DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

logger.info(f"Database URL: {DATABASE_URL.replace(DB_PASSWORD, '***')}")

# Create async engine with optimized settings
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True,
    pool_recycle=3600,  # Recycle connections every hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()

@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with proper error handling"""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()


async def run_migrations():
    """Run Alembic migrations automatically"""
    try:
        # Импортируем Alembic
        from alembic.config import Config
        from alembic import command
        
        # Путь к alembic.ini
        alembic_ini_path = os.path.join(os.path.dirname(__file__), '..', '..', 'alembic.ini')
        
        if not os.path.exists(alembic_ini_path):
            logger.warning("alembic.ini not found, creating tables directly")
            await create_tables_direct()
            return
        
        # Создаем конфиг Alembic
        alembic_cfg = Config(alembic_ini_path)
        
        # Устанавливаем URL базы данных
        alembic_cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        
        logger.info("Running Alembic migrations...")
        command.upgrade(alembic_cfg, "head")
        logger.info("✅ Alembic migrations completed")
        
    except ImportError:
        logger.warning("Alembic not installed, creating tables directly")
        await create_tables_direct()
    except Exception as e:
        logger.error(f"❌ Alembic migration failed: {e}")
        logger.info("⚠️ Falling back to direct table creation...")
        await create_tables_direct()


async def create_tables_direct():
    """Create tables directly (fallback method)"""
    from .models import Base
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created directly")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise


async def create_tables():
    """Main function to create tables (uses Alembic if available)"""
    await run_migrations()


async def drop_tables():
    """Drop all tables (use with caution!)"""
    from .models import Base
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("✅ Database tables dropped")
    except Exception as e:
        logger.error(f"❌ Failed to drop tables: {e}")
        raise


async def close_engine():
    """Properly close the database engine"""
    await engine.dispose()
    logger.info("Database engine closed")