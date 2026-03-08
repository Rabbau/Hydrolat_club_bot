from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.admin_components.admin_callbacks import AdminAction, AdminCallback


admin_main_menu_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Анкета",
                callback_data=AdminCallback(action=AdminAction.SURVEY_MENU).pack(),
            ),
            InlineKeyboardButton(
                text="Модерация",
                callback_data=AdminCallback(action=AdminAction.MODERATION).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Статистика",
                callback_data=AdminCallback(action=AdminAction.STATISTICS).pack(),
            ),
            InlineKeyboardButton(
                text="Настройки бота",
                callback_data=AdminCallback(action=AdminAction.HISTORY).pack(),
            ),
        ],
    ]
)


moderation_main_menu_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Анкеты на проверке",
                callback_data=AdminCallback(action=AdminAction.REVIEW_SURVEYS).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="Ожидают оплату",
                callback_data=AdminCallback(action=AdminAction.PENDING_PAYMENTS).pack(),
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


super_admin_settings_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Настройка вывода",
                callback_data=AdminCallback(action=AdminAction.OUTPUT_SETTINGS).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Список тарифов",
                callback_data=AdminCallback(action=AdminAction.LIST_PLANS).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="Список промокодов",
                callback_data=AdminCallback(action=AdminAction.LIST_PROMOS).pack(),
            )
        ],
        [
            InlineKeyboardButton(
                text="Список админов",
                callback_data=AdminCallback(action=AdminAction.LIST_ADMINS).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Настройка чата",
                callback_data=AdminCallback(action=AdminAction.CHAT_SETTINGS).pack(),
            ),
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

admins_list_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Добавить админа",
                callback_data=AdminCallback(action=AdminAction.ADD_ADMIN).pack(),
            ),
            InlineKeyboardButton(
                text="Удалить админа",
                callback_data=AdminCallback(action=AdminAction.REMOVE_ADMIN).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.HISTORY).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ],
    ]
)

chat_settings_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Установить чат",
                callback_data=AdminCallback(action=AdminAction.SET_CHAT_ID).pack(),
            ),
            InlineKeyboardButton(
                text="Очистить",
                callback_data=AdminCallback(action=AdminAction.CLEAR_CHAT_ID).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.HISTORY).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ],
    ]
)


output_settings_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Приветствие",
                callback_data=AdminCallback(action=AdminAction.EDIT_WELCOME).pack(),
            ),
            InlineKeyboardButton(
                text="Реквизиты",
                callback_data=AdminCallback(action=AdminAction.EDIT_PAYMENT_DETAILS).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Принятие оплаты",
                callback_data=AdminCallback(action=AdminAction.EDIT_PAYMENT_CONFIRMED).pack(),
            ),
            InlineKeyboardButton(
                text="Отказ",
                callback_data=AdminCallback(action=AdminAction.EDIT_SURVEY_REJECTED).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Правила чата",
                callback_data=AdminCallback(action=AdminAction.EDIT_CHAT_RULES).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Отправка анкеты",
                callback_data=AdminCallback(action=AdminAction.EDIT_SURVEY_SUBMITTED).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Промо: успех",
                callback_data=AdminCallback(action=AdminAction.EDIT_PROMO_APPLIED).pack(),
            ),
            InlineKeyboardButton(
                text="Промо: ошибка",
                callback_data=AdminCallback(action=AdminAction.EDIT_PROMO_INVALID).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Статус: нет анкеты",
                callback_data=AdminCallback(action=AdminAction.EDIT_STATUS_EMPTY).pack(),
            ),
            InlineKeyboardButton(
                text="Заголовок тарифов",
                callback_data=AdminCallback(action=AdminAction.EDIT_TARIFFS_HEADER).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Подписка: за 14 дней",
                callback_data=AdminCallback(
                    action=AdminAction.EDIT_SUBSCRIPTION_EXPIRING_SOON
                ).pack(),
            ),
            InlineKeyboardButton(
                text="Подписка: окончена",
                callback_data=AdminCallback(
                    action=AdminAction.EDIT_SUBSCRIPTION_EXPIRED
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.HISTORY).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ],
    ]
)


# Navigation keyboards for section screens (not for data entry prompts).
back_to_moderation_and_menu_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.MODERATION).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ]
    ]
)

back_to_review_surveys_and_menu_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.REVIEW_SURVEYS).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ]
    ]
)

back_to_pending_payments_and_menu_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.PENDING_PAYMENTS).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ]
    ]
)

back_to_statistics_and_menu_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.STATISTICS).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ]
    ]
)

back_to_super_admin_and_menu_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.HISTORY).pack(),
            ),
            InlineKeyboardButton(
                text="В меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            ),
        ]
    ]
)


back_to_main_inline_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Назад в меню",
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            )
        ]
    ]
)
