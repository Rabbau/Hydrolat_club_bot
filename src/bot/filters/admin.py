from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from src.database.crud import is_admin

class IsAdmin(Filter):
    """Фильтр для проверки прав администратора."""
    
    async def __call__(self, message_or_callback: Message | CallbackQuery) -> bool:
        user_id = getattr(message_or_callback.from_user, 'id', None)
        return await is_admin(user_id) if user_id else False