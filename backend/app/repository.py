from datetime import date
from typing import Any


ASSET_LIST_COLUMNS = (
    "id,source_key,lot,sequence,case_number,asset_type,deed_number,"
    "rai,ngan,square_wah,area_detail,price,price_final,deposit_amount,"
    "tambon,amphur,province,sale_location,location,detail_url,updated_at,"
    "auctions(auction_round,auction_date,status)"
)

ASSET_DETAIL_COLUMNS = (
    "id,source_key,lot,sequence,case_number,asset_type,deed_number,"
    "rai,ngan,square_wah,area_detail,price,price_final,deposit_amount,"
    "tambon,amphur,province,owner_name,officer_name,sale_location,location,"
    "detail_url,raw_detail,source_updated_at,created_at,updated_at,"
    "auctions(auction_round,auction_date,status)"
)

FILTER_FIELDS = {"province", "amphur", "tambon"}
PUBLIC_AUCTION_STATUSES = {"-", "งดขายไม่มีผู้สู้ราคา"}


def prepare_asset_auctions(
    asset: dict[str, Any],
    *,
    today: date | None = None,
) -> dict[str, Any]:
    current_date = today or date.today()
    auctions = [
        auction
        for auction in asset.get("auctions") or []
        if str(auction.get("status") or "").strip() in PUBLIC_AUCTION_STATUSES
    ]
    auctions.sort(
        key=lambda auction: (
            str(auction.get("auction_date") or "9999-12-31"),
            auction.get("auction_round") or 0,
        )
    )
    upcoming_dates = []
    for auction in auctions:
        try:
            auction_date = date.fromisoformat(str(auction.get("auction_date")))
        except ValueError:
            continue
        if auction_date >= current_date:
            upcoming_dates.append(auction_date)
    asset["auctions"] = auctions
    asset["next_auction_date"] = (
        min(upcoming_dates).isoformat() if upcoming_dates else None
    )
    return asset


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

    def list_assets(
        self,
        *,
        page: int,
        page_size: int,
        province: str | None = None,
        amphur: str | None = None,
        tambon: str | None = None,
        asset_type: str | None = None,
        deed_number: str | None = None,
        min_price: str | None = None,
        max_price: str | None = None,
        auction_date_from: str | None = None,
        auction_date_to: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be greater than zero")

        columns = ASSET_LIST_COLUMNS
        if auction_date_from or auction_date_to:
            columns = columns.replace("auctions(", "auctions!inner(")
        query = (
            self.client.table("assets")
            .select(columns, count="exact")
            .neq("asset_type", "")
            .neq("province", "")
            .neq("amphur", "")
        )

        for field, value in (
            ("province", province),
            ("amphur", amphur),
            ("tambon", tambon),
            ("asset_type", asset_type),
        ):
            if value:
                query = query.eq(field, value)
        if deed_number:
            query = query.ilike("deed_number", f"%{deed_number}%")
        if min_price is not None:
            query = query.gte("price_final", min_price)
        if max_price is not None:
            query = query.lte("price_final", max_price)
        if auction_date_from:
            query = query.gte("auctions.auction_date", auction_date_from)
        if auction_date_to:
            query = query.lte("auctions.auction_date", auction_date_to)

        offset = (page - 1) * page_size
        response = (
            query.order("updated_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        rows = [
            prepare_asset_auctions(asset)
            for asset in (getattr(response, "data", None) or [])
        ]
        return rows, int(
            getattr(response, "count", None) or 0
        )

    def update_asset_fields(
        self,
        source_key: str,
        values: dict[str, object],
    ) -> bool:
        if not source_key:
            raise RepositoryError("asset source_key is required")
        if not values:
            return False

        response = (
            self.client.table("assets")
            .update(values)
            .eq("source_key", source_key)
            .execute()
        )
        return bool(getattr(response, "data", None))

    def get_asset(self, asset_id: str) -> dict[str, Any] | None:
        response = (
            self.client.table("assets")
            .select(ASSET_DETAIL_COLUMNS)
            .eq("id", asset_id)
            .limit(1)
            .execute()
        )
        rows = getattr(response, "data", None) or []
        if not rows:
            return None
        return prepare_asset_auctions(rows[0])

    def list_filter_values(
        self,
        field: str,
        *,
        province: str | None = None,
        amphur: str | None = None,
        page_size: int = 1000,
    ) -> list[str]:
        if field not in FILTER_FIELDS:
            raise ValueError(f"Unsupported filter field: {field}")
        if page_size < 1:
            raise ValueError("page_size must be greater than zero")

        values: set[str] = set()
        offset = 0
        while True:
            query = (
                self.client.table("assets")
                .select(field)
                .neq("asset_type", "")
                .neq("province", "")
                .neq("amphur", "")
            )
            if province:
                query = query.eq("province", province.strip())
            if amphur:
                query = query.eq("amphur", amphur.strip())
            response = (
                query.order(field)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            rows = getattr(response, "data", None) or []
            values.update(
                str(row.get(field)).strip()
                for row in rows
                if row.get(field) and str(row.get(field)).strip()
            )
            if len(rows) < page_size:
                return sorted(values)
            offset += page_size
