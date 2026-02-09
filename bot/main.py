# bot/main.py
import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.admin_components.admin_router import admin_router
from src.user_components.user_router import user_router
from src.FormManager.FormManager import FormManager
from src.FormManager.form_middleware import FormMiddleware
from src.db_components.database import create_tables
from src.db_components.db_middleware import DBMiddleware

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_environment():
    """Проверяет наличие критических переменных окружения"""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("❌ BOT_TOKEN не установлен в переменных окружения!")
        raise ValueError("BOT_TOKEN environment variable is required")
    return bot_token

async def main():
    logger.info("🚀 Starting bot...")
    
    # Валидируем окружение
    try:
        bot_token = validate_environment()
    except ValueError as e:
        logger.error(f"Environment validation failed: {e}")
        return
    
    # Автоматически применяем миграции/создаем таблицы
    try:
        logger.info("📊 Applying database migrations...")
        await create_tables()
        logger.info("✅ Database migrations applied")
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        return
    
    # Инициализация бота и диспетчера
    try:
        bot = Bot(token=bot_token)
        dp = Dispatcher(storage=MemoryStorage())
    except Exception as e:
        logger.error(f"❌ Failed to initialize bot: {e}")
        return
    
    # Инициализация FormManager
    form = FormManager()
    
    # Регистрируем middleware (порядок важен!)
    dp.update.middleware(DBMiddleware())
    dp.update.middleware(FormMiddleware(form))
    
    # Регистрируем роутеры
    dp.include_router(admin_router)
    dp.include_router(user_router)
    
    # Запускаем бота
    try:
        logger.info("🤖 Bot is starting polling...")
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Bot polling error: {e}")
        raise
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Bot interrupted by user")
    except Exception as e:
        logger.critical(f"❌ Critical error: {e}")