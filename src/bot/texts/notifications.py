"""
Тексты уведомлений для бота Hydrolat Club.
"""
from datetime import datetime


def get_approval_message() -> str:
    """Сообщение об одобрении анкеты."""
    current_date = datetime.now().strftime("%d.%m.%Y")
    
    return f"""
    🎉 *Поздравляем! Ваша анкета одобрена!*

    ✅ Вы прошли модерацию и теперь можете стать членом Hydrolat Club.

    💳 *Для завершения регистрации оплатите вступительный взнос:*

    *Реквизиты для оплаты:*
    📌 Банк: Тинькофф
    📌 Номер карты: `2200 7001 2345 6789`
    📌 Получатель: Иванов Иван Иванович
    📌 Сумма: 5 000 руб.
    📌 Назначение: "Вступительный взнос Hydrolat Club"

    *Или перейдите по ссылке для быстрой оплаты:*
    🔗 https://pay.hydrolat-club.ru/join

    ⚠️ *Важно:*
    • После оплаты пришлите скриншот чека @admin_hydrolat
    • В течение 24 часов вас добавят в закрытый чат
    • Ссылка действительна до: {current_date}

    📞 Вопросы? Пишите: @hydrolat_support

    *Добро пожаловать в клуб!* 🎊
    """


def get_rejection_message() -> str:
    """Сообщение об отклонении анкеты."""
    return """
    ❌ К сожалению, ваша анкета была отклонена.

    Возможные причины:
    • Неполная или неточная информация
    • Несоответствие требованиям клуба
    • Технические проблемы с анкетой

    🔄 Вы можете подать новую анкету через 30 дней.

    📞 Если у вас есть вопросы, обратитесь к администратору: @admin_hydrolat

    С уважением,
    Команда Hydrolat Club
    """


def get_admin_notification(user_telegram_id: int, user_name: str, action: str, questionnaire_id: int) -> str:
    """Уведомление для администратора после действия."""
    if action == "approved":
        emoji = "✅"
        action_text = "одобрена"
    else:
        emoji = "❌"
        action_text = "отклонена"
    
    time_str = datetime.now().strftime("%H:%M:%S")
    
    return f"""
{emoji} *Анкета #{questionnaire_id} {action_text}*

👤 Пользователь: {user_name}
🆔 ID: {user_telegram_id}
⏰ Время: {time_str}

✅ Пользователь получил уведомление.
"""