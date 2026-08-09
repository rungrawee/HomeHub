from typing import Any


class RepositoryError(RuntimeError):
    """Raised when Supabase returns an unusable response."""


class SupabaseRepository:
    def __init__(self, client: Any):
        self.client = client

    def upsert_asset(self, values: dict[str, object]) -> str:
        source_key = values.get("source_key")
        if not source_key:
            raise RepositoryError("asset source_key is required")

        response = (
            self.client.table("assets")
            .upsert(values, on_conflict="source_key")
            .execute()
        )
        data = getattr(response, "data", None) or []
        if not data:
            raise RepositoryError(f"Supabase returned no asset for {source_key!r}")

        asset_id = data[0].get("id")
        if not asset_id:
            raise RepositoryError(f"Supabase asset has no id for {source_key!r}")
        return str(asset_id)
