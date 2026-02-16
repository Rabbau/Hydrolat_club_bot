"""
Инициализация стандартных сообщений бота при первом запуске
"""
import asyncio
import logging
from src.db_components.survey_manager import bot_message_manager
from src.db_components.models import BotMessageType

logger = logging.getLogger(__name__)

async def init_bot_messages():
    """Инициализировать стандартные сообщения"""
    try:
        await bot_message_manager.init_default_messages()
        logger.info("✅ Стандартные сообщения инициализированы")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации сообщений: {e}")

if __name__ == "__main__":
    asyncio.run(init_bot_messages())
