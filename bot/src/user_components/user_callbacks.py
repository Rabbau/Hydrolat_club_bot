from aiogram.filters.callback_data import CallbackData
from enum import StrEnum

class UserAction(StrEnum):
    FILL_SURVEY = 'fill_survey'
    YES_NO_ANSWER = 'yes_no'
    RENEW_SUBSCRIPTION_SELECT_PLAN = "renew_subscription_select_plan"
    APPROVED_SURVEY_SELECT_PLAN = "approved_survey_select_plan"

class UserCallback(CallbackData, prefix="user"):
    action: UserAction
    value: str | None = None
    plan_id: int | None = None
