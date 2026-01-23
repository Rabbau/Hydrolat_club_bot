from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Главное меню бота.

    Сейчас используется только базовая кнопка запуска анкеты.
    """
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Подать заявку")]],
        resize_keyboard=True,
        selective=True,
    )

