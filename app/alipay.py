import base64
import json
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.config import Settings


def _normalize_pem(value: str, marker: str) -> bytes:
    value = value.strip().strip('"').replace("\\n", "\n")
    if "BEGIN" in value:
        return value.encode("utf-8")
    body = "\n".join(value[i:i + 64] for i in range(0, len(value), 64))
    return f"-----BEGIN {marker}-----\n{body}\n-----END {marker}-----\n".encode("utf-8")


def _canonical(params: dict[str, str]) -> str:
    items = []
    for key in sorted(params):
        if key in {"sign", "sign_type"}:
            continue
        value = params[key]
        if value is None or value == "":
            continue
        items.append(f"{key}={value}")
    return "&".join(items)


class AlipayClient:
    def __init__(self, settings: Settings):
        if not settings.alipay_app_id:
            raise RuntimeError("ALIPAY_APP_ID 未配置")
        if not settings.alipay_private_key:
            raise RuntimeError("ALIPAY_PRIVATE_KEY 未配置")
        if not settings.alipay_public_key:
            raise RuntimeError("ALIPAY_PUBLIC_KEY 未配置")
        self._settings = settings
        self._private_key = serialization.load_pem_private_key(
            _normalize_pem(settings.alipay_private_key, "PRIVATE KEY"),
            password=None,
        )
        self._public_key = serialization.load_pem_public_key(
            _normalize_pem(settings.alipay_public_key, "PUBLIC KEY"),
        )

    def build_page_pay_url(
        self,
        out_trade_no: str,
        subject: str,
        total_amount_cents: int,
    ) -> str:
        biz_content = {
            "out_trade_no": out_trade_no,
            "product_code": "FAST_INSTANT_TRADE_PAY",
            "total_amount": self._format_amount(total_amount_cents),
            "subject": subject,
        }
        params = {
            "app_id": self._settings.alipay_app_id,
            "method": "alipay.trade.page.pay",
            "format": "JSON",
            "charset": "utf-8",
            "sign_type": "RSA2",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
            "notify_url": self._settings.alipay_notify_url,
            "return_url": self._settings.resolved_return_url,
            "biz_content": json.dumps(biz_content, ensure_ascii=False, separators=(",", ":")),
        }
        params["sign"] = self.sign(params)
        return f"{self._settings.alipay_gateway}?{urlencode(params)}"

    def sign(self, params: dict[str, str]) -> str:
        payload = _canonical(params).encode("utf-8")
        signature = self._private_key.sign(payload, padding.PKCS1v15(), hashes.SHA256())
        return base64.b64encode(signature).decode("ascii")

    def verify_notify(self, params: dict[str, str]) -> bool:
        sign = params.get("sign")
        if not sign:
            return False
        payload = _canonical(params).encode("utf-8")
        try:
            self._public_key.verify(
                base64.b64decode(sign),
                payload,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except Exception:
            return False

    @staticmethod
    def _format_amount(cents: int) -> str:
        return f"{Decimal(cents) / Decimal(100):.2f}"


def amount_to_cents(amount: str) -> int:
    return int((Decimal(amount) * Decimal(100)).quantize(Decimal("1")))
