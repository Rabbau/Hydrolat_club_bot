from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from .user_manager import user_manager


class DBMiddleware(BaseMiddleware):
    """Inject shared user manager into aiogram handler context."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        data["user_manager"] = user_manager
        data["users"] = user_manager
        return await handler(event, data)
