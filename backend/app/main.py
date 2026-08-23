from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import Depends, FastAPI, Query

from app.repository import SupabaseRepository
from app.supabase_client import create_supabase_client


def create_app(repository: Any | None = None) -> FastAPI:
    app = FastAPI(title="HomeHub API", version="0.1.0")

    def get_repository() -> Any:
        return repository or SupabaseRepository(create_supabase_client())

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/assets")
    def list_assets(
        repository: Annotated[Any, Depends(get_repository)],
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 20,
        province: str | None = None,
        amphur: str | None = None,
        tambon: str | None = None,
        asset_type: str | None = None,
        deed_number: str | None = None,
        min_price: Annotated[Decimal | None, Query(ge=0)] = None,
        max_price: Annotated[Decimal | None, Query(ge=0)] = None,
        auction_date_from: date | None = None,
        auction_date_to: date | None = None,
    ) -> dict[str, object]:
        items, total = repository.list_assets(
            page=page,
            page_size=page_size,
            province=province,
            amphur=amphur,
            tambon=tambon,
            asset_type=asset_type,
            deed_number=deed_number,
            min_price=str(min_price) if min_price is not None else None,
            max_price=str(max_price) if max_price is not None else None,
            auction_date_from=(
                auction_date_from.isoformat() if auction_date_from else None
            ),
            auction_date_to=auction_date_to.isoformat() if auction_date_to else None,
        )
        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size,
            },
        }

    return app


app = create_app()
