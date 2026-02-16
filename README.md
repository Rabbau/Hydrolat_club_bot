# 🎯 Дискуссионный клуб по гидролатам - Telegram бот

Полнофункциональный Telegram бот для управления закрытым платным дискуссионным клубом по гидролатам с системой анкет, модерации, платежей и администраторов.

## ✨ Основные возможности

### 👤 Для пользователей
- ✅ Заполнение анкеты с несколькими типами вопросов
- ✅ Проверка статуса своей анкеты
- ✅ Получение реквизитов при одобрении
- ✅ Использование промокодов для скидок
- ✅ Управление подписками

### 👨‍💼 Для администраторов
- ✅ Просмотр и модерация анкет (одобрение/отклонение)
- ✅ Подтверждение платежей
- ✅ Выставление персональных скидок
- ✅ Редактирование вопросов анкеты (survey.json)
- ✅ История всех решений

### 🔴 Для супер-администраторов
- ✅ Все права администратора +
- ✅ Управление администраторами (добавление/удаление)
- ✅ Редактирование сообщений бота (4 шаблона)
- ✅ Управление тарифными планами
- ✅ Управление промокодами (групповые и личные)
- ✅ Контроль всех параметров системы

## 🏗️ Архитектура

```
tg_bot/
├── bot/
│   ├── main.py                          # Главный файл бота
│   ├── src/
│   │   ├── admin_components/            # Компоненты для администраторов
│   │   │   ├── admin_router.py          # Основные маршруты админа
│   │   │   ├── admin_filter.py          # Фильтры доступа
│   │   │   ├── admin_callbacks.py       # Callback действия
│   │   │   ├── admin_keyboards.py       # Клавиатуры админа
│   │   │   ├── admin_utils.py           # Утилиты отображения
│   │   │   └── moderation_router.py     # Маршруты модерации
│   │   │
│   │   ├── user_components/             # Компоненты для пользователей
│   │   │   ├── user_router.py           # Маршруты пользователя
│   │   │   ├── user_states.py           # FSM состояния
│   │   │   ├── user_callbacks.py        # Callback действия
│   │   │   └── user_keyboard.py         # Клавиатуры пользователя
│   │   │
│   │   ├── db_components/               # Компоненты БД
│   │   │   ├── models.py                # SQLAlchemy модели
│   │   │   ├── database.py              # Конфиг БД
│   │   │   ├── survey_manager.py        # 5 менеджеров для работы с БД
│   │   │   ├── user_manager.py          # Управление пользователями
│   │   │   └── db_middleware.py         # Middleware для БД
│   │   │
│   │   ├── FormManager/                 # Управление анкетой
│   │   │   ├── FormManager.py           # Основной класс
│   │   │   └── form_middleware.py       # Middleware для форм
│   │   │
│   │   └── survey.json                  # Вопросы анкеты
│   │
│   └── alembic/                         # Миграции БД
│       ├── versions/
│       │   ├── 001_initial.py
│       │   └── 2_add_payment_survey_tables.py
│       ├── env.py
│       ├── script.py.mako
│       └── alembic.ini
│
├── SETUP.md                             # Инструкция по запуску
├── README.md                            # Этот файл
└── requirements.txt                     # Зависимости проекта
```

## 📊 Модели БД

### Основные таблицы
- **users** - пользователи системы
- **user_answers** - ответы на вопросы анкеты (архивные)
- **survey_submissions** - сами анкеты с статусами и результатами
- **payment_plans** - тарифные планы (ежемесячно, полугодие, год и т.д.)
- **subscriptions** - активные подписки пользователей
- **promo_codes** - промокоды (групповые и личные с лимитом использований)
- **admin_users** - администраторы системы с разделением на уровни
- **bot_messages** - управляемые сообщения (приветствие, реквизиты, подтверждения)

### Статусы анкеты
1. **PENDING_REVIEW** - ожидает рассмотрения администратором
2. **APPROVED** - одобрена, ждет оплаты
3. **PENDING_PAYMENT** - оплата ожидается подтверждения админом
4. **PAID** - оплачена, доступ предоставлен
5. **REJECTED** - отклонена с комментарием

## 🔄 Поток взаимодействия

```
ПОЛЬЗОВАТЕЛЬ:
1. /start → показ приветствия
2. "Заполнить анкету" → заполнение вопросов
3. Отправка анкеты → статус PENDING_REVIEW
4. ⏳ Ожидание решения админа

АДМИНИСТРАТОР:
5. Просмотр анкет на проверку
6. Одобрение/отклонение
   - Если отклонено → REJECTED + уведомление
   - Если одобрено → APPROVED + статус PENDING_PAYMENT

ПОЛЬЗОВАТЕЛЬ (если одобрено):
7. Получает реквизиты оплаты
8. Оплачивает по реквизитам
9. ⏳ Ожидание подтверждения оплаты

АДМИНИСТРАТОР:
10. Видит платеж
11. Подтверждает оплату

ПОЛЬЗОВАТЕЛЬ:
12. Статус → PAID
13. Получает подтверждение
14. 🎉 Доступ в клуб!
```

## 🛠️ Технологический стек

- **Framework:** aiogram 3.x (Telegram Bot API)
- **Database:** PostgreSQL 12+ с asyncpg
- **ORM:** SQLAlchemy 2.0 (async)
- **Миграции:** Alembic
- **Python:** 3.10+

## 🚀 Быстрый старт

### Предварительные требования
```bash
# Создание виртуального окружения
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Установка зависимостей
pip install -r requirements.txt
```

### Настройка .env
```env
BOT_TOKEN=ваш_токен_от_BotFather
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/gidrolat
```

### Запуск
```bash
cd bot
python -m alembic upgrade head
python main.py
```

Подробная инструкция в [SETUP.md](SETUP.md)

## 📝 API Менеджеров

### SurveyManager
```python
await survey_manager.submit_survey(user_id, answers)
await survey_manager.get_survey(user_id)
await survey_manager.get_surveys_by_status(status)
await survey_manager.approve_survey(survey_id, admin_id, discount)
await survey_manager.reject_survey(survey_id, admin_id, comment)
```

### PaymentManager
```python
await payment_manager.create_payment_plan(name, duration_days, price)
await payment_manager.get_payment_plans()
await payment_manager.create_subscription(user_id, plan_id)
await payment_manager.get_user_subscription(user_id)
```

### PromoCodeManager
```python
await promo_code_manager.create_promo_code(code, discount_percent)
await promo_code_manager.validate_promo_code(code, user_id)
await promo_code_manager.use_promo_code(code)
```

### AdminManager
```python
await admin_manager.add_admin(admin_id, is_super_admin=False)
await admin_manager.is_admin(user_id)
await admin_manager.is_super_admin(user_id)
await admin_manager.remove_admin(admin_id)
```

### BotMessageManager
```python
await bot_message_manager.get_message(message_type)
await bot_message_manager.init_default_messages()
await bot_message_manager.update_message(message_type, content)
```

## 🔐 Система прав доступа

### Фильтры
- **AdminFilter** - пользователь является администратором
- **SuperAdminFilter** - пользователь супер-администратор

### Уровни доступа
```
Обычный пользователь
├─ Заполнение анкеты
├─ Проверка статуса
└─ Использование промокодов

Администратор
├─ Все права обычного пользователя +
├─ Модерация анкет
├─ Подтверждение платежей
├─ Редактирование вопросов анкеты
└─ История решений

Супер-администратор
├─ Все права администратора +
├─ Управление администраторами
├─ Редактирование сообщений
├─ Управление тарифами
├─ Управление промокодами
└─ Полный контроль
```

## 📌 Типы вопросов в анкете

### Поддерживаемые типы (survey.json)
1. **yes_no** - вопрос да/нет
2. **text** - текстовый ответ
3. **multiple_choice** - выбор из нескольких вариантов
4. **rating** - оценка по шкале

## 💬 Управляемые сообщения

Четыре ключевых сообщения редактируются супер-администратором:

1. **WELCOME** - приветствие при /start
2. **PAYMENT_DETAILS** - реквизиты оплаты
3. **PAYMENT_CONFIRMED** - подтверждение оплаты
4. **SURVEY_REJECTED** - отклонение анкеты

## 🎟️ Система промокодов

### Типы промокодов
- **Коллективные** - может использовать любой (SUMMER2024, PROMO100)
- **Личные** - только для конкретного пользователя

### Параметры
- Скидка в процентах (1-99%)
- Лимит использований (опционально)
- Статус активности

## 📈 Тарифные планы

### Пример планов
```
Ежемесячно - 30 дней - 500 руб
Квартал - 90 дней - 1200 руб
Полугодие - 180 дней - 2200 руб
Год - 365 дней - 3800 руб
```

Могут быть изменены в любой момент супер-администратором.

## 🧪 Тестирование

### Проверка основного потока
```bash
# 1. Запустить бота
python main.py

# 2. Написать боту /start
# 3. Нажать "Заполнить анкету"
# 4. Ответить на все вопросы
# 5. Проверить анкету в БД

# 6. От админа: /start
# 7. Модерация → Проверить анкеты
# 8. Одобрить анкету
# 9. Пользователь получит реквизиты
# 10. Администратор → Подтверждение платежа
```

## 📚 Документация

- [SETUP.md](SETUP.md) - полная инструкция по установке и запуску
- [ТЗ (Техническое задание)](TZ.md) - полные требования проекта
- Код содержит docstring для каждого метода и класса

## 🐛 Известные ограничения и улучшения

### Текущие ограничения
- ❌ Нет интеграции с платежными системами (только реквизиты)
- ❌ Нет отправки уведомлений при смене статуса
- ❌ Нет системы рефералов
- ❌ Нет рассылок для пользователей

### Планируемые улучшения
- 🔜 Автоматическая интеграция с Яндекс Касса
- 🔜 Push-уведомления на изменение статуса
- 🔜 Система рефералов с бонусами
- 🔜 Периодические рассылки подписчикам
- 🔜 Экспорт отчетов в PDF/Excel
- 🔜 Веб-панель администратора
- 🔜 Analytics и статистика

## 🤝 Разработка

### Добавление нового менеджера БД

```python
# В survey_manager.py
class NewManager:
    async def method_name(self, param):
        async with get_db_session() as session:
            # ваш код
            await session.commit()
            return result

# Экспортируем
new_manager = NewManager()
```

### Добавление нового маршрута

```python
# В new_router.py
from aiogram import Router
router = Router()

@router.message(CommandStart())
async def handler(message: Message):
    await message.answer("Hello!")

# Включаем в main.py
dp.include_router(router)
```

## 📞 Поддержка и контакты

По вопросам:
- Запуска и настройки → см. [SETUP.md](SETUP.md)
- Разработки → см. комментарии в коде
- Использования → см. документацию в docstring

## 📄 Лицензия

Проект разработан для дискуссионного клуба по гидролатам.

---

**Версия:** 1.0.0  
**Дата:** Февраль 2024  
**Статус:** ✅ Готов к запуску в production
