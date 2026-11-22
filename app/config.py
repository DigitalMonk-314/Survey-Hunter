from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- Telegram Bot ---
    bot_token: str = Field(..., validation_alias="BOT_TOKEN")
    my_chat_id: int = Field(..., validation_alias="MY_CHAT_ID")
    
    # --- Project Settings ---
    score_threshold: int = Field(
        default=40, 
        validation_alias="SCORE_THRESHOLD"
    )
    channels_str: str = Field(..., validation_alias="CHANNELS")
    
    # --- Parser Settings (Новое) ---
    poll_interval_seconds: int = Field(
        default=60, 
        validation_alias="POLL_INTERVAL_SECONDS"
    )

    # Настройка Pydantic для чтения .env
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8", 
        extra="ignore"
    )

    @field_validator("channels_str")
    @classmethod
    def clean_channels(cls, v: str) -> str:
        """Убирает символ @ и префикс t.me/ из строки каналов."""
        channels = []
        for ch in v.split(","):
            ch = ch.strip().replace("@", "").replace("https://t.me/", "").replace("t.me/", "")
            if ch:
                channels.append(ch)
        return ",".join(channels)

    @property
    def channels(self) -> List[str]:
        """Возвращает список username каналов."""
        return [ch for ch in self.channels_str.split(",") if ch]

# Глобальный экземпляр настроек
settings = Settings()