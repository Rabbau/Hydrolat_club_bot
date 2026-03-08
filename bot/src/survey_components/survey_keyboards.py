from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.admin_components.admin_callbacks import AdminAction, AdminCallback
from src.survey_components.survey_callbacks import SurveyAction, SurveyCallback


survey_menu_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Добавить вопрос",
                callback_data=SurveyCallback(action=SurveyAction.ADD_QUESTION).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="Редактировать вопрос",
                callback_data=SurveyCallback(action=SurveyAction.EDIT_QUESTION).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="Удалить вопрос",
                callback_data=SurveyCallback(action=SurveyAction.DELETE_QUESTION).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ],
    ]
)


survey_menu_inline_keyboard_empty = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Добавить вопрос",
                callback_data=SurveyCallback(action=SurveyAction.ADD_QUESTION).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ],
    ]
)


survey_menu_back_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=SurveyCallback(action=SurveyAction.BACK).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ]
    ]
)


survey_menu_edit_back_or_next_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=SurveyCallback(action=SurveyAction.BACK).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Далее",
                callback_data=SurveyCallback(action=SurveyAction.QUESTION_TYPE).pack(),
            )
        ],
    ]
)


survey_menu_question_type_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="Да/Нет", callback_data="type:yes_no"),
            InlineKeyboardButton(text="В сообщении", callback_data="type:text"),
        ],
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=SurveyCallback(action=SurveyAction.BACK).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ],
    ]
)


survey_menu_add_question_or_back_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Добавить еще вопрос",
                callback_data=SurveyCallback(action=SurveyAction.ADD_QUESTION).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=SurveyCallback(action=SurveyAction.BACK).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ],
    ]
)
