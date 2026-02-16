import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from src.FormManager.FormManager import FormManager
from src.FormManager.form_middleware import FormMiddleware
from src.admin_components.admin_router import admin_router
from src.db_components.database import create_tables
from src.db_components.db_middleware import DBMiddleware
from src.db_components.survey_manager import bot_message_manager
from src.user_components.user_router import user_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def validate_environment() -> str:
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN environment variable is required")
    return bot_token


async def main() -> None:
    logger.info("Starting bot...")
    try:
        bot_token = validate_environment()
    except ValueError as exc:
        logger.error("Environment validation failed: %s", exc)
        return

    try:
        await create_tables()
        await bot_message_manager.init_default_messages()
    except Exception as exc:
        logger.error("Database initialization failed: %s", exc)
        return

    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    form = FormManager()

    dp.update.middleware(DBMiddleware())
    dp.update.middleware(FormMiddleware(form))

    dp.include_router(admin_router)
    dp.include_router(user_router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
