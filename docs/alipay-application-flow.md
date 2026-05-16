# TypeUp 支付宝申请与接入流程

更新时间：2026-05-16

本文档用于指导 TypeUp 项目申请和配置支付宝支付。当前项目后端需要的核心字段是：

- `ALIPAY_APP_ID`
- `ALIPAY_PRIVATE_KEY`
- `ALIPAY_PUBLIC_KEY`
- `ALIPAY_GATEWAY`
- `APP_BASE_URL`

## 一、先确认当前阶段

建议按两个阶段处理：

1. 开发测试阶段：优先使用支付宝沙箱，或者继续使用项目内置的模拟支付。
2. 正式上线阶段：再申请正式支付产品、完成商家签约、接入公网 HTTPS 回调地址。

开发阶段不建议一开始就切正式支付。先把沙箱支付流程跑通，后面切正式环境会更稳。

当前正式支付由项目组长负责继续开通：项目组长需要使用自己的支付宝商家主体重新走“电脑网站支付”开通流程，并生成自己的应用私钥、应用公钥和支付宝公钥。TypeUp 后端只接收最终正式参数，私钥不要通过群聊、截图或 GitHub 传递。

## 二、开发测试阶段：使用沙箱

### 1. 登录支付宝开放平台

打开支付宝开放平台：

https://open.alipay.com/

使用你的支付宝账号登录。

### 2. 进入控制台并找到沙箱

登录后进入开放平台控制台，查找“沙箱”或“沙箱环境”。

沙箱环境通常会提供：

- 沙箱应用的 `APPID`
- 沙箱买家账号
- 沙箱卖家账号
- 沙箱网关地址

TypeUp 沙箱网关使用：

```env
ALIPAY_GATEWAY=https://openapi-sandbox.dl.alipaydev.com/gateway.do
```

### 3. 生成 RSA2 密钥

打开支付宝开放平台工具页：

https://open.alipay.com/tool

下载或打开支付宝开发者工具，在密钥管理中生成 RSA2 密钥。

你会得到：

- 应用私钥：放到 TypeUp 后端 `.env`，不要提交到 GitHub。
- 应用公钥：上传到支付宝开放平台。

上传应用公钥后，支付宝平台会生成或展示：

- 支付宝公钥：放到 TypeUp 后端 `.env` 的 `ALIPAY_PUBLIC_KEY`。

注意：项目当前按“普通公钥模式”配置，不是“证书模式”。

### 4. 配置后端 `.env`

在后端项目 `voice-keyboard-backend` 的 `.env` 中配置：

```env
DEV_MOCK_PAYMENTS=false
APP_BASE_URL=https://你的后端公网域名

ALIPAY_APP_ID=你的沙箱或正式APPID
ALIPAY_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n你的应用私钥内容\n-----END PRIVATE KEY-----"
ALIPAY_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n支付宝公钥内容\n-----END PUBLIC KEY-----"
ALIPAY_GATEWAY=https://openapi-sandbox.dl.alipaydev.com/gateway.do
```

如果你暂时没有公网 HTTPS 域名，可以先继续使用：

```env
DEV_MOCK_PAYMENTS=true
```

这样项目会继续走模拟支付，不会请求支付宝真实接口。

## 三、正式上线阶段：申请正式支付产品

### 1. 创建网页/移动应用

打开网页/移动应用入口：

https://open.alipay.com/module/webApp

创建应用。TypeUp 是桌面端唤起浏览器付款页，正式支付产品优先看：

- 电脑网站支付

### 2. 准备商家主体资料

正式签约通常需要准备：

- 支付宝商家账号
- 企业或个体工商户主体信息
- 营业执照等主体资料
- 联系人信息
- 网站或应用信息
- 可访问的公网域名
- HTTPS 地址

具体要求以支付宝开放平台和商家中心实际页面为准。

### 3. 开通/签约支付产品

在应用中添加或签约“电脑网站支付”。

签约过程中支付宝会展示：

- 审核要求
- 结算规则
- 服务费率
- 协议条款

是否收费和具体费率以你签约页面显示为准。一般申请开放平台账号、创建应用、生成密钥、使用沙箱不收费；正式收款后会按签约费率收取交易服务费。

### 3.1 备选方案：服务商代开通

如果自己暂时没有营业执照或主体资料不完整，支付宝商家平台的“电脑网站支付”页面还有“服务商代开通”入口。

当前页面提示：服务商代开通在开通成功后需要支付约 100 元服务费。后续如果没有营业执照，可以考虑走这个服务商代开通流程。

注意事项：

- 这不是当前开发阶段必须做的事。
- 费用、服务内容、开通条件以支付宝页面和服务商实际说明为准。
- 选择服务商前要确认是否仍需要提供个人/个体工商户/网站等资料。
- 开通成功后，再把正式支付参数配置到 TypeUp 后端。

### 4. 配置正式环境

正式环境后端 `.env` 推荐配置：

```env
DEV_MOCK_PAYMENTS=false
APP_BASE_URL=https://你的后端公网域名

ALIPAY_APP_ID=你的正式APPID
ALIPAY_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n你的正式应用私钥\n-----END PRIVATE KEY-----"
ALIPAY_PUBLIC_KEY="-----BEGIN PUBLIC KEY-----\n正式支付宝公钥\n-----END PUBLIC KEY-----"
ALIPAY_GATEWAY=https://openapi.alipay.com/gateway.do
```

正式环境必须确保：

- `APP_BASE_URL` 是支付宝服务器可以访问的公网 HTTPS 地址。
- 后端 `/api/orders/{order_id}/alipay/notify` 能被支付宝回调访问。
- 私钥只保存在服务器 `.env` 或密钥管理服务中，不要提交 GitHub。

## 四、TypeUp 项目配置字段说明

| 字段 | 作用 | 从哪里获得 |
| --- | --- | --- |
| `ALIPAY_APP_ID` | 支付宝应用 ID | 开放平台应用详情或沙箱应用 |
| `ALIPAY_PRIVATE_KEY` | 应用私钥 | 支付宝开发者工具本地生成 |
| `ALIPAY_PUBLIC_KEY` | 支付宝公钥 | 上传应用公钥后，在支付宝开放平台获取 |
| `ALIPAY_GATEWAY` | 支付宝接口网关 | 沙箱或正式环境固定地址 |
| `APP_BASE_URL` | 后端公网根地址 | 你的服务器域名 |
| `DEV_MOCK_PAYMENTS` | 是否启用模拟支付 | 本项目 `.env` 自己控制 |

## 五、建议执行顺序

1. 先保持 `DEV_MOCK_PAYMENTS=true`，确认项目订单和会员逻辑正常。
2. 登录支付宝开放平台，进入沙箱。
3. 获取沙箱 `APPID`。
4. 使用支付宝开发者工具生成 RSA2 密钥。
5. 上传应用公钥，复制支付宝公钥。
6. 把沙箱参数填入后端 `.env`。
7. 将 `DEV_MOCK_PAYMENTS=false`，使用沙箱网关测试支付。
8. 沙箱支付跑通后，再准备商家主体和公网 HTTPS 域名。
9. 创建正式网页/移动应用，签约电脑网站支付；如果没有营业执照，可考虑“服务商代开通”。
10. 审核或代开通通过后，替换为正式 `APPID`、支付宝公钥和正式网关。

## 六、容易踩坑的地方

- 不要把应用私钥提交到 GitHub。
- `ALIPAY_PUBLIC_KEY` 要填“支付宝公钥”，不是“应用公钥”。
- 沙箱和正式环境的 `APPID`、公钥、网关不要混用。
- 没有公网 HTTPS 地址时，支付宝正式回调无法访问本机服务。
- 项目当前不支持支付宝证书模式，先使用普通公钥模式。
- 真实支付产品未签约前，不要把生产环境切到正式支付宝网关。
- 服务商代开通是后续备选，不要在没确认费用和资料要求前直接付款。

## 七、官方入口

- 支付宝开放平台：https://open.alipay.com/
- 网页/移动应用：https://open.alipay.com/module/webApp
- 支付宝开发者工具：https://open.alipay.com/tool
- 支付宝商家中心：https://b.alipay.com/
