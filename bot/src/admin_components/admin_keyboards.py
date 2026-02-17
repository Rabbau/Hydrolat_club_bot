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
            )
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
                text="Список админов",
                callback_data=AdminCallback(action=AdminAction.LIST_ADMINS).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="Создать промокод",
                callback_data=AdminCallback(action=AdminAction.CREATE_PROMO).pack(),
            )
        ],
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
                callback_data=AdminCallback(action=AdminAction.SURVEY_BACK).pack(),
            )
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
                text="Назад",
                callback_data=AdminCallback(action=AdminAction.HISTORY).pack(),
            )
        ],
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
