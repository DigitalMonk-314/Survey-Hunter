from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- Telegram API ---
    tg_api_id: int = Field(..., validation_alias="TG_API_ID")
    tg_api_hash: str = Field(..., validation_alias="TG_API_HASH")
    tg_session_name: str = Field(
        default="survey_hunter_session", 
        validation_alias="TG_SESSION_NAME"
    )
    
    # --- Telegram Bot ---
    bot_token: str = Field(..., validation_alias="BOT_TOKEN")
    my_chat_id: int = Field(..., validation_alias="MY_CHAT_ID")
    
    # --- Project Settings ---
    score_threshold: int = Field(
        default=40, 
        validation_alias="SCORE_THRESHOLD"
    )
    channels_str: str = Field(..., validation_alias="CHANNELS")

    # Настройка Pydantic для чтения .env
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    @property
    def channels(self) -> List[int]:
        """Превращает строку '123,-456' в список чисел [123, -456]."""
        return [
            int(ch.strip()) 
            for ch in self.channels_str.split(",") 
            if ch.strip()
        ]

# Глобальный экземпляр настроек
settings = Settings()