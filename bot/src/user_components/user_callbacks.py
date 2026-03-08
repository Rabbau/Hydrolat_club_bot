from aiogram.filters.callback_data import CallbackData
from enum import StrEnum

class UserAction(StrEnum):
    FILL_SURVEY = 'fill_survey'
    YES_NO_ANSWER = 'yes_no'
    RENEW_SUBSCRIPTION_SELECT_PLAN = "renew_subscription_select_plan"
    APPROVED_SURVEY_SELECT_PLAN = "approved_survey_select_plan"
    APPROVED_SURVEY_SKIP_PROMO = "approved_survey_skip_promo"
    APPROVED_SURVEY_PAY = "approved_survey_pay"

class UserCallback(CallbackData, prefix="user"):
    action: UserAction
    value: str | None = None
    plan_id: int | None = None
