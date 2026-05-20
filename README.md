# Voice Keyboard Backend

Voice Keyboard 软件版后端服务，负责账号、授权、订阅支付、用量计量，以及统一代理 STT/LLM 模型请求。

仓库职责边界见 [docs/repository-boundaries.md](docs/repository-boundaries.md)。当前仓库只负责云端账号、订阅、支付、额度和模型代理；桌面端 UI/本地 bridge 在 `typeup-win`，本地录音/热键/输入 engine 在 `voice-keyboard`。桌面端和 engine 依赖的 API 契约见 [docs/api-contract.md](docs/api-contract.md)。

## 功能概览

- 邮箱/密码注册与登录
- 新用户注册后自动发放隐藏的 `free_trial` 免费权益
- Access token + refresh token 鉴权
- 用户权益与 STT/AI 额度校验
- GLM-ASR-2512 语音识别代理
- 智谱 GLM 聊天/编辑代理
- 支付宝电脑网站支付
- 支付成功后自动开通权益
- 本地 mock 支付、mock STT、mock LLM，方便前端先联调
- Admin API：用户列表、手动开通、加额度、禁用账号

当前测试服务器通过 FRP 暴露为 `http://150.158.146.192:6053`，健康检查应返回 `ok=true`、`dev_mock_payments=true`、`dev_mock_models=false`。正式上线前仍需要替换为公网 HTTPS 域名，并关闭 mock 支付。

## 0.1.13 桌面端联调状态

`typeup-win` 0.1.13 主要修复 Windows `ALT + SPACE` AI 编辑后的热键状态残留、底部状态栏对齐、桌面/安装器图标尺寸，以及打包时自动重建内嵌 Python engine。后端 API 契约没有变化，新版桌面端仍通过 Electron 本地 server 调用本仓库的账号、订阅、订单、STT、LLM 和用量接口。

桌面端 AI 编辑已经迁移 macOS 版的 Instruction Mode：`ALT + SPACE` 录音后先调用本后端 STT 转写，再由本地 engine 做意图分类、安全上下文选择和文本替换执行。需要 LLM 的改写、生成、翻译、摘要等能力统一走本后端 `/v1/llm/chat`，由后端继续负责鉴权、权益校验、额度扣减和模型代理。选区读取、替换校验、撤销、删除、快捷键执行和状态框展示仍属于桌面端/engine 职责，后端不直接控制用户输入框。

支付宝回调处理已补强冲突保护：同一个 `trade_no` 只能绑定一个订单；已支付订单只接受相同交易号的重复通知，不能再绑定新的支付宝交易号。

本次发布前后端已验证：

- `.venv\Scripts\python.exe -m pytest -q`
- `.venv\Scripts\python.exe -m compileall -q app tests`

桌面端同步验证：

- `npm.cmd run build:win`
- `engine\voice-keyboard\.venv\Scripts\python.exe -m unittest discover -s engine\voice-keyboard\test`，共 126 项

测试服务器继续保持当前联调模式：真实 GLM 模型链路、mock 支付链路。正式上线真实支付宝收款前，仍需项目组长提供已开通“电脑网站支付”的正式支付宝应用参数，并把后端切到公网 HTTPS 域名。

## 本地启动

```powershell
cd C:\Users\Administrator\Desktop\ai_deploy\voice-keyboard-backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
Copy-Item .env.example .env
.venv\Scripts\uvicorn app.main:app --reload
```

需要运行本仓库测试时，先安装开发依赖：

```powershell
.venv\Scripts\pip install -r requirements-dev.txt
```

启动后：

```text
API Base URL: http://localhost:8000
Health:       http://localhost:8000/health
OpenAPI:      http://localhost:8000/openapi.json
Swagger UI:   http://localhost:8000/docs
```

## 环境变量

复制 `.env.example` 为 `.env`，本地联调推荐先使用 mock 模式：

```env
DATABASE_URL=sqlite:///./voice_keyboard.db
APP_BASE_URL=http://localhost:8000
JWT_SECRET=change-this-long-random-secret
ADMIN_API_KEY=change-this-admin-key
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
DEV_MOCK_MODE=false
DEV_MOCK_PAYMENTS=true
DEV_MOCK_MODELS=false

# Models
GLM_API_KEY=your_zhipuai_api_key
GLM_ASR_MODEL=glm-asr-2512
LLM_PROVIDER=zhipuai
LLM_MODEL=glm-4-flash

# Alipay
ALIPAY_APP_ID=your_app_id
ALIPAY_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
ALIPAY_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do
# Sandbox:
# ALIPAY_GATEWAY=https://openapi-sandbox.dl.alipaydev.com/gateway.do
```

字段说明：

- `APP_BASE_URL`：后端对外地址，支付宝回调和 mock `pay_url` 会使用它。
- `CORS_ORIGINS`：允许访问后端的前端 origin，多个用英文逗号分隔。
- `DEV_MOCK_MODE`：旧版总 mock 开关。设为 `true` 时会同时 mock 支付和模型。
- `DEV_MOCK_PAYMENTS`：只 mock 支付。真实支付宝应用未准备好时设为 `true`。
- `DEV_MOCK_MODELS`：只 mock STT/LLM。已有 GLM 密钥并想测真实模型时设为 `false`。
- `JWT_SECRET`：JWT 签名密钥，生产环境必须换成长随机字符串。
- `ADMIN_API_KEY`：Admin API 的 `X-Admin-Key`。

## 前端联调模式

如果真实支付宝还没准备好，但已有 GLM 密钥，建议使用当前模式：

```env
DEV_MOCK_MODE=false
DEV_MOCK_PAYMENTS=true
DEV_MOCK_MODELS=false
GLM_API_KEY=你的真实 GLM Key
```

开启后：

- `POST /v1/orders` 不再要求支付宝密钥，返回本地 mock `pay_url`。
- 浏览器打开 mock `pay_url` 后，订单会被标记为 `paid`，并自动开通对应套餐权益。
- `POST /v1/stt/transcribe` 仍校验 WAV-only 标准、鉴权和额度，并会请求真实 GLM-ASR。
- `POST /v1/llm/chat` 仍校验鉴权和额度，并会请求真实 GLM。
- `GET /health` 会返回 `dev_mock_mode`、`dev_mock_payments`、`dev_mock_models`，方便前端确认当前后端环境。

如果暂时没有 GLM 密钥，也可以把 `DEV_MOCK_MODELS=true`，这样 STT/LLM 会返回模拟结果。

## 注册与免费权益

注册接口会校验邮箱格式和密码长度，密码必须至少 8 位、最多 128 位。校验失败时会返回可直接展示给用户的中文提示，例如：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "密码至少 8 位",
    "status": 422,
    "details": []
  }
}
```

新用户注册成功后会自动获得隐藏套餐 `free_trial`：

```text
周期：30 天
STT：600 分钟
AI：3000 次
```

`free_trial` 不会出现在 `GET /v1/plans` 的可购买套餐列表中，只用于注册后自动开通。前端不需要让测试用户先购买或手动订阅，注册后刷新 `/v1/auth/me` 即可看到可用权益。

## 支付宝正式支付状态

当前开发和联调阶段继续使用 `DEV_MOCK_PAYMENTS=true`。支付宝开放平台的电脑网站支付接入指引已经走通，但正式收款仍需要项目组长使用自己的支付宝商家主体重新开通“电脑网站支付”，并生成正式参数。

后端切换真实支付宝支付前，需要项目组长提供并确认：

- `ALIPAY_APP_ID`：正式应用 APPID。
- `ALIPAY_PRIVATE_KEY`：项目组长应用对应的应用私钥，只能配置在服务器 `.env` 或密钥管理服务中，不要提交仓库。
- `ALIPAY_PUBLIC_KEY`：支付宝公钥，不是应用公钥。
- `ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do`。
- `APP_BASE_URL`：支付宝服务器可访问的公网 HTTPS 后端地址。

正式参数齐全并且“电脑网站支付”开通后，再把 `DEV_MOCK_PAYMENTS=false`。如果产品未开通、应用未上线，或 `APP_BASE_URL` 仍是本机地址，生产环境不要关闭 mock 支付。

推荐前端先打通这条链路：

1. `POST /v1/auth/register` 或 `POST /v1/auth/login`
2. 保存 `access_token` 和 `refresh_token`
3. `GET /v1/plans`
4. `POST /v1/orders`
5. 打开返回的 `pay_url`
6. 轮询 `GET /v1/orders/{order_id}`，直到 `status` 为 `paid`
7. 调用 `GET /v1/auth/me` 刷新权益状态
8. 调用 `POST /v1/stt/transcribe` 和 `POST /v1/llm/chat`

## TypeUp 桌面端联调

当前 Windows 前端项目位于：

```text
C:\Users\Administrator\Desktop\ai_deploy\typeup-win
```

TypeUp 桌面端接入方式：

- React UI 不直接请求本后端，而是请求 Electron 启动的本地 Node server。
- 本地 Node server 负责代理注册、登录、刷新 token、套餐、订单等接口。
- 登录成功后，本地 Node server 会把后端地址和 token 同时写入 `%APPDATA%\TypeUp\cloud-bridge.json` 和 Python engine 配置。
- Python engine 的 STT/LLM provider 使用 `typeup_backend`，统一调用本后端的 `/v1/stt/transcribe` 和 `/v1/llm/chat`。
- 后端负责权益校验、额度扣减、模型代理和支付状态。
- AI 指令编辑中的选区优先级、可追踪片段、替换计划校验、记忆片段、删除/撤销和快捷键执行都在 TypeUp 桌面端/engine 完成；后端只提供受鉴权保护的 STT/LLM 代理。
- 快捷键、悬浮状态框和本地热键策略由 TypeUp 桌面端/engine 管理；后端只负责账号、权益、额度、支付和模型代理，不下发平台快捷键配置。

推荐本地联调启动顺序：

```powershell
# 1. 启动后端
cd C:\Users\Administrator\Desktop\ai_deploy\voice-keyboard-backend
Copy-Item .env.example .env
# 确认 .env 内 DEV_MOCK_PAYMENTS=true，DEV_MOCK_MODELS=false，并填入 GLM_API_KEY
.venv\Scripts\uvicorn app.main:app --reload

# 2. 启动 TypeUp 前端
cd C:\Users\Administrator\Desktop\ai_deploy\typeup-win
npm.cmd install
npm.cmd run engine:setup
$env:TYPEUP_BACKEND_URL="http://localhost:8000"
npm.cmd run start
```

桌面端联调流程：

1. 在 TypeUp 左侧模块栏打开「账号」模块，填写后端地址。
2. 注册或登录账号。
3. 选择套餐并创建订单。
4. 在 mock 模式下打开 `pay_url`，订单会直接支付成功。
5. 刷新订单或账号状态，确认权益变为 active。
6. 启动本地引擎，STT/LLM 会通过后端代理执行。

测试版安装包已经默认使用 `http://150.158.146.192:6053`，给普通测试用户分发时不需要让他们手动填写后端地址。测试用户只需要注册账号，系统会自动给 `free_trial` 权益；只有验证付费链路时才需要点击套餐购买。

## 当前联调状态

当前后端已经和 `typeup-win` 本地桥接层跑通以下链路：

- 后端健康检查返回 `dev_mock_mode`、`dev_mock_payments`、`dev_mock_models`。
- React UI 通过 Electron 本地 server 注册、登录、刷新 session。
- 注册参数校验会返回明确提示；密码少于 8 位时返回「密码至少 8 位」，便于桌面端直接展示。
- 新注册账号会自动获得 `free_trial` 免费权益，额度为 30 天、600 分钟 STT、3000 次 AI 请求。
- 本地 server 会把后端地址、access token、refresh token 写入 Python engine 配置。
- 桌面端会在 engine 启动、STT/LLM 请求 401、以及刷新 session 后同步 `cloud-bridge.json` 与 engine 配置，避免旋转式 refresh token 失配后出现“刷新凭证无效”。
- `GET /v1/plans`、`POST /v1/orders`、mock `pay_url`、订单 `paid` 状态和权益刷新已打通。
- 支付宝 notify 会拒绝同一 `trade_no` 绑定到不同订单，也会拒绝已支付订单改绑新的交易号，避免支付回调重复或串单时污染订单状态。
- `POST /v1/stt/transcribe` 和 `POST /v1/llm/chat` 可用 `DEV_MOCK_MODELS=true` 验证 mock 模型链路，也可用真实 `GLM_API_KEY` 验证真实模型链路。
- `ALT + SPACE` AI 指令编辑链路已接入后端模型代理：语音指令经 `/v1/stt/transcribe` 识别，需要模型判断或改写时再经 `/v1/llm/chat`，额度和鉴权仍由本后端统一处理。
- AI 普通问答回复只在桌面端状态框展示，不会由后端或 engine 直接打进输入框；只有被桌面端识别为生成、改写或记忆片段召回的操作才会写入当前应用。
- refresh token 使用旋转机制，旧 refresh token 在刷新成功后会失效。
- TypeUp 桌面端快捷键提示会按当前平台和本地 engine 配置动态显示；Windows 默认 `ALT` / `ALT + SPACE`，macOS 默认右 `Shift` / 右 `Option`。
- 用户被 Admin API 禁用后，`POST /v1/auth/refresh` 会撤销当前 refresh token 并返回 `403 FORBIDDEN`。
- `/v1/llm/chat` 已限制消息数量、消息角色、消息长度、`temperature` 和 `max_tokens`，异常输入会返回统一 `VALIDATION_ERROR`。
- SQLite 本地模式下已处理时间字段的 UTC 归一化，避免 refresh token 过期判断出现 naive/aware datetime 比较错误。
- FastAPI 启动初始化已使用 lifespan，在启动时创建表并写入默认套餐。
- 本仓库测试依赖已拆分到 `requirements-dev.txt`；本地或 CI 跑测试前先安装开发依赖，再执行 `pytest tests`。

推荐每次改动后至少跑：

```powershell
cd C:\Users\Administrator\Desktop\ai_deploy\voice-keyboard-backend
.venv\Scripts\python.exe -m compileall app tests
.venv\Scripts\python.exe -m pytest tests
```

前后端联调时再走一遍：注册/登录 -> 创建订单 -> 打开 mock 支付 -> 刷新权益 -> STT -> LLM。

## 统一错误响应

所有 JSON 错误响应统一为：

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "请先登录",
    "status": 401
  }
}
```

参数校验错误会额外带 `details`：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "密码至少 8 位",
    "status": 422,
    "details": []
  }
}
```

前端建议按 `error.code` 做逻辑分支，`error.message` 只用于展示。

常见错误码：

```text
BAD_REQUEST
UNAUTHORIZED
PAYMENT_REQUIRED
FORBIDDEN
NOT_FOUND
CONFLICT
VALIDATION_ERROR
INTERNAL_SERVER_ERROR
UPSTREAM_ERROR
```

## 鉴权

需要登录的接口统一使用：

```text
Authorization: Bearer <ACCESS_TOKEN>
```

登录和注册都会返回：

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user": {
    "id": "usr_xxx",
    "email": "demo@example.com",
    "status": "active",
    "created_at": "2026-05-14T00:00:00Z"
  }
}
```

前端刷新策略：

- `access_token` 过期或接口返回 `401` 时，调用 `POST /v1/auth/refresh`。
- refresh 成功后替换本地的 `access_token` 和 `refresh_token`。
- TypeUp 桌面端需要同时更新 `cloud-bridge.json` 和 Python engine 配置；如果只更新其中一处，旧 refresh token 会因为旋转机制失效，后续 STT/LLM 可能返回“刷新凭证无效”。
- refresh 返回 `401` 或 `403` 时清空本地登录态并回到登录页；`403` 通常表示账号已停用。
- refresh token 是旋转式的，每次刷新都会返回新的 refresh token。

## 核心 API

### 健康检查

```text
GET /health
```

返回：

```json
{
  "ok": true,
  "dev_mock_mode": false,
  "dev_mock_payments": true,
  "dev_mock_models": false
}
```

### 认证

```text
POST /v1/auth/register
POST /v1/auth/login
POST /v1/auth/refresh
GET  /v1/auth/me
```

注册：

```bash
curl -X POST http://localhost:8000/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"password123"}'
```

注册密码至少 8 位。注册成功后会自动发放 `free_trial` 权益，前端可以立即调用 `GET /v1/auth/me` 刷新账号额度。

登录：

```bash
curl -X POST http://localhost:8000/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"password123"}'
```

刷新 token：

```bash
curl -X POST http://localhost:8000/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<REFRESH_TOKEN>"}'
```

当前用户和权益：

```bash
curl http://localhost:8000/v1/auth/me \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

`/v1/auth/me` 返回：

```json
{
  "user": {
    "id": "usr_xxx",
    "email": "demo@example.com",
    "status": "active",
    "created_at": "2026-05-14T00:00:00Z"
  },
  "entitlement": {
    "active": true,
    "plan_id": "free_trial",
    "starts_at": "2026-05-14T00:00:00Z",
    "ends_at": "2026-06-13T00:00:00Z",
    "stt_minutes_limit": 600,
    "stt_seconds_used": 0,
    "ai_requests_limit": 3000,
    "ai_requests_used": 0
  }
}
```

### 套餐与订单

```text
GET  /v1/plans
POST /v1/orders
GET  /v1/orders/{order_id}
```

查看套餐：

```bash
curl http://localhost:8000/v1/plans
```

创建订单：

```bash
curl -X POST http://localhost:8000/v1/orders \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{"plan_id":"pro_monthly","payment_method":"alipay"}'
```

订单返回：

```json
{
  "id": "ord_xxx",
  "user_id": "usr_xxx",
  "plan_id": "pro_monthly",
  "amount_cents": 2900,
  "currency": "CNY",
  "payment_method": "alipay",
  "status": "pending",
  "pay_url": "http://localhost:8000/v1/payments/mock/return?order_id=ord_xxx",
  "paid_at": null,
  "created_at": "2026-05-14T00:00:00Z"
}
```

查询订单：

```bash
curl http://localhost:8000/v1/orders/ord_xxx \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

订单状态：

```text
pending
paid
closed
refunded
```

### 支付流程

真实支付宝流程：

1. 前端登录，拿到 `access_token`。
2. 前端请求 `GET /v1/plans` 展示套餐。
3. 用户选择套餐后，前端请求 `POST /v1/orders`。
4. 后端创建订单并生成支付宝 `pay_url`。
5. 前端打开 `pay_url`，用户在浏览器中付款。
6. 支付宝异步通知 `POST /v1/payments/alipay/notify`。
7. 后端验签、校验金额、标记订单为 `paid`，并创建用户权益。
8. 前端轮询 `GET /v1/orders/{order_id}`，订单变为 `paid` 后刷新 `GET /v1/auth/me`。

mock 支付流程：

1. `.env` 设置 `DEV_MOCK_PAYMENTS=true`。
2. 前端请求 `POST /v1/orders`。
3. 前端打开返回的 mock `pay_url`。
4. 后端直接把订单标记为 `paid` 并开通权益。
5. 前端轮询订单并刷新 `/v1/auth/me`。

### STT 语音识别

```text
POST /v1/stt/transcribe
```

鉴权：

```text
Authorization: Bearer <ACCESS_TOKEN>
```

请求：

```text
multipart/form-data
字段名：file
MIME：audio/wav
```

音频必须使用 WAV-only 标准：

```text
格式：WAV
编码：PCM signed 16-bit little-endian
采样率：16000 Hz
声道：mono / 单声道
单次时长：不超过 30 秒
文件大小：不超过 25 MB
```

客户端不要直接上传 `webm`、`mp3`、`m4a`、`ogg` 或裸 `pcm`。如果录音源不是上述 WAV 标准，需要客户端先转成 `16kHz mono 16-bit PCM WAV` 后再上传。

示例请求：

```bash
curl -X POST http://localhost:8000/v1/stt/transcribe \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -F "file=@audio.wav;type=audio/wav"
```

返回：

```json
{
  "text": "识别文本",
  "audio_seconds": 1
}
```

常见错误：

```text
400: 音频格式不符合 WAV-only 标准，或文件为空、超长、超大
401: 未登录或 access token 失效
402: 当前用户没有有效权益，或 STT 额度不足
502: 上游 GLM-ASR 请求失败
```

### LLM 聊天

```text
POST /v1/llm/chat
```

请求：

```json
{
  "messages": [
    {
      "role": "user",
      "content": "帮我润色这句话"
    }
  ],
  "temperature": 0.1,
  "max_tokens": 1000
}
```

返回：

```json
{
  "text": "AI 回复文本",
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

常见错误：

```text
401: 未登录或 access token 失效
402: 当前用户没有有效权益，或 AI 请求额度不足
502: 上游 LLM 请求失败
```

## Admin API

Admin API 需要请求头：

```text
X-Admin-Key: <ADMIN_API_KEY>
```

接口：

```text
GET  /admin/users
GET  /admin/users/{user_id}
POST /admin/users/{user_id}/grant-pro
POST /admin/users/{user_id}/add-quota
POST /admin/users/{user_id}/disable
```

手动开通权益：

```bash
curl -X POST http://localhost:8000/admin/users/usr_xxx/grant-pro \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: <ADMIN_API_KEY>" \
  -d '{"plan_id":"pro_monthly"}'
```

加额度：

```bash
curl -X POST http://localhost:8000/admin/users/usr_xxx/add-quota \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: <ADMIN_API_KEY>" \
  -d '{"stt_minutes":60,"ai_requests":200}'
```

禁用用户：

```bash
curl -X POST http://localhost:8000/admin/users/usr_xxx/disable \
  -H "X-Admin-Key: <ADMIN_API_KEY>"
```

## 默认套餐

```text
free_trial
价格：0.00 CNY
周期：30 天
STT：600 分钟
AI：3000 次
说明：隐藏套餐，仅注册后自动发放，不在 GET /v1/plans 中展示

pro_monthly
价格：29.00 CNY
周期：30 天
STT：600 分钟
AI：3000 次

pro_yearly
价格：199.00 CNY
周期：365 天
STT：600 分钟
AI：3000 次
```

## 生产部署注意事项

- 使用 PostgreSQL 替代默认 SQLite。
- 使用长随机 `JWT_SECRET`。
- 不要把支付宝私钥提交到仓库。
- `APP_BASE_URL` 必须是支付宝可访问的公网 HTTPS 地址。
- 生产环境关闭 `DEV_MOCK_MODE`、`DEV_MOCK_PAYMENTS`、`DEV_MOCK_MODELS`。
- 按实际前端域名收窄 `CORS_ORIGINS`。
