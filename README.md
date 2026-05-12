# Voice Keyboard Backend

Backend service for Voice Keyboard software launch:

- Email/password account registration and login
- Access token + refresh token auth
- Entitlements and quota checks
- GLM-ASR-2512 STT proxy
- Zhipu GLM chat proxy
- Alipay computer website payment
- Paid order to entitlement activation

## Run locally

```bash
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --reload
```

Copy `.env.example` to `.env` and fill secrets.

## Main API

Auth:

```text
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/refresh
GET  /v1/auth/me
```

Billing:

```text
GET  /v1/plans
POST /v1/orders
GET  /v1/orders/{order_id}
POST /v1/payments/alipay/notify
```

Model proxy:

```text
POST /v1/stt/transcribe
POST /v1/llm/chat
```

## Alipay environment

Use Alipay computer website payment (`alipay.trade.page.pay`).

```env
DATABASE_URL=sqlite:///./voice_keyboard.db
APP_BASE_URL=https://api.example.com
ALIPAY_APP_ID=your_app_id
ALIPAY_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----..."
ALIPAY_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----..."
ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do
```

For sandbox testing, set:

```env
ALIPAY_GATEWAY=https://openapi-sandbox.dl.alipaydev.com/gateway.do
```

## Payment flow

1. App calls `GET /v1/plans`.
2. App calls `POST /v1/orders` with `plan_id` and `user_id`.
3. Backend returns a `pay_url`; the desktop app opens it in a browser.
4. Alipay sends async notification to `/v1/payments/alipay/notify`.
5. Backend verifies the signature, marks the order paid, and grants entitlement.

## API examples

Register:

```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"password123"}'
```

List plans:

```bash
curl http://localhost:8000/v1/plans
```

Create an Alipay order:

```bash
curl -X POST http://localhost:8000/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"plan_id":"pro_monthly","payment_method":"alipay"}'
```

The response contains `pay_url`. The desktop app should open this URL in the
user's browser, then poll:

```bash
curl http://localhost:8000/v1/orders/ord_xxx
```

When the order becomes `paid`, refresh the user's entitlement.

## Notes

- `notify_url` must be a public HTTPS URL reachable by Alipay.
- The backend returns plain text `success` to Alipay only after signature,
  amount, and order checks pass.
- For production, replace the default SQLite URL with PostgreSQL.
