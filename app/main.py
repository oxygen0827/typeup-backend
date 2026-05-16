from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import Base, SessionLocal, engine
from app.errors import http_exception_handler, unhandled_exception_handler, validation_exception_handler
from app.plans import seed_plans
from app.routers import admin, auth, billing, models, payments
from app.schemas import HealthOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_plans(db)
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Voice Keyboard Backend", lifespan=lifespan)
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    @app.get("/health", response_model=HealthOut)
    def health():
        return {
            "ok": True,
            "dev_mock_mode": settings.dev_mock_mode,
            "dev_mock_payments": settings.dev_mock_payments,
            "dev_mock_models": settings.dev_mock_models,
        }

    app.include_router(auth.router)
    app.include_router(billing.router)
    app.include_router(models.router)
    app.include_router(payments.router)
    app.include_router(admin.router)
    return app


app = create_app()
