import os
from sqlalchemy.ext.asyncio import create_async_engine

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("database_url not in .env")

engine = create_async_engine(
    DATABASE_URL,
    echo=True
)