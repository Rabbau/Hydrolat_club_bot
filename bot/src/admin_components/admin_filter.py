# src/admin_components/admin_filter.py
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
import os

from src.db_components.survey_manager import admin_manager


class AdminFilter(BaseFilter):
    """Фильтр обычного администратора.

    Источники прав:
    - таблица admin_users (через AdminManager)
    - переменная окружения ADMIN_ID (для первого/резервного админа)
    - SUPER_ADMIN_ID также считается админом
    """

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id

        admin_id_str = os.getenv("ADMIN_ID")
        super_admin_id_str = os.getenv("SUPER_ADMIN_ID")

        # ENV-переменные как быстрый способ
        try:
            if admin_id_str and user_id == int(admin_id_str):
                return True
        except ValueError:
            pass

        try:
            if super_admin_id_str and user_id == int(super_admin_id_str):
                return True
        except ValueError:
            pass

        # Основной источник прав — БД
        return await admin_manager.is_admin(user_id)


class SuperAdminFilter(BaseFilter):
    """Фильтр супер-администратора.

    Источники прав:
    - поле is_super_admin в таблице admin_users
    - переменная окружения SUPER_ADMIN_ID
    """

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id

        super_admin_id_str = os.getenv("SUPER_ADMIN_ID")
        try:
            if super_admin_id_str and user_id == int(super_admin_id_str):
                return True
        except ValueError:
            pass

        return await admin_manager.is_super_admin(user_id)