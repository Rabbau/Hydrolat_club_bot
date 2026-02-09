from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery
from src.FormManager.FormManager import FormManager
from src.user_components.user_callbacks import UserCallback, UserAction
from src.user_components.user_keyboard import user_main_menu_inline_keyboard as user_main_kb, \
user_filling_survey_inline_keyboard as yes_no_kb, user_survey_check_status as status_kb
from src.user_components.user_states import UserFSM
from src.db_components.user_manager import user_manager, UserManager
import logging

logger = logging.getLogger(__name__)

user_router = Router(name="user_router")

@user_router.message(CommandStart())
async def start(message: Message, users: UserManager):
    user_exists = await users.user_exists(message.from_user.id)
    if user_exists:
        await message.answer(
            text="Вы уже заполнили анкету",
            reply_markup=status_kb
        )
    else:
        await message.answer(
            text="Здравствуйте! Заполните анкету.",
            reply_markup=user_main_kb)

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
        if isinstance(event, Message):
            await event.answer("✅ Анкета отправлена!")
        else:
            await event.message.edit_text("✅ Анкета отправлена!")
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
    
    # Добавляем пользователя в БД если его еще нет
    await users.add_user(
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        first_name=callback.from_user.first_name,
        last_name=callback.from_user.last_name,
    )
    
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











