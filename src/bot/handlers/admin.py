from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from src.database.models import QuestionnaireStatus
from src.bot.filters.admin import IsAdmin
from src.database.crud import (
    get_statistics,
    get_pending_questionnaires_list,
    get_questionnaire_details,
    approve_questionnaire,
    reject_questionnaire,
    get_approved_questionnaires,      
    get_rejected_questionnaires
)

from src.bot.texts.notifications import (
    get_approval_message,
    get_rejection_message,
    get_admin_notification
)

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
            user_info = f"{q.user.fullname or 'Без имени'}"
            if q.user.username:
                user_info += f" (@{q.user.username})"
            
            if len(user_info) > 30:
                user_info = user_info[:27] + "..."
            
            builder.button(
                text=f"📄 #{q.id} - {user_info}",
                callback_data=f"view_questionnaire_{q.id}"
            )
        
        builder.button(text="◀️ Назад", callback_data="admin_back")
        builder.adjust(1)
        
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
                        .button(text="◀️ Назад", callback_data="admin_back")
                        .as_markup()
                )
            except Exception as edit_error:
                if "message is not modified" not in str(edit_error):
                    raise edit_error
            
            await callback.answer()
            return
        
        # Формируем текст анкеты
        user = questionnaire.user
        status_emoji = {
            QuestionnaireStatus.pending: "⏳",
            QuestionnaireStatus.approved: "✅", 
            QuestionnaireStatus.rejected: "❌"
        }.get(questionnaire.status, "📋")
        
        text = f"""
{status_emoji} Анкета #{questionnaire.id}

👤 Пользователь:
• ID: {user.telegram_id}
• Имя: {user.fullname or 'Не указано'}
• Ник: @{user.username or 'нет'}
• Статус: {user.status.value}

📅 Дата подачи: {questionnaire.created_at.strftime('%d.%m.%Y %H:%M')}
🔍 Статус анкеты: {questionnaire.status.value}

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
        
        # Создаем клавиатуру в зависимости от статуса
        builder = InlineKeyboardBuilder()
        
        if questionnaire.status == QuestionnaireStatus.pending:
            # Для анкет на модерации - кнопки действий
            builder.button(text="✅ Одобрить", callback_data=f"approve_{questionnaire.id}")
            builder.button(text="❌ Отклонить", callback_data=f"reject_{questionnaire.id}")
            builder.button(text="◀️ Назад к списку", callback_data="admin_new")
            builder.adjust(2, 1)
            
        elif questionnaire.status == QuestionnaireStatus.approved:
            # Для одобренных - можно отклонить (передумать)
            builder.button(text="❌ Отменить одобрение", callback_data=f"reject_{questionnaire.id}")
            builder.button(text="◀️ Назад к одобренным", callback_data="admin_approved")
            builder.button(text="📋 Все разделы", callback_data="admin_back")
            builder.adjust(1, 1, 1)
            
        elif questionnaire.status == QuestionnaireStatus.rejected:
            # Для отклоненных - можно одобрить (передумать)
            builder.button(text="✅ Восстановить", callback_data=f"approve_{questionnaire.id}")
            builder.button(text="◀️ Назад к отклоненным", callback_data="admin_rejected")
            builder.button(text="📋 Все разделы", callback_data="admin_back")
            builder.adjust(1, 1, 1)
        else:
            # Для других статусов
            builder.button(text="◀️ Назад", callback_data="admin_back")
        
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
                    .button(text="◀️ Назад", callback_data="admin_back")
                    .as_markup()
            )
        except:
            pass
    
    await callback.answer()


@router.callback_query(F.data.startswith("approve_"))
async def approve_questionnaire_handler(callback: CallbackQuery):
    """Одобрить анкету."""
    questionnaire_id = int(callback.data.split("_")[-1])
    
    # Одобряем анкету в БД
    success, user = await approve_questionnaire(questionnaire_id)
    
    if not success or not user:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад", callback_data="admin_new")
        
        await callback.message.edit_text(
            "❌ Ошибка при одобрении анкеты\n"
            "Анкета не найдена или произошла ошибка",
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        return
    
    # Отправляем уведомление пользователю
    try:
        approval_message = get_approval_message()
        await callback.bot.send_message(
            chat_id=user.telegram_id,
            text=approval_message,
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления пользователю: {e}")
    
    # Показываем подтверждение администратору
    admin_message = get_admin_notification(
        user_telegram_id=user.telegram_id,
        user_name=user.fullname or "Неизвестно",
        action="approved",
        questionnaire_id=questionnaire_id
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Ещё анкеты", callback_data="admin_new")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.adjust(2)
    
    try:
        await callback.message.edit_text(
            admin_message,
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    except Exception as edit_error:
        if "message is not modified" not in str(edit_error):
            raise edit_error
    
    await callback.answer()


@router.callback_query(F.data.startswith("reject_"))
async def reject_questionnaire_handler(callback: CallbackQuery):
    """Отклонить анкету."""
    questionnaire_id = int(callback.data.split("_")[-1])
    
    # Отклоняем анкету в БД
    success, user = await reject_questionnaire(questionnaire_id)
    
    if not success or not user:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад", callback_data="admin_new")
        
        await callback.message.edit_text(
            "❌ Ошибка при отклонении анкеты\n"
            "Анкета не найдена или произошла ошибка",
            reply_markup=builder.as_markup()
        )
        await callback.answer()
        return
    
    # Отправляем уведомление пользователю
    try:
        rejection_message = get_rejection_message()
        await callback.bot.send_message(
            chat_id=user.telegram_id,
            text=rejection_message,
            parse_mode=None
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления пользователю: {e}")
    
    # Показываем подтверждение администратору
    admin_message = get_admin_notification(
        user_telegram_id=user.telegram_id,
        user_name=user.fullname or "Неизвестно",
        action="rejected",
        questionnaire_id=questionnaire_id
    )
    
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Ещё анкеты", callback_data="admin_new")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.adjust(2)
    
    try:
        await callback.message.edit_text(
            admin_message,
            reply_markup=builder.as_markup(),
            parse_mode="Markdown"
        )
    except Exception as edit_error:
        if "message is not modified" not in str(edit_error):
            raise edit_error
    
    await callback.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Вернуться в главное меню админки."""
    if hasattr(callback, 'message') and callback.message:
        try:
            await admin_panel(callback.message)
        except Exception as e:
            print(f"Ошибка в admin_back: {e}")
    await callback.answer()


@router.callback_query(F.data == "admin_approved")
async def show_approved_questionnaires(callback: CallbackQuery):
    """Показать одобренные анкеты."""
    try:
        questionnaires = await get_approved_questionnaires(limit=10)
        
        if not questionnaires:
            builder = InlineKeyboardBuilder()
            builder.button(text="◀️ Назад", callback_data="admin_back")
            
            try:
                await callback.message.edit_text(
                    "📭 Нет одобренных анкет",
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
            
            # Добавляем дату для контекста
            date_str = q.created_at.strftime("%d.%m")
            
            # Обрезаем если слишком длинно
            if len(user_info) > 25:
                user_info = user_info[:22] + "..."
            
            builder.button(
                text=f"✅ #{q.id} - {user_info} ({date_str})",
                callback_data=f"view_questionnaire_{q.id}"
            )
        
        # Кнопки навигации
        builder.button(text="📊 Статистика", callback_data="admin_stats")
        builder.button(text="📝 Новые", callback_data="admin_new")
        builder.button(text="❌ Отклоненные", callback_data="admin_rejected")
        builder.button(text="◀️ Назад", callback_data="admin_back")
        builder.adjust(1, 2, 1, 1)  # Анкеты по одной, затем 2 кнопки, затем 1, затем 1
        
        text = f"✅ Одобренные анкеты ({len(questionnaires)}):"
        
        try:
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
        except Exception as edit_error:
            if "message is not modified" not in str(edit_error):
                raise edit_error
        
    except Exception as e:
        print(f"Ошибка при получении одобренных анкет: {e}")
        try:
            await callback.message.edit_text(
                f"❌ Ошибка при загрузке анкет\n{str(e)[:100]}",
                reply_markup=InlineKeyboardBuilder()
                    .button(text="◀️ Назад", callback_data="admin_back")
                    .as_markup()
            )
        except:
            pass
    
    await callback.answer()


@router.callback_query(F.data == "admin_rejected")
async def show_rejected_questionnaires(callback: CallbackQuery):
    """Показать отклоненные анкеты."""
    try:
        questionnaires = await get_rejected_questionnaires(limit=10)
        
        if not questionnaires:
            builder = InlineKeyboardBuilder()
            builder.button(text="◀️ Назад", callback_data="admin_back")
            
            try:
                await callback.message.edit_text(
                    "📭 Нет отклоненных анкет",
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
            
            # Добавляем дату для контекста
            date_str = q.created_at.strftime("%d.%m")
            
            # Обрезаем если слишком длинно
            if len(user_info) > 25:
                user_info = user_info[:22] + "..."
            
            builder.button(
                text=f"❌ #{q.id} - {user_info} ({date_str})",
                callback_data=f"view_questionnaire_{q.id}"
            )
        
        # Кнопки навигации
        builder.button(text="📊 Статистика", callback_data="admin_stats")
        builder.button(text="📝 Новые", callback_data="admin_new")
        builder.button(text="✅ Одобренные", callback_data="admin_approved")
        builder.button(text="◀️ Назад", callback_data="admin_back")
        builder.adjust(1, 2, 1, 1)  # Анкеты по одной, затем 2 кнопки, затем 1, затем 1
        
        text = f"❌ Отклоненные анкеты ({len(questionnaires)}):"
        
        try:
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
        except Exception as edit_error:
            if "message is not modified" not in str(edit_error):
                raise edit_error
        
    except Exception as e:
        print(f"Ошибка при получении отклоненных анкет: {e}")
        try:
            await callback.message.edit_text(
                f"❌ Ошибка при загрузке анкет\n{str(e)[:100]}",
                reply_markup=InlineKeyboardBuilder()
                    .button(text="◀️ Назад", callback_data="admin_back")
                    .as_markup()
            )
        except:
            pass
    
    await callback.answer()

@router.callback_query(F.data.in_([
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