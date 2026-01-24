# src/bot/filters/admin.py
from typing import Union
from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from src.Config.settings import settings


class IsAdmin(BaseFilter):
    """Фильтр для проверки прав администратора."""
    
    async def __call__(
        self, 
        event: Union[Message, CallbackQuery]
    ) -> bool:
        """Проверяет, есть ли пользователь в списке администраторов."""
        user_id = event.from_user.id
        
        # Используем admin_ids_list из настроек
        is_admin = user_id in settings.admin_ids_list
        
        if not is_admin and isinstance(event, Message):
            await event.answer("⛔ У вас нет прав доступа к этой команде")
        
        return is_admin