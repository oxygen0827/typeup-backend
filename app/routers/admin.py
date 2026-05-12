from datetime import timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import Entitlement, EntitlementStatus, Plan, User, UserStatus, now_utc
from app.schemas import AdminAddQuotaIn, AdminGrantIn, UserOut
from app.services import entitlement_summary

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(x_admin_key: str = Header(default="")) -> None:
    expected = get_settings().admin_api_key
    if not expected or x_admin_key != expected:
        raise HTTPException(status_code=403, detail="admin key 无效")


@router.get("/users")
def list_users(
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    users = db.scalars(select(User).order_by(User.created_at.desc()).limit(200)).all()
    return [
        {
            "user": UserOut.model_validate(user),
            "entitlement": entitlement_summary(db, user.id),
        }
        for user in users
    ]


@router.get("/users/{user_id}")
def get_user(
    user_id: str,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return {"user": UserOut.model_validate(user), "entitlement": entitlement_summary(db, user.id)}


@router.post("/users/{user_id}/grant-pro")
def grant_pro(
    user_id: str,
    payload: AdminGrantIn,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    plan = db.get(Plan, payload.plan_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    if plan is None:
        raise HTTPException(status_code=404, detail="套餐不存在")

    now = now_utc()
    entitlement = Entitlement(
        user_id=user.id,
        plan_id=plan.id,
        starts_at=now,
        ends_at=now + timedelta(days=plan.duration_days),
        stt_minutes_limit=plan.stt_minutes,
        ai_requests_limit=plan.ai_requests,
        status=EntitlementStatus.active,
    )
    db.add(entitlement)
    db.commit()
    return {"ok": True, "entitlement": entitlement_summary(db, user.id)}


@router.post("/users/{user_id}/add-quota")
def add_quota(
    user_id: str,
    payload: AdminAddQuotaIn,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    now = now_utc()
    entitlement = db.scalar(
        select(Entitlement)
        .where(
            Entitlement.user_id == user.id,
            Entitlement.status == EntitlementStatus.active,
            Entitlement.ends_at > now,
        )
        .order_by(Entitlement.ends_at.desc())
    )
    if entitlement is None:
        raise HTTPException(status_code=404, detail="用户没有有效权益")
    entitlement.stt_minutes_limit += max(0, payload.stt_minutes)
    entitlement.ai_requests_limit += max(0, payload.ai_requests)
    db.commit()
    return {"ok": True, "entitlement": entitlement_summary(db, user.id)}


@router.post("/users/{user_id}/disable")
def disable_user(
    user_id: str,
    _: None = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = UserStatus.disabled
    db.commit()
    return {"ok": True}
