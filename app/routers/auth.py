from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import RefreshToken, User, UserStatus, as_utc, now_utc
from app.schemas import AuthOut, LoginIn, MeOut, RefreshIn, RegisterIn, UserOut
from app.security import (
    authenticate_user, create_access_token, get_current_user, hash_password,
    issue_refresh_token, token_hash,
)
from app.services import entitlement_summary, grant_registration_trial

router = APIRouter(prefix="/v1/auth", tags=["auth"])


@router.post("/register", response_model=AuthOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    email = payload.email.lower().strip()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="邮箱已注册")
    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    db.flush()
    grant_registration_trial(db, user.id)
    refresh = issue_refresh_token(db, user)
    db.commit()
    db.refresh(user)
    return AuthOut(access_token=create_access_token(user), refresh_token=refresh, user=UserOut.model_validate(user))


@router.post("/login", response_model=AuthOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="邮箱或密码错误")
    refresh = issue_refresh_token(db, user)
    db.commit()
    return AuthOut(access_token=create_access_token(user), refresh_token=refresh, user=UserOut.model_validate(user))


@router.post("/refresh", response_model=AuthOut)
def refresh(payload: RefreshIn, db: Session = Depends(get_db)):
    record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash(payload.refresh_token)))
    if record is None or record.revoked_at is not None or as_utc(record.expires_at) <= now_utc():
        raise HTTPException(status_code=401, detail="刷新凭证无效")
    user = db.get(User, record.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    if user.status != UserStatus.active:
        record.revoked_at = now_utc()
        db.commit()
        raise HTTPException(status_code=403, detail="账号已停用")
    record.revoked_at = now_utc()
    refresh_token = issue_refresh_token(db, user)
    db.commit()
    return AuthOut(access_token=create_access_token(user), refresh_token=refresh_token, user=UserOut.model_validate(user))


@router.get("/me", response_model=MeOut)
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {
        "user": UserOut.model_validate(current_user),
        "entitlement": entitlement_summary(db, current_user.id),
    }
