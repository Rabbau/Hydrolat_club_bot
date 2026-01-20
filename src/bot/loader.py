import os
from pathlib import Path

from aiogram import Bot
from aiogram.enums import ParseMode
from dotenv import load_dotenv

_repo_root = Path(__file__).resolve().parents[3]
_dotenv_path = _repo_root / ".env"
load_dotenv(dotenv_path=_dotenv_path if _dotenv_path.exists() else None, override=True)

BOT_TOKEN = (os.getenv("BOT_TOKEN") or "").strip().strip('"').strip("'")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set")

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
