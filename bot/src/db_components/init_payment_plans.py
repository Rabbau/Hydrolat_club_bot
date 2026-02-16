"""
Скрипт инициализации стандартных платежных планов
Запустить: python -m src.db_components.init_payment_plans
"""
import asyncio
import logging
from src.db_components.survey_manager import payment_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_default_plans():
    """Создать стандартные тарифные планы"""
    
    default_plans = [
        {
            "name": "Месячный",
            "duration_days": 30,
            "price": 990.00,
            "description": "Доступ на 1 месяц"
        },
        {
            "name": "Полугодовой",
            "duration_days": 180,
            "price": 4990.00,
            "description": "Доступ на 6 месяцев (скидка 15%)"
        },
        {
            "name": "Годовой",
            "duration_days": 365,
            "price": 8990.00,
            "description": "Доступ на 1 год (скидка 25%)"
        }
    ]
    
    for plan in default_plans:
        try:
            existing = await payment_manager.get_payment_plans()
            # Проверяем, не существует ли уже такой план
            if any(p.name == plan["name"] for p in existing):
                logger.info(f"⏭️ План '{plan['name']}' уже существует, пропускаем")
                continue
            
            success = await payment_manager.create_payment_plan(
                name=plan["name"],
                duration_days=plan["duration_days"],
                price=plan["price"],
                description=plan["description"]
            )
            
            if success:
                logger.info(f"✅ План '{plan['name']}' создан: {plan['price']} ₽ на {plan['duration_days']} дней")
        except Exception as e:
            logger.error(f"❌ Ошибка при создании плана '{plan['name']}': {e}")


if __name__ == "__main__":
    asyncio.run(create_default_plans())
