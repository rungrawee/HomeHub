from typing import Any

from .settings import Settings, get_settings


def create_supabase_client(settings: Settings | None = None) -> Any:
    """Create a server-side Supabase client without exposing the service key."""
    settings = settings or get_settings()
    settings.require_supabase_credentials()

    try:
        from supabase import create_client
    except ImportError as error:
        raise RuntimeError(
            "supabase package is not installed; run pip install -r requirements.txt"
        ) from error

    return create_client(settings.supabase_url, settings.supabase_service_role_key)
