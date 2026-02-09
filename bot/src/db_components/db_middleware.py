# bot/src/db_components/db_middleware.py
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from .user_manager import user_manager

# # автоматическое добавление в бд
# class DBMiddleware(BaseMiddleware):
#     """Middleware для добавления user_manager в контекст обработчиков"""
    
#     async def __call__(
#         self,
#         handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
#         event: TelegramObject,
#         data: Dict[str, Any]
#     ) -> Any:
#         # Для обратной совместимости добавляем под обоими ключами
#         data["user_manager"] = user_manager
#         data["users"] = user_manager
        
#         # Если есть пользователь, добавляем его в БД (если еще нет)
#         if isinstance(event, (Message, CallbackQuery)):
#             user = event.from_user
#             if user:
#                 # Проверяем, существует ли пользователь
#                 if not user_manager.user_exists(user.id):
#                     user_manager.add_user(
#                         user_id=user.id,
#                         username=user.username,
#                         first_name=user.first_name,
#                         last_name=user.last_name,
#                     )
        
#         return await handler(event, data)
    
# тоже самое без авт.добавления в бд
class DBMiddleware(BaseMiddleware):
    """Middleware для добавления user_manager в контекст обработчиков"""
    
    def __init__(self, user_db=None):
        # Принимаем аргумент для обратной совместимости, но игнорируем его
        # так как используем глобальный user_manager
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Добавляем user_manager в данные обработчиков
        data["user_manager"] = user_manager
        data["users"] = user_manager  # для обратной совместимости
        return await handler(event, data)  # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ!