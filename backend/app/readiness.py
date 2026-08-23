from dataclasses import asdict, dataclass
from urllib.parse import urlparse
from typing import Any

from app.settings import Settings


@dataclass(frozen=True)
class ReadinessReport:
    credentials_configured: bool
    cors_origins: list[str]
    cors_valid: bool
    supabase_reachable: bool
    error: str | None = None

    @property
    def ready(self) -> bool:
        return (
            self.credentials_configured
            and self.cors_valid
            and self.supabase_reachable
        )

    def to_dict(self) -> dict[str, object]:
        return {**asdict(self), "ready": self.ready}


def _cors_is_valid(origins: list[str]) -> bool:
    if not origins or "*" in origins:
        return False
    return all(
        urlparse(origin).scheme in {"http", "https"}
        and bool(urlparse(origin).netloc)
        for origin in origins
    )


def check_backend_readiness(
    settings: Settings,
    client: Any | None,
) -> ReadinessReport:
    credentials_configured = bool(
        settings.supabase_url.strip()
        and settings.supabase_service_role_key.strip()
    )
    origins = settings.allowed_cors_origins()
    cors_valid = _cors_is_valid(origins)
    if not credentials_configured:
        return ReadinessReport(
            credentials_configured=False,
            cors_origins=origins,
            cors_valid=cors_valid,
            supabase_reachable=False,
            error="Supabase credentials are not configured",
        )

    try:
        if client is None:
            raise RuntimeError("Supabase client is unavailable")
        client.table("assets").select("id").limit(1).execute()
    except Exception:
        return ReadinessReport(
            credentials_configured=True,
            cors_origins=origins,
            cors_valid=cors_valid,
            supabase_reachable=False,
            error="Supabase connection failed",
        )
    return ReadinessReport(
        credentials_configured=True,
        cors_origins=origins,
        cors_valid=cors_valid,
        supabase_reachable=True,
    )
