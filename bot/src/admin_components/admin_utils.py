from aiogram.types import Message, CallbackQuery
import os

import src.admin_components.admin_keyboards as kb
from src.db_components.survey_manager import admin_manager


def _parse_env_int(value: str | None) -> int | None:
    if not value:
        return None
    cleaned = value.strip().strip("\"'")
    try:
        return int(cleaned)
    except ValueError:
        return None


async def show_admin_main_menu(callback_or_message: CallbackQuery | Message):
    text, keyboard = "Admin menu:", kb.admin_main_menu_inline_keyboard
    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.message.edit_text(text=text, reply_markup=keyboard)
        await callback_or_message.answer()
    else:
        await callback_or_message.answer(text=text, reply_markup=keyboard)


async def show_moderation_menu(callback_or_message: CallbackQuery | Message):
    """Показать главное меню модерации (для админов)."""
    text, keyboard = "Модерация:", kb.moderation_main_menu_inline_keyboard
    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.message.edit_text(text=text, reply_markup=keyboard)
        await callback_or_message.answer()
    else:
        await callback_or_message.answer(text=text, reply_markup=keyboard)


async def show_super_admin_menu(callback_or_message: CallbackQuery | Message):
    """Показать меню настроек бота для супер-администратора."""
    user = (
        callback_or_message.from_user
        if isinstance(callback_or_message, Message)
        else callback_or_message.from_user
    )

    # Сначала проверяем переменную окружения SUPER_ADMIN_ID
    super_admin_id = _parse_env_int(os.getenv("SUPER_ADMIN_ID"))
    is_env_super_admin = super_admin_id is not None and user.id == super_admin_id

    # Затем проверяем БД
    is_db_super_admin = await admin_manager.is_super_admin(user.id)

    if not (is_env_super_admin or is_db_super_admin):
        # Для обычного админа просто сообщаем об отсутствии прав
        text = "У вас нет прав супер-администратора для изменения настроек бота."
        if isinstance(callback_or_message, CallbackQuery):
            await callback_or_message.answer(text, show_alert=True)
        else:
            await callback_or_message.answer(text)
        return

    text = (
        "⚙️ <b>Настройки бота (супер-админ)</b>\n\n"
        "Выберите действие с помощью кнопок ниже.\n"
    )

    keyboard = kb.super_admin_settings_inline_keyboard

    if isinstance(callback_or_message, CallbackQuery):
        await callback_or_message.message.edit_text(
            text=text,
            reply_markup=keyboard,
        )
        await callback_or_message.answer()
    else:
        await callback_or_message.answer(text, reply_markup=keyboard)
