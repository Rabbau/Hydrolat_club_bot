from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from src.database.crud import is_superadmin

class IsSuperAdmin(Filter):
    """Фильтр для проверки, является ли пользователь суперадмином."""
    
    async def __call__(self, message_or_callback: Message | CallbackQuery) -> bool:
        user_id = getattr(message_or_callback.from_user, 'id', None)
        if user_id:
            result = await is_superadmin(user_id)
            return result
        return False