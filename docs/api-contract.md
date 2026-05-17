# API Contract

TypeUp Desktop and the local engine should treat this backend as the source of truth for accounts, entitlements, quota, payments, and model proxying.

## Stable Client Surface

Public client APIs live under `/v1`:

```text
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/refresh
GET  /v1/auth/me

GET  /v1/plans
POST /v1/orders
GET  /v1/orders/{order_id}

POST /v1/stt/transcribe
POST /v1/llm/chat
```

Payment callbacks and admin APIs are server-side surfaces and should not be called directly by the desktop UI except for local mock payment links in development.

## Error Envelope

All JSON errors should use:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "请先登录",
    "status": 401
  }
}
```

Validation errors include `details`. Desktop code should branch on `error.code` and only display `error.message`.

## Ownership Rules

- The backend enforces entitlement and quota.
- The backend owns model provider credentials.
- Desktop clients only store TypeUp access and refresh tokens.
- Refresh tokens rotate. Clients must persist the latest returned refresh token.
- A `401` means retry refresh if a refresh token exists.
- A `403` means clear local auth state and require login again.
- A `402` means the user is authenticated but lacks active entitlement or quota.

## Model Proxy Rules

`/v1/stt/transcribe` accepts authenticated WAV uploads from trusted clients and returns transcript text plus metered duration.

`/v1/llm/chat` accepts bounded chat messages and returns text plus provider usage. It should remain provider-agnostic from the desktop perspective.

The desktop app should not call GLM, Alipay, or other provider credentials directly in TypeUp backend mode.
