import asyncio
import html
import logging
import os
from datetime import datetime

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.db_components.models import BotMessageType
from src.db_components.survey_manager import (
    admin_manager,
    bot_message_manager,
    payment_manager,
)
from src.db_components.user_manager import user_manager
from src.user_components.user_callbacks import UserAction, UserCallback

logger = logging.getLogger(__name__)


def _parse_env_int(value: str | None) -> int | None:
    if not value:
        return None
    cleaned = value.strip().strip("\"'")
    try:
        return int(cleaned)
    except ValueError:
        return None


def _parse_env_int_set(value: str | None) -> set[int]:
    if not value:
        return set()
    result: set[int] = set()
    for part in value.split(","):
        parsed = _parse_env_int(part)
        if parsed is not None:
            result.add(parsed)
    return result


class SubscriptionNotifier:
    def __init__(self, days_before_end: int = 14, poll_interval_seconds: int = 3600):
        self.days_before_end = days_before_end
        self.poll_interval_seconds = poll_interval_seconds

    async def run(self, bot: Bot) -> None:
        while True:
            try:
                await self.process(bot)
            except Exception as exc:
                logger.exception("Subscription notifier cycle failed: %s", exc)
            await asyncio.sleep(self.poll_interval_seconds)

    async def process(self, bot: Bot) -> None:
        await self._send_renewal_reminders(bot)
        await self._expire_and_notify(bot)

    async def _send_renewal_reminders(self, bot: Bot) -> None:
        subs = await payment_manager.get_subscriptions_for_renewal_reminder(
            self.days_before_end
        )
        if not subs:
            return

        msg = await bot_message_manager.get_message(BotMessageType.SUBSCRIPTION_EXPIRING_SOON)
        template = (
            msg.content
            if msg
            else (
                "Ваша подписка заканчивается {end_date}. До окончания осталось {days_left} дн.\n\n"
                "Чтобы продлить доступ, свяжитесь с администратором."
            )
        )

        now = datetime.utcnow()
        for sub in subs:
            days_left = max(0, (sub.end_date.date() - now.date()).days)
            text = (
                template.replace("{end_date}", sub.end_date.strftime("%d.%m.%Y"))
                .replace("{days_left}", str(days_left))
                .replace("{days}", str(days_left))
            )
            try:
                await bot.send_message(chat_id=sub.user_id, text=text)
                await self._send_renewal_plans_message(bot, sub.user_id)
                await payment_manager.mark_renewal_reminder_sent(sub.id)
            except Exception as exc:
                logger.error(
                    "Failed to send renewal reminder to %s for subscription %s: %s",
                    sub.user_id,
                    sub.id,
                    exc,
                )

    async def _expire_and_notify(self, bot: Bot) -> None:
        subs = await payment_manager.get_expired_active_subscriptions()
        if not subs:
            return

        expired_msg = await bot_message_manager.get_message(BotMessageType.SUBSCRIPTION_EXPIRED)
        expired_text = (
            expired_msg.content
            if expired_msg
            else (
                "Срок вашей подписки истек.\n\n"
                "Чтобы восстановить доступ, оформите продление у администратора."
            )
        )
        admin_recipients = await self._get_admin_recipients()

        for sub in subs:
            await payment_manager.mark_subscription_expired(sub.id)
            try:
                await bot.send_message(chat_id=sub.user_id, text=expired_text)
                await self._send_renewal_plans_message(bot, sub.user_id)
            except Exception as exc:
                logger.error(
                    "Failed to send subscription-expired message to %s: %s",
                    sub.user_id,
                    exc,
                )

            kick_results = await self._remove_user_from_target_chats(bot, sub.user_id)

            user_label = await self._user_label(sub.user_id)
            admin_text = (
                "<b>Подписка завершена</b>\n\n"
                f"Пользователь: {user_label}\n"
                f"Дата окончания: <b>{sub.end_date.strftime('%d.%m.%Y')}</b>\n"
                f"Удаление из беседы: {kick_results}"
            )
            for admin_id in admin_recipients:
                try:
                    await bot.send_message(chat_id=admin_id, text=admin_text)
                except Exception as exc:
                    logger.error(
                        "Failed to send admin expiration alert to %s (sub %s): %s",
                        admin_id,
                        sub.id,
                        exc,
                    )

    async def _send_renewal_plans_message(self, bot: Bot, user_id: int) -> None:
        plans = await payment_manager.get_payment_plans()
        if not plans:
            return

        header_msg = await bot_message_manager.get_message(BotMessageType.TARIFFS_HEADER)
        header = header_msg.content if header_msg else "<b>Доступные тарифы</b>"
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=f"{plan.name} ({plan.price:.2f} ₽ / {plan.duration_days} дн.)",
                        callback_data=UserCallback(
                            action=UserAction.RENEW_SUBSCRIPTION_SELECT_PLAN,
                            plan_id=plan.id,
                        ).pack(),
                    )
                ]
                for plan in plans
            ]
        )
        await bot.send_message(
            chat_id=user_id,
            text=f"{header}\n\nВыберите тариф для продления подписки:",
            reply_markup=kb,
        )

    async def _get_admin_recipients(self) -> set[int]:
        recipients: set[int] = set()
        admin_id = _parse_env_int(os.getenv("ADMIN_ID"))
        if admin_id is not None:
            recipients.add(admin_id)

        legacy_super = _parse_env_int(os.getenv("SUPER_ADMIN_ID"))
        if legacy_super is not None:
            recipients.add(legacy_super)

        recipients.update(_parse_env_int_set(os.getenv("SUPER_ADMIN_IDS")))

        db_admins = await admin_manager.get_all_admins()
        recipients.update(admin.id for admin in db_admins)
        return recipients

    async def _user_label(self, user_id: int) -> str:
        user = await user_manager.get_user(user_id)
        if user and user.username:
            return f"@{html.escape(user.username)}"
        name = "Профиль"
        if user and user.first_name:
            name = html.escape(user.first_name)
        return f'<a href="tg://user?id={user_id}">{name}</a>'

    def _get_target_chat_ids(self) -> set[int]:
        chat_ids: set[int] = set()
        single_chat_id = _parse_env_int(os.getenv("GROUP_CHAT_ID"))
        if single_chat_id is not None:
            chat_ids.add(single_chat_id)
        chat_ids.update(_parse_env_int_set(os.getenv("GROUP_CHAT_IDS")))
        return chat_ids

    async def _remove_user_from_target_chats(self, bot: Bot, user_id: int) -> str:
        chat_ids = self._get_target_chat_ids()
        if not chat_ids:
            return "не настроен (GROUP_CHAT_ID/GROUP_CHAT_IDS)"

        ok_count = 0
        error_count = 0
        for chat_id in sorted(chat_ids):
            try:
                # Soft-kick: remove user now, but allow rejoin later.
                await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                await bot.unban_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    only_if_banned=True,
                )
                ok_count += 1
            except Exception as exc:
                logger.error(
                    "Failed to remove user %s from chat %s: %s",
                    user_id,
                    chat_id,
                    exc,
                )
                error_count += 1

        if error_count == 0:
            return "успешно"
        if ok_count == 0:
            return "ошибка"
        return f"частично (успешно: {ok_count}, ошибок: {error_count})"
