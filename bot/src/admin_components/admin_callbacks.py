from aiogram.filters.callback_data import CallbackData
from enum import StrEnum

class AdminAction(StrEnum):
    SURVEY_MENU = "survey_menu"
    MODERATION = "moderation"
    HISTORY = "history"
    STATISTICS = "statistics"
    STATS_USERS = "stats_users"
    STATS_PENDING_REVIEW = "stats_pending_review"
    STATS_PENDING_PAYMENT = "stats_pending_payment"
    STATS_PAID = "stats_paid"
    STATS_REJECTED = "stats_rejected"
    STATS_ACTIVE_SUBS = "stats_active_subs"
    OUTPUT_SETTINGS = "output_settings"
    SURVEY_BACK = "back"

    # Модерация анкет и оплат
    REVIEW_SURVEYS = "review_surveys"
    PENDING_PAYMENTS = "pending_payments"
    REVIEW_SURVEY_DETAIL = "review_survey_detail"
    APPROVE_SURVEY = "approve_survey"
    APPROVE_SURVEY_WITH_DISCOUNT = "approve_survey_discount"
    REJECT_SURVEY = "reject_survey"
    CONFIRM_PAYMENT = "confirm_payment"
    PENDING_PAYMENT_DETAIL = "pending_payment_detail"
    CONFIRM_TARIFF = "confirm_tariff"
    CHANGE_TARIFF = "change_tariff"
    SET_TARIFF = "set_tariff"
    REMIND_SELECT_TARIFF = "remind_select_tariff"

    # Действия супер-админа (редактирование сообщений и тарифов/админов)
    EDIT_WELCOME = "edit_welcome"
    EDIT_SURVEY_SUBMITTED = "edit_survey_submitted"
    EDIT_PAYMENT_DETAILS = "edit_payment_details"
    EDIT_CHAT_RULES = "edit_chat_rules"
    EDIT_PAYMENT_CONFIRMED = "edit_payment_confirmed"
    EDIT_SURVEY_REJECTED = "edit_survey_rejected"
    EDIT_STATUS_EMPTY = "edit_status_empty"
    EDIT_PROMO_APPLIED = "edit_promo_applied"
    EDIT_PROMO_INVALID = "edit_promo_invalid"
    EDIT_TARIFFS_HEADER = "edit_tariffs_header"
    EDIT_SUBSCRIPTION_EXPIRING_SOON = "edit_subscription_expiring_soon"
    EDIT_SUBSCRIPTION_EXPIRED = "edit_subscription_expired"
    CREATE_PROMO = "create_promo"
    LIST_PROMOS = "list_promos"
    DELETE_PROMO = "delete_promo"
    CREATE_PLAN = "create_plan"
    LIST_PLANS = "list_plans"
    DELETE_PLAN = "delete_plan"
    ADD_ADMIN = "add_admin"
    LIST_ADMINS = "list_admins"
    REMOVE_ADMIN = "remove_admin"
    CHAT_SETTINGS = "chat_settings"
    SET_CHAT_ID = "set_chat_id"
    CLEAR_CHAT_ID = "clear_chat_id"

class AdminCallback(CallbackData, prefix="admin"):
    action: AdminAction
    survey_id: int | None = None
    user_id: int | None = None
    plan_id: int | None = None
    promo_code_id: int | None = None
