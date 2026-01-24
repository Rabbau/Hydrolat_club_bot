import asyncio
import logging

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.bot.loader import bot
from src.bot.handlers.start import router as start_router
from src.bot.handlers.questionnaire.handlers import router as questionnaire_router
from src.bot.handlers.admin import router as admin_router

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Основная функция запуска бота."""
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем роутеры
    dp.include_router(start_router)
    dp.include_router(questionnaire_router)
    dp.include_router(admin_router)
    
    logger.info("✅ Бот запущен")
    logger.info(f"🤖 Имя бота: @{(await bot.get_me()).username}")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())