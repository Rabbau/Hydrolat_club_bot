from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from src.FormManager.FormManager import FormManager
from src.user_components.user_callbacks import UserCallback, UserAction
from src.user_components.user_keyboard import (
    user_main_menu_inline_keyboard as user_main_kb,
    user_filling_survey_inline_keyboard as yes_no_kb,
    user_survey_check_status as status_kb,
)
from src.user_components.user_states import UserFSM
from src.db_components.user_manager import UserManager
from src.db_components.survey_manager import (
    survey_manager,
    payment_manager,
    bot_message_manager,
)
from src.db_components.models import SurveyStatusEnum, BotMessageType

import logging

logger = logging.getLogger(__name__)

user_router = Router(name="user_router")


@user_router.message(CommandStart())
async def start(message: Message, users: UserManager):
    """
    Приветственное сообщение + предложение заполнить анкету
    или посмотреть статус, если анкета уже есть.
    """
    user_id = message.from_user.id

    # Пробуем взять кастомное приветствие из БД
    welcome_msg = await bot_message_manager.get_message(BotMessageType.WELCOME)
    welcome_text = (
        welcome_msg.content
        if welcome_msg
        else "Здравствуйте! Добро пожаловать в клуб.\n\nНажмите кнопку ниже, чтобы заполнить анкету."
    )

    # Проверяем, есть ли уже анкета
    survey = await survey_manager.get_latest_survey(user_id)

    if survey:
        # Пользователь уже когда‑то отправлял анкету — даём сразу кнопку статуса
        await message.answer(welcome_text, reply_markup=status_kb)
    else:
        # Первая анкета
        await message.answer(welcome_text, reply_markup=user_main_kb)

async def handler_answers_survey(
    event: Message | CallbackQuery,
    state: FSMContext,
    users: UserManager,
    form: FormManager,
    event_data: UserCallback | None = None,
):
    """Обработчик ответов на вопросы анкеты"""
    data = await state.get_data()
    answer = event.text if isinstance(event, Message) else event_data.value
    user_id = event.from_user.id
    question_id = data["question_id"]
    total = data["total_questions"]
    
    # Добавляем ответ
    success = await users.add_answer(user_id, question_id, answer)
    if not success:
        logger.error(f"Не удалось добавить ответ пользователя {user_id}")
        return
    
    # Проверяем, все ли вопросы ответены
    if question_id >= total:
        # Собираем все ответы пользователя и создаём запись анкеты
        answers = await users.get_answers(user_id)
        if not answers:
            logger.error(f"Не удалось получить ответы пользователя {user_id} для анкеты")
        else:
            try:
                await survey_manager.submit_survey(user_id=user_id, answers=answers)
            except Exception as e:
                logger.error(f"Ошибка при сохранении анкеты пользователя {user_id}: {e}")

        text_done = (
            "✅ Анкета отправлена на рассмотрение!\n\n"
            "Администратор проверит ваши ответы и примет решение.\n"
            "Вы можете следить за статусом через кнопку «Статус»."
        )

        if isinstance(event, Message):
            await event.answer(text_done, reply_markup=status_kb)
        else:
            await event.message.edit_text(text_done)

        await state.clear()
        return
    
    # Переходим к следующему вопросу
    next_id = question_id + 1
    next_question = form.get_question_by_id(next_id)
    if not next_question:
        logger.error(f"Вопрос #{next_id} не найден в анкете")
        return
    
    await state.update_data(question_id=next_id)
    text = (
        f"Вопрос {next_id}/{total}:\n"
        f"{next_question['text']}"
    )
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
    users: UserManager):
    """Начало заполнения анкеты"""
    if len(form) < 1:
        await callback.answer("❌ Анкеты пока нет", show_alert=True)
        return

    user_id = callback.from_user.id

    # Добавляем пользователя в БД если его еще нет
    await users.add_user(
        user_id=user_id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )

    # Очищаем старые ответы пользователя перед новым заполнением
    await users.clear_answers(user_id)
    
    current_index = 1
    total_questions = len(form)
    question = form.get_question_by_id(current_index)
    
    if not question:
        logger.error(f"Вопрос #{current_index} не найден")
        await callback.answer("❌ Ошибка при загрузке анкеты", show_alert=True)
        return
    
    await state.set_state(UserFSM.filling_survey)
    await state.update_data(
        total_questions=total_questions,
        question_id=current_index,
    )
    
    await callback.message.edit_text(
        text=f'Вопрос {current_index}/{total_questions}:\n{question["text"]}',
        reply_markup=yes_no_kb if question['type'] == 'yes_no' else None
    )
    await callback.answer()


@user_router.message(F.text == "Статус")
async def survey_and_subscription_status(message: Message):
    """Показать статус анкеты и подписки пользователю."""
    user_id = message.from_user.id

    survey = await survey_manager.get_latest_survey(user_id)
    subscription = await payment_manager.get_user_subscription(user_id)

    parts: list[str] = []

    # Статус анкеты
    if not survey:
        parts.append("📝 Анкета ещё не заполнена.\nНажмите кнопку «Заполнить анкету», чтобы начать.")
    else:
        status_map = {
            SurveyStatusEnum.PENDING_REVIEW: "⏳ На проверке у администратора",
            SurveyStatusEnum.PENDING_PAYMENT: "💳 Одобрена, ожидается оплата",
            SurveyStatusEnum.REJECTED: "❌ Отклонена",
            SurveyStatusEnum.PAID: "✅ Оплачена, доступ открыт",
            SurveyStatusEnum.APPROVED: "✅ Одобрена (ожидает дальнейших шагов)",
        }
        human_status = status_map.get(survey.status, survey.status.value)
        parts.append(f"📝 Статус анкеты: {human_status}")

    # Статус подписки
    if subscription:
        plan_id = subscription.plan_id
        # Получаем название тарифа
        plans = await payment_manager.get_payment_plans()
        plan_name = next((p.name for p in plans if p.id == plan_id), "Тариф")
        end_date = subscription.end_date.strftime("%d.%m.%Y")
        parts.append(f"🎫 Подписка: {plan_name} до {end_date}")
    else:
        parts.append("🎫 Активной подписки сейчас нет.")

    await message.answer("\n\n".join(parts))

@user_router.message(UserFSM.filling_survey)
async def survey_text(
    message: Message, 
    state: FSMContext, 
    users: UserManager, 
    form: FormManager,
):
    """Обработка текстовых ответов на вопросы"""
    await handler_answers_survey(
        event=message,
        state=state,
        users=users,
        form=form,
    )

@user_router.callback_query(UserFSM.filling_survey, UserCallback.filter(F.action == UserAction.YES_NO_ANSWER))
async def survey_yes_no(
    callback: CallbackQuery, 
    callback_data: UserCallback, 
    state: FSMContext, 
    users: UserManager, 
    form: FormManager,
):
    """Обработка ответов yes/no на вопросы"""
    await handler_answers_survey(
        event=callback,
        event_data=callback_data,
        state=state,
        users=users,
        form=form,
    )
    await callback.answer()











