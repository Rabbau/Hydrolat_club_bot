from pathlib import Path

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from src.Config.settings import settings

_repo_root = Path(__file__).resolve().parents[3]
_dotenv_path = _repo_root / ".env"
load_dotenv(dotenv_path=_dotenv_path if _dotenv_path.exists() else None, override=True)

bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
