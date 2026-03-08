import logging
import os

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, ChatJoinRequest, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.FormManager.FormManager import FormManager
from src.db_components.models import BotMessageType, SurveyStatusEnum
from src.db_components.survey_manager import (
    admin_manager,
    bot_message_manager,
    bot_settings_manager,
    payment_manager,
    survey_manager,
)
from src.db_components.user_manager import UserManager
from src.user_components.user_callbacks import UserAction, UserCallback
from src.user_components.user_keyboard import (
    admin_survey_check_status as admin_status_kb,
    user_filling_survey_inline_keyboard as yes_no_kb,
    user_survey_check_status as status_kb,
)
from src.user_components.user_states import UserFSM

logger = logging.getLogger(__name__)
user_router = Router(name="user_router")


async def _get_message_text(message_type: BotMessageType, fallback: str) -> str:
    message = await bot_message_manager.get_message(message_type)
    return message.content if message else fallback


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

    out: set[int] = set()
    single_chat_id = _parse_env_int(os.getenv("GROUP_CHAT_ID"))
    if single_chat_id is not None:
        out.add(single_chat_id)
    out.update(_parse_env_int_set(os.getenv("GROUP_CHAT_IDS")))
    return out


async def _is_admin_or_super_admin(user_id: int) -> bool:
    admin_id = _parse_env_int(os.getenv("ADMIN_ID"))
    super_admin_id = _parse_env_int(os.getenv("SUPER_ADMIN_ID"))
    super_admin_ids = _parse_env_int_set(os.getenv("SUPER_ADMIN_IDS"))
    if (admin_id is not None and user_id == admin_id) or (
        (super_admin_id is not None and user_id == super_admin_id)
        or (user_id in super_admin_ids)
    ):
        return True
    return await admin_manager.is_admin(user_id)


async def _status_keyboard_for_user(user_id: int):
    return admin_status_kb if await _is_admin_or_super_admin(user_id) else status_kb


@user_router.message(F.text == "!id")
async def show_chat_id(message: Message):
    # Useful for setup: add bot to a group/supergroup, send "!id" to get chat_id.
    if message.chat.type not in ("group", "supergroup"):
        await message.answer("Эта команда работает только в группе/супергруппе.")
        return

    await message.answer(f"ID этого чата: {message.chat.id}")


@user_router.chat_join_request()
async def auto_approve_join_request(join_request: ChatJoinRequest):
    target_chat_ids = await _get_target_chat_ids()
    if target_chat_ids and join_request.chat.id not in target_chat_ids:
        return

    user_id = join_request.from_user.id
    subscription = await payment_manager.get_user_subscription(user_id)
    if not subscription:
        await join_request.bot.decline_chat_join_request(
            chat_id=join_request.chat.id,
            user_id=user_id,
        )
        try:
            await join_request.bot.send_message(
                chat_id=user_id,
                text="Вход отклонен: активная подписка не найдена.",
            )
        except Exception:
            pass
        return

    await join_request.bot.approve_chat_join_request(
        chat_id=join_request.chat.id,
        user_id=user_id,
    )


async def _start_survey_flow(
    user_id: int,
    username: str | None,
    first_name: str | None,
    last_name: str | None,
    state: FSMContext,
    form: FormManager,
    users: UserManager,
) -> tuple[bool, str, str, str | None]:
    questions_count = await form.get_questions_count()
    if questions_count < 1:
        return (
            False,
            "Анкета пока не настроена. Попробуйте позже или напишите администратору.",
            "",
            None,
        )

    await users.add_user(
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
    )
    await users.clear_answers(user_id)

    current_index = 1
    question = await form.get_question_by_id(current_index)
    if not question:
        return (
            False,
            "Не удалось загрузить первый вопрос анкеты. Попробуйте еще раз позже.",
            "",
            None,
        )

    await state.set_state(UserFSM.filling_survey)
    await state.update_data(total_questions=questions_count, question_id=current_index)
    text = f"<b>Вопрос {current_index}/{questions_count}</b>\n\n{question['text']}"
    kb = yes_no_kb if question["type"] == "yes_no" else None
    return True, "", text, kb


@user_router.message(CommandStart())
async def start(message: Message, users: UserManager):
    user_id = message.from_user.id
    await users.add_user(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    welcome_text = await _get_message_text(
        BotMessageType.WELCOME,
        "Здравствуйте! Используйте кнопки ниже для анкеты, статуса и тарифов.",
    )
    user_status_kb = await _status_keyboard_for_user(user_id)
    await message.answer(welcome_text, reply_markup=user_status_kb)


@user_router.message(Command("id"))
async def show_my_id(message: Message):
    await message.answer(f"Ваш ID: <code>{message.from_user.id}</code>")


async def handler_answers_survey(
    event: Message | CallbackQuery,
    state: FSMContext,
    users: UserManager,
    form: FormManager,
    event_data: UserCallback | None = None,
):
    data = await state.get_data()
    answer = event.text if isinstance(event, Message) else event_data.value
    user_id = event.from_user.id
    question_id = data["question_id"]
    total = data["total_questions"]

    success = await users.add_answer(user_id, question_id, answer)
    if not success:
        logger.error("Не удалось сохранить ответ пользователя %s", user_id)
        return

    # For inline yes/no questions we should not "replace" the question message with the next
    # question via edit_text, otherwise the previous question disappears from chat history.
    # Instead, freeze the current question (remove keyboard) and send next question as a new message.
    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest:
            pass

    if question_id >= total:
        answers = await users.get_answers(user_id)
        if answers:
            await survey_manager.submit_survey(user_id=user_id, answers=answers)

        text_done = await _get_message_text(
            BotMessageType.SURVEY_SUBMITTED,
            "Анкета отправлена на рассмотрение.\n\nПроверяйте результат через кнопку «Статус профиля».",
        )
        user_status_kb = await _status_keyboard_for_user(user_id)
        if isinstance(event, Message):
            await event.answer(text_done, reply_markup=user_status_kb)
        else:
            await event.message.answer(text_done, reply_markup=user_status_kb)
        await state.clear()
        return

    next_id = question_id + 1
    next_question = await form.get_question_by_id(next_id)
    if not next_question:
        logger.error("Вопрос %s не найден", next_id)
        return

    await state.update_data(question_id=next_id)
    text = f"<b>Вопрос {next_id}/{total}</b>\n\n{next_question['text']}"
    kb = yes_no_kb if next_question["type"] == "yes_no" else None
    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        await event.message.answer(text, reply_markup=kb)


@user_router.callback_query(UserCallback.filter(F.action == UserAction.FILL_SURVEY))
async def start_filling_survey(
    callback: CallbackQuery,
    state: FSMContext,
    form: FormManager,
    users: UserManager,
):
    ok, err, text, kb = await _start_survey_flow(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
        state=state,
        form=form,
        users=users,
    )
    if not ok:
        await callback.answer(err, show_alert=True)
        return
    await callback.message.edit_text(text=text, reply_markup=kb)
    await callback.answer()


@user_router.callback_query(
    UserCallback.filter(F.action == UserAction.RENEW_SUBSCRIPTION_SELECT_PLAN)
)
async def select_renewal_plan(callback: CallbackQuery, callback_data: UserCallback):
    user_id = callback.from_user.id
    plan_id = callback_data.plan_id
    logger.info("Renewal plan click: user_id=%s, plan_id=%s", user_id, plan_id)

    try:
        if plan_id is None:
            await callback.answer("Тариф не выбран.", show_alert=True)
            await callback.message.answer("Не удалось определить выбранный тариф.")
            return

        subscription = await payment_manager.get_latest_subscription_for_renewal(user_id)
        if not subscription:
            await callback.answer(
                "Подписка для продления не найдена. Обратитесь к администратору.",
                show_alert=True,
            )
            await callback.message.answer(
                "Продление недоступно: подписка для продления не найдена."
            )
            return

        plans = await payment_manager.get_payment_plans()
        plan = next((p for p in plans if p.id == plan_id), None)
        if not plan:
            await callback.answer("Тариф больше недоступен.", show_alert=True)
            await callback.message.answer("Этот тариф больше недоступен. Выберите другой.")
            return

        request = await survey_manager.create_or_update_renewal_payment_request(
            user_id=user_id,
            plan_id=plan_id,
        )
        if not request:
            await callback.answer("Не удалось создать заявку на продление.", show_alert=True)
            await callback.message.answer(
                "Не удалось создать заявку на продление. Если у вас уже есть ожидающая заявка на оплату, дождитесь решения администратора."
            )
            return

        confirmation_text = (
            "Заявка на продление создана.\n\n"
            f"Выбран тариф: <b>{plan.name}</b> ({plan.duration_days} дн., {plan.price:.2f} ₽).\n"
            "После оплаты администратор подтвердит продление подписки."
        )
        try:
            await callback.message.edit_text(confirmation_text)
        except TelegramBadRequest:
            await callback.message.answer(confirmation_text)
        await callback.answer("Тариф выбран")
    except Exception as exc:
        logger.exception(
            "Renewal plan processing failed for user_id=%s plan_id=%s: %s",
            user_id,
            plan_id,
            exc,
        )
        await callback.answer("Ошибка обработки. Попробуйте еще раз.", show_alert=True)
        await callback.message.answer(
            "Произошла ошибка при обработке продления. Администратор уже может увидеть детали в логах."
        )


@user_router.callback_query(
    UserCallback.filter(F.action == UserAction.APPROVED_SURVEY_SELECT_PLAN)
)
async def select_approved_survey_plan(
    callback: CallbackQuery,
    callback_data: UserCallback,
    state: FSMContext,
):
    user_id = callback.from_user.id
    plan_id = callback_data.plan_id
    if plan_id is None:
        await callback.answer("Тариф не выбран.", show_alert=True)
        return

    plans = await payment_manager.get_payment_plans()
    plan = next((p for p in plans if p.id == plan_id), None)
    if not plan:
        await callback.answer("Тариф больше недоступен.", show_alert=True)
        return

    survey = await survey_manager.set_selected_plan_for_pending_payment(
        user_id=user_id,
        plan_id=plan_id,
    )
    if not survey:
        await callback.answer(
            "Нет одобренной анкеты, ожидающей оплату.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "Тариф выбран.\n\n"
        f"Выбрано: <b>{plan.name}</b> ({plan.duration_days} дн., {plan.price:.2f} ₽).\n\n"
        "Если у вас есть промокод, отправьте его одним сообщением.\n"
        "Если промокода нет, нажмите «Далее без промокода».",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Далее без промокода",
                        callback_data=UserCallback(
                            action=UserAction.APPROVED_SURVEY_SKIP_PROMO
                        ).pack(),
                    )
                ]
            ]
        ),
    )
    await state.set_state(UserFSM.waiting_payment_promo_code)
    await callback.answer("Тариф выбран")


async def _payment_summary_for_user(user_id: int) -> tuple[str, InlineKeyboardMarkup] | None:
    survey = await survey_manager.get_latest_pending_payment_survey(user_id)
    if not survey or survey.selected_plan_id is None:
        return None

    plans = await payment_manager.get_payment_plans()
    plan = next((p for p in plans if p.id == survey.selected_plan_id), None)
    if not plan:
        return None

    personal = int(survey.personal_discount or 0)
    promo = int(survey.promo_discount or 0)
    total_discount = min(100, personal + promo)
    final_price = plan.price * (100 - total_discount) / 100

    lines = [
        "<b>Проверка оплаты</b>",
        "",
        f"Тариф: <b>{plan.name}</b>",
        f"Цена: <b>{plan.price:.2f} ₽</b>",
        f"Скидка персональная: <b>{personal}%</b>",
        f"Скидка по промокоду: <b>{promo}%</b>",
        f"Итого скидка: <b>{total_discount}%</b>",
        f"К оплате: <b>{final_price:.2f} ₽</b>",
        "",
        "Нажмите «Оплатить», чтобы получить реквизиты.",
    ]

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Оплатить",
                    callback_data=UserCallback(action=UserAction.APPROVED_SURVEY_PAY).pack(),
                )
            ]
        ]
    )
    return "\n".join(lines), kb


@user_router.callback_query(
    UserCallback.filter(F.action == UserAction.APPROVED_SURVEY_SKIP_PROMO)
)
async def approved_survey_skip_promo(callback: CallbackQuery, state: FSMContext):
    summary = await _payment_summary_for_user(callback.from_user.id)
    if not summary:
        await callback.answer(
            "Не удалось подготовить оплату. Выберите тариф заново.",
            show_alert=True,
        )
        await callback.message.answer(
            "Не удалось подготовить оплату. Попробуйте выбрать тариф снова."
        )
        await state.clear()
        return
    text, kb = summary
    await callback.message.answer(text, reply_markup=kb)
    await state.clear()
    await callback.answer()


@user_router.callback_query(UserCallback.filter(F.action == UserAction.APPROVED_SURVEY_PAY))
async def approved_survey_pay(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    survey = await survey_manager.get_latest_pending_payment_survey(user_id)
    if not survey or survey.selected_plan_id is None:
        await callback.answer("Нет заявки на оплату.", show_alert=True)
        return
    await survey_manager.mark_user_payment_started(user_id)

    plans = await payment_manager.get_payment_plans()
    plan = next((p for p in plans if p.id == survey.selected_plan_id), None)
    if not plan:
        await callback.answer("Тариф больше недоступен.", show_alert=True)
        return

    personal = int(survey.personal_discount or 0)
    promo = int(survey.promo_discount or 0)
    total_discount = min(100, personal + promo)
    final_price = plan.price * (100 - total_discount) / 100

    payment_details = await bot_message_manager.get_message(BotMessageType.PAYMENT_DETAILS)
    details_text = (
        payment_details.content
        if payment_details
        else "Реквизиты для оплаты не настроены. Напишите администратору."
    )
    await callback.message.answer(
        f"<b>К оплате: {final_price:.2f} ₽</b>\n\n{details_text}\n\n"
        "После оплаты администратор подтвердит платеж, и вы получите доступ."
    )
    await state.clear()
    await callback.answer()


@user_router.message(F.text == "Анкета")
async def restart_survey_from_menu(
    message: Message,
    state: FSMContext,
    form: FormManager,
    users: UserManager,
):
    latest = await survey_manager.get_latest_survey(message.from_user.id)
    if latest and latest.status != SurveyStatusEnum.REJECTED:
        user_status_kb = await _status_keyboard_for_user(message.from_user.id)
        await message.answer(
            "Новая анкета доступна после отклонения текущей.\n\nКогда статус изменится на «Отклонена», вы сможете заполнить ее снова.",
            reply_markup=user_status_kb,
        )
        return

    ok, err, text, kb = await _start_survey_flow(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        state=state,
        form=form,
        users=users,
    )
    if not ok:
        user_status_kb = await _status_keyboard_for_user(message.from_user.id)
        await message.answer(err, reply_markup=user_status_kb)
        return
    await message.answer(text, reply_markup=kb)


@user_router.message((F.text == "Статус") | (F.text == "Статус профиля"))
async def survey_and_subscription_status(message: Message):
    user_id = message.from_user.id
    survey = await survey_manager.get_latest_survey(user_id)
    subscription = await payment_manager.get_latest_subscription_for_renewal(user_id)
    parts: list[str] = []

    if not survey:
        parts.append(
            await _get_message_text(
                BotMessageType.STATUS_EMPTY, "Вы еще не заполняли анкету."
            )
        )
    else:
        status_map = {
            SurveyStatusEnum.PENDING_REVIEW: "На проверке",
            SurveyStatusEnum.PENDING_PAYMENT: "Одобрена, ожидается оплата",
            SurveyStatusEnum.REJECTED: "Отклонена",
            SurveyStatusEnum.PAID: "Оплачена",
            SurveyStatusEnum.APPROVED: "Одобрена",
        }
        parts.append(f"Статус анкеты: <b>{status_map.get(survey.status, str(survey.status))}</b>")
        if survey.personal_discount:
            parts.append(f"Персональная скидка: <b>{survey.personal_discount}%</b>")
        if survey.promo_discount:
            parts.append(f"Скидка по промокоду: <b>{survey.promo_discount}%</b>")

    if subscription:
        plans = await payment_manager.get_payment_plans()
        plan_name = next((p.name for p in plans if p.id == subscription.plan_id), "Тариф")
        parts.append(
            f"Подписка: <b>{plan_name}</b> до <b>{subscription.end_date.strftime('%d.%m.%Y')}</b>"
        )
    else:
        parts.append("Активной подписки пока нет.")

    await message.answer("<b>Статус профиля</b>\n\n" + "\n\n".join(parts))


@user_router.message(F.text == "Тарифы")
async def show_tariffs(message: Message):
    plans = await payment_manager.get_payment_plans()
    if not plans:
        user_status_kb = await _status_keyboard_for_user(message.from_user.id)
        await message.answer(
            "Сейчас активных тарифов нет. Попробуйте позже.",
            reply_markup=user_status_kb,
        )
        return

    header = await _get_message_text(BotMessageType.TARIFFS_HEADER, "<b>Доступные тарифы</b>")
    lines = [header]
    for plan in plans:
        line = f"• <b>{plan.name}</b> — {plan.price:.2f} ₽ / {plan.duration_days} дн."
        if plan.description:
            line += f"\n{plan.description}"
        lines.append(line)
    user_status_kb = await _status_keyboard_for_user(message.from_user.id)
    await message.answer("\n\n".join(lines), reply_markup=user_status_kb)


@user_router.message(F.text == "Промокод")
async def promo_code_start(message: Message, state: FSMContext):
    await state.set_state(UserFSM.waiting_promo_code)
    await message.answer("Введите промокод одним сообщением:")


@user_router.message(UserFSM.waiting_promo_code)
async def promo_code_process(message: Message, state: FSMContext):
    code = message.text.strip()
    ok, text, _discount = await survey_manager.apply_promo_code_to_latest_survey(
        message.from_user.id, code
    )
    if ok:
        applied_template = await _get_message_text(
            BotMessageType.PROMO_APPLIED, "Промокод применен: {text}"
        )
        reply = applied_template.replace("{text}", text)
    else:
        invalid_template = await _get_message_text(
            BotMessageType.PROMO_INVALID, "Промокод не применен: {text}"
        )
        reply = invalid_template.replace("{text}", text)

    user_status_kb = await _status_keyboard_for_user(message.from_user.id)
    await message.answer(reply, reply_markup=user_status_kb)
    await state.clear()


@user_router.message(UserFSM.waiting_payment_promo_code)
async def payment_promo_code_process(message: Message, state: FSMContext):
    user_id = message.from_user.id
    code = (message.text or "").strip()
    if not code:
        await message.answer(
            "Введите промокод одним сообщением или нажмите «Далее без промокода».",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Далее без промокода",
                            callback_data=UserCallback(
                                action=UserAction.APPROVED_SURVEY_SKIP_PROMO
                            ).pack(),
                        )
                    ]
                ]
            ),
        )
        return

    ok, text, _discount = await survey_manager.apply_promo_code_to_pending_payment_survey(
        user_id, code
    )
    if not ok:
        invalid_template = await _get_message_text(
            BotMessageType.PROMO_INVALID, "Промокод не применен: {text}"
        )
        reply = invalid_template.replace("{text}", text)
        await message.answer(
            reply + "\n\nОтправьте другой промокод или нажмите «Далее без промокода».",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="Далее без промокода",
                            callback_data=UserCallback(
                                action=UserAction.APPROVED_SURVEY_SKIP_PROMO
                            ).pack(),
                        )
                    ]
                ]
            ),
        )
        return

    applied_template = await _get_message_text(
        BotMessageType.PROMO_APPLIED, "Промокод применен: {text}"
    )
    await message.answer(applied_template.replace("{text}", text))

    summary = await _payment_summary_for_user(user_id)
    if not summary:
        await message.answer("Не удалось посчитать сумму. Напишите администратору.")
        await state.clear()
        return
    summary_text, kb = summary
    await message.answer(summary_text, reply_markup=kb)
    await state.clear()


@user_router.message(UserFSM.filling_survey)
async def survey_text(
    message: Message,
    state: FSMContext,
    users: UserManager,
    form: FormManager,
):
    await handler_answers_survey(
        event=message,
        state=state,
        users=users,
        form=form,
    )


@user_router.callback_query(
    UserFSM.filling_survey,
    UserCallback.filter(F.action == UserAction.YES_NO_ANSWER),
)
async def survey_yes_no(
    callback: CallbackQuery,
    callback_data: UserCallback,
    state: FSMContext,
    users: UserManager,
    form: FormManager,
):
    await handler_answers_survey(
        event=callback,
        event_data=callback_data,
        state=state,
        users=users,
        form=form,
    )
    await callback.answer()

