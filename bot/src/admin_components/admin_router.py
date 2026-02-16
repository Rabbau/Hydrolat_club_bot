from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from src.FormManager.FormManager import FormManager
from src.admin_components.admin_callbacks import AdminAction, AdminCallback
from src.admin_components.admin_filter import AdminFilter
from src.admin_components.admin_keyboards import back_to_main_inline_keyboard
from src.admin_components.admin_utils import (
    show_admin_main_menu,
    show_moderation_menu,
    show_super_admin_menu,
)
from src.admin_components.moderation_router import moderation_router
from src.db_components.survey_manager import payment_manager, survey_manager
from src.db_components.user_manager import user_manager
from src.survey_components.survey_router import survey_router
from src.survey_components.survey_utils import show_survey_menu

admin_router = Router(name="admin_router")
admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())

admin_router.include_router(survey_router)
admin_router.include_router(moderation_router)


@admin_router.message(CommandStart())
async def start(message: Message):
    await show_admin_main_menu(message)


@admin_router.message(Command("id"))
async def show_my_id(message: Message):
    await message.answer(f"Ваш ID: <code>{message.from_user.id}</code>")


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.SURVEY_MENU))
async def survey_menu(callback: CallbackQuery, form: FormManager):
    await show_survey_menu(callback, form)


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.MODERATION))
async def moderation_menu(callback: CallbackQuery):
    await show_moderation_menu(callback)


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.STATISTICS))
async def statistics_menu(callback: CallbackQuery):
    counts = await survey_manager.get_status_counts()
    users_count = await user_manager.get_users_count()
    active_subs = 0
    for user_id in await user_manager.get_all_users():
        sub = await payment_manager.get_user_subscription(user_id)
        if sub:
            active_subs += 1

    text = (
        "<b>Статистика</b>\n\n"
        f"Пользователей: <b>{users_count}</b>\n"
        f"На проверке: <b>{counts.get('pending_review', 0)}</b>\n"
        f"Ожидают оплату: <b>{counts.get('pending_payment', 0)}</b>\n"
        f"Оплачено: <b>{counts.get('paid', 0)}</b>\n"
        f"Отклонено: <b>{counts.get('rejected', 0)}</b>\n"
        f"Активных подписок: <b>{active_subs}</b>"
    )
    await callback.message.edit_text(text, reply_markup=back_to_main_inline_keyboard)
    await callback.answer()


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.HISTORY))
async def super_admin_menu(callback: CallbackQuery):
    await show_super_admin_menu(callback)
