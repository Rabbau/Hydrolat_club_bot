from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv

# Загружаем .env для прямого доступа к ADMIN_IDS
load_dotenv()

class Settings(BaseSettings):
    """Настройки приложения с использованием Pydantic v2."""
    
    bot_token: str = Field(..., env="BOT_TOKEN")
    database_url: str = Field(..., env="DATABASE_URL")
    
    # admin_ids объявляем как Optional[str] и парсим вручную
    admin_ids: Optional[str] = Field(default=None, env="ADMIN_IDS")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    @field_validator("admin_ids", mode="before")
    @classmethod
    def validate_admin_ids(cls, v):
        """Валидатор для admin_ids - оставляем как строку."""
        if v is None:
            return ""
        return str(v)
    
    @property
    def admin_ids_list(self) -> List[int]:
        """Свойство для получения списка ID администраторов."""
        if not self.admin_ids or not self.admin_ids.strip():
            return []
        
        try:
            return [
                int(admin_id.strip())
                for admin_id in self.admin_ids.split(",")
                if admin_id.strip()
            ]
        except (ValueError, AttributeError):
            return []


# Создаем экземпляр настроек
settings = Settings()