# Hydrolat club bot

Telegram бот: `@hydrol_cl_bot`

## Быстрый старт (Windows)

1) Создайте `.env` в корне проекта:

```env
BOT_TOKEN=...
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/dbname
ADMIN_IDS=...
```

2) Установите зависимости:

```bash
pip install -r requirements.txt
```

3) Запуск бота:

```bash
python -m src.bot.main
```

Примечание: если проект лежит в пути с кириллицей (например, `C:\Users\Aлек\...`) и у вас возникают ошибки PowerShell при `cd`, запускайте команды из `cmd.exe` или Windows Terminal (Command Prompt).

## Миграции (Alembic)

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```
