import asyncio

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.loader import bot
from src.bot.handlers.start import router as start_router
from src.bot.handlers.questionnaire.handlers import router as questionnaire_router


async def main() -> None:
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(start_router)
    dp.include_router(questionnaire_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
