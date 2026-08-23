from datetime import date
from decimal import Decimal
import logging
from typing import Annotated, Any
from uuid import UUID
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.repository import RepositoryError, SupabaseRepository
from app.settings import Settings, get_settings
from app.supabase_client import create_supabase_client


LOGGER = logging.getLogger("homehub.api")


def create_app(
    repository: Any | None = None,
    settings: Settings | None = None,
) -> FastAPI:
    app_settings = settings or get_settings()
    app = FastAPI(title="HomeHub API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app_settings.allowed_cors_origins(),
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def add_security_headers(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.exception_handler(RepositoryError)
    async def handle_repository_error(
        request: Request, error: RepositoryError
    ) -> JSONResponse:
        LOGGER.exception("Supabase repository error on %s", request.url.path)
        return JSONResponse(
            status_code=502,
            content={"detail": "Data service temporarily unavailable"},
        )

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
        if min_price is not None and max_price is not None and min_price > max_price:
            raise HTTPException(
                status_code=422, detail="min_price must not exceed max_price"
            )
        if (
            auction_date_from is not None
            and auction_date_to is not None
            and auction_date_from > auction_date_to
        ):
            raise HTTPException(
                status_code=422,
                detail="auction_date_from must not exceed auction_date_to",
            )
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

    @app.get("/assets/{asset_id}")
    def get_asset(
        asset_id: UUID,
        repository: Annotated[Any, Depends(get_repository)],
    ) -> dict[str, object]:
        asset = repository.get_asset(str(asset_id))
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        return asset

    return app


app = create_app()
