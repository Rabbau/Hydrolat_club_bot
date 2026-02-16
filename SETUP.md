# 🚀 ИНСТРУКЦИЯ ПО ЗАПУСКУ ПРОЕКТА

## 📋 Требования

- Python 3.10+
- PostgreSQL 12+
- pip и virtualenv

## 1️⃣ Установка зависимостей

```bash
# Создаем виртуальное окружение
python -m venv venv

# Активируем (Windows)
venv\Scripts\activate

# Активируем (Linux/Mac)
source venv/bin/activate

# Установляем зависимости
pip install -r requirements.txt
```

## 2️⃣ Настройка переменных окружения

Создайте файл `.env` в корне проекта:

```env
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/gidrolat
ADMIN_IDS=123456789,987654321
```

### Где взять BOT_TOKEN?
1. Напишите боту @BotFather в Telegram
2. Выполните команду `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный token

## 3️⃣ Подготовка БД

### Вариант 1: Docker (рекомендуется)

```bash
# Запустить PostgreSQL контейнер
docker-compose up -d

# Или вручную
docker run --name gidrolat_db \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=gidrolat \
  -p 5432:5432 \
  -d postgres:15
```

### Вариант 2: Локальная PostgreSQL

Убедитесь, что PostgreSQL запущена и доступна по адресу из `.env`

## 4️⃣ Применение миграций

```bash
# Переходим в папку bot
cd bot

# Применяем все миграции
python -m alembic upgrade head
```

## 5️⃣ Запуск бота

```bash
# Из папки bot
python main.py
```

Если всё работает, вы должны увидеть:
```
🚀 Starting bot...
📊 Applying database migrations...
✅ Database migrations applied
💬 Initializing bot messages...
✅ Bot messages initialized
🤖 Bot is starting polling...
```

## ⚙️ Добавление администраторов

После первого запуска, добавьте администраторов в БД. Используйте PostgreSQL клиент:

```sql
-- Добавить обычного администратора
INSERT INTO admin_users (id, username, first_name, is_super_admin, created_at, updated_at)
VALUES (YOUR_ID, 'username', 'Name', false, now(), now());

-- Добавить супер-администратора
INSERT INTO admin_users (id, username, first_name, is_super_admin, created_at, updated_at)
VALUES (YOUR_ID, 'username', 'Name', true, now(), now());
```

Или через код в Python:

```python
import asyncio
from src.db_components.survey_manager import admin_manager

async def add_admins():
    # Добавить супер-админа
    await admin_manager.add_admin(
        admin_id=YOUR_ID,
        username='your_username',
        first_name='Your Name',
        is_super_admin=True
    )

asyncio.run(add_admins())
```

## 🧪 Тестирование

### Проверка работы с пользователем

1. Напишите боту `/start`
2. Нажмите "📋 Заполнить анкету"
3. Ответьте на все вопросы
4. Анкета должна сохраниться в БД

### Проверка админ-панели

1. Напишите боту `/start` с аккаунта администратора
2. Вы должны увидеть админ-меню
3. Перейдите в "👥 Модерация"
4. Нажмите "📋 Проверить анкеты"
5. Должны появиться анкеты на рассмотрение

## 📊 Структура БД

После миграций будут созданы таблицы:
- `users` - пользователи
- `user_answers` - ответы на анкету
- `survey_submissions` - сами анкеты с статусами
- `payment_plans` - тарифные планы
- `subscriptions` - подписки пользователей
- `promo_codes` - промокоды
- `admin_users` - администраторы
- `bot_messages` - управляемые сообщения

## 🔧 Полезные команды

```bash
# Создать новую миграцию
python -m alembic revision --autogenerate -m "Description"

# Откатить последнюю миграцию
python -m alembic downgrade -1

# Просмотр истории миграций
python -m alembic history

# Очистить БД (ОПАСНО!)
python -m alembic downgrade base
```

## 🐛 Решение проблем

### Ошибка: "No 'script_location' key found"
- Убедитесь, что вы в папке `bot`
- Проверьте наличие файла `alembic.ini`

### Ошибка: "DATABASE_URL environment variable is required"
- Установите переменную окружения `DATABASE_URL`
- Или отредактируйте `alembic.ini` и `env.py`

### Ошибка подключения к БД
- Убедитесь, что PostgreSQL запущена
- Проверьте credentials в `.env`
- Проверьте, что БД создана: `createdb gidrolat`

### Ошибка импорта модулей
- Убедитесь, что вы в папке `bot` при запуске
- Или добавьте корень проекта в PYTHONPATH: `export PYTHONPATH=$PYTHONPATH:.`

## 📱 Использование бота

### Для пользователя:
1. `/start` - начать
2. Заполнить анкету
3. Ждать одобрения от админа
4. Получить реквизиты
5. Оплатить
6. Получить доступ в клуб

### Для администратора:
1. `/start` - админ-панель
2. "👥 Модерация" → "📋 Проверить анкеты"
3. Одобрить или отклонить
4. "💳 Подтвердить платежи"
5. Подтвердить оплату

### Для супер-администратора:
- Все права администратора +
- Управление другими администраторами
- Редактирование сообщений бота
- Управление тарифными планами
- Управление промокодами

## 📞 Контакты и поддержка

По вопросам запуска и настройки обратитесь к разработчикам проекта.
