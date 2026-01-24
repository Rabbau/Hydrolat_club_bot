from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.bot.filters.admin import IsAdmin
from src.database.crud import (
    get_statistics,
    get_pending_questionnaires_list,
    get_questionnaire_details
)
from datetime import datetime


router = Router()

# Подключаем фильтр IsAdmin ко всем хендлерам в этом роутере
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Главная панель администратора."""
    
    # Получаем статистику для отображения
    stats = await get_statistics()
    
    # Создаем клавиатуру
    builder = InlineKeyboardBuilder()
    
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📝 Новые анкеты", callback_data="admin_new")
    builder.button(text="✅ Одобренные", callback_data="admin_approved")
    builder.button(text="❌ Отклоненные", callback_data="admin_rejected")
    builder.button(text="👥 Пользователи", callback_data="admin_users")
    builder.button(text="⚙️ Настройки", callback_data="admin_settings")
    
    # Располагаем кнопки по 2 в ряд
    builder.adjust(2, 2, 2)
    
    text = f"""
👑 Панель администратора

📈 Краткая статистика:
• 👥 Пользователей: {stats.get('total_users', 0)}
• 📝 Анкет всего: {stats.get('total_questionnaires', 0)}
• ⏳ На модерации: {stats.get('pending_count', 0)}
• ✅ Одобрено: {stats.get('approved_count', 0)}

Выберите раздел для управления:
    """
    
    await message.answer(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "admin_stats")
async def show_statistics(callback: CallbackQuery):
    """Показать статистику."""
    try:
        stats = await get_statistics()
        
        current_time = datetime.now().strftime("%H:%M:%S")
        
        text = f"""
📊 Статистика системы (обновлено: {current_time})

👥 Пользователи:
• Всего: {stats.get('total_users', 0)}
• Заполнили анкету: {stats.get('questionnaire_completed', 0)}
• За сегодня: {stats.get('users_today', 0)}

📋 Анкеты:
• Всего: {stats.get('total_questionnaires', 0)}
• ⏳ На модерации: {stats.get('pending_count', 0)}
• ✅ Одобрено: {stats.get('approved_count', 0)}
• ❌ Отклонено: {stats.get('rejected_count', 0)}
• За сегодня: {stats.get('questionnaires_today', 0)}
        """
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Обновить", callback_data="admin_stats")
        builder.button(text="◀️ Назад", callback_data="admin_back")
        builder.adjust(2)
        
        try:
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
        except Exception as edit_error:
            # Если не удалось отредактировать (например, сообщение не изменилось),
            # просто отвечаем на callback
            if "message is not modified" not in str(edit_error):
                raise edit_error
        
    except Exception as e:
        print(f"Ошибка при получении статистики: {e}")
        try:
            await callback.message.edit_text(
                "❌ Ошибка при получении статистики\n"
                "Проверьте подключение к базе данных",
                reply_markup=InlineKeyboardBuilder()
                    .button(text="◀️ Назад", callback_data="admin_back")
                    .as_markup()
            )
        except:
            pass
    
    await callback.answer()


@router.callback_query(F.data == "admin_new")
async def show_new_questionnaires(callback: CallbackQuery):
    """Показать новые анкеты на модерации."""
    try:
        questionnaires = await get_pending_questionnaires_list(limit=10)
        
        if not questionnaires:
            builder = InlineKeyboardBuilder()
            builder.button(text="◀️ Назад", callback_data="admin_back")
            
            try:
                await callback.message.edit_text(
                    "📭 Нет новых анкет на модерации",
                    reply_markup=builder.as_markup()
                )
            except Exception as edit_error:
                if "message is not modified" not in str(edit_error):
                    raise edit_error
            
            await callback.answer()
            return
        
        builder = InlineKeyboardBuilder()
        
        for q in questionnaires:
            # Формируем текст для кнопки
            user_info = f"{q.user.fullname or 'Без имени'}"
            if q.user.username:
                user_info += f" (@{q.user.username})"
            
            # Обрезаем если слишком длинно
            if len(user_info) > 30:
                user_info = user_info[:27] + "..."
            
            builder.button(
                text=f"📄 #{q.id} - {user_info}",
                callback_data=f"view_questionnaire_{q.id}"
            )
        
        builder.button(text="◀️ Назад", callback_data="admin_back")
        builder.adjust(1)  # Все кнопки в один столбец
        
        text = f"📝 Новые анкеты ({len(questionnaires)}):"
        
        try:
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
        except Exception as edit_error:
            if "message is not modified" not in str(edit_error):
                raise edit_error
        
    except Exception as e:
        print(f"Ошибка при получении анкет: {e}")
        try:
            await callback.message.edit_text(
                "❌ Ошибка при загрузке анкет",
                reply_markup=InlineKeyboardBuilder()
                    .button(text="◀️ Назад", callback_data="admin_back")
                    .as_markup()
            )
        except:
            pass
    
    await callback.answer()


@router.callback_query(F.data.startswith("view_questionnaire_"))
async def view_questionnaire_details(callback: CallbackQuery):
    """Просмотреть детали анкеты."""
    try:
        questionnaire_id = int(callback.data.split("_")[-1])
        
        questionnaire = await get_questionnaire_details(questionnaire_id)
        
        if not questionnaire:
            try:
                await callback.message.edit_text(
                    "❌ Анкета не найдена",
                    reply_markup=InlineKeyboardBuilder()
                        .button(text="◀️ Назад", callback_data="admin_new")
                        .as_markup()
                )
            except Exception as edit_error:
                if "message is not modified" not in str(edit_error):
                    raise edit_error
            
            await callback.answer()
            return
        
        # Формируем текст анкеты
        user = questionnaire.user
        text = f"""
📋 Анкета #{questionnaire.id}

👤 Пользователь:
• ID: {user.telegram_id}
• Имя: {user.fullname or 'Не указано'}
• Ник: @{user.username or 'нет'}

📅 Дата подачи: {questionnaire.created_at.strftime('%d.%m.%Y %H:%M')}
🔍 Статус: {questionnaire.status.value}

━━━━━━━━━━━━━━━━━━━━

📝 Ответы:
        """
        
        # Добавляем ответы
        if hasattr(questionnaire, 'answers') and questionnaire.answers:
            for answer in questionnaire.answers:
                question_text = answer.question.text
                if len(question_text) > 50:
                    question_text = question_text[:47] + "..."
                
                text += f"\n• {question_text}\n  → {answer.answer_text}\n"
        else:
            text += "\n⚠️ Ответы не найдены\n"
        
        # Кнопки действий
        builder = InlineKeyboardBuilder()
        builder.button(text="✅ Одобрить", callback_data=f"approve_{questionnaire.id}")
        builder.button(text="❌ Отклонить", callback_data=f"reject_{questionnaire.id}")
        builder.button(text="◀️ Назад к списку", callback_data="admin_new")
        builder.adjust(2, 1)  # Первые две кнопки в ряд, третья отдельно
        
        try:
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
        except Exception as edit_error:
            if "message is not modified" not in str(edit_error):
                raise edit_error
        
    except Exception as e:
        print(f"Ошибка при просмотре анкеты: {e}")
        try:
            await callback.message.edit_text(
                "❌ Ошибка при загрузке анкеты",
                reply_markup=InlineKeyboardBuilder()
                    .button(text="◀️ Назад", callback_data="admin_new")
                    .as_markup()
            )
        except:
            pass
    
    await callback.answer()


@router.callback_query(F.data.startswith("approve_"))
async def approve_questionnaire(callback: CallbackQuery):
    """Одобрить анкету (заглушка)."""
    questionnaire_id = int(callback.data.split("_")[-1])
    
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад к списку", callback_data="admin_new")
    
    try:
        await callback.message.edit_text(
            f"✅ Анкета #{questionnaire_id} одобрена!\n"
            "(функция в разработке)",
            reply_markup=builder.as_markup()
        )
    except Exception as edit_error:
        if "message is not modified" not in str(edit_error):
            raise edit_error
    
    await callback.answer()


@router.callback_query(F.data.startswith("reject_"))
async def reject_questionnaire(callback: CallbackQuery):
    """Отклонить анкету (заглушка)."""
    questionnaire_id = int(callback.data.split("_")[-1])
    
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад к списку", callback_data="admin_new")
    
    try:
        await callback.message.edit_text(
            f"❌ Анкета #{questionnaire_id} отклонена!\n"
            "(функция в разработке)",
            reply_markup=builder.as_markup()
        )
    except Exception as edit_error:
        if "message is not modified" not in str(edit_error):
            raise edit_error
    
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Вернуться в главное меню админки."""
    # Используем message для вызова функции админ-панели
    if hasattr(callback, 'message') and callback.message:
        try:
            await admin_panel(callback.message)
        except Exception as e:
            print(f"Ошибка в admin_back: {e}")
    await callback.answer()


@router.callback_query(F.data.in_([
    "admin_approved", "admin_rejected", 
    "admin_users", "admin_settings"
]))
async def admin_coming_soon(callback: CallbackQuery):
    """Заглушка для разделов в разработке."""
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="admin_back")
    
    try:
        await callback.message.edit_text(
            "🚧 Этот раздел находится в разработке\n"
            "Скоро будет доступен!",
            reply_markup=builder.as_markup()
        )
    except Exception as edit_error:
        if "message is not modified" not in str(edit_error):
            raise edit_error
    
    await callback.answer()