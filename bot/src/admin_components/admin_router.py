from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from src.admin_components.admin_callbacks import AdminCallback, AdminAction
from src.admin_components.admin_filter import AdminFilter
from src.admin_components.admin_utils import (
    show_admin_main_menu,
    show_moderation_menu,
    show_super_admin_menu,
)
from src.survey_components.survey_utils import show_survey_menu
from src.survey_components.survey_router import survey_router
from src.admin_components.moderation_router import moderation_router

admin_router = Router(name="admin_router")

admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())

# Вложенные роутеры
admin_router.include_router(survey_router)
admin_router.include_router(moderation_router)


@admin_router.message(CommandStart())
async def start(message: Message):
    await show_admin_main_menu(message)


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.SURVEY_MENU))
async def survey_menu(callback: CallbackQuery):
    await show_survey_menu(callback)


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.MODERATION))
async def moderation_menu(callback: CallbackQuery):
    await show_moderation_menu(callback)


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.HISTORY))
async def super_admin_menu(callback: CallbackQuery):
    """Открыть меню настроек бота (для супер-админа)."""
    await show_super_admin_menu(callback)
