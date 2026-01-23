from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
import logging

from src.bot.handlers.questionnaire.states import Questionnaire
from src.database.crud import save_questionnaire

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text == "Подать заявку")
async def start_questionnaire(message: Message, state: FSMContext):
    await state.set_state(Questionnaire.Q1)
    await message.answer("Вопрос 1: Как давно вы делаете гидролаты?")

@router.message(Questionnaire.Q1)
async def answer_q1(message: Message, state: FSMContext):
    await state.update_data(q1=message.text)
    await state.set_state(Questionnaire.Q2)
    await message.answer("Вопрос 2: Сколько видов гидролатов вы делаете?")

@router.message(Questionnaire.Q2)
async def answer_q2(message: Message, state: FSMContext):
    await state.update_data(q2=message.text)
    await state.set_state(Questionnaire.Q3)
    await message.answer("Вопрос 3: Почему хотите вступить в клуб?")

@router.message(Questionnaire.Q3)
async def answer_q3(message: Message, state: FSMContext):
    # Добавляем ответ на 3-й вопрос в данные
    await state.update_data(q3=message.text)
    
    # Получаем все данные из состояния
    data = await state.get_data()
    
    # Логируем для отладки
    logger.info(f"Сохранение анкеты для пользователя {message.from_user.id}")
    logger.info(f"Данные для сохранения: {data}")
    
    # Сохраняем данные в базу
    success, message_text = await save_questionnaire(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        fullname=message.from_user.full_name,
        answers_data=data
    )
    
    if success:
        await message.answer("✅ Спасибо! Ваша анкета отправлена на проверку администратором.")
        logger.info(f"Анкета для пользователя {message.from_user.id} успешно сохранена")
    else:
        await message.answer(f"❌ {message_text}\nПожалуйста, попробуйте позже или обратитесь к администратору.")
        logger.error(f"Ошибка при сохранении анкеты для пользователя {message.from_user.id}: {message_text}")
    
    # Очищаем состояние
    await state.clear()