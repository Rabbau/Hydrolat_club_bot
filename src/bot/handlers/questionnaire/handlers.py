from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from src.bot.handlers.questionnaire.states import Questionnaire

router = Router()

@router.message(F.text=="Подать заявку")
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
    data = await state.get_data()
    # Сохраняем данные в базу (мок)
    await message.answer("Спасибо! Ваша анкета отправлена на проверку администратором.")
    await state.clear()
