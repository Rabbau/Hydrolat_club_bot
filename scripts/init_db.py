import asyncio

from src.database.database import Base 
from src.database.session import engine
from src.database import models

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

if __name__ == "__maain__":
    asyncio.run(init_db())