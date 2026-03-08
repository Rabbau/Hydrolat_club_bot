import logging

import os
from datetime import datetime, timezone

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import func, select

from src.FormManager.FormManager import FormManager
from src.admin_components.admin_callbacks import AdminAction, AdminCallback
from src.admin_components.admin_filter import AdminFilter, SuperAdminFilter
from src.admin_components.admin_keyboards import (
    back_to_main_inline_keyboard,
    back_to_moderation_and_menu_inline_keyboard,
    back_to_pending_payments_and_menu_inline_keyboard,
    back_to_review_surveys_and_menu_inline_keyboard,
    back_to_super_admin_and_menu_inline_keyboard,
    admins_list_inline_keyboard,
    chat_settings_inline_keyboard,
    output_settings_inline_keyboard,
)
from src.db_components.database import get_db_session
from src.db_components.models import BotMessageType, SurveyStatusEnum, SurveySubmission, User
from src.db_components.survey_manager import (
    admin_manager,
    bot_message_manager,
    bot_settings_manager,
    payment_manager,
    promo_code_manager,
    survey_manager,
)
from src.user_components.user_callbacks import UserAction, UserCallback

logger = logging.getLogger(__name__)

moderation_router = Router(name="moderation_router")
moderation_router.message.filter(AdminFilter())
moderation_router.callback_query.filter(AdminFilter())

super_admin_router = Router(name="super_admin_router")
super_admin_router.message.filter(SuperAdminFilter())
super_admin_router.callback_query.filter(SuperAdminFilter())


class ModerationFSM(StatesGroup):
    editing_message = State()
    setting_discount = State()
    adding_admin = State()
    removing_admin = State()
    creating_promo = State()
    creating_plan = State()
    setting_chat_id = State()

async def _resolve_user_id_from_admin_input(message: Message) -> tuple[int | None, str | None]:
    """
    Resolve a Telegram user_id from admin input:
    - numeric text -> tg_id
    - @username or username -> lookup in users.username (case-insensitive)
    - forwarded message -> uses forward_from.id when available
    Returns (user_id, pretty_label_for_messages).
    """
    if message.forward_from and message.forward_from.id:
        fwd = message.forward_from
        pretty = (
            f"@{fwd.username}"
            if fwd.username
            else f'<a href="tg://user?id={fwd.id}">Профиль</a>'
        )
        return int(fwd.id), pretty

    raw = (message.text or "").strip()
    if not raw:
        return None, None

    if raw.isdigit():
        user_id = int(raw)
        return user_id, f'<a href="tg://user?id={user_id}">Профиль</a>'

    username = raw[1:] if raw.startswith("@") else raw
    username = username.strip()
    if not username or " " in username:
        return None, None

    async with get_db_session() as session:
        result = await session.execute(
            select(User.id).where(func.lower(User.username) == username.lower())
        )
        user_id = result.scalar_one_or_none()

    if user_id is None:
        return None, f"@{username}"
    return int(user_id), f"@{username}"


async def _users_display_map(user_ids: list[int]) -> dict[int, str]:
    unique_ids = list(set(user_ids))
    if not unique_ids:
        return {}

    async with get_db_session() as session:
        result = await session.execute(select(User).where(User.id.in_(unique_ids)))
        users = result.scalars().all()

    display_map: dict[int, str] = {}
    for user in users:
        if user.username:
            display_map[user.id] = f"@{user.username}"
        else:
            display_map[user.id] = "без_username"
    return display_map


def _fallback_user_label(user_id: int, users_map: dict[int, str]) -> str:
    return users_map.get(user_id, "без_username")


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


async def _get_target_chat_ids() -> set[int]:
    chat_ids = await bot_settings_manager.get_group_chat_ids()
    if chat_ids:
        return chat_ids

    # Fallback to env for first-run / migration scenarios.
    out: set[int] = set()
    single_chat_id = _parse_env_int(os.getenv("GROUP_CHAT_ID"))
    if single_chat_id is not None:
        out.add(single_chat_id)
    out.update(_parse_env_int_set(os.getenv("GROUP_CHAT_IDS")))
    return out


async def _create_personal_join_link(bot: Bot, user_id: int) -> str | None:
    for chat_id in sorted(await _get_target_chat_ids()):
        try:
            link = await bot.create_chat_invite_link(
                chat_id=chat_id,
                name=f"paid_user_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
                creates_join_request=True,
            )
            return link.invite_link
        except Exception as exc:
            logger.error(
                "Failed to create invite link for user %s in chat %s: %s",
                user_id,
                chat_id,
                exc,
            )
    return None


def _approved_survey_plans_keyboard(plans) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Оплатить: {plan.name} ({plan.price:.2f} ₽ / {plan.duration_days} дн.)",
                    callback_data=UserCallback(
                        action=UserAction.APPROVED_SURVEY_SELECT_PLAN,
                        plan_id=plan.id,
                    ).pack(),
                )
            ]
            for plan in plans
        ]
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.CHAT_SETTINGS))
async def chat_settings_menu(callback: CallbackQuery):
    db_chat_ids = await bot_settings_manager.get_group_chat_ids()
    env_chat_ids: set[int] = set()
    single_env = _parse_env_int(os.getenv("GROUP_CHAT_ID"))
    if single_env is not None:
        env_chat_ids.add(single_env)
    env_chat_ids.update(_parse_env_int_set(os.getenv("GROUP_CHAT_IDS")))

    if db_chat_ids:
        lines = ["<b>Чат(ы) для доступа:</b>", "Источник: <b>настройки бота</b>", ""]
        for cid in sorted(db_chat_ids):
            lines.append(f"• <code>{cid}</code>")
    else:
        lines = [
            "<b>Чат(ы) для доступа:</b>",
            "Источник: <b>.env</b> (GROUP_CHAT_ID/GROUP_CHAT_IDS)",
            "",
        ]
        if env_chat_ids:
            for cid in sorted(env_chat_ids):
                lines.append(f"• <code>{cid}</code>")
        else:
            lines.append("• <i>не задан</i>")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=chat_settings_inline_keyboard,
    )
    await callback.answer()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.SET_CHAT_ID))
async def set_chat_id_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ModerationFSM.setting_chat_id)
    await callback.message.edit_text(
        "Отправьте <b>ID чата</b> (например <code>-100...</code>).\n"
        "Можно прислать числом или переслать сообщение из нужного чата.\n\n"
        "Важно: бот должен быть добавлен в этот чат и иметь нужные права.",
    )
    await callback.answer()


@super_admin_router.message(ModerationFSM.setting_chat_id)
async def set_chat_id_process(message: Message, state: FSMContext):
    chat_id: int | None = None

    if message.forward_from_chat and message.forward_from_chat.id:
        chat_id = int(message.forward_from_chat.id)
    elif message.chat and message.chat.type in ("group", "supergroup"):
        chat_id = int(message.chat.id)
    else:
        chat_id = _parse_env_int(message.text)

    if chat_id is None:
        await message.answer(
            "Не смог распознать ID чата.\n"
            "Пришлите число вида <code>-100...</code> или перешлите сообщение из нужного чата."
        )
        return

    await bot_settings_manager.set_group_chat_id(chat_id)
    await message.answer(
        f"Чат сохранен: <code>{chat_id}</code>",
        reply_markup=chat_settings_inline_keyboard,
    )
    await state.clear()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.CLEAR_CHAT_ID))
async def clear_chat_id(callback: CallbackQuery):
    await bot_settings_manager.clear_group_chat_ids()
    await callback.answer("Очищено.")
    await chat_settings_menu(callback)


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.REVIEW_SURVEYS))
async def review_surveys_menu(callback: CallbackQuery):
    surveys = await survey_manager.get_surveys_by_status(SurveyStatusEnum.PENDING_REVIEW)
    if not surveys:
        await callback.message.edit_text(
            "Нет анкет для проверки.",
            reply_markup=back_to_moderation_and_menu_inline_keyboard,
        )
        await callback.answer()
        return

    users_map = await _users_display_map([survey.user_id for survey in surveys])
    lines = ["<b>Анкеты на проверке:</b>\n"]
    kb_rows: list[list[InlineKeyboardButton]] = []
    for survey in surveys[:50]:
        username = _fallback_user_label(survey.user_id, users_map)
        lines.append(f"• user <b>{username}</b>, анкета <code>{survey.id}</code>")
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=f"Анкета {survey.id} ({username})",
                    callback_data=AdminCallback(
                        action=AdminAction.REVIEW_SURVEY_DETAIL, survey_id=survey.id
                    ).pack(),
                )
            ]
        )
    kb_rows.append(
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.MODERATION).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            )
        ]
    )

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
    )
    await callback.answer()


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.REVIEW_SURVEY_DETAIL)
)
async def review_survey_detail(
    callback: CallbackQuery, callback_data: AdminCallback, form: FormManager
):
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана.", show_alert=True)
        return

    surveys = await survey_manager.get_surveys_by_status(SurveyStatusEnum.PENDING_REVIEW)
    target = next((s for s in surveys if s.id == survey_id), None)
    if not target:
        await callback.answer("Анкета не найдена или уже обработана.", show_alert=True)
        return

    users_map = await _users_display_map([target.user_id])
    username = _fallback_user_label(target.user_id, users_map)
    lines = [
        f"<b>Анкета ID {target.id}</b>",
        f"Пользователь: <b>{username}</b>",
        "",
        "<b>Ответы:</b>",
    ]
    for qid_str, answer in (target.answers or {}).items():
        question_text = f"Вопрос {qid_str}"
        try:
            qid = int(qid_str)
            q = await form.get_question_by_id(qid)
            if q:
                question_text = q["text"]
        except ValueError:
            pass
        lines.append(f"• <b>{question_text}</b>\n  Ответ: {answer}")

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Одобрить",
                    callback_data=AdminCallback(
                        action=AdminAction.APPROVE_SURVEY, survey_id=target.id
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="Одобрить со скидкой",
                    callback_data=AdminCallback(
                        action=AdminAction.APPROVE_SURVEY_WITH_DISCOUNT, survey_id=target.id
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="Отклонить",
                    callback_data=AdminCallback(
                        action=AdminAction.REJECT_SURVEY, survey_id=target.id
                    ).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=AdminCallback(action=AdminAction.REVIEW_SURVEYS).pack(),
                ),
                InlineKeyboardButton(
                    text="В меню",
                    callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
                ),
            ],
        ]
    )
    await callback.message.edit_text("\n".join(lines), reply_markup=kb)
    await callback.answer()


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.APPROVE_SURVEY))
async def approve_survey(callback: CallbackQuery, callback_data: AdminCallback):
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана.", show_alert=True)
        return

    ok = await survey_manager.approve_survey(
        survey_id=survey_id, admin_id=callback.from_user.id, discount=0
    )
    if not ok:
        await callback.answer("Анкета не найдена.", show_alert=True)
        return

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()

    if survey:
        try:
            bot: Bot = callback.message.bot
            plans = await payment_manager.get_payment_plans()
            if plans:
                await bot.send_message(
                    chat_id=survey.user_id,
                    text=(
                        "Анкета одобрена.\n\n"
                        "Выберите тариф для оплаты кнопкой ниже.\n"
                        "Далее бот предложит промокод и покажет итоговую сумму."
                    ),
                    reply_markup=_approved_survey_plans_keyboard(plans),
                )
        except Exception as exc:
            logger.error("Failed to send payment details to %s: %s", survey.user_id, exc)

    await callback.message.edit_text(
        f"Анкета {survey_id} одобрена.",
        reply_markup=back_to_review_surveys_and_menu_inline_keyboard,
    )
    await callback.answer()


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.APPROVE_SURVEY_WITH_DISCOUNT)
)
async def approve_survey_with_discount_start(
    callback: CallbackQuery, callback_data: AdminCallback, state: FSMContext
):
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана.", show_alert=True)
        return

    await state.set_state(ModerationFSM.setting_discount)
    await state.update_data(survey_id=survey_id)
    await callback.message.edit_text("Введите персональную скидку в процентах (0-100):")
    await callback.answer()


@moderation_router.message(ModerationFSM.setting_discount)
async def approve_survey_with_discount_process(message: Message, state: FSMContext):
    data = await state.get_data()
    survey_id = data.get("survey_id")
    if survey_id is None:
        await message.answer("Анкета не выбрана.")
        await state.clear()
        return

    try:
        discount = int(message.text.strip())
    except ValueError:
        await message.answer("Введите целое число от 0 до 100.")
        return
    if discount < 0 or discount > 100:
        await message.answer("Скидка должна быть от 0 до 100.")
        return

    ok = await survey_manager.approve_survey(
        survey_id=survey_id, admin_id=message.from_user.id, discount=discount
    )
    if not ok:
        await message.answer("Анкета не найдена или уже обработана.")
        await state.clear()
        return

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()

    if survey:
        try:
            bot: Bot = message.bot
            plans = await payment_manager.get_payment_plans()
            if plans:
                await bot.send_message(
                    chat_id=survey.user_id,
                    text=(
                        "Анкета одобрена.\n\n"
                        "Выберите тариф для оплаты кнопкой ниже.\n"
                        "Далее бот предложит промокод и покажет итоговую сумму."
                    ),
                    reply_markup=_approved_survey_plans_keyboard(plans),
                )
        except Exception as exc:
            logger.error("Failed to send payment details to %s: %s", survey.user_id, exc)

    await message.answer(
        f"Анкета {survey_id} одобрена. Персональная скидка: {discount}%",
        reply_markup=back_to_review_surveys_and_menu_inline_keyboard,
    )
    await state.clear()


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.REJECT_SURVEY))
async def reject_survey(callback: CallbackQuery, callback_data: AdminCallback):
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана.", show_alert=True)
        return

    ok = await survey_manager.reject_survey(
        survey_id=survey_id, admin_id=callback.from_user.id, comment=""
    )
    if not ok:
        await callback.answer("Анкета не найдена.", show_alert=True)
        return

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()

    if survey:
        reject_msg = await bot_message_manager.get_message(BotMessageType.SURVEY_REJECTED)
        text = (
            reject_msg.content if reject_msg else "К сожалению, ваша анкета отклонена."
        )
        try:
            bot: Bot = callback.message.bot
            await bot.send_message(chat_id=survey.user_id, text=text)
        except Exception as exc:
            logger.error("Failed to send rejection to %s: %s", survey.user_id, exc)

    await callback.message.edit_text(
        f"Анкета {survey_id} отклонена.",
        reply_markup=back_to_review_surveys_and_menu_inline_keyboard,
    )
    await callback.answer()


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.PENDING_PAYMENTS))
async def pending_payments(callback: CallbackQuery):
    surveys = await survey_manager.get_surveys_by_status(SurveyStatusEnum.PENDING_PAYMENT)
    if not surveys:
        await callback.message.edit_text(
            "Нет анкет, ожидающих оплату.",
            reply_markup=back_to_moderation_and_menu_inline_keyboard,
        )
        await callback.answer()
        return

    users_map = await _users_display_map([survey.user_id for survey in surveys])
    plans = await payment_manager.get_payment_plans()
    plan_map = {plan.id: plan for plan in plans}
    lines = ["<b>Ожидают подтверждения оплаты:</b>\n"]
    kb_rows: list[list[InlineKeyboardButton]] = []
    for survey in surveys[:50]:
        username = _fallback_user_label(survey.user_id, users_map)
        personal = survey.personal_discount or 0
        promo = survey.promo_discount or 0
        total = min(100, personal + promo)
        if survey.selected_plan_id is None:
            selected_plan_label = "не выбран"
        else:
            selected_plan = plan_map.get(survey.selected_plan_id)
            if selected_plan:
                selected_plan_label = (
                    f"{selected_plan.name} ({selected_plan.price:.2f} ₽)"
                )
            else:
                selected_plan_label = f"id={survey.selected_plan_id} (неактивен)"
        lines.append(
            f"• user <b>{username}</b>, анкета <code>{survey.id}</code>, "
            f"тариф: <b>{selected_plan_label}</b>, скидка {total}%"
        )
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=f"Открыть {username}",
                    callback_data=AdminCallback(
                        action=AdminAction.PENDING_PAYMENT_DETAIL, survey_id=survey.id
                    ).pack(),
                )
            ]
        )
    kb_rows.append(
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.MODERATION).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            )
        ]
    )

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
    )
    await callback.answer()


def _payment_flow_flags(survey: SurveySubmission) -> dict:
    answers = survey.answers or {}
    pf = answers.get("payment_flow") or {}
    if not isinstance(pf, dict):
        return {}
    return pf


async def _pending_payment_details_text(survey: SurveySubmission) -> str:
    users_map = await _users_display_map([survey.user_id])
    username = _fallback_user_label(survey.user_id, users_map)
    plans = await payment_manager.get_payment_plans()
    plan_map = {p.id: p for p in plans}
    plan = plan_map.get(survey.selected_plan_id) if survey.selected_plan_id else None

    pf = _payment_flow_flags(survey)
    user_clicked_pay = bool(pf.get("user_clicked_pay"))
    admin_tariff_confirmed = bool(pf.get("admin_tariff_confirmed"))

    personal_discount = int(survey.personal_discount or 0)
    promo_discount = int(survey.promo_discount or 0)
    total_discount = min(100, personal_discount + promo_discount)

    if plan is None:
        price_line = "Сумма: <b>нельзя рассчитать (тариф не выбран)</b>"
        plan_line = "Тариф: <b>не выбран</b>"
    else:
        final_price = plan.price * (100 - total_discount) / 100
        plan_line = f"Тариф: <b>{plan.name}</b> ({plan.price:.2f} ₽ / {plan.duration_days} дн.)"
        price_line = f"К оплате: <b>{final_price:.2f} ₽</b>"

    lines = [
        "<b>Оплата: детали</b>",
        "",
        f"Пользователь: <b>{username}</b>",
        f"Анкета ID: <code>{survey.id}</code>",
        plan_line,
        f"Скидка персональная: <b>{personal_discount}%</b>",
        f"Скидка промокод: <b>{promo_discount}%</b>",
        f"Итого скидка: <b>{total_discount}%</b>",
        price_line,
        "",
        f"Пользователь нажал «Оплатить»: <b>{'да' if user_clicked_pay else 'нет'}</b>",
        f"Тариф подтвержден админом: <b>{'да' if admin_tariff_confirmed else 'нет'}</b>",
    ]
    return "\n".join(lines)


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.PENDING_PAYMENT_DETAIL)
)
async def pending_payment_detail(callback: CallbackQuery, callback_data: AdminCallback):
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана.", show_alert=True)
        return

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()
    if not survey:
        await callback.answer("Анкета не найдена.", show_alert=True)
        return

    pf = _payment_flow_flags(survey)
    admin_tariff_confirmed = bool(pf.get("admin_tariff_confirmed"))

    kb_rows: list[list[InlineKeyboardButton]] = []
    if survey.selected_plan_id is None:
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text="Напомнить выбрать тариф",
                    callback_data=AdminCallback(
                        action=AdminAction.REMIND_SELECT_TARIFF, survey_id=survey_id
                    ).pack(),
                )
            ]
        )
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text="Изменить тариф",
                    callback_data=AdminCallback(
                        action=AdminAction.CHANGE_TARIFF, survey_id=survey_id
                    ).pack(),
                )
            ]
        )
    else:
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text="Подтвердить тариф",
                    callback_data=AdminCallback(
                        action=AdminAction.CONFIRM_TARIFF, survey_id=survey_id
                    ).pack(),
                )
            ]
        )
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text="Изменить тариф",
                    callback_data=AdminCallback(
                        action=AdminAction.CHANGE_TARIFF, survey_id=survey_id
                    ).pack(),
                )
            ]
        )
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text="Подтвердить оплату",
                    callback_data=AdminCallback(
                        action=AdminAction.CONFIRM_PAYMENT, survey_id=survey_id
                    ).pack(),
                )
            ]
        )
        if not admin_tariff_confirmed:
            # Keep UX: admin sees the required step in the details screen.
            pass

    kb_rows.append(
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.PENDING_PAYMENTS).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ]
    )

    text = await _pending_payment_details_text(survey)
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
    )
    await callback.answer()


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.REMIND_SELECT_TARIFF)
)
async def remind_select_tariff(callback: CallbackQuery, callback_data: AdminCallback):
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана.", show_alert=True)
        return

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()
    if not survey:
        await callback.answer("Анкета не найдена.", show_alert=True)
        return

    try:
        bot: Bot = callback.message.bot
        await bot.send_message(
            chat_id=survey.user_id,
            text=(
                "Для оплаты нужно выбрать тариф.\n\n"
                "Откройте сообщение с тарифами и нажмите кнопку нужного тарифа."
            ),
        )
        await callback.answer("Отправлено пользователю")
    except Exception:
        await callback.answer("Не удалось отправить сообщение", show_alert=True)


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.CHANGE_TARIFF))
async def change_tariff(callback: CallbackQuery, callback_data: AdminCallback):
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана.", show_alert=True)
        return

    plans = await payment_manager.get_payment_plans()
    if not plans:
        await callback.answer("Нет активных тарифов.", show_alert=True)
        return

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{p.name} ({p.price:.2f} ₽ / {p.duration_days} дн.)",
                    callback_data=AdminCallback(
                        action=AdminAction.SET_TARIFF,
                        survey_id=survey_id,
                        plan_id=p.id,
                    ).pack(),
                )
            ]
            for p in plans
        ]
        + [
            [
                InlineKeyboardButton(
                    text="Назад",
                    callback_data=AdminCallback(
                        action=AdminAction.PENDING_PAYMENT_DETAIL, survey_id=survey_id
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="В меню",
                    callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
                ),
            ]
        ]
    )
    await callback.message.edit_text("Выберите новый тариф:", reply_markup=kb)
    await callback.answer()


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.SET_TARIFF))
async def set_tariff(callback: CallbackQuery, callback_data: AdminCallback):
    survey_id = callback_data.survey_id
    plan_id = callback_data.plan_id
    if survey_id is None or plan_id is None:
        await callback.answer("Не удалось определить анкету/тариф.", show_alert=True)
        return

    updated = await survey_manager.admin_set_selected_plan_for_survey(
        survey_id=survey_id,
        plan_id=plan_id,
        admin_id=callback.from_user.id,
    )
    if not updated:
        await callback.answer("Не удалось обновить тариф.", show_alert=True)
        return

    await callback.answer("Тариф обновлен")
    await pending_payment_detail(
        callback,
        AdminCallback(action=AdminAction.PENDING_PAYMENT_DETAIL, survey_id=survey_id),
    )


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.CONFIRM_TARIFF))
async def confirm_tariff(callback: CallbackQuery, callback_data: AdminCallback):
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана.", show_alert=True)
        return

    ok = await survey_manager.admin_confirm_tariff(survey_id, callback.from_user.id)
    if not ok:
        await callback.answer(
            "Нельзя подтвердить тариф (тариф не выбран или анкета не в оплате).",
            show_alert=True,
        )
        return

    await callback.answer("Тариф подтвержден")
    await pending_payment_detail(
        callback,
        AdminCallback(action=AdminAction.PENDING_PAYMENT_DETAIL, survey_id=survey_id),
    )


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.CONFIRM_PAYMENT))
async def confirm_payment(callback: CallbackQuery, callback_data: AdminCallback):
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана.", show_alert=True)
        return

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()
    if not survey:
        await callback.answer("Анкета не найдена.", show_alert=True)
        return

    users_map = await _users_display_map([survey.user_id])
    username = _fallback_user_label(survey.user_id, users_map)
    plans = await payment_manager.get_payment_plans()
    if not plans:
        await callback.answer("Нет активных тарифных планов.", show_alert=True)
        return
    if survey.selected_plan_id is None:
        await callback.answer(
            "Пользователь еще не выбрал тариф. Откройте детали и напомните выбрать тариф.",
            show_alert=True,
        )
        return

    pf = _payment_flow_flags(survey)
    if not pf.get("admin_tariff_confirmed"):
        await callback.answer(
            "Сначала нажмите «Подтвердить тариф» в деталях оплаты.",
            show_alert=True,
        )
        return

    plan = next((p for p in plans if p.id == survey.selected_plan_id), None)
    if not plan:
        await callback.answer("Тарифный план не найден.", show_alert=True)
        return

    personal_discount = survey.personal_discount or 0
    promo_discount = survey.promo_discount or 0
    total_discount = min(100, personal_discount + promo_discount)
    final_price = plan.price * (100 - total_discount) / 100

    created = await payment_manager.create_subscription(
        user_id=survey.user_id,
        plan_id=plan.id,
        promo_code_id=survey.promo_code_id,
        custom_price=final_price,
    )
    if not created:
        await callback.answer("Ошибка создания подписки.", show_alert=True)
        return

    if survey.promo_code_id:
        await promo_code_manager.use_promo_code_by_id(survey.promo_code_id)

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey_db = result.scalar_one_or_none()
        if survey_db:
            survey_db.status = SurveyStatusEnum.PAID

    confirm_msg = await bot_message_manager.get_message(BotMessageType.PAYMENT_CONFIRMED)
    text = (
        confirm_msg.content
        if confirm_msg
        else "Оплата подтверждена, подписка активирована."
    )
    try:
        bot: Bot = callback.message.bot
        await bot.send_message(chat_id=survey.user_id, text=text)
        invite_link = await _create_personal_join_link(bot, survey.user_id)
        if invite_link:
            await bot.send_message(
                chat_id=survey.user_id,
                text=(
                    "Ссылка для вступления в беседу:\n"
                    f"{invite_link}\n\n"
                    "После запроса бот автоматически подтвердит вход при активной подписке."
                ),
            )
        else:
            await bot.send_message(
                chat_id=survey.user_id,
                text=(
                    "Не удалось сформировать новую ссылку в беседу автоматически.\n"
                    "Напишите администратору для ручной выдачи доступа."
                ),
            )
    except Exception as exc:
        logger.error("Failed to send payment confirmation to %s: %s", survey.user_id, exc)

    await callback.message.edit_text(
        "Платеж подтвержден.\n"
        f"user <b>{username}</b>, тариф: {plan.name}, "
        f"скидка: {total_discount}%, цена: {final_price:.2f} ₽",
        reply_markup=back_to_pending_payments_and_menu_inline_keyboard,
    )
    await callback.answer()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.OUTPUT_SETTINGS))
async def output_settings_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "<b>Настройка вывода</b>\n\nВыберите сообщение для редактирования:",
        reply_markup=output_settings_inline_keyboard,
    )
    await callback.answer()


async def _start_message_edit(
    callback: CallbackQuery,
    state: FSMContext,
    message_type: BotMessageType,
    title: str,
):
    current_msg = await bot_message_manager.get_message(message_type)
    text = (
        f"<b>{title}</b>\n\n"
        f"{current_msg.content if current_msg else 'не установлено'}\n\n"
        "Отправьте новый текст:"
    )
    await state.set_state(ModerationFSM.editing_message)
    await state.update_data(message_type=message_type)
    await callback.message.edit_text(text=text, reply_markup=back_to_main_inline_keyboard)
    await callback.answer()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_WELCOME))
async def edit_welcome_start(callback: CallbackQuery, state: FSMContext):
    await _start_message_edit(callback, state, BotMessageType.WELCOME, "Текущее приветствие")


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_PAYMENT_DETAILS))
async def edit_payment_details_start(callback: CallbackQuery, state: FSMContext):
    await _start_message_edit(
        callback, state, BotMessageType.PAYMENT_DETAILS, "Текущие реквизиты"
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_PAYMENT_CONFIRMED))
async def edit_payment_confirmed_start(callback: CallbackQuery, state: FSMContext):
    await _start_message_edit(
        callback,
        state,
        BotMessageType.PAYMENT_CONFIRMED,
        "Текущее сообщение принятия оплаты",
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_SURVEY_REJECTED))
async def edit_survey_rejected_start(callback: CallbackQuery, state: FSMContext):
    await _start_message_edit(
        callback, state, BotMessageType.SURVEY_REJECTED, "Текущее сообщение отказа"
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_SURVEY_SUBMITTED))
async def edit_survey_submitted_start(callback: CallbackQuery, state: FSMContext):
    await _start_message_edit(
        callback,
        state,
        BotMessageType.SURVEY_SUBMITTED,
        "Текущее сообщение после отправки анкеты",
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_STATUS_EMPTY))
async def edit_status_empty_start(callback: CallbackQuery, state: FSMContext):
    await _start_message_edit(
        callback,
        state,
        BotMessageType.STATUS_EMPTY,
        "Текущее сообщение для пользователя без анкеты",
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_PROMO_APPLIED))
async def edit_promo_applied_start(callback: CallbackQuery, state: FSMContext):
    await _start_message_edit(
        callback,
        state,
        BotMessageType.PROMO_APPLIED,
        "Текущее сообщение успешного промокода",
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_PROMO_INVALID))
async def edit_promo_invalid_start(callback: CallbackQuery, state: FSMContext):
    await _start_message_edit(
        callback,
        state,
        BotMessageType.PROMO_INVALID,
        "Текущее сообщение ошибки промокода",
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_TARIFFS_HEADER))
async def edit_tariffs_header_start(callback: CallbackQuery, state: FSMContext):
    await _start_message_edit(
        callback,
        state,
        BotMessageType.TARIFFS_HEADER,
        "Текущий заголовок списка тарифов",
    )


@super_admin_router.message(ModerationFSM.editing_message)
async def edit_message_process(message: Message, state: FSMContext):
    data = await state.get_data()
    message_type = data.get("message_type")
    success = await bot_message_manager.update_message(message_type, message.text)
    if success:
        await message.answer(
            "Сообщение успешно обновлено.",
            reply_markup=back_to_super_admin_and_menu_inline_keyboard,
        )
    else:
        await message.answer(
            "Ошибка при обновлении сообщения.",
            reply_markup=back_to_super_admin_and_menu_inline_keyboard,
        )
    await state.clear()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.LIST_PLANS))
async def list_plans(callback: CallbackQuery):
    plans = await payment_manager.get_payment_plans()
    lines = ["<b>Список активных тарифов:</b>\n"]
    kb_rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="Добавить тариф",
                callback_data=AdminCallback(action=AdminAction.CREATE_PLAN).pack(),
            )
        ]
    ]

    if not plans:
        lines.append("Тарифы пока не добавлены.")
    else:
        for plan in plans:
            details = f"• <b>{plan.name}</b>: {plan.price:.2f} ₽ / {plan.duration_days} дн."
            if plan.description:
                details += f"\n{plan.description}"
            lines.append(details)
            kb_rows.append(
                [
                    InlineKeyboardButton(
                        text=f"Удалить тариф: {plan.name}",
                        callback_data=AdminCallback(
                            action=AdminAction.DELETE_PLAN, plan_id=plan.id
                        ).pack(),
                    )
                ]
            )

    kb_rows.append(
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.HISTORY).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            )
        ]
    )

    await callback.message.edit_text(
        "\n\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows),
    )
    await callback.answer()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.LIST_PROMOS))
async def list_promos(callback: CallbackQuery):
    promos = await promo_code_manager.list_promo_codes(include_inactive=True)

    lines = ["<b>Список промокодов:</b>\n"]
    kb_rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="Создать промокод",
                callback_data=AdminCallback(action=AdminAction.CREATE_PROMO).pack(),
            )
        ]
    ]

    if not promos:
        lines.append("Промокодов пока нет.")
    else:
        for promo in promos[:100]:
            status = "активен" if promo.is_active else "неактивен"
            scope = "общий" if promo.is_collective else "персональный"
            usage = ""
            if promo.max_uses is not None:
                usage = f", использований {promo.current_uses}/{promo.max_uses}"
            else:
                usage = f", использований {promo.current_uses}"

            assigned = ""
            if (not promo.is_collective) and promo.assigned_user_id:
                assigned = f", для <code>{promo.assigned_user_id}</code>"

            lines.append(
                f"• <b>{promo.code}</b> — {promo.discount_percent}% ({scope}, {status}{usage}{assigned})"
            )
            if promo.is_active:
                kb_rows.append(
                    [
                        InlineKeyboardButton(
                            text=f"Удалить промокод: {promo.code}",
                            callback_data=AdminCallback(
                                action=AdminAction.DELETE_PROMO, promo_code_id=promo.id
                            ).pack(),
                        )
                    ]
                )

    kb_rows.append(
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.HISTORY).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ]
    )

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
    )
    await callback.answer()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.DELETE_PROMO))
async def delete_promo(callback: CallbackQuery, callback_data: AdminCallback):
    promo_code_id = callback_data.promo_code_id
    if promo_code_id is None:
        await callback.answer("Промокод не выбран.", show_alert=True)
        return

    ok = await promo_code_manager.delete_promo_code_by_id(promo_code_id)
    if not ok:
        await callback.answer("Промокод не найден.", show_alert=True)
        return

    await callback.answer("Промокод удален.")
    await list_promos(callback)


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.DELETE_PLAN))
async def delete_plan(callback: CallbackQuery, callback_data: AdminCallback):
    plan_id = callback_data.plan_id
    if plan_id is None:
        await callback.answer("Тариф не выбран.", show_alert=True)
        return

    success = await payment_manager.delete_payment_plan(plan_id)
    if not success:
        await callback.answer("Тариф не найден.", show_alert=True)
        return

    await callback.answer("Тариф удален.")
    await list_plans(callback)


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.LIST_ADMINS))
async def list_admins(callback: CallbackQuery):
    admins = await admin_manager.get_all_admins()
    if not admins:
        await callback.message.edit_text(
            "Администраторы не найдены.",
            reply_markup=admins_list_inline_keyboard,
        )
        await callback.answer()
        return

    users_map = await _users_display_map([admin.id for admin in admins])
    lines = ["<b>Администраторы системы:</b>\n"]
    for admin in admins:
        role = "Супер-админ" if admin.is_super_admin else "Админ"
        username = (
            f"@{admin.username}"
            if admin.username
            else _fallback_user_label(admin.id, users_map)
        )
        lines.append(f"{role}: <b>{username}</b>")
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=admins_list_inline_keyboard
    )
    await callback.answer()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.ADD_ADMIN))
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ModerationFSM.adding_admin)
    await callback.message.edit_text(
        "Отправьте Telegram ID или @username нового администратора.\n"
        "Если пользователь не найден по @username, попросите его написать боту /start "
        "или перешлите сюда сообщение от него."
    )
    await callback.answer()


@super_admin_router.message(ModerationFSM.adding_admin)
async def add_admin_process(message: Message, state: FSMContext):
    admin_id, label = await _resolve_user_id_from_admin_input(message)
    if admin_id is None:
        await message.answer(
            "Не смог определить пользователя.\n"
            "Пришлите Telegram ID (числом), @username, или перешлите сообщение от пользователя."
        )
        return

    success = await admin_manager.add_admin(admin_id, is_super_admin=False)
    users_map = await _users_display_map([admin_id])
    username = label or _fallback_user_label(admin_id, users_map)
    await message.answer(
        (
            f"Админ {username} добавлен."
            if success
            else f"Админ {username} уже существует."
        ),
        reply_markup=admins_list_inline_keyboard,
    )
    await state.clear()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.REMOVE_ADMIN))
async def remove_admin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ModerationFSM.removing_admin)
    await callback.message.edit_text(
        "Отправьте Telegram ID или @username администратора для удаления.\n"
        "Если пользователь не найден по @username, попросите его написать боту /start "
        "или перешлите сюда сообщение от него."
    )
    await callback.answer()


@super_admin_router.message(ModerationFSM.removing_admin)
async def remove_admin_process(message: Message, state: FSMContext):
    admin_id, label = await _resolve_user_id_from_admin_input(message)
    if admin_id is None:
        await message.answer(
            "Не смог определить пользователя.\n"
            "Пришлите Telegram ID (числом), @username, или перешлите сообщение от пользователя."
        )
        return

    users_map = await _users_display_map([admin_id])
    username = label or _fallback_user_label(admin_id, users_map)
    success = await admin_manager.remove_admin(admin_id)
    await message.answer(
        f"Админ {username} удален." if success else f"Админ {username} не найден.",
        reply_markup=admins_list_inline_keyboard,
    )
    await state.clear()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.CREATE_PROMO))
async def create_promo_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ModerationFSM.creating_promo)
    await callback.message.edit_text(
        "Введите промокод и скидку через пробел, например:\n<code>SPRING25 25</code>"
    )
    await callback.answer()


@super_admin_router.message(ModerationFSM.creating_promo)
async def create_promo_process(message: Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 2:
        await message.answer("Формат: CODE 10")
        return
    code, discount_raw = parts
    try:
        discount = int(discount_raw)
    except ValueError:
        await message.answer("Скидка должна быть числом.")
        return
    if discount < 1 or discount > 99:
        await message.answer("Скидка должна быть от 1 до 99.")
        return

    success = await promo_code_manager.create_promo_code(
        code=code, discount_percent=discount, is_collective=True
    )
    await message.answer(
        (
            f"Промокод {code.upper()} создан со скидкой {discount}%."
            if success
            else "Не удалось создать промокод."
        ),
        reply_markup=back_to_super_admin_and_menu_inline_keyboard,
    )
    await state.clear()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.CREATE_PLAN))
async def create_plan_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ModerationFSM.creating_plan)
    await callback.message.edit_text(
        "Введите тариф в формате:\n"
        "<code>Название;дней;цена;описание</code>\n\n"
        "Пример:\n"
        "<code>Месяц;30;990;Доступ на 30 дней</code>"
    )
    await callback.answer()


@super_admin_router.message(ModerationFSM.creating_plan)
async def create_plan_process(message: Message, state: FSMContext):
    parts = [part.strip() for part in message.text.split(";", 3)]
    if len(parts) < 3:
        await message.answer(
            "Неверный формат. Используйте: Название;дней;цена;описание"
        )
        return

    name = parts[0]
    try:
        duration_days = int(parts[1])
        price = float(parts[2].replace(",", "."))
    except ValueError:
        await message.answer(
            "Дни должны быть числом, цена - числом (например 990 или 990.50)"
        )
        return

    description = parts[3] if len(parts) == 4 else ""
    if duration_days <= 0:
        await message.answer("Количество дней должно быть больше 0.")
        return
    if price < 0:
        await message.answer("Цена не может быть отрицательной.")
        return

    success = await payment_manager.create_payment_plan(
        name=name,
        duration_days=duration_days,
        price=price,
        description=description,
    )
    await message.answer(
        (
            f"Тариф создан: {name} ({duration_days} дн., {price:.2f} ₽)."
            if success
            else "Не удалось создать тариф."
        ),
        reply_markup=back_to_super_admin_and_menu_inline_keyboard,
    )
    await state.clear()


moderation_router.include_router(super_admin_router)
