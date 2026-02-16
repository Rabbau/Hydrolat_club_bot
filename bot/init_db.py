"""
Скрипт для инициализации таблиц БД
"""
import asyncio
import os
from sqlalchemy import text
from src.db_components.database import engine, get_db_session
from src.db_components.models import Base


async def create_tables():
    """Создать все таблицы"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблицы БД созданы успешно!")


if __name__ == "__main__":
    asyncio.run(create_tables())
