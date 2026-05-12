from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class UserOut(BaseModel):
    id: str
    email: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RegisterIn(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.lower().strip()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("邮箱格式不正确")
        return value


class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.lower().strip()
        if "@" not in value or "." not in value.rsplit("@", 1)[-1]:
            raise ValueError("邮箱格式不正确")
        return value


class RefreshIn(BaseModel):
    refresh_token: str


class AuthOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class PlanOut(BaseModel):
    id: str
    name: str
    price_cents: int
    currency: str
    duration_days: int
    stt_minutes: int
    ai_requests: int

    model_config = {"from_attributes": True}


class CreateOrderIn(BaseModel):
    plan_id: str
    payment_method: str = "alipay"


class OrderOut(BaseModel):
    id: str
    user_id: str
    plan_id: str
    amount_cents: int
    currency: str
    payment_method: str
    status: str
    pay_url: str | None = None
    paid_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatMessage(BaseModel):
    role: str
    content: str


class LLMChatIn(BaseModel):
    messages: list[ChatMessage]
    temperature: float = 0.1
    max_tokens: int = 1000


class LLMChatOut(BaseModel):
    text: str
    usage: dict[str, Any] = Field(default_factory=dict)


class AdminGrantIn(BaseModel):
    plan_id: str = "pro_monthly"


class AdminAddQuotaIn(BaseModel):
    stt_minutes: int = 0
    ai_requests: int = 0
