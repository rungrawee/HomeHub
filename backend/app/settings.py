from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_prefix="",
        extra="ignore",
    )

    def require_supabase_credentials(self) -> None:
        missing = []
        if not self.supabase_url.strip():
            missing.append("SUPABASE_URL")
        if not self.supabase_service_role_key.strip():
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if missing:
            raise ValueError(
                "Missing required Supabase environment variables: "
                + ", ".join(missing)
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()
