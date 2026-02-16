"""
Скрипт инициализации первого администратора
Запустить: python -m src.db_components.init_admin <admin_id> <is_super_admin>
"""
import asyncio
import sys
import logging
from src.db_components.survey_manager import admin_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_first_admin(admin_id: int, is_super_admin: bool = True):
    """Создать первого администратора"""
    try:
        success = await admin_manager.add_admin(
            admin_id=admin_id,
            is_super_admin=is_super_admin
        )
        if success:
            role = "Супер-администратор" if is_super_admin else "Администратор"
            logger.info(f"✅ {role} {admin_id} успешно создан!")
            return True
        else:
            logger.error(f"❌ Администратор {admin_id} уже существует")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка при создании администратора: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python -m src.db_components.init_admin <admin_id> [is_super_admin]")
        print("Пример: python -m src.db_components.init_admin 123456789 true")
        sys.exit(1)
    
    try:
        admin_id = int(sys.argv[1])
        is_super = sys.argv[2].lower() == "true" if len(sys.argv) > 2 else True
        
        asyncio.run(create_first_admin(admin_id, is_super))
    except ValueError:
        print("❌ admin_id должен быть числом")
        sys.exit(1)
