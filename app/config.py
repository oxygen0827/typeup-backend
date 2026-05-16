from functools import lru_cache
import os

from pydantic import BaseModel


DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


def _load_dotenv() -> None:
    env_path = os.path.join(os.getcwd(), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            os.environ.setdefault(key, value)


class Settings(BaseModel):
    database_url: str = "sqlite:///./voice_keyboard.db"
    app_base_url: str = "http://localhost:8000"
    cors_origins: list[str] = DEFAULT_CORS_ORIGINS
    dev_mock_mode: bool = False
    dev_mock_payments: bool = False
    dev_mock_models: bool = False

    alipay_app_id: str = ""
    alipay_private_key: str = ""
    alipay_public_key: str = ""
    alipay_gateway: str = "https://openapi.alipay.com/gateway.do"
    alipay_return_url: str = ""
    jwt_secret: str = "change-me-in-production"
    access_token_minutes: int = 30
    refresh_token_days: int = 30
    glm_api_key: str = ""
    glm_asr_model: str = "glm-asr-2512"
    llm_provider: str = "zhipuai"
    llm_model: str = "glm-4-flash"
    admin_api_key: str = ""

    @property
    def alipay_notify_url(self) -> str:
        return f"{self.app_base_url.rstrip('/')}/v1/payments/alipay/notify"

    @property
    def resolved_return_url(self) -> str:
        if self.alipay_return_url:
            return self.alipay_return_url
        return f"{self.app_base_url.rstrip('/')}/v1/payments/alipay/return"


@lru_cache
def get_settings() -> Settings:
    _load_dotenv()
    legacy_mock_mode = _bool_env("DEV_MOCK_MODE", False)
    return Settings(
        database_url=os.getenv("DATABASE_URL", Settings.model_fields["database_url"].default),
        app_base_url=os.getenv("APP_BASE_URL", Settings.model_fields["app_base_url"].default),
        cors_origins=_csv_env("CORS_ORIGINS", DEFAULT_CORS_ORIGINS),
        dev_mock_mode=legacy_mock_mode,
        dev_mock_payments=_bool_env("DEV_MOCK_PAYMENTS", legacy_mock_mode),
        dev_mock_models=_bool_env("DEV_MOCK_MODELS", legacy_mock_mode),
        alipay_app_id=os.getenv("ALIPAY_APP_ID", ""),
        alipay_private_key=os.getenv("ALIPAY_PRIVATE_KEY", ""),
        alipay_public_key=os.getenv("ALIPAY_PUBLIC_KEY", ""),
        alipay_gateway=os.getenv("ALIPAY_GATEWAY", Settings.model_fields["alipay_gateway"].default),
        alipay_return_url=os.getenv("ALIPAY_RETURN_URL", ""),
        jwt_secret=os.getenv("JWT_SECRET", Settings.model_fields["jwt_secret"].default),
        access_token_minutes=int(os.getenv("ACCESS_TOKEN_MINUTES", Settings.model_fields["access_token_minutes"].default)),
        refresh_token_days=int(os.getenv("REFRESH_TOKEN_DAYS", Settings.model_fields["refresh_token_days"].default)),
        glm_api_key=os.getenv("GLM_API_KEY", ""),
        glm_asr_model=os.getenv("GLM_ASR_MODEL", Settings.model_fields["glm_asr_model"].default),
        llm_provider=os.getenv("LLM_PROVIDER", Settings.model_fields["llm_provider"].default),
        llm_model=os.getenv("LLM_MODEL", Settings.model_fields["llm_model"].default),
        admin_api_key=os.getenv("ADMIN_API_KEY", ""),
    )


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if value is None:
        return list(default)
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or list(default)
