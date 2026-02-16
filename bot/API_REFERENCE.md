# 🎯 Чек-лист запуска и справка по API

## ✅ Чек-лист перед запуском

### Предварительная подготовка
- [ ] Создан Telegram бот через @BotFather
- [ ] Получен BOT_TOKEN
- [ ] Установлена Python 3.10+
- [ ] Клонирован репозиторий

### Установка окружения
- [ ] `pip install -r requirements.txt` выполнен без ошибок
- [ ] Создан файл `.env` с переменными:
  - [ ] BOT_TOKEN
  - [ ] DATABASE_URL (или оставлена SQLite по умолчанию)
- [ ] Проверена БД (доступность хоста, порта, учётных данных)

### Инициализация
- [ ] `python main.py` запущен (создаёт таблицы автоматически)
- [ ] Создан первый администратор: `python -m src.db_components.init_admin <ID> true`
- [ ] Созданы платежные планы: `python -m src.db_components.init_payment_plans`

### Тестирование
- [ ] Написана команда `/start` от обычного пользователя
  - [ ] Видно приветствие
  - [ ] Работает кнопка "Заполнить анкету"
- [ ] Написана команда `/start` от администратора
  - [ ] Видна админ-панель
  - [ ] Видны кнопки модерации, платежей и т.д.
- [ ] Пройдена анкета пользователем (1-2 вопроса)
  - [ ] Ответы сохранились в БД
  - [ ] Статус изменился на "pending_review"
- [ ] Администратор может одобрить/отклонить анкету
  - [ ] Пользователь видит статус "одобрена"
- [ ] Администратор может подтвердить платёж
  - [ ] Создаётся подписка
  - [ ] Пользователь видит "доступ получен"

---

## 📚 API справка по менеджерам

### UserManager
```python
from src.db_components.user_manager import user_manager

# Добавить пользователя
await user_manager.add_user(user_id, username, first_name, last_name)

# Получить пользователя
user = await user_manager.get_user(user_id)

# Добавить ответ на вопрос
await user_manager.add_answer(user_id, question_id, answer)

# Получить все ответы
answers = await user_manager.get_answers(user_id)

# Получить конкретный ответ
answer = await user_manager.get_answer(user_id, question_id)

# Очистить все ответы
await user_manager.clear_answers(user_id)

# Проверить существование
exists = await user_manager.user_exists(user_id)

# Получить количество пользователей
count = await user_manager.get_users_count()
```

### SurveyManager
```python
from src.db_components.survey_manager import survey_manager

# Отправить анкету на проверку
await survey_manager.submit_survey(user_id, answers_dict)

# Получить анкету пользователя
survey = await survey_manager.get_survey(user_id)

# Получить все анкеты по статусу
surveys = await survey_manager.get_surveys_by_status(SurveyStatusEnum.PENDING_REVIEW)

# Одобрить анкету
await survey_manager.approve_survey(user_id, admin_id, comment=None)

# Отклонить анкету
await survey_manager.reject_survey(user_id, admin_id, "Причина отклонения")

# Установить статус "ожидание оплаты"
await survey_manager.set_survey_awaiting_payment(user_id)

# Установить статус "оплачена"
await survey_manager.set_survey_paid(user_id)
```

### PaymentManager
```python
from src.db_components.survey_manager import payment_manager

# Получить все активные планы
plans = await payment_manager.get_payment_plans()

# Получить план по ID
plan = await payment_manager.get_payment_plan(plan_id)

# Создать новый план
await payment_manager.create_payment_plan("Месячный", 30, 990.00, "Описание")

# Обновить план
await payment_manager.update_payment_plan(plan_id, name="Новое имя", price=1090.00)

# Удалить план (деактивировать)
await payment_manager.delete_payment_plan(plan_id)

# Создать подписку
subscription = await payment_manager.create_subscription(user_id, plan_id, price_paid)

# Получить подписку пользователя
sub = await payment_manager.get_user_subscription(user_id)

# Проверить, активна ли подписка
is_subscribed = await payment_manager.is_user_subscribed(user_id)

# Обновить статус подписки
await payment_manager.update_subscription_status(subscription_id, SubscriptionStatusEnum.EXPIRED)
```

### PromoCodeManager
```python
from src.db_components.survey_manager import promo_code_manager

# Получить промокод
promo = await promo_code_manager.get_promo_code("HYDROLAT50")

# Проверить валидность промокода
result = await promo_code_manager.validate_promo_code("HYDROLAT50", user_id)
# result = {"valid": True/False, "discount_percent": 10, "promo_id": 1}

# Создать промокод
await promo_code_manager.create_promo_code(
    code="HYDROLAT50",
    discount_percent=50,
    is_collective=True,
    max_uses=100
)

# Использовать промокод (увеличить счётчик)
await promo_code_manager.use_promo_code(promo_id)

# Получить все промокоды
promos = await promo_code_manager.get_all_promo_codes()

# Удалить промокод
await promo_code_manager.delete_promo_code("HYDROLAT50")
```

### AdminManager
```python
from src.db_components.survey_manager import admin_manager

# Получить администратора
admin = await admin_manager.get_admin(admin_id)

# Добавить администратора
await admin_manager.add_admin(admin_id, username, first_name, is_super_admin=False)

# Удалить администратора
await admin_manager.remove_admin(admin_id)

# Проверить, является ли администратором
is_admin = await admin_manager.is_admin(user_id)

# Проверить, является ли супер-администратором
is_super = await admin_manager.is_super_admin(user_id)

# Получить всех администраторов
admins = await admin_manager.get_all_admins()

# Повысить до супер-администратора
await admin_manager.promote_to_super_admin(admin_id)
```

---

## 🔄 Статусы и Enum'ы

### SurveyStatusEnum
```python
from src.db_components.models import SurveyStatusEnum

SurveyStatusEnum.PENDING_REVIEW   # Ожидает проверки
SurveyStatusEnum.APPROVED          # Одобрена
SurveyStatusEnum.REJECTED          # Отклонена
SurveyStatusEnum.PENDING_PAYMENT   # Ожидание оплаты
SurveyStatusEnum.PAID              # Оплачена
```

### SubscriptionStatusEnum
```python
from src.db_components.models import SubscriptionStatusEnum

SubscriptionStatusEnum.ACTIVE      # Активна
SubscriptionStatusEnum.EXPIRED     # Истекла
SubscriptionStatusEnum.CANCELLED   # Отменена
```

---

## 🎨 Примеры использования в роутерах

### Пример: Одобрение анкеты
```python
@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.APPROVE_SURVEY))
async def approve_survey(callback: CallbackQuery, callback_data: AdminCallback):
    user_id = callback_data.user_id
    
    # Одобрить анкету
    success = await survey_manager.approve_survey(
        user_id=user_id,
        admin_id=callback.from_user.id
    )
    
    if success:
        # Установить статус "ожидание оплаты"
        await survey_manager.set_survey_awaiting_payment(user_id)
        
        await callback.message.edit_text(
            "✅ Анкета одобрена! Отправляем реквизиты пользователю..."
        )
        
        # TODO: Отправить реквизиты пользователю
        # await bot.send_message(user_id, "Реквизиты: ...")
```

### Пример: Подтверждение платежа
```python
@admin_router.callback_query(AdminCallback.filter(F.action == AdminAction.CONFIRM_PAYMENT))
async def confirm_payment(callback: CallbackQuery, callback_data: AdminCallback):
    user_id = callback_data.user_id
    
    # Получить план (берём первый активный)
    plans = await payment_manager.get_payment_plans()
    plan = plans[0]
    
    # Создать подписку
    subscription = await payment_manager.create_subscription(
        user_id=user_id,
        plan_id=plan.id,
        price_paid=float(plan.price)
    )
    
    if subscription:
        # Отметить анкету как оплаченную
        await survey_manager.set_survey_paid(user_id)
        
        await callback.message.edit_text(
            f"✅ Платёж подтвержден! Создана подписка '{plan.name}'"
        )
```

### Пример: Создание промокода (супер-админ)
```python
@super_admin_router.message(SomeState)
async def create_promo(message: Message):
    code = message.text.upper()
    
    # Создать коллективный промокод
    success = await promo_code_manager.create_promo_code(
        code=code,
        discount_percent=20,
        is_collective=True,
        max_uses=50
    )
    
    if success:
        await message.answer(f"✅ Промокод '{code}' создан с скидкой 20%")
```

---

## 📊 Структура FSM для аутентификации

```python
from aiogram.fsm.state import State, StatesGroup

class ModerationFSM(StatesGroup):
    reviewing_survey = State()          # Просмотр анкеты
    rejecting_survey = State()          # Ввод причины отклонения
    confirm_payment = State()           # Подтверждение платежа
    creating_promo = State()            # Создание промокода
    adding_admin = State()              # Добавление администратора
```

---

## 🔍 Useful SQL Queries

```sql
-- Найти всех пользователей со статусом "pending_review"
SELECT u.id, u.first_name, ss.created_at 
FROM users u 
JOIN survey_submissions ss ON u.id = ss.user_id 
WHERE ss.status = 'pending_review'
ORDER BY ss.created_at DESC;

-- Найти пользователя и его статус подписки
SELECT u.id, u.first_name, s.status, s.end_date 
FROM users u 
LEFT JOIN subscriptions s ON u.id = s.user_id 
WHERE u.id = 123456789;

-- Статистика по платежам за месяц
SELECT 
    DATE_TRUNC('day', s.created_at) as date,
    COUNT(*) as payments_count,
    SUM(s.price_paid) as total_revenue
FROM subscriptions s
WHERE DATE_TRUNC('month', s.created_at) = DATE_TRUNC('month', CURRENT_DATE)
GROUP BY DATE_TRUNC('day', s.created_at)
ORDER BY date;

-- Использованные промокоды
SELECT pc.code, pc.discount_percent, COUNT(pu.id) as used_count
FROM promo_codes pc
LEFT JOIN subscriptions s ON pc.id = ANY(string_to_array(s.payment_confirmation, ','))
GROUP BY pc.id
ORDER BY used_count DESC;
```

---

## 🚨 Возможные ошибки и решения

### "No such table: users"
**Решение:** Бот не создал таблицы. Запустите `python main.py` перед другими командами.

### "AdminFilter() returned False"
**Решение:** Пользователь не администратор. Создайте админа: `python -m src.db_components.init_admin <ID> true`

### "AttributeError: 'NoneType' object has no attribute 'status'"
**Решение:** Анкета не существует. Проверьте, что пользователь заполнил анкету: `await survey_manager.get_survey(user_id)`

### "Foreign key constraint failed"
**Решение:** Проверьте, что referenced объект существует (например, план существует перед созданием подписки)

### "Duplicate entry for key 'code'"
**Решение:** Промокод с таким кодом уже существует. Используйте другой код.

---

**Готово к разработке! 🎉**
