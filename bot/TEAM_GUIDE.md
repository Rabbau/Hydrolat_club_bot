# 👥 Инструкции для команды

## 🎯 Распределение ответственности

### Frontend/Telegram интеграция
- **Ответственный:** (назначить)
- **Задачи:**
  - Тестирование UI/UX в Telegram
  - Улучшение клавиатур и навигации
  - Добавление новых типов вопросов в анкету
  - Локализация сообщений (если нужно)

### Backend/БД
- **Ответственный:** (назначить)
- **Задачи:**
  - Оптимизация запросов к БД
  - Миграции при изменении схемы
  - Резервное копирование БД
  - Оптимизация производительности

### Платежи и интеграции
- **Ответственный:** (назначить)
- **Задачи:**
  - Интеграция с Yookassa (когда будет ИП)
  - Система уведомлений о платежах
  - Отчёты по доходам
  - Система рефандов

### Администрирование
- **Ответственный:** Евгения
- **Задачи:**
  - Управление вопросами анкеты
  - Модерация анкет
  - Управление администраторами
  - Поддержка пользователей

---

## 📌 Текущие задачи (To-Do)

### 1️⃣ Высокий приоритет
- [ ] Реализовать отправку реквизитов пользователю после одобрения
- [ ] Создать интерфейс для управления платежными планами в боте
- [ ] Добавить уведомления администратору при новых анкетах
- [ ] Реализовать отправку сообщений об отклонении с причиной
- [ ] Система уведомлений о подтверждении платежа

### 2️⃣ Средний приоритет
- [ ] Интеграция с системой платежей (Yookassa когда будет ИП)
- [ ] Расширенная статистика для администратора
- [ ] История изменений статусов анкет
- [ ] Возможность переотправки анкеты после отклонения
- [ ] Система поддержки/чата

### 3️⃣ Низкий приоритет
- [ ] Экспорт анкет в CSV/Excel
- [ ] Система рейтинга членов клуба
- [ ] Интеграция с сообществом (группа в Telegram)
- [ ] Email рассылки
- [ ] Web-интерфейс администратора

---

## 🔗 API/Интеграции в будущем

### Yookassa
```python
# Когда будет ИП, используйте этот код:
from yookassa import Configuration, Payment

Configuration.account_id = "SHOP_ID"
Configuration.secret_key = "SECRET_KEY"

payment = Payment.create({
    "amount": {
        "value": "1000.00",
        "currency": "RUB"
    },
    "confirmation": {
        "type": "redirect",
        "return_url": "https://yoursite.com"
    },
    "description": "Подписка на клуб"
})
```

### Telegram бот API
Текущая версия: aiogram 3.3.0
- Поддерживает все основные методы
- Асинхронный
- Type-safe

---

## 💾 Резервное копирование

### Стратегия бэкапов
```bash
# Ежедневный бэкап БД
0 3 * * * pg_dump bot_db > /backups/bot_$(date +\%Y\%m\%d).sql

# Ежедневный бэкап на облако (S3, Google Drive и т.д.)
0 4 * * * aws s3 cp /backups/bot_*.sql s3://my-bucket/backups/
```

---

## 📊 Мониторинг

### Показатели для отслеживания
1. **Количество анкет** - per день/неделя/месяц
2. **Конверсия** - сколько анкет → одобрено → оплачено
3. **Доход** - ежемесячный доход
4. **Активные подписки** - текущее количество активных пользователей
5. **Среднее время модерации** - как долго анкета ждёт проверки

### Queries для проверки
```sql
-- Количество анкет по статусам
SELECT status, COUNT(*) as count FROM survey_submissions GROUP BY status;

-- Активные подписки
SELECT COUNT(*) FROM subscriptions WHERE status = 'active' AND end_date > NOW();

-- Доход по месяцам
SELECT DATE_TRUNC('month', created_at), SUM(price_paid) FROM subscriptions GROUP BY DATE_TRUNC('month', created_at);

-- Время ожидания модерации
SELECT AVG(EXTRACT(EPOCH FROM (updated_at - created_at))/3600) as avg_hours FROM survey_submissions WHERE status != 'pending_review';
```

---

## 🔐 Безопасность

### Чек-лист безопасности
- ✅ Переменные окружения для токенов (используйте .env)
- ✅ Проверка прав доступа (AdminFilter, SuperAdminFilter)
- ✅ SQL инъекции защищены (используем SQLAlchemy)
- ✅ Rate limiting на Telegram уровне (встроено в aiogram)
- ⚠️ TODO: HTTPS для webhook'ов (при переходе на webhook)
- ⚠️ TODO: Шифрование чувствительных данных в БД
- ⚠️ TODO: GDPR - удаление персональных данных

### Переменные окружения
```env
BOT_TOKEN=xxxxx  # Никогда не коммитьте!
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
LOG_LEVEL=INFO
ENVIRONMENT=production
```

---

## 🚀 Развёртывание

### Production окружение
```bash
# 1. Установите зависимости
pip install -r requirements.txt

# 2. Примените миграции
alembic upgrade head

# 3. Инициализируйте данные
python -m src.db_components.init_admin <ADMIN_ID> true
python -m src.db_components.init_payment_plans

# 4. Запустите бота в фоне (используйте systemd/supervisor)
# systemd example:
[Unit]
Description=Gidrolat Bot
After=network.target

[Service]
Type=simple
User=bot
WorkingDirectory=/home/bot/gidrolat_bot/bot
ExecStart=/home/bot/.venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Docker
```bash
docker-compose up -d
```

### Мониторинг и логирование
```bash
# Посмотреть логи
docker logs -f gidrolat_bot

# Или systemd
journalctl -u gidrolat_bot -f
```

---

## 📞 Контакты и поддержка

**Евгения** (Product Owner)
- Управление требованиями
- Модерация анкет
- Коммуникация с пользователями

**Техническая команда**
- Backend разработка
- DevOps/Infrastructure
- QA и тестирование

---

## 📚 Полезные ссылки

- **Aiogram документация:** https://docs.aiogram.dev/
- **SQLAlchemy:** https://docs.sqlalchemy.org/
- **PostgreSQL:** https://www.postgresql.org/docs/
- **Telegram Bot API:** https://core.telegram.org/bots/api

---

**Успехов в разработке! 🚀**
