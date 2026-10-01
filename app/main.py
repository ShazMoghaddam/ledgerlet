"""Application factory. Wires the modules together; contains no business logic."""

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.error_handlers import register_error_handlers
from app.modules.properties.router import router as properties_router
from app.modules.transactions.router import router as transactions_router

API_PREFIX = "/api/v1"


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")

    register_error_handlers(app)
    app.include_router(properties_router, prefix=API_PREFIX)
    app.include_router(transactions_router, prefix=API_PREFIX)

    @app.get("/health", tags=["meta"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
