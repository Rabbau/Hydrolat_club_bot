import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.FormManager.FormManager import FormManager
from src.db_components.models import BotMessageType, SurveyStatusEnum
from src.db_components.survey_manager import (
    bot_message_manager,
    payment_manager,
    survey_manager,
)
from src.db_components.user_manager import UserManager
from src.user_components.user_callbacks import UserAction, UserCallback
from src.user_components.user_keyboard import (
    user_filling_survey_inline_keyboard as yes_no_kb,
    user_main_menu_inline_keyboard as user_main_kb,
    user_survey_check_status as status_kb,
)
from src.user_components.user_states import UserFSM

logger = logging.getLogger(__name__)
user_router = Router(name="user_router")


async def _get_message_text(message_type: BotMessageType, fallback: str) -> str:
    message = await bot_message_manager.get_message(message_type)
    return message.content if message else fallback


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
        return False, "Анкета пока не настроена", "", None

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
        return False, "Ошибка загрузки анкеты", "", None

    await state.set_state(UserFSM.filling_survey)
    await state.update_data(total_questions=questions_count, question_id=current_index)
    text = f"Вопрос {current_index}/{questions_count}:\n{question['text']}"
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
        "Здравствуйте! Нажмите кнопку ниже, чтобы заполнить анкету.",
    )
    survey = await survey_manager.get_latest_survey(user_id)
    if survey:
        await message.answer(welcome_text, reply_markup=status_kb)
    else:
        await message.answer(welcome_text, reply_markup=user_main_kb)


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

    if question_id >= total:
        answers = await users.get_answers(user_id)
        if answers:
            await survey_manager.submit_survey(user_id=user_id, answers=answers)

        text_done = await _get_message_text(
            BotMessageType.SURVEY_SUBMITTED,
            "Анкета отправлена на рассмотрение.\n\nСледите за статусом через кнопку «Статус профиля».",
        )
        if isinstance(event, Message):
            await event.answer(text_done, reply_markup=status_kb)
        else:
            await event.message.edit_text(text_done)
        await state.clear()
        return

    next_id = question_id + 1
    next_question = await form.get_question_by_id(next_id)
    if not next_question:
        logger.error("Вопрос %s не найден", next_id)
        return

    await state.update_data(question_id=next_id)
    text = f"Вопрос {next_id}/{total}:\n{next_question['text']}"
    kb = yes_no_kb if next_question["type"] == "yes_no" else None
    if isinstance(event, Message):
        await event.answer(text, reply_markup=kb)
    else:
        await event.message.edit_text(text, reply_markup=kb)


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


@user_router.message(F.text == "Анкета")
async def restart_survey_from_menu(
    message: Message,
    state: FSMContext,
    form: FormManager,
    users: UserManager,
):
    latest = await survey_manager.get_latest_survey(message.from_user.id)
    if latest and latest.status != SurveyStatusEnum.REJECTED:
        await message.answer(
            "Повторная анкета доступна после отклонения текущей анкеты.",
            reply_markup=status_kb,
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
        await message.answer(err, reply_markup=status_kb)
        return
    await message.answer(text, reply_markup=kb)


@user_router.message((F.text == "Статус") | (F.text == "Статус профиля"))
async def survey_and_subscription_status(message: Message):
    user_id = message.from_user.id
    survey = await survey_manager.get_latest_survey(user_id)
    subscription = await payment_manager.get_user_subscription(user_id)
    parts: list[str] = []

    if not survey:
        parts.append(
            await _get_message_text(
                BotMessageType.STATUS_EMPTY, "Анкета еще не заполнена."
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
        parts.append(f"Статус анкеты: {status_map.get(survey.status, str(survey.status))}")
        if survey.personal_discount:
            parts.append(f"Персональная скидка: {survey.personal_discount}%")
        if survey.promo_discount:
            parts.append(f"Промокод: {survey.promo_discount}%")

    if subscription:
        plans = await payment_manager.get_payment_plans()
        plan_name = next((p.name for p in plans if p.id == subscription.plan_id), "Тариф")
        parts.append(f"Подписка: {plan_name} до {subscription.end_date.strftime('%d.%m.%Y')}")
    else:
        parts.append("Активной подписки нет.")

    await message.answer("<b>Статус профиля</b>\n\n" + "\n\n".join(parts))


@user_router.message(F.text == "Тарифы")
async def show_tariffs(message: Message):
    plans = await payment_manager.get_payment_plans()
    if not plans:
        await message.answer("Активные тарифы пока не добавлены.", reply_markup=status_kb)
        return

    header = await _get_message_text(BotMessageType.TARIFFS_HEADER, "<b>Доступные тарифы</b>")
    lines = [header]
    for plan in plans:
        line = f"• <b>{plan.name}</b> — {plan.price:.2f} ₽ / {plan.duration_days} дн."
        if plan.description:
            line += f"\n{plan.description}"
        lines.append(line)
    await message.answer("\n\n".join(lines), reply_markup=status_kb)


@user_router.message(F.text == "Промокод")
async def promo_code_start(message: Message, state: FSMContext):
    await state.set_state(UserFSM.waiting_promo_code)
    await message.answer("Введите промокод:")


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

    await message.answer(reply, reply_markup=status_kb)
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
