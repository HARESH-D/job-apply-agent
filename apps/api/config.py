from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


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

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
