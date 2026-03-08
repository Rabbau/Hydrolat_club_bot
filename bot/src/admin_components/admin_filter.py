import os

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from src.db_components.survey_manager import admin_manager


def _parse_env_int(value: str | None) -> int | None:
    if not value:
        return None
    cleaned = value.strip().strip("\"'")
    try:
        return int(cleaned)
    except ValueError:
        return None


def _parse_env_int_set(value: str | None) -> set[int]:
    if not value:
        return set()
    result: set[int] = set()
    for part in value.split(","):
        parsed = _parse_env_int(part)
        if parsed is not None:
            result.add(parsed)
    return result


class AdminFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id

        admin_id = _parse_env_int(os.getenv("ADMIN_ID"))
        super_admin_id = _parse_env_int(os.getenv("SUPER_ADMIN_ID"))
        super_admin_ids = _parse_env_int_set(os.getenv("SUPER_ADMIN_IDS"))

        if admin_id is not None and user_id == admin_id:
            return True
        if (super_admin_id is not None and user_id == super_admin_id) or (
            user_id in super_admin_ids
        ):
            return True

        return await admin_manager.is_admin(user_id)


class SuperAdminFilter(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        user_id = event.from_user.id
        super_admin_id = _parse_env_int(os.getenv("SUPER_ADMIN_ID"))
        super_admin_ids = _parse_env_int_set(os.getenv("SUPER_ADMIN_IDS"))

        if (super_admin_id is not None and user_id == super_admin_id) or (
            user_id in super_admin_ids
        ):
            return True

        return await admin_manager.is_super_admin(user_id)
