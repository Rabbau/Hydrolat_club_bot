from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.admin_components.admin_callbacks import AdminCallback, AdminAction


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
                text="Настройки бота",
                callback_data=AdminCallback(action=AdminAction.HISTORY).pack(),
            )
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
                callback_data=AdminCallback(
                    action=AdminAction.PENDING_PAYMENTS
                ).pack(),
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
                text="👋 Приветствие",
                callback_data=AdminCallback(
                    action=AdminAction.EDIT_WELCOME
                ).pack(),
            ),
            InlineKeyboardButton(
                text="💳 Реквизиты",
                callback_data=AdminCallback(
                    action=AdminAction.EDIT_PAYMENT_DETAILS
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="✅ Сообщение об оплате",
                callback_data=AdminCallback(
                    action=AdminAction.EDIT_PAYMENT_CONFIRMED
                ).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Сообщение об отказе",
                callback_data=AdminCallback(
                    action=AdminAction.EDIT_SURVEY_REJECTED
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="👥 Список админов",
                callback_data=AdminCallback(
                    action=AdminAction.LIST_ADMINS
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="➕ Добавить админа",
                callback_data=AdminCallback(
                    action=AdminAction.ADD_ADMIN
                ).pack(),
            ),
            InlineKeyboardButton(
                text="➖ Удалить админа",
                callback_data=AdminCallback(
                    action=AdminAction.REMOVE_ADMIN
                ).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=AdminCallback(
                    action=AdminAction.SURVEY_BACK
                ).pack(),
            )
        ],
    ]
)
