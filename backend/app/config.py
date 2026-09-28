from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    api_prefix: str = "/api"
    frontend_origin: str = "http://localhost:3000"
    database_url: str = "postgresql+asyncpg://beautify:beautify@localhost:5433/beautify_slides"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-20b"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    soffice_path: str = "soffice"
    pdftoppm_path: str = "pdftoppm"
    storage_dir: Path = Path("../storage")
    reference_slides_dir: Path = Path("../reference-slides")
    max_upload_mb: int = Field(default=25, ge=1, le=200)

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def previews_dir(self) -> Path:
        return self.storage_dir / "previews"


@lru_cache
def get_settings() -> Settings:
    return Settings()
