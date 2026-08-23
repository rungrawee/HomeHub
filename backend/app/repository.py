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

    def upsert_auctions(self, asset_id: str, auctions: list[Any]) -> int:
        if not asset_id:
            raise RepositoryError("asset_id is required for auction records")
        if not auctions:
            return 0

        rows = []
        for auction in auctions:
            values = auction.to_dict() if hasattr(auction, "to_dict") else dict(auction)
            values["asset_id"] = asset_id
            rows.append(values)

        response = (
            self.client.table("auctions")
            .upsert(
                rows,
                on_conflict="asset_id,auction_round,auction_date",
            )
            .execute()
        )
        return len(getattr(response, "data", None) or rows)

    def fetch_all(
        self,
        table: str,
        columns: str,
        *,
        page_size: int = 1000,
    ) -> list[dict[str, Any]]:
        if page_size < 1:
            raise ValueError("page_size must be greater than zero")

        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            response = (
                self.client.table(table)
                .select(columns)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            page = getattr(response, "data", None) or []
            rows.extend(page)
            if len(page) < page_size:
                return rows
            offset += page_size
