import html

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

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
from src.db_components.models import SurveyStatusEnum
from src.db_components.survey_manager import payment_manager, survey_manager
from src.db_components.user_manager import user_manager
from src.survey_components.survey_router import survey_router
from src.survey_components.survey_utils import show_survey_menu
from src.user_components.user_keyboard import admin_survey_check_status as admin_status_kb

admin_router = Router(name="admin_router")
admin_router.message.filter(AdminFilter())
admin_router.callback_query.filter(AdminFilter())

admin_router.include_router(survey_router)
admin_router.include_router(moderation_router)


@admin_router.message(Command("admin"))
async def open_admin_panel(message: Message):
    await show_admin_main_menu(message)
    await message.answer("Быстрые действия:", reply_markup=admin_status_kb)


@admin_router.message(Command("id"))
async def show_my_id(message: Message):
    await message.answer(f"Ваш ID: <code>{message.from_user.id}</code>")


@admin_router.message(F.text == "Админка")
async def open_admin_panel_from_user_keyboard(message: Message):
    await show_admin_main_menu(message)


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
    active_subs = len(await payment_manager.get_active_subscriptions())

    text = (
        "<b>Статистика</b>\n\n"
        f"Пользователей: <b>{users_count}</b>\n"
        f"На проверке: <b>{counts.get('pending_review', 0)}</b>\n"
        f"Ожидают оплату: <b>{counts.get('pending_payment', 0)}</b>\n"
        f"Оплачено: <b>{counts.get('paid', 0)}</b>\n"
        f"Отклонено: <b>{counts.get('rejected', 0)}</b>\n"
        f"Активных подписок: <b>{active_subs}</b>"
    )
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Пользователей: {users_count}",
                    callback_data=AdminCallback(action=AdminAction.STATS_USERS).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"На проверке: {counts.get('pending_review', 0)}",
                    callback_data=AdminCallback(
                        action=AdminAction.STATS_PENDING_REVIEW
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Ожидают оплату: {counts.get('pending_payment', 0)}",
                    callback_data=AdminCallback(
                        action=AdminAction.STATS_PENDING_PAYMENT
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Оплачено: {counts.get('paid', 0)}",
                    callback_data=AdminCallback(action=AdminAction.STATS_PAID).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Отклонено: {counts.get('rejected', 0)}",
                    callback_data=AdminCallback(action=AdminAction.STATS_REJECTED).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"Активных подписок: {active_subs}",
                    callback_data=AdminCallback(action=AdminAction.STATS_ACTIVE_SUBS).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
                )
            ],
        ]
    )
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


async def _users_display_map() -> dict[int, str]:
    users = await user_manager.get_all_users_with_info()
    display_map: dict[int, str] = {}
    for user in users:
        user_id = user["id"]
        username = user.get("username")
        first_name = user.get("first_name") or "Профиль"
        if username:
            display_map[user_id] = f"@{html.escape(username)}"
        else:
            display_map[user_id] = (
                f'<a href="tg://user?id={user_id}">{html.escape(first_name)}</a>'
            )
    return display_map


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.STATS_USERS))
async def statistics_users_list(callback: CallbackQuery):
    users = await user_manager.get_all_users_with_info()
    if not users:
        await callback.message.edit_text(
            "Пользователи не найдены.", reply_markup=back_to_main_inline_keyboard
        )
        await callback.answer()
        return

    lines = ["<b>Пользователи:</b>\n"]
    for user in users[:100]:
        user_id = user["id"]
        username = user.get("username")
        first_name = user.get("first_name") or "Профиль"
        if username:
            lines.append(f"• @{html.escape(username)}")
        else:
            lines.append(
                f'• <a href="tg://user?id={user_id}">{html.escape(first_name)}</a>'
            )

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=back_to_main_inline_keyboard
    )
    await callback.answer()


async def _show_survey_status_list(
    callback: CallbackQuery, status: SurveyStatusEnum, title: str
):
    surveys = await survey_manager.get_surveys_by_status(status)
    if not surveys:
        await callback.message.edit_text(
            f"{title}: пусто.", reply_markup=back_to_main_inline_keyboard
        )
        await callback.answer()
        return

    display_map = await _users_display_map()
    lines = [f"<b>{title}</b>\n"]
    for survey in surveys[:100]:
        user_label = display_map.get(
            survey.user_id, f'<a href="tg://user?id={survey.user_id}">Профиль</a>'
        )
        lines.append(f"• {user_label}, анкета <code>{survey.id}</code>")
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=back_to_main_inline_keyboard
    )
    await callback.answer()


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.STATS_PENDING_REVIEW))
async def statistics_pending_review_list(callback: CallbackQuery):
    await _show_survey_status_list(callback, SurveyStatusEnum.PENDING_REVIEW, "На проверке")


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.STATS_PENDING_PAYMENT))
async def statistics_pending_payment_list(callback: CallbackQuery):
    await _show_survey_status_list(
        callback, SurveyStatusEnum.PENDING_PAYMENT, "Ожидают оплату"
    )


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.STATS_PAID))
async def statistics_paid_list(callback: CallbackQuery):
    await _show_survey_status_list(callback, SurveyStatusEnum.PAID, "Оплачено")


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.STATS_REJECTED))
async def statistics_rejected_list(callback: CallbackQuery):
    await _show_survey_status_list(callback, SurveyStatusEnum.REJECTED, "Отклонено")


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.STATS_ACTIVE_SUBS))
async def statistics_active_subscriptions_list(callback: CallbackQuery):
    active_subscriptions = await payment_manager.get_active_subscriptions()
    if not active_subscriptions:
        await callback.message.edit_text(
            "Активные подписки не найдены.", reply_markup=back_to_main_inline_keyboard
        )
        await callback.answer()
        return

    plans = await payment_manager.get_payment_plans()
    plan_map = {plan.id: plan.name for plan in plans}
    display_map = await _users_display_map()

    lines = ["<b>Активные подписки:</b>\n"]
    for sub in active_subscriptions[:100]:
        user_label = display_map.get(
            sub.user_id, f'<a href="tg://user?id={sub.user_id}">Профиль</a>'
        )
        plan_name = plan_map.get(sub.plan_id, f"id={sub.plan_id}")
        lines.append(
            f"• {user_label}, тариф <b>{html.escape(plan_name)}</b>, до {sub.end_date.strftime('%d.%m.%Y')}"
        )
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=back_to_main_inline_keyboard
    )
    await callback.answer()


@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.HISTORY))
async def super_admin_menu(callback: CallbackQuery):
    await show_super_admin_menu(callback)
