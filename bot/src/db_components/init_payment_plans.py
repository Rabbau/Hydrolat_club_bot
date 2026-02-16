"""
Initialization script for default payment plans.
Run: python -m src.db_components.init_payment_plans
"""
import asyncio
import logging

from src.db_components.survey_manager import payment_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_default_plans():
    default_plans = [
        {
            "name": "Месячный",
            "duration_days": 30,
            "price": 990.00,
            "description": "Доступ на 1 месяц",
        },
        {
            "name": "Полугодовой",
            "duration_days": 180,
            "price": 4990.00,
            "description": "Доступ на 6 месяцев (скидка 15%)",
        },
        {
            "name": "Годовой",
            "duration_days": 365,
            "price": 8990.00,
            "description": "Доступ на 1 год (скидка 25%)",
        },
    ]

    existing = await payment_manager.get_payment_plans()
    existing_names = {p.name for p in existing}

    for plan in default_plans:
        try:
            if plan["name"] in existing_names:
                logger.info("Plan '%s' already exists, skipping", plan["name"])
                continue

            success = await payment_manager.create_payment_plan(
                name=plan["name"],
                duration_days=plan["duration_days"],
                price=plan["price"],
                description=plan["description"],
            )
            if success:
                existing_names.add(plan["name"])
                logger.info(
                    "Created plan '%s': %.2f RUB for %s days",
                    plan["name"],
                    plan["price"],
                    plan["duration_days"],
                )
        except Exception as exc:
            logger.error("Failed to create plan '%s': %s", plan["name"], exc)


if __name__ == "__main__":
    asyncio.run(create_default_plans())
