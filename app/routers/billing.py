from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alipay import AlipayClient
from app.config import get_settings
from app.db import get_db
from app.models import Order, Plan, User
from app.schemas import CreateOrderIn, OrderOut, PlanOut
from app.security import get_current_user

router = APIRouter(prefix="/v1", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    return db.scalars(select(Plan).where(Plan.active == 1).order_by(Plan.price_cents)).all()


@router.post("/orders", response_model=OrderOut)
def create_order(
    payload: CreateOrderIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.payment_method != "alipay":
        raise HTTPException(status_code=400, detail="目前仅支持 alipay")

    plan = db.get(Plan, payload.plan_id)
    if plan is None or not plan.active:
        raise HTTPException(status_code=404, detail="套餐不存在")

    order = Order(
        user_id=current_user.id,
        plan_id=plan.id,
        amount_cents=plan.price_cents,
        currency=plan.currency,
        payment_method="alipay",
    )
    db.add(order)
    db.flush()

    try:
        settings = get_settings()
        if settings.dev_mock_payments:
            order.pay_url = f"{settings.app_base_url.rstrip('/')}/v1/payments/mock/return?order_id={order.id}"
        else:
            client = AlipayClient(settings)
            order.pay_url = client.build_page_pay_url(
                out_trade_no=order.id,
                subject=f"Voice Keyboard {plan.name}",
                total_amount_cents=order.amount_cents,
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"支付宝配置错误: {e}") from e

    db.commit()
    db.refresh(order)
    return order


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    order = db.get(Order, order_id)
    if order is None or order.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="订单不存在")
    return order
