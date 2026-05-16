import json
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.alipay import amount_to_cents
from app.models import Entitlement, EntitlementStatus, Order, OrderStatus, Payment, Plan, UsageKind, UsageRecord, now_utc


def grant_entitlement(db: Session, order: Order, plan: Plan) -> Entitlement:
    now = now_utc()
    active = db.scalar(
        select(Entitlement)
        .where(
            Entitlement.user_id == order.user_id,
            Entitlement.status == EntitlementStatus.active,
            Entitlement.ends_at > now,
        )
        .order_by(Entitlement.ends_at.desc())
    )
    starts_at = active.ends_at if active else now
    ends_at = starts_at + timedelta(days=plan.duration_days)
    entitlement = Entitlement(
        user_id=order.user_id,
        plan_id=plan.id,
        starts_at=starts_at,
        ends_at=ends_at,
        stt_minutes_limit=plan.stt_minutes,
        ai_requests_limit=plan.ai_requests,
        status=EntitlementStatus.active,
    )
    db.add(entitlement)
    return entitlement


def mark_alipay_order_paid(db: Session, notify: dict[str, str]) -> bool:
    out_trade_no = notify.get("out_trade_no", "")
    trade_no = notify.get("trade_no", "")
    trade_status = notify.get("trade_status", "")
    total_amount = notify.get("total_amount", "")

    if trade_status not in {"TRADE_SUCCESS", "TRADE_FINISHED"}:
        return False

    order = db.get(Order, out_trade_no)
    if order is None:
        raise ValueError("订单不存在")

    paid_cents = amount_to_cents(total_amount)
    if paid_cents != order.amount_cents:
        raise ValueError("支付宝通知金额与订单金额不一致")

    existing_payment = db.scalar(
        select(Payment).where(Payment.provider == "alipay", Payment.provider_trade_no == trade_no)
    )
    if existing_payment is not None:
        return order.status == OrderStatus.paid

    plan = db.get(Plan, order.plan_id)
    if plan is None:
        raise ValueError("套餐不存在")

    paid_at = now_utc()
    payment = Payment(
        order_id=order.id,
        provider="alipay",
        provider_trade_no=trade_no,
        status=trade_status,
        raw_notify=json.dumps(notify, ensure_ascii=False, sort_keys=True),
        paid_at=paid_at,
    )
    db.add(payment)

    if order.status != OrderStatus.paid:
        order.status = OrderStatus.paid
        order.provider_trade_no = trade_no
        order.paid_at = paid_at
        grant_entitlement(db, order, plan)

    db.commit()
    return True


def mark_mock_order_paid(db: Session, order_id: str) -> bool:
    order = db.get(Order, order_id)
    if order is None:
        raise ValueError("订单不存在")

    plan = db.get(Plan, order.plan_id)
    if plan is None:
        raise ValueError("套餐不存在")

    provider_trade_no = f"mock_{order.id}"
    existing_payment = db.scalar(
        select(Payment).where(Payment.provider == "mock", Payment.provider_trade_no == provider_trade_no)
    )
    if existing_payment is not None:
        return order.status == OrderStatus.paid

    paid_at = now_utc()
    db.add(Payment(
        order_id=order.id,
        provider="mock",
        provider_trade_no=provider_trade_no,
        status="TRADE_SUCCESS",
        raw_notify=json.dumps({"order_id": order.id, "mock": True}, ensure_ascii=False, sort_keys=True),
        paid_at=paid_at,
    ))

    if order.status != OrderStatus.paid:
        order.status = OrderStatus.paid
        order.provider_trade_no = provider_trade_no
        order.paid_at = paid_at
        grant_entitlement(db, order, plan)

    db.commit()
    return True


def current_entitlement(db: Session, user_id: str) -> Entitlement | None:
    now = now_utc()
    return db.scalar(
        select(Entitlement)
        .where(
            Entitlement.user_id == user_id,
            Entitlement.status == EntitlementStatus.active,
            Entitlement.starts_at <= now,
            Entitlement.ends_at > now,
        )
        .order_by(Entitlement.ends_at.desc())
    )


def usage_totals(db: Session, user_id: str, entitlement: Entitlement | None) -> dict:
    if entitlement is None:
        return {"stt_seconds": 0, "ai_requests": 0}
    stt_seconds = db.scalar(
        select(func.coalesce(func.sum(UsageRecord.audio_seconds), 0)).where(
            UsageRecord.user_id == user_id,
            UsageRecord.kind == UsageKind.stt,
            UsageRecord.created_at >= entitlement.starts_at,
            UsageRecord.created_at < entitlement.ends_at,
        )
    ) or 0
    ai_requests = db.scalar(
        select(func.count(UsageRecord.id)).where(
            UsageRecord.user_id == user_id,
            UsageRecord.kind.in_([UsageKind.llm_chat, UsageKind.llm_stream]),
            UsageRecord.created_at >= entitlement.starts_at,
            UsageRecord.created_at < entitlement.ends_at,
        )
    ) or 0
    return {"stt_seconds": int(stt_seconds), "ai_requests": int(ai_requests)}


def entitlement_summary(db: Session, user_id: str) -> dict:
    entitlement = current_entitlement(db, user_id)
    totals = usage_totals(db, user_id, entitlement)
    if entitlement is None:
        return {
            "active": False,
            "plan_id": None,
            "stt_minutes_limit": 0,
            "stt_seconds_used": totals["stt_seconds"],
            "ai_requests_limit": 0,
            "ai_requests_used": totals["ai_requests"],
        }
    return {
        "active": True,
        "plan_id": entitlement.plan_id,
        "starts_at": entitlement.starts_at.isoformat(),
        "ends_at": entitlement.ends_at.isoformat(),
        "stt_minutes_limit": entitlement.stt_minutes_limit,
        "stt_seconds_used": totals["stt_seconds"],
        "ai_requests_limit": entitlement.ai_requests_limit,
        "ai_requests_used": totals["ai_requests"],
    }


def ensure_stt_quota(db: Session, user_id: str, audio_seconds: int) -> Entitlement:
    entitlement = current_entitlement(db, user_id)
    if entitlement is None:
        raise PermissionError("请先开通服务")
    totals = usage_totals(db, user_id, entitlement)
    if totals["stt_seconds"] + audio_seconds > entitlement.stt_minutes_limit * 60:
        raise PermissionError("本期语音额度已用完")
    return entitlement


def ensure_ai_quota(db: Session, user_id: str) -> Entitlement:
    entitlement = current_entitlement(db, user_id)
    if entitlement is None:
        raise PermissionError("请先开通服务")
    totals = usage_totals(db, user_id, entitlement)
    if totals["ai_requests"] + 1 > entitlement.ai_requests_limit:
        raise PermissionError("本期 AI 请求额度已用完")
    return entitlement
