import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy import select

from src.FormManager.FormManager import FormManager
from src.admin_components.admin_callbacks import AdminAction, AdminCallback
from src.admin_components.admin_keyboards import (
    back_to_main_inline_keyboard,
    output_settings_inline_keyboard,
)
from src.admin_components.admin_filter import AdminFilter, SuperAdminFilter
from src.db_components.database import get_db_session
from src.db_components.models import BotMessageType, SurveyStatusEnum, SurveySubmission
from src.db_components.survey_manager import (
    admin_manager,
    bot_message_manager,
    payment_manager,
    promo_code_manager,
    survey_manager,
)

logger = logging.getLogger(__name__)

moderation_router = Router(name="moderation_router")
moderation_router.message.filter(AdminFilter())
moderation_router.callback_query.filter(AdminFilter())


class ModerationFSM(StatesGroup):
    editing_message = State()
    setting_discount = State()
    adding_admin = State()
    removing_admin = State()
    creating_promo = State()
    creating_plan = State()


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.REVIEW_SURVEYS))
async def review_surveys_menu(callback: CallbackQuery):
    surveys = await survey_manager.get_surveys_by_status(SurveyStatusEnum.PENDING_REVIEW)
    if not surveys:
        await callback.message.edit_text(
            "Нет анкет для проверки", reply_markup=back_to_main_inline_keyboard
        )
        await callback.answer()
        return

    lines = ["<b>Анкеты на проверку:</b>\n"]
    kb = []
    for survey in surveys[:20]:
        lines.append(
            f"• user <code>{survey.user_id}</code>, survey <code>{survey.id}</code>"
        )
        kb.append(
            [
                InlineKeyboardButton(
                    text=f"Анкета {survey.id} (user {survey.user_id})",
                    callback_data=AdminCallback(
                        action=AdminAction.REVIEW_SURVEY_DETAIL, survey_id=survey.id
                    ).pack(),
                )
            ]
        )

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb)
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
        await callback.answer("Анкета не выбрана", show_alert=True)
        return

    surveys = await survey_manager.get_surveys_by_status(SurveyStatusEnum.PENDING_REVIEW)
    target = next((s for s in surveys if s.id == survey_id), None)
    if not target:
        await callback.answer("Анкета не найдена или уже обработана", show_alert=True)
        return

    lines = [
        f"<b>Анкета ID {target.id}</b>",
        f"Пользователь: <code>{target.user_id}</code>",
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
                        action=AdminAction.APPROVE_SURVEY_WITH_DISCOUNT,
                        survey_id=target.id,
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
        ]
    )

    await callback.message.edit_text("\n".join(lines), reply_markup=kb)
    await callback.answer()


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.APPROVE_SURVEY))
async def approve_survey(callback: CallbackQuery, callback_data: AdminCallback):
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана", show_alert=True)
        return

    ok = await survey_manager.approve_survey(
        survey_id=survey_id, admin_id=callback.from_user.id, discount=0
    )
    if not ok:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()

    if survey:
        payment_details = await bot_message_manager.get_message(BotMessageType.PAYMENT_DETAILS)
        text = (
            payment_details.content
            if payment_details
            else "Анкета одобрена. Свяжитесь с администратором для оплаты."
        )
        try:
            bot: Bot = callback.message.bot
            await bot.send_message(chat_id=survey.user_id, text=text, parse_mode="HTML")
        except Exception as exc:
            logger.error("Failed to send payment details to %s: %s", survey.user_id, exc)

    await callback.message.edit_text(
        f"Анкета {survey_id} одобрена", reply_markup=back_to_main_inline_keyboard
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
        await callback.answer("Анкета не выбрана", show_alert=True)
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
        await message.answer("Анкета не выбрана")
        await state.clear()
        return

    try:
        discount = int(message.text.strip())
    except ValueError:
        await message.answer("Введите целое число от 0 до 100")
        return
    if discount < 0 or discount > 100:
        await message.answer("Скидка должна быть от 0 до 100")
        return

    ok = await survey_manager.approve_survey(
        survey_id=survey_id, admin_id=message.from_user.id, discount=discount
    )
    if not ok:
        await message.answer("Анкета не найдена или уже обработана")
        await state.clear()
        return

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()

    if survey:
        payment_details = await bot_message_manager.get_message(BotMessageType.PAYMENT_DETAILS)
        text = (
            payment_details.content
            if payment_details
            else "Анкета одобрена. Свяжитесь с администратором для оплаты."
        )
        try:
            bot: Bot = message.bot
            await bot.send_message(chat_id=survey.user_id, text=text, parse_mode="HTML")
        except Exception as exc:
            logger.error("Failed to send payment details to %s: %s", survey.user_id, exc)

    await message.answer(
        f"Анкета {survey_id} одобрена. Персональная скидка: {discount}%",
        reply_markup=back_to_main_inline_keyboard,
    )
    await state.clear()


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.REJECT_SURVEY))
async def reject_survey(callback: CallbackQuery, callback_data: AdminCallback):
    survey_id = callback_data.survey_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана", show_alert=True)
        return

    ok = await survey_manager.reject_survey(
        survey_id=survey_id, admin_id=callback.from_user.id, comment=""
    )
    if not ok:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()

    if survey:
        reject_msg = await bot_message_manager.get_message(BotMessageType.SURVEY_REJECTED)
        text = (
            reject_msg.content
            if reject_msg
            else "К сожалению, ваша анкета отклонена."
        )
        try:
            bot: Bot = callback.message.bot
            await bot.send_message(chat_id=survey.user_id, text=text, parse_mode="HTML")
        except Exception as exc:
            logger.error("Failed to send rejection to %s: %s", survey.user_id, exc)

    await callback.message.edit_text(
        f"Анкета {survey_id} отклонена", reply_markup=back_to_main_inline_keyboard
    )
    await callback.answer()


@moderation_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.PENDING_PAYMENTS)
)
async def pending_payments(callback: CallbackQuery):
    surveys = await survey_manager.get_surveys_by_status(SurveyStatusEnum.PENDING_PAYMENT)
    if not surveys:
        await callback.message.edit_text(
            "Нет анкет, ожидающих оплату", reply_markup=back_to_main_inline_keyboard
        )
        await callback.answer()
        return

    kb_rows = []
    lines = ["<b>Ожидают подтверждения оплаты:</b>\n"]
    for survey in surveys[:20]:
        personal = survey.personal_discount or 0
        promo = survey.promo_discount or 0
        total = min(100, personal + promo)
        lines.append(
            f"• user <code>{survey.user_id}</code>, survey <code>{survey.id}</code>, "
            f"скидка {total}%"
        )
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

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows)
    )
    await callback.answer()


@moderation_router.callback_query(AdminCallback.filter(F.action == AdminAction.CONFIRM_PAYMENT))
async def confirm_payment(callback: CallbackQuery, callback_data: AdminCallback):
    survey_id = callback_data.survey_id
    plan_id = callback_data.plan_id
    if survey_id is None:
        await callback.answer("Анкета не выбрана", show_alert=True)
        return

    async with get_db_session() as session:
        result = await session.execute(
            select(SurveySubmission).where(SurveySubmission.id == survey_id)
        )
        survey = result.scalar_one_or_none()
    if not survey:
        await callback.answer("Анкета не найдена", show_alert=True)
        return

    user_id = survey.user_id
    plans = await payment_manager.get_payment_plans()
    if plan_id is None:
        if not plans:
            await callback.answer("Нет активных тарифных планов", show_alert=True)
            return
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
            f"Выберите тариф для user <code>{user_id}</code> (анкета {survey_id}):",
            reply_markup=kb,
        )
        await callback.answer()
        return

    plan = next((p for p in plans if p.id == plan_id), None)
    if not plan:
        await callback.answer("Тарифный план не найден", show_alert=True)
        return

    personal_discount = survey.personal_discount or 0
    promo_discount = survey.promo_discount or 0
    total_discount = min(100, personal_discount + promo_discount)
    final_price = plan.price * (100 - total_discount) / 100

    created = await payment_manager.create_subscription(
        user_id=user_id,
        plan_id=plan_id,
        promo_code_id=survey.promo_code_id,
        custom_price=final_price,
    )
    if not created:
        await callback.answer("Ошибка создания подписки", show_alert=True)
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
        await bot.send_message(chat_id=user_id, text=text, parse_mode="HTML")
    except Exception as exc:
        logger.error("Failed to send payment confirmation to %s: %s", user_id, exc)

    await callback.message.edit_text(
        f"Платеж подтвержден.\n"
        f"user <code>{user_id}</code>, тариф: {plan.name}, "
        f"скидка: {total_discount}%, цена: {final_price:.2f} ₽",
        reply_markup=back_to_main_inline_keyboard,
    )
    await callback.answer()


super_admin_router = Router(name="super_admin_router")
super_admin_router.message.filter(SuperAdminFilter())
super_admin_router.callback_query.filter(SuperAdminFilter())

@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.OUTPUT_SETTINGS))
async def output_settings_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "<b>Настройка вывода</b>\n\nВыберите сообщение для редактирования:",
        reply_markup=output_settings_inline_keyboard,
    )
    await callback.answer()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_WELCOME))
async def edit_welcome_start(callback: CallbackQuery, state: FSMContext):
    current_msg = await bot_message_manager.get_message(BotMessageType.WELCOME)
    text = (
        "<b>Текущее приветствие:</b>\n\n"
        f"{current_msg.content if current_msg else 'не установлено'}\n\n"
        "Отправьте новый текст приветствия:"
    )
    await state.set_state(ModerationFSM.editing_message)
    await state.update_data(message_type=BotMessageType.WELCOME)
    await callback.message.edit_text(text=text, reply_markup=back_to_main_inline_keyboard)
    await callback.answer()


@super_admin_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.EDIT_PAYMENT_DETAILS)
)
async def edit_payment_details_start(callback: CallbackQuery, state: FSMContext):
    current_msg = await bot_message_manager.get_message(BotMessageType.PAYMENT_DETAILS)
    text = (
        "<b>Текущие реквизиты:</b>\n\n"
        f"{current_msg.content if current_msg else 'не установлены'}\n\n"
        "Отправьте новые реквизиты:"
    )
    await state.set_state(ModerationFSM.editing_message)
    await state.update_data(message_type=BotMessageType.PAYMENT_DETAILS)
    await callback.message.edit_text(text=text, reply_markup=back_to_main_inline_keyboard)
    await callback.answer()


@super_admin_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.EDIT_PAYMENT_CONFIRMED)
)
async def edit_payment_confirmed_start(callback: CallbackQuery, state: FSMContext):
    current_msg = await bot_message_manager.get_message(BotMessageType.PAYMENT_CONFIRMED)
    text = (
        "<b>Текущее сообщение принятия оплаты:</b>\n\n"
        f"{current_msg.content if current_msg else 'не установлено'}\n\n"
        "Отправьте новый текст:"
    )
    await state.set_state(ModerationFSM.editing_message)
    await state.update_data(message_type=BotMessageType.PAYMENT_CONFIRMED)
    await callback.message.edit_text(text=text, reply_markup=back_to_main_inline_keyboard)
    await callback.answer()


@super_admin_router.callback_query(
    AdminCallback.filter(F.action == AdminAction.EDIT_SURVEY_REJECTED)
)
async def edit_survey_rejected_start(callback: CallbackQuery, state: FSMContext):
    current_msg = await bot_message_manager.get_message(BotMessageType.SURVEY_REJECTED)
    text = (
        "<b>Текущее сообщение отказа:</b>\n\n"
        f"{current_msg.content if current_msg else 'не установлено'}\n\n"
        "Отправьте новый текст:"
    )
    await state.set_state(ModerationFSM.editing_message)
    await state.update_data(message_type=BotMessageType.SURVEY_REJECTED)
    await callback.message.edit_text(text=text, reply_markup=back_to_main_inline_keyboard)
    await callback.answer()


async def _start_generic_message_edit(
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


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_SURVEY_SUBMITTED))
async def edit_survey_submitted_start(callback: CallbackQuery, state: FSMContext):
    await _start_generic_message_edit(
        callback,
        state,
        BotMessageType.SURVEY_SUBMITTED,
        "Текущее сообщение после отправки анкеты",
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_STATUS_EMPTY))
async def edit_status_empty_start(callback: CallbackQuery, state: FSMContext):
    await _start_generic_message_edit(
        callback,
        state,
        BotMessageType.STATUS_EMPTY,
        "Текущее сообщение для пользователя без анкеты",
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_PROMO_APPLIED))
async def edit_promo_applied_start(callback: CallbackQuery, state: FSMContext):
    await _start_generic_message_edit(
        callback,
        state,
        BotMessageType.PROMO_APPLIED,
        "Текущее сообщение успешного промокода",
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_PROMO_INVALID))
async def edit_promo_invalid_start(callback: CallbackQuery, state: FSMContext):
    await _start_generic_message_edit(
        callback,
        state,
        BotMessageType.PROMO_INVALID,
        "Текущее сообщение ошибки промокода",
    )


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.EDIT_TARIFFS_HEADER))
async def edit_tariffs_header_start(callback: CallbackQuery, state: FSMContext):
    await _start_generic_message_edit(
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
            "Сообщение успешно обновлено", reply_markup=back_to_main_inline_keyboard
        )
    else:
        await message.answer(
            "Ошибка при обновлении сообщения", reply_markup=back_to_main_inline_keyboard
        )
    await state.clear()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.LIST_PLANS))
async def list_plans(callback: CallbackQuery):
    plans = await payment_manager.get_payment_plans()
    if not plans:
        await callback.message.edit_text(
            "Активные тарифы не найдены", reply_markup=back_to_main_inline_keyboard
        )
        await callback.answer()
        return

    lines = ["<b>Список активных тарифов:</b>\n"]
    for plan in plans:
        details = f"{plan.name}: {plan.price:.2f} ₽ / {plan.duration_days} дн."
        if plan.description:
            details += f"\n{plan.description}"
        lines.append(details)
    await callback.message.edit_text(
        "\n\n".join(lines), reply_markup=back_to_main_inline_keyboard
    )
    await callback.answer()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.LIST_ADMINS))
async def list_admins(callback: CallbackQuery):
    admins = await admin_manager.get_all_admins()
    if not admins:
        await callback.message.edit_text(
            "Администраторы не найдены", reply_markup=back_to_main_inline_keyboard
        )
        await callback.answer()
        return

    lines = ["<b>Администраторы системы:</b>\n"]
    for admin in admins:
        role = "Супер-админ" if admin.is_super_admin else "Админ"
        lines.append(f"{role}: <code>{admin.id}</code>")
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=back_to_main_inline_keyboard
    )
    await callback.answer()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.ADD_ADMIN))
async def add_admin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ModerationFSM.adding_admin)
    await callback.message.edit_text("Отправьте Telegram ID нового администратора:")
    await callback.answer()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.CREATE_PROMO))
async def create_promo_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ModerationFSM.creating_promo)
    await callback.message.edit_text(
        "Введите промокод и скидку через пробел, например:\n<code>SPRING25 25</code>"
    )
    await callback.answer()


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
        await message.answer("Скидка должна быть числом")
        return
    if discount < 1 or discount > 99:
        await message.answer("Скидка должна быть от 1 до 99")
        return

    success = await promo_code_manager.create_promo_code(
        code=code, discount_percent=discount, is_collective=True
    )
    await message.answer(
        (
            f"Промокод {code.upper()} создан со скидкой {discount}%"
            if success
            else "Не удалось создать промокод"
        ),
        reply_markup=back_to_main_inline_keyboard,
    )
    await state.clear()


@super_admin_router.message(ModerationFSM.creating_plan)
async def create_plan_process(message: Message, state: FSMContext):
    parts = [part.strip() for part in message.text.split(";", 3)]
    if len(parts) < 3:
        await message.answer("Неверный формат. Используйте: Название;дней;цена;описание")
        return

    name = parts[0]
    try:
        duration_days = int(parts[1])
        price = float(parts[2].replace(",", "."))
    except ValueError:
        await message.answer("Дни должны быть числом, цена - числом (например 990 или 990.50)")
        return

    description = parts[3] if len(parts) == 4 else ""
    if duration_days <= 0:
        await message.answer("Количество дней должно быть больше 0")
        return
    if price < 0:
        await message.answer("Цена не может быть отрицательной")
        return

    success = await payment_manager.create_payment_plan(
        name=name,
        duration_days=duration_days,
        price=price,
        description=description,
    )
    await message.answer(
        (
            f"Тариф создан: {name} ({duration_days} дн., {price:.2f} ₽)"
            if success
            else "Не удалось создать тариф"
        ),
        reply_markup=back_to_main_inline_keyboard,
    )
    await state.clear()


@super_admin_router.message(ModerationFSM.adding_admin)
async def add_admin_process(message: Message, state: FSMContext):
    try:
        admin_id = int(message.text.strip())
    except ValueError:
        await message.answer("Некорректный ID")
        return

    success = await admin_manager.add_admin(admin_id, is_super_admin=False)
    await message.answer(
        f"Админ {admin_id} добавлен" if success else f"Админ {admin_id} уже существует",
        reply_markup=back_to_main_inline_keyboard,
    )
    await state.clear()


@super_admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.REMOVE_ADMIN))
async def remove_admin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ModerationFSM.removing_admin)
    await callback.message.edit_text("Отправьте Telegram ID администратора для удаления:")
    await callback.answer()


@super_admin_router.message(ModerationFSM.removing_admin)
async def remove_admin_process(message: Message, state: FSMContext):
    try:
        admin_id = int(message.text.strip())
    except ValueError:
        await message.answer("Некорректный ID")
        return

    success = await admin_manager.remove_admin(admin_id)
    await message.answer(
        f"Админ {admin_id} удален" if success else f"Админ {admin_id} не найден",
        reply_markup=back_to_main_inline_keyboard,
    )
    await state.clear()


moderation_router.include_router(super_admin_router)
