"""App factory. Run with `uvicorn vendor_intake.main:create_app --factory`."""

from collections.abc import Callable
from datetime import date

from fastapi import FastAPI

from vendor_intake.config import Settings, get_settings
from vendor_intake.db import Base, make_engine, make_session_factory, utcnow
from vendor_intake.errors import install_error_handlers
from vendor_intake.routes import auth, documents, review, vendors
from vendor_intake.services.storage import LocalStorage


def create_app(
    settings: Settings | None = None, today: Callable[[], date] | None = None
) -> FastAPI:
    settings = settings or get_settings()
    settings.prepare_paths()
    engine = make_engine(settings.database_url)
    Base.metadata.create_all(engine)

    app = FastAPI(
        title="Vendor Intake API",
        version="0.1.0",
        description="Vendor onboarding with document extraction and human review.",
    )
    app.state.settings = settings
    app.state.session_factory = make_session_factory(engine)
    app.state.storage = LocalStorage(settings.storage_dir)
    app.state.today = today or (lambda: utcnow().date())
    install_error_handlers(app)

    @app.get("/api/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    for module in (auth, vendors, documents, review):
        app.include_router(module.router, prefix="/api")
    return app
