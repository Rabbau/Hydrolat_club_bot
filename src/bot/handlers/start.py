from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message,InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from src.database.crud import can_user_create_questionnaire, is_admin

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обработчик команды /start."""
    telegram_id = message.from_user.id

    keyboard = await get_user_keyboard(telegram_id)

    # Проверяем, может ли пользователь создать анкету
    can_create, reason = await can_user_create_questionnaire(telegram_id)
    
    # Создаем клавиатуру в зависимости от возможности создания анкеты
    builder = ReplyKeyboardBuilder()
    
    if can_create:
        text = f"""
👋 Добро пожаловать в Hydrolat Club, {message.from_user.full_name}!

{reason}

Здесь вы можете подать заявку на вступление в закрытый клуб.

Правила:
1. Одна анкета на человека
2. Рассмотрение заявки в течение 24 часов
3. После одобрения - оплата вступительного взноса
4. Доступ к закрытому сообществу

Готовы начать?"""
        builder.button(text="📝 Подать заявку")
    else:
        text = f"""
👋 C возвращением, {message.from_user.full_name}!

{reason}

Для просмотра статуса вашей анкеты нажмите кнопку ниже или используйте команду /my_questionnaire"""
        

    await message.answer(text, reply_markup=keyboard)
    
    # Если пользователь админ - добавляем inline кнопку админ-панели
    if await is_admin(telegram_id):
        admin_builder = InlineKeyboardBuilder()
        admin_builder.button(text="👑 Админ панель", callback_data="admin_panel")
        
        await message.answer(
            "🔐 Доступны функции администратора:",
            reply_markup=admin_builder.as_markup()
        )


@router.message(F.text == "❓ Как это работает?")
async def how_it_works(message: Message):
    """Показать информацию o процессе."""
    text = """
📋 Как работает процесс в Hydrolat Club:

1. Подача заявки
   • Заполняете анкету (несколько вопросов)
   • Отправляете на рассмотрение

2. Модерация
   • Администратор проверяет вашу анкету
   • Срок: до 24 часов

3. Решение
   • ✅ Одобрено - получаете реквизиты для оплаты
   • ❌ Отклонено - узнаете причину

4. Оплата
   • Оплачиваете вступительный взнос
   • Отправляете скриншот администратору

5. Вступление в клуб
   • Добавляетесь в закрытый чат
   • Получаете доступ к материалам

⚠️ Правила:
• Одна анкета на человека
• При отклонении можно подать новую
• Оплата только после одобрения
"""
    
    await message.answer(text)

async def get_user_keyboard(telegram_id: int):
    """Получить клавиатуру в зависимости от статуса пользователя."""
    builder = ReplyKeyboardBuilder()
    
    can_create, reason = await can_user_create_questionnaire(telegram_id)
    
    if can_create:
        builder.button(text="📝 Подать заявку")
    else:
        builder.button(text="📋 Моя анкета")
    
    builder.button(text="❓ Как это работает?")
    builder.adjust(1)
    
    return builder.as_markup(resize_keyboard=True)

@router.message(F.text == "🔄 Обновить меню")
async def update_menu(message: Message):
    """Обновить меню пользователя."""
    telegram_id = message.from_user.id
    keyboard = await get_user_keyboard(telegram_id)
    
    await message.answer(
        "Меню обновлено! Теперь вы видите актуальные кнопки.",
        reply_markup=keyboard
    )

