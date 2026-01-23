import os
from typing import AsyncGenerator  # Добавьте этот импорт
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class Base(DeclarativeBase):
    pass

# Получаем URL базы данных из переменных окружения
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL не найден в .env файле. "
        "Убедитесь, что файл .env существует и содержит DATABASE_URL"
    )

# Создаем асинхронный движок для PostgreSQL
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Показывать SQL-запросы в консоли (полезно для отладки)
    future=True  # Использовать новые версии SQLAlchemy
)

# Создаем фабрику для асинхронных сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Генератор для получения асинхронной сессии.
    Используется в зависимостях FastAPI, но может пригодиться и в других случаях.
    """
    async with async_session_maker() as session:
        yield session