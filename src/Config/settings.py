from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения с использованием Pydantic v2."""
    
    bot_token: str = Field(..., env="BOT_TOKEN")
    database_url: str = Field(..., env="DATABASE_URL")
    
    # Администраторы - делаем строкой
    admin_ids: str = Field("", env="ADMIN_IDS")
    superadmin_id: Optional[int] = Field(None, env="SUPERADMIN_ID")
    
    # Вычисляемое свойство для получения списка ID
    @property
    def admin_ids_list(self) -> List[int]:
        """Получить список ID администраторов."""
        if not self.admin_ids or not self.admin_ids.strip():
            return []
        
        ids = []
        for admin_id in self.admin_ids.split(","):
            try:
                ids.append(int(admin_id.strip()))
            except ValueError:
                continue
        return ids
    
    debug: bool = Field(False, env="DEBUG")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()