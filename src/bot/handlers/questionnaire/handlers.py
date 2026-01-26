from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
import logging
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.handlers.questionnaire.states import Questionnaire
from src.database.crud import (
    save_questionnaire, 
    can_user_create_questionnaire, 
    get_user_questionnaires
)
from src.database.models import QuestionnaireStatus
from src.bot.handlers.start import get_user_keyboard

router = Router()
logger = logging.getLogger(__name__)


async def show_user_questionnaire(telegram_id: int, message_or_callback):
    """Показать анкету пользователя."""
    questionnaires = await get_user_questionnaires(telegram_id)
    
    if not questionnaires:
        await message_or_callback.answer(
            "📭 У вас нет активных анкет.\n"
            "Вы можете подать заявку, нажав кнопку ниже:",
            reply_markup=InlineKeyboardBuilder()
                .button(text="📝 Подать заявку", callback_data="start_questionnaire")
                .as_markup()
        )
        return
    
    latest = questionnaires[0]
    status_emoji = {
        QuestionnaireStatus.pending: "⏳",
        QuestionnaireStatus.approved: "✅",
        QuestionnaireStatus.rejected: "❌"
    }.get(latest.status, "📋")
    
    text = f"""
{status_emoji} Статус вашей анкеты #{latest.id}:

📅 Дата подачи: {latest.created_at.strftime('%d.%m.%Y %H:%M')}
🔍 Статус: {latest.status.value}

"""
    
    # Добавляем информацию в зависимости от статуса
    if latest.status == QuestionnaireStatus.pending:
        text += """
⏳ Ваша анкета находится на модерации.
Ожидайте решения администратора."""
    
    elif latest.status == QuestionnaireStatus.approved:
        text += """
✅ Ваша анкета одобрена!
Для завершения регистрации оплатите вступительный взнос.

Реквизиты для оплаты:
📌 Банк: Тинькофф
📌 Номер карты: 2200 7001 2345 6789
📌 Получатель: Иванов Иван Иванович
📌 Сумма: 5 000 руб.
📌 Назначение: "Вступительный взнос Hydrolat Club"

После оплаты отправьте скриншот чека @admin_hydrolat"""
    
    elif latest.status == QuestionnaireStatus.rejected:
        text += """
❌ Ваша анкета была отклонена.

Вы можете подать новую анкету.
Если у вас есть вопросы, обратитесь к администратору: @admin_hydrolat"""
    
    builder = InlineKeyboardBuilder()
    
    if latest.status == QuestionnaireStatus.rejected:
        # Если отклонена - можно подать новую
        builder.button(text="📝 Подать новую анкету", callback_data="start_questionnaire")
    elif latest.status == QuestionnaireStatus.approved:
        # Если одобрена - можно связаться с администратором
        builder.button(text="💳 Я оплатил", callback_data="i_paid")
    
    builder.button(text="📞 Связаться с администратором", url="https://t.me/admin_hydrolat")
    builder.adjust(1)
    
    await message_or_callback.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "start_questionnaire")
async def start_questionnaire_callback(callback: CallbackQuery, state: FSMContext):
    """Начать заполнение анкеты (через инлайн-кнопку)."""
    await start_questionnaire_handler(callback.from_user.id, callback.message, state)
    await callback.answer()


@router.message(F.text == "📝 Подать заявку")
async def start_questionnaire_message(message: Message, state: FSMContext):
    """Начать заполнение анкеты (через текстовую кнопку)."""
    await start_questionnaire_handler(message.from_user.id, message, state)


async def start_questionnaire_handler(telegram_id: int, message: Message, state: FSMContext):
    """Основной обработчик начала анкеты."""
    # Проверяем, может ли пользователь создать анкету
    can_create, reason = await can_user_create_questionnaire(telegram_id)
    
    if not can_create:
        # Показываем информацию о текущих анкетах
        questionnaires = await get_user_questionnaires(telegram_id)
        
        if questionnaires:
            latest = questionnaires[0]
            status_emoji = {
                QuestionnaireStatus.pending: "⏳",
                QuestionnaireStatus.approved: "✅",
                QuestionnaireStatus.rejected: "❌"
            }.get(latest.status, "📋")
            
            text = f"""
{reason}

📋 Ваша текущая анкета:
• ID: #{latest.id}
• Статус: {status_emoji} {latest.status.value}
• Дата подачи: {latest.created_at.strftime('%d.%m.%Y')}

Для проверки статуса используйте команду /my_questionnaire
"""
        else:
            text = reason
        
        await message.answer(text)
        return
    
    # Если можно создать - начинаем FSM
    await state.set_state(Questionnaire.Q1)
    await message.answer("📝 Вопрос 1 из 3:\n\nКак давно вы делаете гидролаты?")


@router.message(F.text == "Моя анкета")
async def my_questionnaire_message(message: Message):
    """Показать мою анкету (через текстовую кнопку)."""
    await show_user_questionnaire(message.from_user.id, message)


@router.message(Questionnaire.Q1)
async def answer_q1(message: Message, state: FSMContext):
    await state.update_data(q1=message.text)
    await state.set_state(Questionnaire.Q2)
    await message.answer("📝 Вопрос 2 из 3:\n\nСколько видов гидролатов вы делаете?")


@router.message(Questionnaire.Q2)
async def answer_q2(message: Message, state: FSMContext):
    await state.update_data(q2=message.text)
    await state.set_state(Questionnaire.Q3)
    await message.answer("📝 Вопрос 3 из 3:\n\nПочему хотите вступить в клуб?")


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
        keyboard = await get_user_keyboard(message.from_user.id)
        await message.answer(
            "✅ Спасибо! Ваша анкета отправлена на проверку администратором.\n\n"
            "Мы рассмотрим вашу заявку в течение 24 часов. "
            "Вы можете проверить статус анкеты с помощью команды /my_questionnaire",
            reply_markup=keyboard
        )

        logger.info(f"Анкета для пользователя {message.from_user.id} успешно сохранена")
    else:
        await message.answer(
            f"❌ {message_text}\n"
            f"Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
        logger.error(f"Ошибка при сохранении анкеты для пользователя {message.from_user.id}: {message_text}")
    
    # Очищаем состояние
    await state.clear()


@router.callback_query(F.data == "my_questionnaire_status")
async def my_questionnaire_callback(callback: CallbackQuery):
    """Обработчик инлайн-кнопки 'Моя анкета'."""
    await show_user_questionnaire(callback.from_user.id, callback.message)
    await callback.answer()


@router.message(F.text == "/my_questionnaire")
async def my_questionnaire_command(message: Message):
    """Обработчик команды /my_questionnaire."""
    await show_user_questionnaire(message.from_user.id, message)

@router.message(F.text == "📋 Моя анкета")
async def my_questionnaire_message_with_emoji(message: Message):
    """Показать мою анкету (через текстовую кнопку с эмодзи)."""
    await show_user_questionnaire(message.from_user.id, message)
