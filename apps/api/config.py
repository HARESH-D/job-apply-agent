from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


def resolve_database_url(value: str) -> str:
    """Anchor relative SQLite files to the repository root."""
    prefix = "sqlite:///"
    if not value.startswith(prefix):
        return value
    raw_path = value[len(prefix):]
    path = Path(raw_path)
    if path.is_absolute():
        return value
    resolved = (ROOT / raw_path).resolve().as_posix()
    return f"{prefix}{resolved}"


def resolve_storage_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((ROOT / path).resolve())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./jobagent.db"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    worker_api_key: str = "change-me-local-worker-key"
    storage_path: str = str(ROOT / "storage")
    cors_origins: str = "http://localhost:3000"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"

    def model_post_init(self, __context) -> None:
        self.database_url = resolve_database_url(self.database_url)
        self.storage_path = resolve_storage_path(self.storage_path)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
