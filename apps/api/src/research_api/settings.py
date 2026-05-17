from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=[".env", "../../.env"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    ai_provider_default: Literal["gemini", "claude", "openai"] = "gemini"
    gemini_api_key: str | None = None
    claude_api_key: str | None = None
    openai_api_key: str | None = None

    data_dir: Path = Field(default=Path("./data"))
    sqlite_url: str = "sqlite+aiosqlite:///./data/research.db"
    storage_backend: Literal["local", "supabase"] = "local"

    local_user_id: str = "local-user"

    api_host: str = "127.0.0.1"
    api_port: int = 8787
    api_signing_secret: str = "change-me-before-deploy"

    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]


def get_settings() -> Settings:
    return Settings()
