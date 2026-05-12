from fastapi import FastAPI

from app.db import Base, SessionLocal, engine
from app.plans import seed_plans
from app.routers import admin, auth, billing, models, payments


def create_app() -> FastAPI:
    app = FastAPI(title="Voice Keyboard Backend")

    @app.on_event("startup")
    def startup() -> None:
        Base.metadata.create_all(bind=engine)
        with SessionLocal() as db:
            seed_plans(db)

    @app.get("/health")
    def health():
        return {"ok": True}

    app.include_router(auth.router)
    app.include_router(billing.router)
    app.include_router(models.router)
    app.include_router(payments.router)
    app.include_router(admin.router)
    return app


app = create_app()
