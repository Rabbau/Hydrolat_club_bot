from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

from src.bot.filters.superadmin import IsSuperAdmin
from src.database.crud import (
    add_admin, 
    remove_admin, 
    get_admins_with_users,
    get_admin
)

router = Router()

# Этот роутер доступен только суперадминам
router.message.filter(IsSuperAdmin())
router.callback_query.filter(IsSuperAdmin())


async def get_admin_management_keyboard():
    """Клавиатура для управления администраторами."""
    builder = InlineKeyboardBuilder()
    
    builder.button(text="👥 Список админов", callback_data="admin_list")
    builder.button(text="➕ Добавить админа", callback_data="admin_add_form")
    builder.button(text="🔙 Назад в админку", callback_data="admin_back")
    builder.adjust(1)
    
    return builder.as_markup()


@router.message(Command("manage_admins"))
async def admin_management_panel(message: Message):
    """Панель управления администраторами."""
    text = """
👑 *Управление администраторами*

Здесь вы можете:
• 👥 Просмотреть список администраторов
• ➕ Добавить нового администратора
• ➖ Удалить администратора
"""
    
    await message.answer(text, reply_markup=await get_admin_management_keyboard())


@router.callback_query(F.data == "admin_list")
async def show_admin_list(callback: CallbackQuery):
    """Показать список администраторов."""
    admins_with_users = await get_admins_with_users()
    
    if not admins_with_users:
        text = "📭 Список администраторов пуст"
    else:
        text = "👥 *Список администраторов:*\n\n"
        for i, (admin, user) in enumerate(admins_with_users, 1):
            level = "👑 Суперадмин" if admin.level == 2 else "⚙️ Админ"
            text += f"{i}. ID: `{admin.telegram_id}`\n"
            
            if user and user.fullname:
                text += f"   Имя: {user.fullname}\n"
            elif admin.fullname:
                text += f"   Имя: {admin.fullname}\n"
                
            if user and user.username:
                text += f"   Ник: @{user.username}\n"
            elif admin.username:
                text += f"   Ник: @{admin.username}\n"
                
            text += f"   Уровень: {level}\n"
            text += f"   Добавлен: {admin.created_at.strftime('%d.%m.%Y')}\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="➖ Удалить админа", callback_data="admin_remove_list")
    builder.button(text="🔙 Назад", callback_data="admin_manage_back")
    builder.adjust(1)
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "admin_add_form")
async def admin_add_form(callback: CallbackQuery):
    """Форма добавления администратора."""
    text = """
➕ *Добавление администратора*

Для добавления администратора отправьте команду:
`/add_admin <ID пользователя>`

Например:
`/add_admin 123456789`

Чтобы узнать ID пользователя:
1. Попросите пользователя отправить команду `/myid`
2. Или используйте онлайн-инструменты для получения ID

*Важно:* Пользователь должен хотя бы раз запустить бота (`/start`), чтобы быть в базе данных.
"""
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Назад", callback_data="admin_manage_back")
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()


@router.message(Command("add_admin"))
async def admin_add_command(message: Message):
    """Добавить администратора через команду."""
    try:
        # Парсим аргументы
        args = message.text.split()
        if len(args) != 2:
            await message.answer(
                "❌ Неправильный формат команды.\n"
                "Использование: `/add_admin <ID пользователя>`\n\n"
                "Пример: `/add_admin 123456789`",
                parse_mode="Markdown"
            )
            return
        
        new_admin_id = int(args[1])
        
        # Нельзя добавить себя (ты уже суперадмин)
        if new_admin_id == message.from_user.id:
            await message.answer("❌ Вы уже являетесь суперадмином!")
            return
        
        # Добавляем админа
        success, msg = await add_admin(
            telegram_id=new_admin_id,
            level=1
        )
        
        await message.answer(msg)
        
    except ValueError:
        await message.answer("❌ ID должен быть числом!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@router.callback_query(F.data == "admin_remove_list")
async def admin_remove_list(callback: CallbackQuery):
    """Список админов для удаления."""
    admins = await get_admins_with_users()
    
    # Фильтруем - нельзя удалить себя (суперадмина)
    admins = [a for a in admins if a[0].telegram_id != callback.from_user.id]
    
    if not admins:
        text = "📭 Нет администраторов для удаления"
        builder = InlineKeyboardBuilder()
        builder.button(text="🔙 Назад", callback_data="admin_list")
    else:
        text = "➖ *Выберите администратора для удаления:*"
        builder = InlineKeyboardBuilder()
        
        for admin, user in admins:
            label = f"ID: {admin.telegram_id}"
            if user and user.username:
                label += f" (@{user.username})"
            elif admin.username:
                label += f" (@{admin.username})"
            if admin.level == 2:
                label += " 👑"
            
            builder.button(text=label, callback_data=f"admin_remove_{admin.telegram_id}")
        
        builder.button(text="🔙 Назад", callback_data="admin_list")
        builder.adjust(1)
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("admin_remove_confirm_"))
async def admin_remove_execute(callback: CallbackQuery):
    """Удаление администратора."""
    try:
        telegram_id = int(callback.data.split("_")[-1])
        
        # Вызываем функцию удаления
        success, msg = await remove_admin(
            telegram_id=telegram_id,
            by_superadmin_id=callback.from_user.id
        )
        
        
        if success:
            await callback.answer("✅ Администратор удален", show_alert=False)
            await admin_remove_list(callback)
        else:
            await callback.answer(msg, show_alert=True)
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        await callback.answer(f"❌ Ошибка: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("admin_remove_"))
async def admin_remove_confirm(callback: CallbackQuery):
    """Подтверждение удаления администратора."""

    telegram_id = int(callback.data.split("_")[-1])
    # Получаем информацию об админе
    admin = await get_admin(telegram_id)
    
    if not admin:
        await callback.answer("❌ Администратор не найден", show_alert=True)
        return
    
    if telegram_id == callback.from_user.id:
        await callback.answer("❌ Нельзя удалить самого себя", show_alert=True)
        return

    text = f"""
❓ *Подтверждение удаления*

Вы уверены, что хотите удалить администратора?

ID: `{admin.telegram_id}`
"""
    
    if admin.username:
        text += f"Ник: @{admin.username}\n"
    if admin.fullname:
        text += f"Имя: {admin.fullname}\n"
    
    text += f"Уровень: {'👑 Суперадмин' if admin.level == 2 else '⚙️ Админ'}"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"admin_remove_confirm_{telegram_id}")
    builder.button(text="❌ Нет, отмена", callback_data="admin_remove_list")
    builder.adjust(1)
    print(f"🔍 DEBUG: Создана кнопка с callback_data=admin_remove_confirm_{telegram_id}")
    
    try:
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup())
    except TelegramBadRequest as e:
        # Игнорируем ошибку "message is not modified"
        if "message is not modified" not in str(e):
            raise e
    await callback.answer()





@router.callback_query(F.data.in_(["admin_manage_back", "admin_back"]))
async def admin_management_back(callback: CallbackQuery):
    """Вернуться в панель управления админами."""
    text = """
👑 *Управление администраторами*

Здесь вы можете:
• 👥 Просмотреть список администраторов
• ➕ Добавить нового администратора
• ➖ Удалить администратора
"""
    
    await callback.message.edit_text(text, reply_markup=await get_admin_management_keyboard())
    await callback.answer()


@router.message(Command("myid"))
async def get_my_id(message: Message):
    """Показать свой ID."""
    await message.answer(f"👤 Ваш ID: `{message.from_user.id}`", parse_mode="Markdown")


@router.message(Command("id"))
async def get_user_id_by_username(message: Message):
    """Получить ID пользователя по username."""
    args = message.text.split()
    if len(args) != 2:
        await message.answer(
            "❌ Неправильный формат команды.\n"
            "Использование: `/id @username`",
            parse_mode="Markdown"
        )
        return
    
    username = args[1].lstrip('@')
    await message.answer(
        f"🔍 Для получения ID пользователя @{username} попросите его отправить команду `/myid`",
        parse_mode="Markdown"
    )



#-------------------------------------- блок для отладки ---------------------------------------------------------------

@router.message(Command("test_remove"))
async def test_remove_command(message: Message):
    """Тестовая команда для удаления администратора."""
    try:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Использование: /test_remove <ID>")
            return
        
        telegram_id = int(args[1])
        success, msg = await remove_admin(telegram_id, by_superadmin_id=message.from_user.id)
        
        await message.answer(f"Результат:\nУспех: {success}\nСообщение: {msg}")
        
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

@router.message(Command("list_admins"))
async def list_admins_command(message: Message):
    """Показать всех администраторов."""
    admins_with_users = await get_admins_with_users()
    
    if not admins_with_users:
        await message.answer("📭 Список администраторов пуст")
        return
    
    text = "👥 *Список администраторов:*\n\n"
    for i, (admin, user) in enumerate(admins_with_users, 1):
        level = "👑 Суперадмин" if admin.level == 2 else "⚙️ Админ"
        text += f"{i}. ID: `{admin.telegram_id}`\n"
        
        if user and user.fullname:
            text += f"   Имя: {user.fullname}\n"
        elif admin.fullname:
            text += f"   Имя: {admin.fullname}\n"
            
        if user and user.username:
            text += f"   Ник: @{user.username}\n"
        elif admin.username:
            text += f"   Ник: @{admin.username}\n"
            
        text += f"   Уровень: {level}\n"
        text += f"   Добавлен: {admin.created_at.strftime('%d.%m.%Y')}\n\n"
    
    await message.answer(text, parse_mode="Markdown")

#-----------------------------------------------------------------------------------------------------
