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
    # If left as the placeholder default, ensure_signing_secret() generates a
    # cryptographically-strong secret on first boot and persists it under data_dir.
    api_signing_secret: str = "change-me-before-deploy"

    cors_origins: list[str] = ["http://127.0.0.1:5173", "http://localhost:5173"]

    file_size_cap_mb: int = 50
    ai_timeout_s: int = 60
    allowed_upload_mime: list[str] = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]

    # Phase 8.6 — ingestion / external metadata APIs
    ncbi_api_key: str | None = None
    entrez_email: str = "noreply@research-assistant.local"


_DEFAULT_SECRET = "change-me-before-deploy"


def get_settings() -> Settings:
    s = Settings()
    # If the secret is still the placeholder, transparently generate a strong
    # one and persist it under data_dir so it survives restarts. Local-first
    # apps shouldn't fail to boot just because the operator didn't set a key.
    # Operator-supplied secrets are accepted as-is — we only refuse to ship
    # the placeholder.
    if s.api_signing_secret == _DEFAULT_SECRET:
        s = s.model_copy(update={"api_signing_secret": _ensure_persistent_secret(s.data_dir)})
    return s


def _ensure_persistent_secret(data_dir: Path) -> str:
    import secrets

    data_dir.mkdir(parents=True, exist_ok=True)
    secret_path = data_dir / ".signing_secret"
    if secret_path.exists():
        existing = secret_path.read_text(encoding="utf-8").strip()
        if existing and len(existing) >= 32:
            return existing
    new_secret = secrets.token_urlsafe(48)
    secret_path.write_text(new_secret, encoding="utf-8")
    # Best-effort file mode tightening (POSIX only)
    try:
        secret_path.chmod(0o600)
    except OSError:
        pass
    return new_secret
