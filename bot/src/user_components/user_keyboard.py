from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from src.user_components.user_callbacks import UserAction, UserCallback


user_main_menu_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Заполнить анкету",
                callback_data=UserCallback(action=UserAction.FILL_SURVEY).pack(),
            )
        ]
    ]
)

user_filling_survey_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Да",
                callback_data=UserCallback(
                    action=UserAction.YES_NO_ANSWER, value="yes"
                ).pack(),
            ),
            InlineKeyboardButton(
                text="Нет",
                callback_data=UserCallback(
                    action=UserAction.YES_NO_ANSWER, value="no"
                ).pack(),
            ),
        ]
    ]
)

user_survey_check_status = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Анкета"),
            KeyboardButton(text="Статус профиля"),
            KeyboardButton(text="Тарифы"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)


admin_survey_check_status = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="Админка"),
            KeyboardButton(text="Статус профиля"),
            KeyboardButton(text="Тарифы"),
        ],
    ],
    resize_keyboard=True,
    one_time_keyboard=False,
)
