from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import Bot

from src.admin_components.admin_callbacks import AdminCallback, AdminAction
from src.admin_components.admin_filter import AdminFilter, SuperAdminFilter
from src.db_components.survey_manager import (
    survey_manager,
    payment_manager,
    admin_manager,
    bot_message_manager,
)
from src.db_components.models import SurveyStatusEnum, BotMessageType
from src.FormManager.FormManager import FormManager

import logging

logger = logging.getLogger(__name__)

moderation_router = Router(name="moderation_router")
moderation_router.message.filter(AdminFilter())
moderation_router.callback_query.filter(AdminFilter())


class ModerationFSM(StatesGroup):
    """FSM для процесса модерации (оставлена на будущее расширение)."""

    rejecting_survey = State()
    editing_message = State()
    setting_discount = State()
    adding_admin = State()
    removing_admin = State()


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.REVIEW_SURVEYS)
)
async def review_surveys_menu(callback: CallbackQuery):
    """Показать список анкет для проверки (PENDING_REVIEW)."""
    surveys = await survey_manager.get_surveys_by_status(
        SurveyStatusEnum.PENDING_REVIEW
    )
    
    if not surveys:
        await callback.message.edit_text(text="📋 Нет анкет для проверки")
        await callback.answer()
        return
    
    lines = ["📋 <b>Анкеты на проверку:</b>\n"]
    keyboard_rows = []
    
    for survey in surveys[:10]:
        created = survey.created_at.strftime("%d.%m.%Y %H:%M")
        lines.append(
            f"• Пользователь ID <code>{survey.user_id}</code>, анкета ID <code>{survey.id}</code>, дата: {created}"
        )
        keyboard_rows.append(
            [
                {
                    "text": f"Анкета {survey.id} (user {survey.user_id})",
                    "survey_id": survey.id,
                }
            ]
        )

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=row[0]["text"],
                    callback_data=AdminCallback(
                        action=AdminAction.REVIEW_SURVEY_DETAIL,
                        survey_id=row[0]["survey_id"],
                    ).pack(),
                )
            ]
            for row in keyboard_rows
        ]
    )

    await callback.message.edit_text(text="\n".join(lines), reply_markup=kb)
    await callback.answer()


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.REVIEW_SURVEY_DETAIL)
)
async def review_survey_detail(
    callback: CallbackQuery, callback_data: AdminCallback, form: FormManager
):
    """Показать содержимое конкретной анкеты и кнопки Одобрить/Отклонить."""
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Не удалось определить анкету", show_alert=True)
        return

    async_survey = await survey_manager.get_surveys_by_status(SurveyStatusEnum.PENDING_REVIEW)
    # Получаем конкретную анкету
    target = next((s for s in async_survey if s.id == survey_id), None)

    if not target:
        await callback.answer("Анкета не найдена или уже обработана", show_alert=True)
        return

    answers: dict = target.answers or {}

    lines = [
        f"📝 <b>Анкета ID {target.id}</b>",
        f"Пользователь ID: <code>{target.user_id}</code>",
        "",
        "<b>Ответы:</b>",
    ]

    # Форматируем ответы, подтягивая текст вопросов из FormManager, если возможно
    for qid_str, answer in answers.items():
        try:
            qid = int(qid_str)
        except (TypeError, ValueError):
            qid = None
        question_text = None
        if qid is not None:
            q = form.get_question_by_id(qid)
            if q:
                question_text = q.get("text")
        if not question_text:
            question_text = f"Вопрос {qid_str}"

        lines.append(f"• <b>{question_text}</b>\n  Ответ: {answer}")

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Одобрить (без скидки)",
                    callback_data=AdminCallback(
                        action=AdminAction.APPROVE_SURVEY, survey_id=target.id
                    ).pack(),
                ),
                InlineKeyboardButton(
                    text="✅ Одобрить со скидкой",
                    callback_data=AdminCallback(
                        action=AdminAction.APPROVE_SURVEY_WITH_DISCOUNT,
                        survey_id=target.id,
                    ).pack(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=AdminCallback(
                        action=AdminAction.REJECT_SURVEY, survey_id=target.id
                    ).pack(),
                )
            ],
        ]
    )

    await callback.message.edit_text("\n".join(lines), reply_markup=kb)
    await callback.answer()


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.APPROVE_SURVEY)
)
async def approve_survey(callback: CallbackQuery, callback_data: AdminCallback):
    """Одобрить анкету без персональной скидки и отправить реквизиты пользователю."""
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Не удалось определить анкету", show_alert=True)
        return

    admin_id = callback.from_user.id

    ok = await survey_manager.approve_survey(
        survey_id=survey_id, admin_id=admin_id, discount=0
    )
    if not ok:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    # Получаем обновлённую анкету, чтобы узнать пользователя
    from sqlalchemy import select
    from src.db_components.database import get_db_session
    from src.db_components.models import SurveySubmission

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()

    if not survey:
        await callback.answer("Ошибка при обновлении анкеты", show_alert=True)
        return

    # Отправляем реквизиты пользователю
    payment_details = await bot_message_manager.get_message(
        BotMessageType.PAYMENT_DETAILS
    )
    text = (
        payment_details.content
        if payment_details
        else "Анкета одобрена. Пожалуйста, свяжитесь с администратором для оплаты."
    )

    bot: Bot = callback.message.bot
    try:
        await bot.send_message(chat_id=survey.user_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Не удалось отправить реквизиты пользователю {survey.user_id}: {e}")

    await callback.message.edit_text(
        text=f"✅ Анкета ID {survey_id} одобрена. Реквизиты отправлены пользователю."
    )
    await callback.answer()


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.APPROVE_SURVEY_WITH_DISCOUNT)
)
async def approve_survey_with_discount_start(
    callback: CallbackQuery, callback_data: AdminCallback, state: FSMContext
):
    """Начать процесс одобрения с персональной скидкой."""
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Не удалось определить анкету", show_alert=True)
        return

    await state.set_state(ModerationFSM.setting_discount)
    await state.update_data(survey_id=survey_id)
    await callback.message.edit_text(
        text=(
            "Введите размер персональной скидки в процентах (0–100).\n"
            "Например, '20' для скидки 20%."
        )
    )
    await callback.answer()


@moderation_router.message(ModerationFSM.setting_discount)
async def approve_survey_with_discount_process(message: Message, state: FSMContext):
    """Получить размер скидки, сохранить в анкете и отправить реквизиты."""
    data = await state.get_data()
    survey_id = data.get("survey_id")
    if survey_id is None:
        await message.answer("Не удалось найти анкету. Попробуйте ещё раз.")
        await state.clear()
        return

    try:
        discount = int(message.text.strip())
    except ValueError:
        await message.answer("Пожалуйста, введите целое число от 0 до 100.")
        return

    if discount < 0 or discount > 100:
        await message.answer("Скидка должна быть от 0 до 100 процентов.")
        return

    admin_id = message.from_user.id

    ok = await survey_manager.approve_survey(
        survey_id=survey_id, admin_id=admin_id, discount=discount
    )
    if not ok:
        await message.answer("Анкета не найдена или уже обработана.")
        await state.clear()
        return

    from sqlalchemy import select
    from src.db_components.database import get_db_session
    from src.db_components.models import SurveySubmission

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()

    if not survey:
        await message.answer("Ошибка при обновлении анкеты.")
        await state.clear()
        return

    payment_details = await bot_message_manager.get_message(
        BotMessageType.PAYMENT_DETAILS
    )
    text = (
        payment_details.content
        if payment_details
        else "Анкета одобрена. Пожалуйста, свяжитесь с администратором для оплаты."
    )

    bot: Bot = message.bot
    try:
        await bot.send_message(chat_id=survey.user_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Не удалось отправить реквизиты пользователю {survey.user_id}: {e}")

    await message.answer(
        f"✅ Анкета ID {survey_id} одобрена с персональной скидкой {discount}%. "
        f"Реквизиты отправлены пользователю."
    )
    await state.clear()


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.REJECT_SURVEY)
)
async def reject_survey(callback: CallbackQuery, callback_data: AdminCallback):
    """Отклонить анкету (без указания причины) и отправить сообщение пользователю."""
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Не удалось определить анкету", show_alert=True)
        return

    admin_id = callback.from_user.id

    ok = await survey_manager.reject_survey(
        survey_id=survey_id, admin_id=admin_id, comment=""
    )
    if not ok:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    from sqlalchemy import select
    from src.db_components.database import get_db_session
    from src.db_components.models import SurveySubmission

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()

    if not survey:
        await callback.answer("Ошибка при обновлении анкеты", show_alert=True)
        return

    # Отправляем пользователю сообщение об отказе
    reject_msg = await bot_message_manager.get_message(
        BotMessageType.SURVEY_REJECTED
    )
    text = (
        reject_msg.content
        if reject_msg
        else "К сожалению, ваша анкета отклонена. При необходимости свяжитесь с администратором."
    )

    bot: Bot = callback.message.bot
    try:
        await bot.send_message(chat_id=survey.user_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Не удалось отправить отказ пользователю {survey.user_id}: {e}")

    await callback.message.edit_text(
        text=f"❌ Анкета ID {survey_id} отклонена. Пользователь уведомлён."
    )
    await callback.answer()


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.PENDING_PAYMENTS)
)
async def pending_payments(callback: CallbackQuery):
    """Показать анкеты, которые ожидают оплаты (PENDING_PAYMENT)."""
    surveys = await survey_manager.get_surveys_by_status(
        SurveyStatusEnum.PENDING_PAYMENT
    )
    
    if not surveys:
        await callback.message.edit_text(text="✅ Все ожидающие оплаты обработаны")
        await callback.answer()
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    lines = ["💳 <b>Ожидается подтверждение оплаты:</b>\n"]
    kb_rows = []

    for survey in surveys[:10]:
        lines.append(f"• Пользователь ID <code>{survey.user_id}</code>, анкета ID <code>{survey.id}</code>")
        kb_rows.append(
            [
                InlineKeyboardButton(
                    text=f"Подтвердить для {survey.user_id}",
                    callback_data=AdminCallback(
                        action=AdminAction.CONFIRM_PAYMENT, survey_id=survey.id
                    ).pack(),
                )
            ]
        )

    kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    await callback.message.edit_text(text="\n".join(lines), reply_markup=kb)
    await callback.answer()


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.CONFIRM_PAYMENT)
)
async def confirm_payment(callback: CallbackQuery, callback_data: AdminCallback):
    """Подтверждение оплаты: выбор плана и создание подписки."""
    survey_id = callback_data.survey_id
    plan_id = callback_data.plan_id

    from sqlalchemy import select
    from src.db_components.database import get_db_session
    from src.db_components.models import SurveySubmission

    # Получаем анкету и пользователя
    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()

    if not survey:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    user_id = survey.user_id

    # Шаг 1: предложить выбрать план
    if plan_id is None:
        plans = await payment_manager.get_payment_plans()
        if not plans:
            await callback.answer(
                "Нет активных тарифных планов для оформления подписки",
                show_alert=True,
            )
            return

        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{p.name} ({p.price} ₽, {p.duration_days} дн.)",
                        callback_data=AdminCallback(
                            action=AdminAction.CONFIRM_PAYMENT,
                            survey_id=survey_id,
                            plan_id=p.id,
                        ).pack(),
                    )
                ]
                for p in plans
            ]
        )

        await callback.message.edit_text(
            text=(
                f"Выберите тарифный план для пользователя <code>{user_id}</code> "
                f"(анкета ID {survey_id}):"
            ),
            reply_markup=kb,
        )
        await callback.answer()
        return

    # Шаг 2: создаём подписку с учётом персональной скидки (если есть)
    plans = await payment_manager.get_payment_plans()
    plan = next((p for p in plans if p.id == plan_id), None)
    if not plan:
        await callback.answer("Тарифный план не найден", show_alert=True)
        return

    base_price = plan.price
    discount = survey.personal_discount or 0
    final_price = base_price * (100 - discount) / 100 if discount else base_price

    created = await payment_manager.create_subscription(
        user_id=user_id, plan_id=plan_id, custom_price=final_price
    )

    if not created:
        await callback.answer("Ошибка при создании подписки", show_alert=True)
        return

    # Обновляем статус анкеты как оплаченной
    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey_db = result.scalar_one_or_none()
        if survey_db:
            survey_db.status = SurveyStatusEnum.PAID
            await session.commit()

    # Отправляем пользователю сообщение о подтверждении
    confirm_msg = await bot_message_manager.get_message(
        BotMessageType.PAYMENT_CONFIRMED
    )
    text = (
        confirm_msg.content
        if confirm_msg
        else "Оплата подтверждена, ваша подписка активирована. Добро пожаловать в клуб!"
    )

    bot: Bot = callback.message.bot
    try:
        await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Не удалось отправить подтверждение оплаты пользователю {user_id}: {e}")

    await callback.message.edit_text(
        text=(
            f"✅ Платёж подтверждён.\n"
            f"Пользователь ID <code>{user_id}</code>, тариф: {plan.name}, цена: {final_price} ₽."
        )
    )
    await callback.answer()


# Суперадмин маршруты (редактирование сообщений и управление админами)
super_admin_router = Router(name="super_admin_router")
super_admin_router.message.filter(SuperAdminFilter())
super_admin_router.callback_query.filter(SuperAdminFilter())


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_WELCOME))
async def edit_welcome_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование приветствия."""
    current_msg = await bot_message_manager.get_message(BotMessageType.WELCOME)
    text = (
        "👋 <b>Текущее приветствие:</b>\n\n"
        f"{current_msg.content if current_msg else 'не установлено'}\n\n"
        "Отправьте новый текст приветствия:"
    )
    
    await state.set_state(ModerationFSM.editing_message)
    await state.update_data(message_type=BotMessageType.WELCOME)
    await callback.message.edit_text(text=text)
    await callback.answer()


@super_admin_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.EDIT_PAYMENT_DETAILS)
)
async def edit_payment_details_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование реквизитов оплаты."""
    current_msg = await bot_message_manager.get_message(
        BotMessageType.PAYMENT_DETAILS
    )
    text = (
        "💳 <b>Текущие реквизиты:</b>\n\n"
        f"{current_msg.content if current_msg else 'не установлены'}\n\n"
        "Отправьте новые реквизиты:"
    )
    
    await state.set_state(ModerationFSM.editing_message)
    await state.update_data(message_type=BotMessageType.PAYMENT_DETAILS)
    await callback.message.edit_text(text=text)
    await callback.answer()


@super_admin_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.EDIT_PAYMENT_CONFIRMED)
)
async def edit_payment_confirmed_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование сообщения подтверждения оплаты."""
    current_msg = await bot_message_manager.get_message(
        BotMessageType.PAYMENT_CONFIRMED
    )
    text = (
        "✅ <b>Текущее сообщение подтверждения:</b>\n\n"
        f"{current_msg.content if current_msg else 'не установлено'}\n\n"
        "Отправьте новый текст:"
    )
    
    await state.set_state(ModerationFSM.editing_message)
    await state.update_data(message_type=BotMessageType.PAYMENT_CONFIRMED)
    await callback.message.edit_text(text=text)
    await callback.answer()


@super_admin_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.EDIT_SURVEY_REJECTED)
)
async def edit_survey_rejected_start(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование сообщения об отклонении анкеты."""
    current_msg = await bot_message_manager.get_message(
        BotMessageType.SURVEY_REJECTED
    )
    text = (
        "❌ <b>Текущее сообщение об отклонении:</b>\n\n"
        f"{current_msg.content if current_msg else 'не установлено'}\n\n"
        "Отправьте новый текст:"
    )
    
    await state.set_state(ModerationFSM.editing_message)
    await state.update_data(message_type=BotMessageType.SURVEY_REJECTED)
    await callback.message.edit_text(text=text)
    await callback.answer()


@super_admin_router.message(ModerationFSM.editing_message)
async def edit_message_process(message: Message, state: FSMContext):
    """Обработать редактирование одного из управляемых сообщений бота."""
    data = await state.get_data()
    message_type = data.get("message_type")
    
    success = await bot_message_manager.update_message(message_type, message.text)
    
    if success:
        await message.answer("✅ Сообщение успешно обновлено!")
    else:
        await message.answer("❌ Ошибка при обновлении сообщения")
    
    await state.clear()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.LIST_ADMINS))
async def list_admins(callback: CallbackQuery):
    """Показать список администраторов."""
    admins = await admin_manager.get_all_admins()

    if not admins:
        await callback.message.edit_text(text="👥 Администраторы не найдены")
        await callback.answer()
        return

    lines = ["👥 <b>Администраторы системы:</b>\n"]
    for admin in admins:
        role = "🔴 <b>Супер-админ</b>" if admin.is_super_admin else "🟡 <b>Админ</b>"
        lines.append(role)
        lines.append(f"  ID: <code>{admin.id}</code>")
        if admin.first_name:
            lines.append(f"  Имя: {admin.first_name}")
        if admin.username:
            lines.append(f"  Username: @{admin.username}")
        lines.append("")

    await callback.message.edit_text(text="\n".join(lines))
    await callback.answer()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.ADD_ADMIN))
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    """Начать добавление администратора."""
    await state.set_state(ModerationFSM.adding_admin)
    await callback.message.edit_text(
        text=(
            "👤 <b>Добавление администратора</b>\n\n"
            "Отправьте Telegram ID пользователя, которого нужно сделать админом."
        )
    )
    await callback.answer()


@super_admin_router.message(ModerationFSM.adding_admin)
async def add_admin_process(message: Message, state: FSMContext):
    """Обработать добавление администратора."""
    try:
        admin_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID. Используйте только цифры.")
        return

    success = await admin_manager.add_admin(admin_id, is_super_admin=False)

    if success:
        await message.answer(f"✅ Администратор {admin_id} успешно добавлен")
    else:
        await message.answer(f"❌ Администратор с ID {admin_id} уже существует")

    await state.clear()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.REMOVE_ADMIN))
async def remove_admin_start(callback: CallbackQuery, state: FSMContext):
    """Начать удаление администратора."""
    admins = await admin_manager.get_all_admins()

    if not admins:
        await callback.message.edit_text(text="❌ Нет администраторов для удаления")
        await callback.answer()
        return

    lines = ["👤 <b>Удаление администратора</b>\n"]
    for admin in admins:
        lines.append(f"ID: <code>{admin.id}</code> - {admin.first_name or ''}")

    lines.append("\nОтправьте ID администратора, которого нужно удалить.")

    await state.set_state(ModerationFSM.removing_admin)
    await callback.message.edit_text(text="\n".join(lines))
    await callback.answer()


@super_admin_router.message(ModerationFSM.removing_admin)
async def remove_admin_process(message: Message, state: FSMContext):
    """Обработать удаление администратора."""
    try:
        admin_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID. Используйте только цифры.")
        return

    success = await admin_manager.remove_admin(admin_id)

    if success:
        await message.answer(f"✅ Администратор {admin_id} успешно удалён")
    else:
        await message.answer(f"❌ Администратор с ID {admin_id} не найден")

    await state.clear()


moderation_router.include_router(super_admin_router)
