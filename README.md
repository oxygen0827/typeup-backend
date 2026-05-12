# Voice Keyboard Backend

Voice Keyboard 软件版后端服务，负责账号、授权、订阅支付、用量计量，以及统一代理 STT/LLM 模型请求。

## 功能概览

- 邮箱/密码注册与登录
- Access token + refresh token 鉴权
- 用户权益与额度校验
- GLM-ASR-2512 语音识别代理
- 智谱 GLM 聊天/编辑代理
- 支付宝电脑网站支付
- 支付成功后自动开通权益
- 简单 Admin API：用户列表、手动开通、加额度、禁用账号

## 本地启动

```powershell
cd C:\Users\19051\Desktop\ai_deploy\voice-keyboard-backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\uvicorn app.main:app --reload
```

复制 `.env.example` 为 `.env`，填写密钥：

```env
DATABASE_URL=sqlite:///./voice_keyboard.db
APP_BASE_URL=http://localhost:8000
JWT_SECRET=change-this-long-random-secret
ADMIN_API_KEY=change-this-admin-key

GLM_API_KEY=your_zhipuai_api_key
GLM_ASR_MODEL=glm-asr-2512
LLM_PROVIDER=zhipuai
LLM_MODEL=glm-4-flash

ALIPAY_APP_ID=your_app_id
ALIPAY_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
ALIPAY_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do
```

支付宝沙箱：

```env
ALIPAY_GATEWAY=https://openapi-sandbox.dl.alipaydev.com/gateway.do
```

## 核心 API

认证：

```text
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/refresh
GET  /v1/auth/me
```

支付与套餐：

```text
GET  /v1/plans
POST /v1/orders
GET  /v1/orders/{order_id}
POST /v1/payments/alipay/notify
```

模型代理：

```text
POST /v1/stt/transcribe
POST /v1/llm/chat
```

管理接口：

```text
GET  /admin/users
GET  /admin/users/{user_id}
POST /admin/users/{user_id}/grant-pro
POST /admin/users/{user_id}/add-quota
POST /admin/users/{user_id}/disable
```

Admin API 需要请求头：

```text
X-Admin-Key: <ADMIN_API_KEY>
```

## 用户支付流程

1. 客户端登录，拿到 `access_token`。
2. 客户端请求 `GET /v1/plans` 展示套餐。
3. 用户选择套餐后，客户端请求 `POST /v1/orders`。
4. 后端根据当前登录用户创建订单，生成支付宝 `pay_url`。
5. 客户端打开 `pay_url`，用户在浏览器中完成支付宝付款。
6. 支付宝异步通知 `/v1/payments/alipay/notify`。
7. 后端验签、校验金额、标记订单为 `paid`，并创建用户权益。
8. 客户端轮询 `GET /v1/orders/{order_id}`，订单变为 `paid` 后刷新 `/v1/auth/me`。

支付成功后，权益示例：

```text
plan_id = pro_monthly
starts_at = 当前时间
ends_at = 当前时间 + 30 天
stt_minutes_limit = 600
ai_requests_limit = 3000
status = active
```

## 示例请求

注册：

```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"password123"}'
```

登录：

```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"password123"}'
```

查看套餐：

```bash
curl http://localhost:8000/v1/plans
```

创建支付宝订单：

```bash
curl -X POST http://localhost:8000/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"plan_id":"pro_monthly","payment_method":"alipay"}'
```

返回里会包含 `pay_url`。桌面客户端打开该链接，然后轮询：

```bash
curl http://localhost:8000/v1/orders/ord_xxx \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

## Notes

This service provides the backend for Voice Keyboard software launch:

- Account registration and login
- Access token and refresh token auth
- Entitlement and quota checks
- GLM-ASR-2512 STT proxy
- Zhipu GLM chat proxy
- Alipay computer website payment
- Paid order to entitlement activation

For production:

- Use PostgreSQL instead of the default SQLite database.
- Use a long random `JWT_SECRET`.
- Keep Alipay private keys out of source control.
- `APP_BASE_URL` must be a public HTTPS URL reachable by Alipay notify callbacks.
