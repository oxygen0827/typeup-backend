from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.alipay import AlipayClient
from app.config import get_settings
from app.db import get_db
from app.services import mark_alipay_order_paid

router = APIRouter(prefix="/v1/payments", tags=["payments"])


@router.post("/alipay/notify", response_class=PlainTextResponse)
async def alipay_notify(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    params = {k: str(v) for k, v in form.items()}

    client = AlipayClient(get_settings())
    if not client.verify_notify(params):
        raise HTTPException(status_code=400, detail="支付宝通知验签失败")

    try:
        mark_alipay_order_paid(db, params)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return "success"


@router.get("/alipay/return", response_class=HTMLResponse)
def alipay_return():
    return """
    <!doctype html>
    <html lang="zh-CN">
      <head><meta charset="utf-8"><title>支付完成</title></head>
      <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; padding: 32px;">
        <h2>支付结果处理中</h2>
        <p>你可以回到 Voice Keyboard，应用会自动刷新订阅状态。</p>
      </body>
    </html>
    """
