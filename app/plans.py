from sqlalchemy.orm import Session

from app.models import Plan


DEFAULT_PLANS = [
    {
        "id": "pro_monthly",
        "name": "Pro 月卡",
        "price_cents": 2900,
        "currency": "CNY",
        "duration_days": 30,
        "stt_minutes": 600,
        "ai_requests": 3000,
    },
    {
        "id": "pro_yearly",
        "name": "Pro 年卡",
        "price_cents": 19900,
        "currency": "CNY",
        "duration_days": 365,
        "stt_minutes": 600,
        "ai_requests": 3000,
    },
]


def seed_plans(db: Session) -> None:
    for item in DEFAULT_PLANS:
        existing = db.get(Plan, item["id"])
        if existing is None:
            db.add(Plan(**item))
    db.commit()
