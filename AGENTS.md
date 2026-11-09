# 浙江理工福瑞圈（Furry ZJUT）— 项目架构与实施规范

> **最终部署边界（请以此为准）：只有前端静态页面部署在腾讯云 EdgeOne Pages；后端整体部署在同一台宝塔 2C2G 服务器上，包括 FastAPI API、PostgreSQL、Redis、Nginx 反向代理及 systemd 服务。** COS/对象存储、邮件/短信/人机验证等第三方云服务属于外部托管依赖，不部署在这台 2C2G 服务器上。


> **项目定位：** 面向浙江理工大学相关 Furry 社群的门户、图片展示、成员空间、课表工具与活动运营平台。  
> **架构目标：** 前后端分离、对象存储优先、API 独立部署、配置驱动运营、安全可审计、可逐步扩展。  
> **文档性质：** 本文是技术选型与开发约定。实际接入的云厂商、短信/邮件服务商、对象存储产品及备案信息均由部署方配置，不在代码中写死。

---

## 0. 总体建议与关键决策

### 0.1 推荐技术栈

| 层 | 推荐方案 | 说明 |
|---|---|---|
| Web 前端 | Vue 3 + TypeScript + Vite | SPA，组件化开发；构建后部署至腾讯云 EdgeOne Pages |
| UI / 样式 | Tailwind CSS + 自选组件库 | 统一设计令牌，支持响应式 |
| 状态管理 | Pinia | 只保存必要的客户端状态 |
| 路由 | Vue Router | 路由守卫只负责体验，权限最终由后端判定 |
| HTTP | Axios 或原生 fetch 封装 | 统一超时、错误处理、请求 ID、刷新令牌 |
| 后端 API | Python 3.11+ + FastAPI | 类型校验、OpenAPI、异步 I/O、开发效率高 |
| 数据校验 | Pydantic v2 | 请求/响应 Schema |
| ORM / 迁移 | SQLAlchemy 2.x + Alembic | 数据模型和版本化迁移 |
| 生产数据库 | PostgreSQL | 正式环境统一使用 PostgreSQL |
| 缓存 / 限流 / 队列 | Redis | 缓存、验证码状态、限流计数、任务队列 |
| 异步任务 | Celery / Dramatiq / ARQ（三选一） | 邮件、短信、图片处理、清理任务 |
| 文件存储 | S3 兼容对象存储 | 例如云厂商 OSS / COS / OBS / S3；通过适配层接入 |
| CDN | CDN + 自定义存储域名 | 图片分发与缓存 |
| 反向代理 | Nginx / Caddy / 云负载均衡 | TLS、路由、基础安全头 |
| 部署 | EdgeOne Pages + 宝塔 2C2G 原生部署 | 前端托管与 API 主机分离；API、PostgreSQL、Redis 本机运行，Nginx + systemd |
| 可观测性 | 结构化日志 + Sentry 类错误追踪 + Prometheus/Grafana（按需） | 请求追踪、告警、性能指标 |

### 0.2 Python 后端是否合适？

**结论：本项目使用 Python + FastAPI 是合适的，建议继续采用，不需要为了“性能”盲目换语言。**

适合的原因：
- 图片、用户、相册、活动、课表解析、邮件/短信调用等业务以数据库、对象存储和第三方 API I/O 为主，FastAPI 足够胜任。
- Python 的 PDF/TXT/ICS 解析生态成熟，适合课表解析及后续数据处理。
- FastAPI + Pydantic 能快速建立清晰的 API 契约和自动 OpenAPI 文档。
- 业务规模尚未证明需要 Go、Java 或微服务架构，先保持单体分层架构更容易开发、测试和部署。

需要注意：
- `async def` 不会自动让 CPU 密集任务变快。PDF 解析、图片转码、缩略图生成等任务应放入后台任务/独立 Worker，避免阻塞 API 事件循环。
- 不要在异步路由中直接调用阻塞式 SDK；使用异步客户端、线程池或后台任务。
- FastAPI 不是安全网关。限流、WAF、Bot 防护和 DDoS 防护应由边缘/CDN/API 网关承担一部分，应用层仍需做用户级限流和权限校验。
- 初期采用**模块化单体（Modular Monolith）**，不要一开始拆成多个微服务。模块边界清晰即可。

何时考虑其他语言：
- 大量 CPU 密集型实时处理、超高并发长连接或团队已有成熟 Go/Java 基础设施时，再评估独立服务。
- 即使未来增加 Go 服务，用户、内容、活动等主业务仍可由 FastAPI 管理，不必整体重写。

### 0.3 域名规划

建议将前端站点与 API 分离：

| 域名 | 用途 | 访问策略 |
|---|---|---|
| `www.example.com` | 主站前端 | 腾讯云 EdgeOne Pages（静态托管/CDN） |
| `api.example.com` | 后端 API | DNS 指向宝塔 2C2G 服务器；Nginx 反向代理至本机 FastAPI |
| `static.example.com` | 前端静态资源（可选） | EdgeOne Pages/CDN 或静态资源 CDN |
| `img.example.com` | 对象存储图片代理域名（可选） | CDN 回源对象存储 |
| `admin.example.com` | 管理后台（可选独立域名） | 建议额外 MFA、访问策略和审计 |
| `status.example.com` | 服务状态页（可选） | 仅公开运行状态，不泄露内部信息 |

说明：
- 上述 `example.com` 仅为占位符，部署时替换为实际域名。
- API 域名应启用 HTTPS、严格 CORS、请求体大小限制和安全响应头。
- 如果前端与 API 跨站，Cookie 认证需正确设置 `Secure`、`HttpOnly`、`SameSite`，并配套 CSRF 防护。
- 不建议把对象存储桶设为可任意写入的公开桶。上传应由后端签发短时效预签名 URL，或由后端代理上传。
- `img` 域名可以切换为自定义 CDN/代理域名，但数据库保存对象 Key，不应把某个 CDN 域名永久写入每条图片记录。

---

## 一、核心架构

```text
浏览器 / 移动端
      |
      +---- www.example.com -------- CDN / Web 前端
      |                                  |
      |                                  +-- Vue 3 SPA
      |
      +---- api.example.com -------- WAF / API 网关 / 反向代理
                                         |
                                      FastAPI
                                         |
              +--------------------------+--------------------------+
              |             |             |            |             |
          PostgreSQL      Redis       Object Store   Worker      外部服务
          业务数据       缓存/限流       图片/文件     异步任务    邮件/短信/验证码
              |             |             |            |             |
              +-------------+-------------+------------+-------------+
```

原则：
1. 前端只通过版本化 API 与后端通信，不直连数据库。
2. 业务元数据放 PostgreSQL，文件二进制放对象存储。
3. Redis 不作为唯一数据源；缓存丢失不能导致用户、订单式业务记录或文件元数据丢失。
4. 所有外部服务通过 Provider/Adapter 接口接入，避免绑定单一云厂商。
5. 管理操作、权限变更、内容审核、配置发布均记录审计日志。

---

## 二、项目目录结构

```text
furry-zjut/
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── api/                    # API 客户端、类型、错误处理
│   │   ├── assets/
│   │   ├── components/
│   │   ├── composables/
│   │   ├── layouts/
│   │   ├── router/
│   │   ├── stores/
│   │   ├── types/
│   │   ├── utils/
│   │   └── views/
│   │       ├── Home.vue
│   │       ├── Gallery.vue
│   │       ├── Schedule.vue
│   │       ├── Events.vue
│   │       ├── About.vue
│   │       ├── Profile.vue
│   │       ├── DynamicPage.vue       # 活动/临时页面渲染入口
│   │       └── admin/
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── redis.py
│   │   │   ├── security.py
│   │   │   ├── logging.py
│   │   │   └── permissions.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/            # 数据访问层（复杂查询时使用）
│   │   ├── services/                # 业务逻辑层
│   │   ├── providers/
│   │   │   ├── storage/
│   │   │   ├── email/
│   │   │   ├── sms/
│   │   │   ├── captcha/
│   │   │   └── human_verification/
│   │   ├── workers/                 # 异步任务
│   │   ├── middleware/
│   │   └── utils/
│   ├── migrations/                  # Alembic
│   ├── tests/
│   └── pyproject.toml
│
├── deploy/
│   ├── nginx/                    # 宝塔 API 站点配置模板
│   ├── edgeone/                  # EdgeOne Pages 配置/部署说明
│   └── scripts/
├── docs/
│   ├── API.md
│   ├── SECURITY.md
│   └── DEPLOYMENT.md
├── .env.example
├── docker-compose.yml
└── README.md
```

约定：
- Router 只处理 HTTP 层：参数、认证依赖、响应码。
- Service 处理业务规则。
- Provider 负责调用对象存储、邮件、短信、验证码等外部服务。
- Model 表示数据库实体，Schema 表示 API 输入输出，二者不要混用。
- 复杂业务逻辑不要全部堆在 `main.py` 或路由函数中。

---

## 三、业务模块

### 3.1 用户、注册与认证

注册至少收集：
- 用户名（唯一）
- 昵称
- 邮箱
- 手机号（含国家/地区码）
- 密码
- 邮箱验证码
- 手机验证码
- 用户协议及隐私政策确认记录

推荐注册流程：
1. 用户填写邮箱、手机号、用户名和密码。
2. 邮箱与手机号分别发送一次性验证码。
3. 后端校验验证码、有效期、发送次数、尝试次数及用途。
4. 创建 `pending` 状态用户。
5. 管理员审批通过后激活账号；摄影师申请需额外提交申请理由和作品集链接。
6. 激活后允许登录；重要操作可要求重新验证邮箱/手机号或 MFA。

设计注意：
- 邮箱和手机号应分别唯一；手机号存储为标准化 E.164 格式。
- 验证码只保存哈希值，不保存明文；设置短有效期、单次使用、发送冷却和失败锁定。
- 验证码必须绑定用途（注册、改邮箱、找回密码等），不可跨用途复用。
- 不向客户端暴露账号是否存在等不必要信息，降低账号枚举风险。
- 手机号、邮箱属于个人信息，应限制后台可见范围、日志脱敏并制定删除/保留策略。
- 可预留 OAuth 登录，但第三方登录不能绕过账号绑定和风险控制。

认证建议：
- 浏览器优先考虑服务端安全 Cookie（HttpOnly + Secure）和 CSRF 防护。
- 若使用 JWT：短时效 Access Token + 可撤销 Refresh Token；Refresh Token 轮换、复用检测、设备会话管理。
- 密码使用 Argon2id 或经过充分评估的 bcrypt；不自行设计密码哈希算法。
- 管理员启用 MFA；支持退出所有设备、查看登录设备、撤销会话。
- 登录、注册、验证码、密码重置均设置 IP、账号、设备维度限流。

### 3.2 角色与权限（RBAC）

角色建议：
- `guest`：游客
- `member`：普通成员
- `photographer`：摄影师
- `moderator`：内容审核员（可选）
- `admin`：管理员
- `super_admin`：系统最高管理员（可选，权限应极少）

权限必须由后端逐请求校验。角色用于分组，细粒度操作使用 permission，例如：
- `gallery.image.upload`
- `gallery.image.publish`
- `gallery.image.delete.any`
- `profile.image.read.own`
- `event.manage`
- `page.publish`
- `site_config.manage`
- `user.approve`
- `audit_log.read`

避免仅凭前端路由守卫或按钮隐藏来保护接口。

### 3.3 图片与个人相册

公开 Gallery：
- 图片列表、详情、标签、日期筛选、分页。
- 摄影师/管理员上传后可按配置直接发布；普通成员上传进入待审核队列。
- 支持审核、下架、删除、举报、版权/署名信息。
- 原图、展示图、缩略图分层存储；支持 WebP/AVIF 派生图。
- 图片元数据记录宽高、文件大小、MIME、SHA-256、对象 Key、处理状态。

个人空间：
- 默认私有，仅本人可见。
- 管理员访问需有明确权限并记录审计原因。
- 私有图片下载通过后端鉴权后签发短时效预签名 URL。
- 不允许通过猜测对象 Key 访问其他用户文件。

上传安全：
- 校验文件大小、真实文件类型、扩展名、图片解码结果。
- 随机生成对象 Key，不直接使用用户文件名作为存储路径。
- 限制 SVG、HTML、脚本、压缩包等高风险类型；如需支持 SVG，必须净化内容并采用独立来源域名。
- 可选接入恶意文件扫描。
- 上传成功后由 Worker 生成缩略图、元数据和内容指纹。
- 删除采用数据库软删除/状态标记与对象存储清理任务配合，避免数据库与对象存储不一致。

### 3.4 课表解析与对比

保留原有功能：
- ICS：Python `icalendar`。
- ZJUT PDF/TXT：自定义解析器。
- 内部统一为 `CourseSlot`。
- 支持两人及多人空闲时间对比、同教室同时间冲突检查、推荐聚会时间。

建议增加：
- 解析任务异步执行，返回 `job_id`，前端轮询任务状态。
- 保存原文件时采用私有对象存储。
- 课表默认私有；公开分享必须由用户主动开启，并支持随时撤销。
- 课表设置过期时间、自动清理与下载权限。
- 解析失败时返回可定位的错误信息，不把原始堆栈返回前端。

### 3.5 活动、公告与报名

建议从预留功能提升为正式模块：
- 活动创建、编辑、草稿、发布、报名开始/截止时间。
- 报名人数上限、候补名单、取消报名。
- 签到码/二维码、签到记录、活动管理员。
- 活动图片、附件、地点、时间、组织者。
- 公告置顶、定时发布、过期下架。
- 站内通知与邮件通知；短信仅用于必要的高优先级通知。
- 防止重复报名、超额报名和重复签到；关键操作使用事务和幂等键。

---

## 四、对象存储与图片域名设计

### 4.1 存储策略

生产环境使用 S3 兼容对象存储，数据库仅保存元数据和对象 Key。

推荐逻辑分区（可使用同一 Bucket 的不同前缀，也可按安全级别拆 Bucket）：

```text
public/
  gallery/original/{yyyy}/{mm}/{random_id}
  gallery/derived/{yyyy}/{mm}/{random_id}/
  site-assets/{random_id}

private/
  profiles/{user_id}/{random_id}
  schedules/{user_id}/{random_id}
  event-private/{event_id}/{random_id}
```

建议：
- 公开图片和私有文件采用不同访问策略，最好使用不同 Bucket 或独立访问策略。
- Bucket 默认私有；公开内容通过 CDN 自定义域名读取，私有内容通过短时效签名 URL 访问。
- 数据库保存 `storage_provider`、`bucket`、`object_key`、`visibility`、`mime_type`、`size_bytes`、`checksum` 等字段。
- 不把长期有效的对象存储密钥放在前端。
- 生产密钥通过环境变量或 Secret 管理服务注入，禁止提交 Git。

### 4.2 自定义代理域名

管理后台提供存储/CDN 配置：
- 对象存储服务商类型。
- Endpoint、Region、Bucket。
- 公开访问域名，例如 `https://img.example.com`。
- 可选备用域名/代理域名。
- 私有文件签名有效期。
- CDN 缓存策略与刷新接口配置。
- 域名健康检查和配置状态。

重要约定：
- 数据库存储对象 Key，而不是完整 URL。
- URL 由后端根据当前有效域名配置动态生成。
- 更换图片域名时无需批量修改图片记录。
- 备用域名切换必须校验 HTTPS、域名归属和对象路径映射。
- 不允许管理员把任意 URL 配置成图片代理回源地址，否则可能造成 SSRF。
- 代理回源目标应限制为已验证的存储服务商和白名单域名。

### 4.3 上传流程

1. 前端向 API 申请上传凭证，提交文件名、大小、MIME、用途。
2. 后端校验用户权限、配额、文件类型和上传频率。
3. 后端生成随机 Object Key 和短时效预签名上传 URL。
4. 前端直接上传到对象存储。
5. 前端通知 API 上传完成。
6. 后端验证对象是否存在、大小和元数据；标记为待处理。
7. Worker 扫描/解码/生成缩略图。
8. 根据审核状态设置公开或私有访问策略。

如果云服务商不支持预签名上传，可由后端代理上传，但要设置严格的请求体大小和超时限制。

---

## 五、邮件、短信、验证码与人机验证网关

### 5.1 Provider 抽象

不要把云厂商 SDK 写进业务路由。统一定义接口：

```python
class EmailProvider:
    async def send(self, to: str, subject: str, template: str, variables: dict): ...

class SmsProvider:
    async def send_code(self, phone: str, template: str, variables: dict): ...

class CaptchaProvider:
    async def verify(self, token: str, remote_ip: str | None = None) -> bool: ...

class HumanVerificationProvider:
    async def verify(self, token: str, remote_ip: str | None = None) -> bool: ...
```

具体实现可接入：
- 云厂商邮件推送服务 / SMTP。
- 云厂商短信服务。
- 云厂商验证码/安全验证产品。
- 第三方 CAPTCHA / Bot 检测服务。
- 后续可增加备用服务商。

“云服务商验证码网关”和“第三方人机验证接口”应区分：
- **验证码发送网关：** 邮件/短信 OTP 的发送、模板、签名、频控。
- **人机验证：** 判断请求是否由真实用户发起，防自动化注册、撞库和刷接口。
- 二者可组合使用，不能把短信验证码当作唯一 Bot 防护。

### 5.2 验证策略

按风险场景启用：
- 注册：人机验证 + 邮箱 OTP + 手机 OTP。
- 登录：风险评分异常时触发人机验证；密码错误次数限制。
- 找回密码：人机验证 + 邮箱或手机号验证。
- 批量上传、评论、报名：按风险和频率触发验证。
- 管理员登录及敏感操作：MFA/重新认证。

安全要求：
- 第三方验证 Token 必须由后端向验证服务校验，不能只相信前端返回的“成功”状态。
- 校验 Token 的有效期、站点密钥、动作名称、域名/来源和服务端响应。
- 验证失败或服务不可用时采用明确的降级策略；注册、登录等敏感操作默认失败关闭。
- 不同用途使用不同验证码记录；验证码短时效、单次使用、哈希存储。
- 对 IP、手机号、邮箱、账号、设备指纹设置分层发送频控和每日配额。
- 对短信费用设置预算告警和异常发送熔断，防止短信轰炸及资损。

---

## 六、API 设计、限流与网关

### 6.1 API 规范

- 统一前缀：`/api/v1`。
- 统一 JSON 响应结构和错误码。
- 所有列表接口支持分页，限制最大 page size。
- 上传接口独立设置大小限制和超时。
- 写操作使用权限校验；对报名、支付类未来业务使用幂等键。
- API 文档仅在开发环境或管理员授权后公开。
- 生产环境禁用调试模式，不向客户端返回堆栈、SQL、密钥或内部路径。
- 使用 OpenAPI 生成前端类型或客户端，减少接口字段漂移。

建议响应结构：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "request_id": "server-generated-id"
}
```

错误响应示例：

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "RATE_LIMITED",
    "message": "请求过于频繁，请稍后再试"
  },
  "request_id": "server-generated-id"
}
```

### 6.2 多层限流

| 层级 | 维度 | 示例策略（上线后按流量调优） |
|---|---|---|
| CDN/WAF | IP、地区、Bot 特征 | 拦截明显恶意流量、DDoS |
| API 网关 | IP、路径、请求体大小 | 全局与单路径限制 |
| 应用层 | 用户 ID、IP、设备 | 登录、注册、上传分别限流 |
| 业务层 | 邮箱、手机号、资源 ID | OTP 发送、报名、评论限频 |

示例初始策略（不是固定安全标准）：
- 登录：每 IP 与每账号分别限制，连续失败后指数退避。
- 注册：IP、邮箱、手机号多维限流。
- 邮件/短信验证码：设置发送冷却、每小时/每日配额和重发上限。
- 上传：按用户角色设置并发数、单文件大小、每日容量。
- 公共列表：限制分页大小和查询复杂度。
- 管理 API：更严格限流并记录审计。

实现：
- Redis 作为分布式计数器，使用原子操作/Lua 脚本避免并发绕过。
- 返回 HTTP `429` 和合理的 `Retry-After`。
- 限流规则放配置中心/数据库，支持启停、调整与变更审计。
- 可信代理 IP 只能从已配置的反向代理链读取，不能无条件信任客户端 `X-Forwarded-For`。

---

## 七、动态页面 / 临时活动页面系统

目标：管理员可在后台创建临时活动页面，API 返回页面数据，Vue 前端使用统一渲染器生成页面；无需每次活动都重新构建前端。

### 7.1 推荐方案：Schema 驱动，而非任意 HTML 执行

API 返回 JSON 页面 Schema，前端通过白名单组件渲染：

```json
{
  "slug": "welcome-party-2026",
  "title": "迎新活动",
  "status": "published",
  "starts_at": "2026-11-20T09:00:00+08:00",
  "ends_at": "2026-11-22T18:00:00+08:00",
  "theme": {
    "primary": "#6B5CE7",
    "background": "#F7F6FC"
  },
  "blocks": [
    {
      "type": "hero",
      "props": {
        "title": "欢迎来到活动现场",
        "subtitle": "活动介绍",
        "image": "site-assets/hero-example"
      }
    },
    {
      "type": "rich_text",
      "props": {
        "content": "经过净化的 Markdown 内容"
      }
    },
    {
      "type": "countdown",
      "props": {
        "target": "2026-11-20T09:00:00+08:00"
      }
    },
    {
      "type": "button",
      "props": {
        "label": "立即报名",
        "action": "event_register",
        "event_id": "event-id"
      }
    }
  ]
}
```

前端建立组件白名单：
- `hero`
- `rich_text`
- `image`
- `gallery`
- `countdown`
- `schedule`
- `button`
- `notice`
- `event_info`
- `registration_form`

未知组件类型直接忽略并记录错误，不执行其内容。

### 7.2 页面 API

```text
GET    /api/v1/pages/{slug}             # 获取已发布页面
GET    /api/v1/admin/pages              # 管理员页面列表
POST   /api/v1/admin/pages              # 创建页面
PUT    /api/v1/admin/pages/{id}         # 修改草稿
POST   /api/v1/admin/pages/{id}/publish # 发布
POST   /api/v1/admin/pages/{id}/unpublish
DELETE /api/v1/admin/pages/{id}         # 删除/归档
```

页面字段：
- `id`、`slug`、`title`、`description`
- `status`（draft/published/archived）
- `schema_json`
- `starts_at`、`ends_at`
- `published_at`、`created_by`
- `seo_title`、`seo_description`
- `created_at`、`updated_at`

### 7.3 如果确实需要 HTML

可以增加受限 HTML 模式，但必须：
- 服务端保存前使用可靠 HTML Sanitizer 清理。
- 禁止 `<script>`、内联事件属性、`javascript:` URL、危险 iframe、对象嵌入等。
- 禁止任意外链资源或限制为可信域名。
- 使用严格 CSP；高风险页面考虑独立子域名和沙箱 iframe。
- 不允许通过页面 HTML 执行任意 API 请求或访问用户 Token。
- 管理员发布前预览，发布后保留版本和回滚能力。

**推荐优先实现 JSON Schema + Markdown 子集。** 这能满足活动页、临时公告、专题页、报名页需求，同时比任意 HTML/JS 安全且容易维护。

---

## 八、网站基础信息、备案与版权配置

管理后台增加“网站设置 / 法律信息”模块，内容由管理员配置，前端页脚统一读取 API 配置。

建议字段：
- 网站名称（`site_name`）
- 网站副标题 / 简介
- 网站 Logo、Favicon
- 网站主域名
- 网站版权主体名称
- 版权年份（支持自动显示当前年份）
- ICP 备案号及备案链接（如适用）
- 公安机关联网备案号及查询链接（如适用）
- 主办单位名称
- 联系邮箱
- 联系地址（确有必要时才公开）
- 用户协议链接
- 隐私政策链接
- Cookie/数据使用说明（如适用）
- 版权声明
- 图片授权与转载规则
- 内容举报/侵权投诉入口
- 免责声明
- 网站运行状态/版本信息（可选）

页脚示例（由配置生成，不写死）：

```text
© 2026 浙江理工福瑞圈 · All Rights Reserved
网站名称及主办主体信息
ICP备案号（如适用） | 公安联网备案信息（如适用）
用户协议 | 隐私政策 | 版权声明 | 联系我们
```

注意：
- 备案号、公安备案号、主体名称必须使用真实获批信息；未取得前不要伪造或展示虚假编号。
- 不同地区、主体类型和服务形态适用的备案/许可要求不同，上线前由运营主体核实。
- 版权声明不等于自动取得用户上传作品的版权。上传时应要求用户确认拥有上传/授权权利，并提供投诉处理机制。
- 记录用户协议、隐私政策的版本号及用户同意时间，政策更新时可要求重新确认。

---

## 九、建议新增的数据模型

原有 `User`、`Image`、`ProfileImage`、`Schedule` 保留并扩展。

### User
```text
id, username, display_name, email, email_verified_at,
phone_e164, phone_verified_at, hashed_password,
role, status, is_active, created_at, updated_at, last_login_at
```

### UserSession
```text
id, user_id, refresh_token_hash, device_name,
ip_hash_or_masked, user_agent_summary,
created_at, expires_at, revoked_at, last_used_at
```

### VerificationChallenge
```text
id, target_hash, purpose, channel, code_hash,
provider, status, attempts, expires_at, consumed_at, created_at
```

### StoredObject
```text
id, provider, bucket, object_key, visibility,
mime_type, size_bytes, checksum_sha256,
processing_status, created_by, created_at, deleted_at
```

### Image
```text
id, stored_object_id, original_name, uploader_id,
tags, width, height, description, moderation_status,
is_public, copyright_owner, license_type, created_at
```

### Schedule
```text
id, owner_id, stored_object_id, parsed_json,
is_public, expires_at, created_at
```

### SiteSetting
```text
id, key, value_json, category, is_public,
updated_by, updated_at
```

### DynamicPage
```text
id, slug, title, status, schema_json,
starts_at, ends_at, seo_title, seo_description,
created_by, published_at, created_at, updated_at
```

### DynamicPageVersion
```text
id, page_id, version, schema_snapshot,
operator_id, change_summary, created_at
```

### Event / EventRegistration
```text
Event: id, title, description, location, starts_at, ends_at,
       capacity, registration_starts_at, registration_ends_at,
       status, created_by
EventRegistration: id, event_id, user_id, status,
                   signup_at, checkin_at, idempotency_key
```

### Announcement
```text
id, title, content, status, is_pinned,
published_at, expires_at, created_by
```

### AuditLog
```text
id, actor_user_id, action, target_type, target_id,
request_id, ip_masked, metadata_json, created_at
```

### Report
```text
id, reporter_id, target_type, target_id,
reason, description, status, handled_by, handled_at, created_at
```

### SiteSetting 安全约定
- 只允许明确标记为公开的配置通过公共 API 输出。
- SMTP 密码、短信密钥、对象存储 Secret、验证码 Secret 等必须放 Secret 管理，不放在可被前端读取的设置表中。
- 配置修改记录审计日志；敏感配置修改要求重新认证或 MFA。

---

## 十、API 接口清单

统一前缀 `/api/v1`。

### Auth `/auth`
```text
POST   /register
POST   /verify/email
POST   /verify/phone
POST   /login
POST   /refresh
POST   /logout
POST   /logout-all
POST   /password/forgot
POST   /password/reset
GET    /me
```

### Admin Users `/admin/users`
```text
GET    /
GET    /pending
GET    /{user_id}
POST   /{user_id}/approve
POST   /{user_id}/reject
PATCH  /{user_id}/role
PATCH  /{user_id}/status
```

### Gallery `/images`
```text
GET    /
GET    /{image_id}
POST   /upload-intent
POST   /upload-complete
DELETE /{image_id}
POST   /{image_id}/report
GET    /{image_id}/download
```

### Profile `/profile`
```text
GET    /me
PUT    /me
GET    /me/images
POST   /me/images/upload-intent
DELETE /me/images/{image_id}
GET    /{user_id}
```

### Schedule `/schedule`
```text
POST   /upload-intent
POST   /upload-complete
GET    /jobs/{job_id}
GET    /{schedule_id}
POST   /compare
DELETE /{schedule_id}
```

### Pages `/pages`
```text
GET    /{slug}
GET    /admin
POST   /admin
PUT    /admin/{page_id}
POST   /admin/{page_id}/publish
POST   /admin/{page_id}/unpublish
DELETE /admin/{page_id}
```

### Events `/events`
```text
GET    /
GET    /{event_id}
POST   /{event_id}/register
DELETE /{event_id}/register
POST   /{event_id}/checkin
```

### Site `/site`
```text
GET    /public-config
GET    /footer
GET    /legal
```

### Admin Settings `/admin/settings`
```text
GET    /
PUT    /
POST   /storage/test
POST   /email/test
POST   /sms/test
POST   /captcha/test
```

### Club `/club`
```text
GET    /intro
PUT    /intro
```

管理接口必须单独进行权限检查，不能因为路径含 `/admin` 就默认安全。测试接口在生产环境应限制管理员权限、频率并避免回显密钥。

---

## 十一、权限矩阵（概要）

| 操作 | 游客 | 成员 | 摄影师 | 审核员 | 管理员 |
|---|:---:|:---:|:---:|:---:|:---:|
| 查看公开图片 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 下载公开原图 | — | ✓ | ✓ | ✓ | ✓ |
| 上传个人私有图片 | — | ✓ | ✓ | ✓ | ✓ |
| 上传公开图片 | — | — | ✓ | ✓ | ✓ |
| 发布公开图片 | — | — | 按策略 | ✓ | ✓ |
| 删除自己的图片 | — | ✓ | ✓ | ✓ | ✓ |
| 删除他人图片 | — | — | — | 按授权 | ✓ |
| 查看自己的私有相册 | — | ✓ | ✓ | ✓ | ✓ |
| 查看他人私有相册 | — | — | — | — | 仅特殊授权并审计 |
| 上传/对比自己的课表 | — | ✓ | ✓ | ✓ | ✓ |
| 查看公开活动/公告 | ✓ | ✓ | ✓ | ✓ | ✓ |
| 报名活动 | 按配置 | ✓ | ✓ | ✓ | ✓ |
| 审批用户 | — | — | — | 按授权 | ✓ |
| 管理网站设置 | — | — | — | — | ✓ |
| 发布动态页面 | — | — | — | 按授权 | ✓ |
| 查看审计日志 | — | — | — | 按授权 | ✓ |

---

## 十二、安全基线

上线前至少完成：
1. 全站 HTTPS，HSTS 按部署情况启用。
2. CORS 只允许正式前端来源，不使用生产环境 `*` 搭配凭证。
3. Cookie 认证启用 CSRF 防护；JWT 刷新令牌可撤销、轮换。
4. 密码使用成熟哈希算法；管理员强制 MFA。
5. 邮箱/手机号验证码哈希存储、短时效、单次使用、用途隔离。
6. CDN/WAF + API 层 + Redis 应用层多层限流。
7. 文件类型、大小、内容解码校验；对象存储默认私有。
8. SQL 使用 ORM 参数化查询；输出进行上下文安全转义。
9. 动态页面采用白名单 Schema；禁止任意脚本执行。
10. 管理操作、登录失败、权限变更、配置修改有审计日志。
11. `.env`、Secret、私钥、备份文件不进入 Git。
12. 数据库和对象存储制定备份、恢复演练和生命周期策略。
13. 依赖定期更新，生产镜像固定版本并扫描漏洞。
14. 生产环境关闭调试、限制 API 文档访问、隐藏内部异常。
15. 对个人信息实行最小化收集、访问控制、脱敏、保留期限和删除流程。

---

## 十三、部署与环境配置

### 环境划分
- `development`：本地开发，可使用 Docker PostgreSQL/Redis；不接真实短信或生产对象存储。
- `staging`：预发布，使用独立数据库、Bucket、域名和测试短信模板。
- `production`：生产环境，独立密钥、数据库、Redis、Bucket、邮件/短信服务。

### `.env.example`（示意，不放真实密钥）

```dotenv
APP_ENV=development
APP_NAME=Furry ZJUT
SECRET_KEY=replace-me
DATABASE_URL=postgresql+psycopg://user:password@postgres:5432/furry_zjut
REDIS_URL=redis://redis:6379/0

FRONTEND_ORIGINS=https://www.example.com
PUBLIC_API_BASE_URL=https://api.example.com

STORAGE_PROVIDER=s3
S3_ENDPOINT=
S3_REGION=
S3_BUCKET_PUBLIC=
S3_BUCKET_PRIVATE=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
PUBLIC_ASSET_BASE_URL=https://img.example.com

EMAIL_PROVIDER=
EMAIL_API_KEY=
SMS_PROVIDER=
SMS_API_KEY=
CAPTCHA_PROVIDER=
CAPTCHA_SECRET_KEY=

ACCESS_TOKEN_TTL_MINUTES=15
REFRESH_TOKEN_TTL_DAYS=14
UPLOAD_MAX_BYTES=52428800
```

部署注意：
- `.env.example` 只放变量名和占位值；真实 `.env` 不提交仓库。
- 生产环境数据库只允许应用网络访问，不暴露公网端口。
- 对象存储通过最小权限 Access Policy 授权。
- 定期备份 PostgreSQL；对象存储启用版本控制/生命周期规则（按成本选择）。
- 当前采用 EdgeOne Pages + 宝塔原生部署；不使用 Docker。业务增长后再考虑托管数据库、独立 Worker 或升级服务器。

---

## 十四、后台管理系统建议

建议建立完整管理后台，至少包括：

| 管理模块 | 功能 |
|---|---|
| 仪表盘 | 用户数、待审核数、图片数、存储用量、活动报名、异常请求 |
| 用户管理 | 搜索、审批、封禁、角色、邮箱/手机验证状态 |
| 图片管理 | 待审核、公开图片、举报、版权信息、批量下架 |
| 相册管理 | 存储配额、违规内容处理、私有文件访问审计 |
| 课表管理 | 任务状态、解析失败记录、过期清理 |
| 活动管理 | 活动、报名、候补、签到、导出 |
| 页面管理 | Schema 编辑、预览、定时发布、版本回滚 |
| 公告管理 | 草稿、置顶、定时发布、过期 |
| 网站设置 | 网站名称、Logo、页脚、备案/网安信息、法律链接 |
| 服务商配置 | 对象存储、CDN 域名、邮件、短信、人机验证 |
| 安全中心 | 限流规则、登录会话、风险事件、MFA |
| 审计日志 | 管理员操作、配置变更、敏感数据访问 |
| 系统任务 | 邮件/短信发送状态、图片处理、清理任务、失败重试 |

---

## 十五、建议额外增加的功能

按优先级建议：

### P0 — 上线必备
- 用户协议、隐私政策、版权声明、内容举报/侵权投诉。
- 邮箱/手机号验证、密码找回、设备会话管理。
- 管理员 MFA、审计日志、账号封禁。
- 图片审核、文件安全校验、私有对象访问控制。
- 数据库备份与恢复演练。
- 邮件/短信发送失败重试、发送记录和费用告警。
- 统一错误码、请求 ID、健康检查与日志脱敏。

### P1 — 强烈建议
- 活动报名、签到、候补和通知。
- 动态页面 Schema 编辑器、预览、定时发布、版本回滚。
- 站内通知中心。
- 用户举报、图片版权/授权标记。
- 图片 EXIF 隐私清理（尤其是 GPS 信息）。
- 用户存储配额、上传并发限制、重复文件检测。
- 公开页面 SEO、Open Graph 分享卡片、站点地图。
- 多语言预留（简体中文优先）。

### P2 — 后续扩展
- Web Push 通知。
- OAuth 第三方登录与账号绑定。
- 多校区/多社团空间。
- 图片收藏、点赞、评论和关注。
- 活动日历订阅（ICS）。
- 公开活动报名二维码、签到统计。
- CDN 缓存刷新与图片处理队列监控。
- 数据导出、账号注销、个人数据删除申请。
- 运营数据分析（避免采集不必要的个人行为数据）。

---

## 十六、原有课表解析定义（保留）

### `CourseSlot`

```python
from dataclasses import dataclass

@dataclass
class CourseSlot:
    name: str
    location: str
    weekday: int       # 0=周一 … 6=周日
    lesson_start: int # 开始节次（1-12）
    lesson_end: int   # 结束节次
    weeks: list[int]  # [1, 2, 3, ...]
    campus: str | None = None
```

### ZJUT 课表解析约定

示例单元格：

```text
课程名★ (3-5节)1-11周/校区:下沙校区/场地:2-N130/教师:xxx/...
```

- 节次：`(1-2节)` → `lesson_start=1`、`lesson_end=2`。
- 周次：`1-16周` 表示连续周；`1,3,5周` 表示指定周。
- 教室：从 `场地:` 后解析。
- 星期：由 PDF 表格列索引确定，列索引与星期映射必须保留。
- 解析器应有真实样本测试集，覆盖跨周、单双周、节次范围、空单元格、换行和异常格式。

### 对比算法输出

```python
def compare(
    slots_a: list[CourseSlot],
    slots_b: list[CourseSlot],
) -> dict:
    return {
        "same_classroom": [],
        "both_free": [],
        "overlaps": [],
    }
```

算法应考虑周次交集，而不能只比较星期和节次；只有实际周次重叠时才算冲突。

---

## 十七、开发实施顺序

建议分阶段交付，避免一次性堆积功能：

1. **基础工程：** Vue + FastAPI + PostgreSQL + Alembic + Redis；EdgeOne Pages 前端、宝塔 API 主机、域名与 CORS 配置。
2. **认证安全：** 注册、邮箱/手机验证、审批、登录、刷新令牌、MFA、限流。
3. **对象存储：** Provider 抽象、上传凭证、公开/私有桶、图片处理任务。
4. **核心业务：** Gallery、个人空间、课表上传解析与对比。
5. **运营内容：** 社团介绍、公告、网站设置、页脚法律信息。
6. **活动系统：** 活动、报名、候补、签到、通知。
7. **动态页面：** JSON Schema 编辑器、预览、发布、定时上下线、版本回滚。
8. **上线加固：** WAF、备份恢复、日志告警、压力测试、安全检查。

每个阶段都应提供数据库迁移、API 文档、自动化测试、部署说明和回滚方式。

---

## 十八、验收标准

- 前端与后端通过独立 API 域名通信，生产环境 HTTPS 正常。
- 正式环境使用 PostgreSQL；数据库迁移可重复部署。
- 公开图片与私有文件存储隔离，私有文件无法通过猜测 URL 访问。
- 切换 CDN/图片代理域名无需修改历史图片数据库记录。
- 注册必须完成邮箱和手机号验证，并按配置经过管理员审批。
- OTP、人机验证、API 限流在服务端完成验证，Redis 多实例部署下仍有效。
- 动态页面通过白名单 Schema 渲染；任意脚本不能被执行。
- 网站名称、Logo、页脚、备案/网安信息和版权内容由后台配置。
- 管理员关键操作有审计记录，敏感密钥不会被公共 API 返回。
- 数据库备份可恢复；对象存储文件有生命周期和删除策略。
- 课表解析、图片处理等耗时任务不阻塞 API 请求。

---

## 附录：原方案的关键调整摘要

| 原方案 | 优化后 |
|---|---|
| SQLite 开发 → PostgreSQL 上线 | 保留；正式环境统一 PostgreSQL，使用 Alembic 管理迁移 |
| 本地 `/storage`，以后再换 OSS | 生产直接采用对象存储 Provider 抽象；本地仅用于开发/测试 |
| JWT | 短时 Access + 可撤销/轮换 Refresh，浏览器优先安全 Cookie |
| 用户名密码注册 | 邮箱 + 手机号验证、管理员审批、风险验证 |
| 公开图片与私有图片分表 | 保留业务隔离，同时统一 StoredObject 元数据和访问策略 |
| 摄影师上传直接公开 | 支持后台配置发布策略、审核、举报和版权标记 |
| StorageAdapter | 扩展为对象存储 Provider、预签名上传、CDN 域名配置 |
| 未来活动功能 | 纳入正式模块规划 |
| 社团介绍 Markdown | 扩展公告、动态页面、网站配置和版本管理 |
| 无统一限流/审计 | 增加 WAF/API/Redis 多层限流、审计日志和告警 |
| 未定义网站法律信息 | 增加后台可配置页脚、备案、网安、版权、协议和隐私政策 |

**最终技术路线：Vue 3 + TypeScript + Vite（EdgeOne Pages）+ FastAPI（宝塔 2C2G / systemd）+ PostgreSQL 与 Redis 本机部署 + S3 兼容对象存储（建议腾讯云 COS）+ EdgeOne/CDN。**  
优先做安全可靠的模块化单体，等实际流量和团队规模证明有必要时，再拆分服务。


---

# 附录 A：2C2G 宝塔面板原生部署实施方案

> 本附录是针对 2 vCPU / 2 GiB RAM、宝塔面板 Linux、PostgreSQL 新装、国内云对象存储、轻量 Redis 的部署建议。全程不要求 Docker。  
> **重要：** 具体安装命令取决于操作系统发行版及版本。执行前先确认系统和宝塔已有服务，避免重复安装或覆盖已有配置。

## A1. 部署目标与边界

- 前端：Vue 3 编译为静态文件，部署至腾讯云 EdgeOne Pages；宝塔 Nginx 只承载 API 域名，不托管前端。
- API：FastAPI + Uvicorn，使用 Python 虚拟环境，由 systemd 管理；Nginx 反向代理。
- 数据库：PostgreSQL 本机部署，仅监听 `127.0.0.1` 或 Unix socket。
- 缓存/限流：Redis 本机部署，仅监听 `127.0.0.1`，启用认证并设置内存上限。
- 文件：国内 S3 兼容对象存储；不在服务器保存长期文件副本。
- 邮件/短信/人机验证：调用服务商 API，不自行运行 SMTP 或短信平台。
- 耗时任务：初期使用受控的轻量任务方式；课表 PDF 解析、图片转码等任务应限并发，避免占满 2GB 内存。
- 部署：Nginx + systemd + shell 脚本；不依赖 Docker。

## A2. 部署前检查

先在 SSH 中确认系统、内存、磁盘与已有服务：

```bash
cat /etc/os-release
uname -a
free -h
df -h
nproc
systemctl --type=service --state=running
ss -lntup
```

检查宝塔 Nginx 的实际安装路径和配置路径。宝塔环境中常见路径为 `/www/server/nginx/`，但应以当前机器为准。

**不要直接把 Debian、Ubuntu、Rocky Linux 的安装命令混用。** 先确定系统版本，再选择对应的软件源。数据库和 Redis 若已由宝塔安装，应优先复用现有服务，不要同时启动第二套实例。

## A3. 建议目录与账号

```text
/www/wwwroot/furry-zjut/
├── frontend/
│   └── dist/                  # Vue 构建产物
├── backend/
│   ├── app/
│   ├── venv/                  # Python 虚拟环境
│   ├── .env                   # 仅服务账号可读
│   └── requirements.txt
├── releases/                  # 可选：版本发布目录
└── shared/
    └── tmp/                   # 有限的临时文件，定期清理
```

建议单独创建无登录权限的系统用户（例如 `furry`）运行 API，不使用 `root` 运行 Python 应用。目录属主和权限按实际宝塔站点用户统一设置，避免为了省事把项目目录全部设为 `777`。

示例（确认系统支持后执行）：

```bash
useradd --system --home /www/wwwroot/furry-zjut --shell /usr/sbin/nologin furry
install -d -o furry -g furry /www/wwwroot/furry-zjut/backend
install -d -o furry -g furry /www/wwwroot/furry-zjut/shared/tmp
```

若系统已经存在该用户，先检查，不要重复创建。

## A4. 资源预算

2GB 是总内存，不是可全部分配给应用的内存。宝塔面板、系统服务、文件缓存和瞬时峰值都要留空间。

| 项目 | 初始规划预算 | 控制方式 |
|---|---:|---|
| Linux、SSH、宝塔面板及常驻系统服务 | 400–650 MiB | 精简不必要的面板插件和服务 |
| Nginx | 30–80 MiB | 静态托管，限制连接和缓冲规模 |
| FastAPI（1 Worker） | 150–300 MiB 起步 | 限制并发、上传体积和任务量 |
| PostgreSQL | 200–350 MiB 起步 | 限制共享缓冲、连接数和单次查询内存 |
| Redis | 40–80 MiB | 设置 `maxmemory` 和淘汰策略 |
| 文件缓存及临时峰值预留 | 其余内存 | 不要人为全部占满 |

以上是规划区间，实际进程 RSS 会随负载、扩展、查询和后台任务变化。首次上线后以 `free -h`、`ps aux --sort=-rss`、`systemd-cgtop`（若系统支持）持续观测。

### 初期应避免

- 多个 Uvicorn Worker。
- 同时运行 Celery、Flower、多个 Worker 和独立消息代理。
- 本地 MinIO、Elasticsearch、完整监控套件。
- 在 API 进程中执行高分辨率图片转码或大 PDF 解析。
- 大量数据库连接或无上限的上传并发。

### Swap

如果系统没有 Swap，可根据磁盘空间和服务商限制考虑创建 1–2 GiB Swap 作为突发内存压力缓冲。Swap 不能代替 RAM；若持续频繁换页，应降低任务并发或升级内存。创建前先确认磁盘空间、现有 Swap 与云主机限制，不要重复创建。

## A5. Python 环境与依赖

建议使用 Python 3.11 或项目验证通过的兼容版本。不要覆盖系统 Python，也不要用 `sudo pip install` 修改系统环境。

示例：

```bash
cd /www/wwwroot/furry-zjut/backend
python3 -m venv venv
./venv/bin/python -m pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

依赖版本应在 `requirements.txt` 或锁文件中固定，并先在测试环境验证升级。生产环境不要使用 `--reload`。

`.env` 示例：

```dotenv
APP_ENV=production
APP_NAME=Furry ZJUT
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_URL=postgresql+psycopg://furry_app:replace-password@127.0.0.1:5432/furry_zjut
REDIS_URL=redis://:replace-redis-password@127.0.0.1:6379/0

FRONTEND_ORIGINS=https://www.example.com
PUBLIC_API_BASE_URL=https://api.example.com

STORAGE_PROVIDER=s3
S3_ENDPOINT=
S3_REGION=
S3_BUCKET_PUBLIC=
S3_BUCKET_PRIVATE=
S3_ACCESS_KEY_ID=
S3_SECRET_ACCESS_KEY=
PUBLIC_ASSET_BASE_URL=https://img.example.com

EMAIL_PROVIDER=
EMAIL_API_KEY=
SMS_PROVIDER=
SMS_API_KEY=
CAPTCHA_PROVIDER=
CAPTCHA_SECRET_KEY=
```

将示例域名和占位密钥替换为真实配置。生成强随机密钥；`.env` 不提交 Git，权限建议 `640` 或更严格，并确保只有服务账号及授权管理员可读取。密钥不要写进前端变量（例如 `VITE_*`），因为这些变量会被编译进浏览器资源。

## A6. FastAPI systemd 服务

假设入口是 `app.main:app`，工作目录和虚拟环境路径与上文一致。若实际入口不同，请相应调整。

创建 `/etc/systemd/system/furry-zjut-api.service`：

```ini
[Unit]
Description=Furry ZJUT FastAPI
After=network.target postgresql.service redis.service
Wants=postgresql.service redis.service

[Service]
Type=simple
User=furry
Group=furry
WorkingDirectory=/www/wwwroot/furry-zjut/backend
EnvironmentFile=/www/wwwroot/furry-zjut/backend/.env
ExecStart=/www/wwwroot/furry-zjut/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=3
TimeoutStopSec=30
KillSignal=SIGTERM
UMask=0027
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

`After=postgresql.service redis.service` 的服务名需要按当前系统实际 unit 名称核对。若 Redis/数据库未使用 systemd 管理或服务名不同，应调整依赖项。`NoNewPrivileges` 等加固选项启用后需进行上传、临时目录和日志测试。

启用并检查：

```bash
systemctl daemon-reload
systemctl enable --now furry-zjut-api
systemctl status furry-zjut-api --no-pager
journalctl -u furry-zjut-api -n 100 --no-pager
```

验证本机 API：

```bash
curl -i http://127.0.0.1:8000/health
```

建议提供只返回状态、不包含密钥/版本敏感信息的 `/health`，另设仅内部使用的 `/ready` 检查数据库与必要依赖。不要把内部诊断端点无保护地暴露给公网。

## A7. PostgreSQL 轻量调优

正式环境使用 PostgreSQL。数据库只允许本机访问；不要在宝塔防火墙中开放公网 `5432`。

以下是 **2GB 总内存主机的保守起点**，不是所有 PostgreSQL 版本和工作负载都适用的绝对最优值。PostgreSQL 文档指出，`work_mem` 是每个查询操作可使用的基础内存，复杂查询和并发会使总消耗显著放大，因此小内存机器应谨慎设置。参见官方资源消耗文档：https://www.postgresql.org/docs/current/runtime-config-resource.html

建议先评估以下参数：

```conf
# 需按实际 PostgreSQL 主版本及配置文件位置修改
listen_addresses = '127.0.0.1'
max_connections = 30
shared_buffers = 256MB
effective_cache_size = 768MB
work_mem = 4MB
maintenance_work_mem = 64MB
autovacuum_work_mem = 32MB
wal_buffers = -1
min_wal_size = 128MB
max_wal_size = 512MB
checkpoint_completion_target = 0.9
max_worker_processes = 4
max_parallel_workers = 2
max_parallel_workers_per_gather = 1
```

说明：
- `shared_buffers=256MB` 是起始值，宝塔和其他服务占用较高时可进一步降低。
- `effective_cache_size` 是查询规划器的估算提示，不是 PostgreSQL 实际预留的内存。
- `work_mem` 不能简单理解为整个数据库的总内存上限；并发查询中的多个排序/哈希操作可能分别消耗内存。
- 不要为了“调优”盲目增大 `work_mem`、并行 Worker 或连接数。
- `max_connections=30` 需和应用连接池一起设计。SQLAlchemy 建议从小连接池开始，例如 `pool_size=5`、`max_overflow=2`，再依据实际并发和连接等待情况调整；若只有一个 API Worker，不必预先开几十个应用连接。
- 若 PostgreSQL 运行在共享主机上，`effective_cache_size` 应按系统可用缓存重新估算。
- 参数是否可热加载取决于具体参数；修改后用 `SHOW` 验证，并只在必要时重启。

建库建议：
- 创建专用数据库 `furry_zjut` 和非超级用户 `furry_app`。
- 应用账号只获得业务数据库所需权限，不使用 `postgres` 超级用户连接应用。
- 迁移由 Alembic 执行，备份恢复使用独立备份账号或管理员操作。
- 使用 `pg_hba.conf` 限制为本机连接；禁止 `0.0.0.0/0` 的宽泛访问规则。
- 开启合理的慢查询记录阈值（例如 500–1000ms 起步），日志需避免记录密码、验证码、完整个人信息或 Token。

## A8. Redis 轻量配置与安全

Redis 用于限流计数、短期缓存、一次性任务状态等。验证码的最终校验记录应采用安全的 TTL/单次消费机制；若要求在 Redis 故障后仍可审计或恢复，关键验证记录应在 PostgreSQL 留存必要元数据。

配置起点（具体文件路径以安装版本为准）：

```conf
bind 127.0.0.1 ::1
protected-mode yes
port 6379
timeout 0
tcp-keepalive 300
maxmemory 64mb
maxmemory-policy allkeys-lru
appendonly no
save 900 1
save 300 10
save 60 10000
```

注意：
- 若 Redis 只用于可重建缓存，`allkeys-lru` 可接受；如果数据库、队列或验证码记录需要持久化，不能把这些关键数据与可随时淘汰的缓存混在同一 Redis 实例和淘汰策略中。
- 本方案初期建议 Redis 仅用于缓存/限流，业务真相数据存 PostgreSQL。验证码记录可用带 TTL 的 Redis 配合数据库策略，但要明确 Redis 不可用时注册、登录、短信发送应如何安全降级。
- 不要把 Redis 暴露到公网；不要在无鉴权状态下监听所有网卡。
- 若启用密码，使用随机强密码，配置中不要直接复用数据库密码。
- `maxmemory` 不是 Redis 进程 RSS 的绝对总上限，仍需为管理开销和内存碎片留余量。
- Redis 官方安全建议强调不要将实例暴露到不可信网络，并正确配置绑定地址、保护模式和认证：https://redis.io/docs/latest/operate/oss_and_stack/management/security/

验证：

```bash
redis-cli -h 127.0.0.1 ping
redis-cli -h 127.0.0.1 INFO memory
```

如启用了密码，使用安全的交互方式输入凭据，避免把密码直接写进 shell 历史或命令行参数。

## A9. 宝塔 Nginx 配置

建议由宝塔创建两个站点：
1. `www.example.com`：站点根目录指向 `frontend/dist`。
2. `api.example.com`：反向代理到 `http://127.0.0.1:8000`。

域名的 DNS、TLS 证书和站点根目录请在宝塔面板配置。下面是配置思路，合并到对应站点的 Nginx 配置中，不要直接覆盖宝塔生成的全部配置。

### 主站 SPA

```nginx
server {
    listen 80;
    server_name www.example.com;
    # TLS 证书由宝塔配置；HTTP 应跳转 HTTPS

    root /www/wwwroot/furry-zjut/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location ~* \.(?:env|ini|log|sql|bak|conf|pem|key)$ {
        deny all;
    }

    location ~ /\.(?!well-known) {
        deny all;
    }
}
```

实际生产环境应使用宝塔生成的 HTTPS `server` 配置，或由面板启用强制 HTTPS。不要因为示例中只展示了站点逻辑就删除证书路径、证书续期或原有安全配置。

### API 站点

```nginx
server {
    listen 80;
    server_name api.example.com;
    # TLS 证书由宝塔配置；HTTP 应跳转 HTTPS

    client_max_body_size 10m;
    client_body_timeout 30s;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering on;
    }
}
```

注意：
- 示例中的 `client_max_body_size 10m` 只是 API 默认上限。若文件上传通过对象存储预签名 URL 直传，API 通常只接收元数据，可保持较小；若后端确实代理上传，需按业务设定大小上限和超时。
- FastAPI 信任的代理 IP 应仅限本机 Nginx 或明确的可信代理，不能无条件信任任意客户端的转发头。
- CORS 在 FastAPI 中配置为精确允许 `https://www.example.com` 等实际来源；不要在生产环境使用 `allow_origins=["*"]` 配合 Cookie 凭证。
- `proxy_read_timeout` 不应被用来掩盖长时间阻塞。长任务应改为后台任务和任务状态查询。
- 反向代理头、缓冲与超时的配置可参考 NGINX 官方文档：https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy

### 站点安全头

在确认不影响 OAuth、验证码服务、图片预览和管理后台后，逐步启用 `X-Content-Type-Options: nosniff`、`Referrer-Policy`、合适的 `Content-Security-Policy` 和 HSTS。CSP 应根据实际资源域名制定，不建议直接复制过于宽松的 `unsafe-inline` 策略。HSTS 应在 HTTPS、子域名和证书部署确认无误后再启用。

## A10. 对象存储与 CDN 配置

- 使用国内云对象存储的官方 SDK 或 S3 兼容接口，并通过 `StorageProvider` 统一封装。
- 数据库只存 `bucket`、`object_key`、`visibility`、MIME、大小、校验和等元数据，不保存固定 CDN 完整 URL。
- 公开图片通过 `img.example.com` 的 CDN/自定义域名访问；私有相册、课表附件通过后端鉴权后生成短时效签名 URL。
- Bucket 默认私有；只读公开访问应通过明确的公开前缀或 CDN 访问策略控制，禁止任意写入。
- 上传采用短时效预签名 URL；后端完成对象存在性、大小和内容类型复核后，再创建业务记录。
- Access Key 只授予指定 Bucket/前缀所需权限；生产密钥不进入前端、不提交 Git。
- 更换图片域名时只修改服务端公开域名配置；对象 Key 保持不变。
- 代理回源域名必须使用白名单并验证归属，不能允许管理员输入任意回源 URL，避免 SSRF。
- 为上传设置用户配额、单文件大小限制、文件类型白名单和并发限制；图片处理设置最大像素数，防止解压炸弹或超大图片造成内存耗尽。

## A11. 邮件、短信与人机验证

所有供应商调用由 Provider 层封装，不在路由中直接写厂商 SDK。

- 邮件验证码：发送冷却、每小时/每日额度、单次使用、短时效、模板变量转义。
- 手机验证码：设置手机号/IP/设备多维频控、每日费用上限、异常发送熔断。
- 人机验证：服务端向厂商验证 Token，检查有效期、站点/动作等字段，不能只相信前端结果。
- 服务商故障：注册、登录、密码重置等敏感操作默认失败关闭；允许用户安全重试，但不得绕过验证。
- 邮件/短信失败记录任务状态、供应商错误码和重试次数；日志不记录完整验证码或 Secret。
- 初期可用 PostgreSQL 记录发送任务状态和失败重试，避免为了任务队列再引入大量组件。任务量增大后再引入轻量队列/Worker。

## A12. 备份与恢复

### 数据库备份

建议每日执行逻辑备份，并把备份上传到与生产 Bucket/权限隔离的对象存储位置。保留策略可从每日备份 7 份、每周备份 4 份起步，再根据业务重要性和存储费用调整。

示例备份脚本 `/usr/local/bin/backup-furry-zjut.sh`：

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077

BACKUP_DIR="/var/backups/furry-zjut"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 建议使用受限的 .pgpass 文件或系统 Secret 管理，权限必须为 0600。
export PGPASSFILE="/root/.pgpass-furry-zjut"

pg_dump \
  --host=127.0.0.1 \
  --username=furry_backup \
  --dbname=furry_zjut \
  --format=custom \
  --file="$BACKUP_DIR/furry_zjut-$STAMP.dump"

find "$BACKUP_DIR" -type f -name 'furry_zjut-*.dump' -mtime +7 -delete

# 下一步应通过云厂商 CLI/SDK 上传到独立备份前缀。
# 不要在此脚本中硬编码 Access Key；上传失败时应返回非零状态并触发告警。
```

注意：
- 示例只完成数据库本地备份和本地保留清理；**它尚未实现对象存储上传**。应根据实际云厂商选择官方 CLI/SDK，使用最小权限的备份凭据补齐上传步骤。
- `pg_dump` 的备份账号需有足够读取权限；备份密钥文件应严格限制权限。
- 备份目录不应放在公开网站根目录。
- 备份完成后记录大小、退出码和上传状态，并配置失败告警。
- 备份中可能包含个人信息，应加密传输、限制访问，并按隐私保留策略删除过期备份。
- 对象存储中的图片/文件也应有版本控制、生命周期或独立备份策略。数据库备份不包含对象存储里的文件本体。

### 定时任务

备份脚本确认可运行后，可用 root 的 cron 每日低峰执行，例如：

```cron
20 3 * * * /usr/local/bin/backup-furry-zjut.sh >> /var/log/backup-furry-zjut.log 2>&1
```

设置前先手动执行并验证备份文件可生成。之后至少定期执行一次恢复演练：恢复到临时数据库，验证表、用户、记录和关键业务查询。只有“备份成功且可恢复”才算有可用备份。

## A13. 日志、监控与清理

初期只部署轻量监控：
- `systemctl status furry-zjut-api`
- `journalctl -u furry-zjut-api`
- `free -h`、`df -h`、`uptime`
- PostgreSQL 连接数、慢查询、磁盘占用。
- Redis 内存、命中率、淘汰数。
- 云对象存储用量、短信/邮件费用、API 429/5xx 比例。

日志规则：
- 设置日志轮转与保留期限。
- 脱敏邮箱、手机号、IP、Authorization、Cookie、验证码和签名 URL。
- 请求记录 `request_id`，方便前后端和服务日志关联。
- 不把上传文件、用户隐私或 Token 写入日志。
- 临时目录、过期课表和孤儿对象由定时任务清理，先检查数据库引用再删除对象，避免误删。

## A14. 防火墙与安全基线

公网通常只开放：
- TCP 80、443：Web。
- TCP 22：SSH（建议限制来源 IP 或使用密钥登录）。

不应公网开放：
- PostgreSQL 5432。
- Redis 6379。
- Uvicorn 8000。
- 数据库管理端口或内部任务端口。

其他要求：
1. SSH 使用密钥登录，条件允许时禁用密码登录并限制管理员来源。
2. 宝塔面板端口设置强密码、MFA（若版本支持）和 IP 白名单；不要把面板端口当作公开网站服务端口。
3. 数据库应用账号不是超级用户。
4. Redis 仅绑定回环地址，启用认证并设置内存上限。
5. 管理员账号启用 MFA；关键配置修改和权限变更写入审计日志。
6. 使用可信代理 IP 配置；不要直接信任客户端传来的 `X-Forwarded-For`。
7. 依赖定期更新，但生产升级前先备份并在测试环境验证。
8. API 生产环境关闭调试与自动重载，隐藏堆栈和敏感配置。
9. 对登录、注册、OTP、上传、报名和公开搜索配置多维限流。
10. 定期检查 `ss -lntup`，确认数据库、Redis 和应用端口没有意外暴露。

## A15. 上线验收清单

- [ ] `www` 与 `api` 域名 HTTPS 正常，证书自动续期已验证。
- [ ] 前端 SPA 路由刷新不返回 404。
- [ ] API 只监听 `127.0.0.1:8000`，公网无法直接访问该端口。
- [ ] PostgreSQL 只允许本机连接，应用使用最小权限账号。
- [ ] Redis 只监听本机，有内存上限，不承载唯一业务数据。
- [ ] 邮箱、手机验证码由后端校验，有过期、单次使用、限频和费用告警。
- [ ] 人机验证 Token 经过服务端校验。
- [ ] 图片通过对象存储上传，数据库只存对象 Key 和元数据。
- [ ] 私有相册和课表不能通过公开 URL 或猜测对象 Key 访问。
- [ ] 动态页面使用白名单 Schema，禁止执行任意脚本。
- [ ] 管理员 MFA、审计日志、用户协议和隐私政策已启用。
- [ ] 数据库备份已上传到独立位置，并完成恢复演练。
- [ ] Nginx、API、PostgreSQL、Redis 日志有轮转和脱敏。
- [ ] `free -h` 在正常负载下有余量；没有持续 Swap 抖动或 OOM。
- [ ] 图片/课表后台任务不会与 API 同时争抢大量内存。

## A16. 资源超限时的降级顺序

当内存持续不足时，优先采取：
1. 暂停或降低图片转码、PDF 解析等任务并发。
2. 检查 Python Worker 数量、连接池和内存泄漏。
3. 降低 PostgreSQL 连接数及不必要的查询内存配置。
4. 降低 Redis `maxmemory`，并确认其中只放可重建缓存/可安全淘汰的数据。
5. 停用不必要的宝塔插件与常驻服务。
6. 评估将 PostgreSQL 或 Redis 迁移到托管服务；若业务增长明显，优先升级 RAM，而不是无限增加 Swap。

**建议上线起点：** Nginx + FastAPI 1 Worker + PostgreSQL + Redis 64MB + 国内对象存储/CDN。先用真实流量和内存监控验证，再决定是否增加 Worker 或任务队列。


---

# 附录 B：EdgeOne Pages 前端 + 宝塔 2C2G API + 本机 PostgreSQL/Redis（最终部署方案）

> **本附录是本项目生产部署的最终选择，优先级高于前文任何通用部署示例或附录 A 中“前端由宝塔 Nginx 托管”的旧描述。**
>
> - 前端：腾讯云 EdgeOne Pages（Vue/Vite 静态构建产物）
> - API：宝塔面板管理的 2 vCPU / 2 GiB Linux 服务器，FastAPI + Uvicorn + systemd
> - 反向代理：宝塔 Nginx，仅代理 API
> - 数据库：PostgreSQL 与 API 同机部署，监听回环地址
> - 缓存：Redis 与 API 同机部署，监听回环地址
> - 图片/附件：腾讯云 COS（或其他 S3 兼容对象存储），不将业务文件长期保存在 2C2G 服务器
> - 不使用 Docker；不把数据库、Redis、Uvicorn 端口暴露到公网

## B1. 最终拓扑

```text
用户浏览器
  |
  +-- https://www.example.com
  |       |
  |       +--> 腾讯云 EdgeOne Pages（Vue 3 + Vite 静态 SPA）
  |               |
  |               +-- API 请求： https://api.example.com
  |               +-- 图片：     https://img.example.com（可选，COS + CDN）
  |
  +-- https://api.example.com
          |
          +--> DNS A 记录 → 宝塔 2C2G 服务器公网 IP
                  |
                  +--> 宝塔 Nginx（TLS、限流、请求体限制、安全头）
                          |
                          +--> 127.0.0.1:8000（FastAPI/Uvicorn，systemd）
                                  |
                                  +--> 127.0.0.1:5432（PostgreSQL）
                                  |
                                  +--> 127.0.0.1:6379（Redis）
                                  |
                                  +--> 腾讯云 COS / S3 兼容对象存储
                                  +--> 邮件、短信、人机验证等外部服务
```

**信任边界：**
1. 浏览器不连接 PostgreSQL、Redis 或 Uvicorn。
2. EdgeOne Pages 只托管静态前端，不保存服务端密钥。
3. Nginx 是公网 API 的唯一入口；FastAPI 只监听 `127.0.0.1:8000`。
4. PostgreSQL、Redis 只允许本机访问。
5. COS Bucket 默认私有；前端通过后端签发的短时效预签名 URL 上传，公开内容通过 CDN 读取。
6. 宝塔面板端口与 SSH 不作为 API 入口，单独限制访问来源。

## B2. 域名与 DNS 规划

建议使用同一主域名下的子域名，避免不必要的跨站 Cookie 问题：

| 域名 | 用途 | DNS/接入 |
|---|---|---|
| `example.com` | 根域名，可跳转主站 | EdgeOne Pages 或 301 跳转至 `www` |
| `www.example.com` | 前端主站 | 绑定 EdgeOne Pages 自定义域名 |
| `api.example.com` | FastAPI API | A 记录指向宝塔服务器公网 IPv4；IPv6 未配置时不要发布 AAAA |
| `img.example.com` | 图片 CDN（可选） | 绑定 COS/CDN 自定义域名 |
| `admin.example.com` | 管理后台（可选） | 可与主站共用前端应用路由；敏感管理入口需 MFA、严格权限和审计 |

实施要点：
- 将 `example.com` 替换为实际域名。
- EdgeOne Pages 中添加 `www.example.com` 自定义域名并按控制台提示完成 DNS 验证和 HTTPS 配置。
- `api.example.com` 的 DNS 指向 API 服务器；在宝塔中创建该域名的 Nginx 站点并配置证书。
- `img.example.com` 仅在 COS/CDN 完成域名绑定、证书和回源验证后启用。
- 若 EdgeOne Pages 使用平台默认域名，浏览器来源会与 `api.example.com` 跨站；生产环境优先绑定自己的 `www.example.com`。
- DNS 变更前确认当前解析、证书和备案/合规要求；不要随意添加指向不存在服务的 AAAA 记录。

## B3. EdgeOne Pages 前端配置

### Vite 环境变量

`.env.production` 示例：

```dotenv
VITE_API_BASE_URL=https://api.example.com/api/v1
VITE_PUBLIC_ASSET_BASE_URL=https://img.example.com
```

注意：
- `VITE_*` 会进入浏览器构建产物，只能放公开 URL、公开标识等非秘密配置。
- 禁止把数据库密码、JWT Secret、COS Secret、短信密钥、邮件密钥或验证码 Secret 放入前端环境变量。
- 若使用相对 API 路径 `/api/v1`，需要在 EdgeOne Pages 额外配置反向代理/边缘规则；本方案默认使用独立 `https://api.example.com`。
- 生产与预发布环境应分别配置 API 域名、COS Bucket 和第三方服务凭据。

### SPA 路由回退

Vue Router 使用 `createWebHistory()` 时，EdgeOne Pages 需要将未知前端路由回退到 `index.html`。在 Pages 控制台/项目配置中设置 SPA fallback 或 rewrite：

```text
/*  → /index.html  （仅前端站点）
```

不要将 API 域名也配置成 SPA fallback。API 不存在的路径应由 FastAPI 返回 JSON 404。

### 构建与发布流程

1. 本地或 CI 执行 `npm ci`。
2. 执行 `npm run build`，确认产物为 `dist/`。
3. 在 EdgeOne Pages 绑定 Git 仓库或上传构建产物。
4. 设置构建命令和输出目录：`npm run build` / `dist`。
5. 先发布预览环境，验证路由、登录、上传、API CORS 和缓存。
6. 正式发布后确认 HTTPS、缓存刷新和回滚能力。

前端发布不应触发 API 服务器重启；API 发布也不应依赖 EdgeOne Pages 重新构建。

## B4. CORS 与跨域策略

前端与 API 是不同 Origin（主机名不同），因此浏览器会执行 CORS。CORS 不是认证或授权机制。

### FastAPI 配置示例

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://www.example.com",
        # 仅在确实部署独立管理前端时加入：
        # "https://admin.example.com",
    ],
    allow_credentials=True,  # 仅当使用 Cookie 认证时开启
    allow_methods=[
        "GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-CSRF-Token",
        "X-Request-ID",
        "Idempotency-Key",
    ],
    expose_headers=["X-Request-ID", "Retry-After"],
    max_age=600,
)
```

规则：
- 生产环境只列出真实前端 Origin，禁止 `allow_origins=["*"]` 与 `allow_credentials=True` 同时使用。
- Origin 必须精确匹配协议、域名和端口；`https://example.com` 与 `https://www.example.com` 是不同 Origin。
- 开发环境单独允许 `http://localhost:5173`，不要把它带入生产配置。
- 若使用 Bearer Access Token 且不使用 Cookie，通常设置 `allow_credentials=False`；仍需允许 `Authorization` 请求头。
- 若使用 Cookie，设置 `allow_credentials=True`，并确保前端请求使用 `credentials: "include"`。
- CORS 预检 OPTIONS 请求应正常返回，不应要求用户登录。
- Nginx 不要与 FastAPI 重复添加互相冲突的 CORS 响应头。建议统一由 FastAPI 管理 CORS。
- API 仍需做认证、权限、CSRF（Cookie 模式）、限流和输入校验。

## B5. 认证方案选择

### 推荐：短时 Access Token + HttpOnly Refresh Cookie

适用于浏览器 SPA，建议采用以下组合：

- Access Token：有效期约 5–15 分钟，前端内存持有，API 请求通过 `Authorization: Bearer ...` 发送。
- Refresh Token：服务端生成随机高熵令牌，浏览器存入 `HttpOnly; Secure` Cookie；数据库只保存 Refresh Token 哈希。
- Refresh Token：轮换使用、可撤销、绑定会话；检测旧令牌重用时撤销该会话族。
- 登录、刷新、登出、退出所有设备接口由后端负责。
- 不把长期 Refresh Token 放入 `localStorage` 或 `sessionStorage`。
- 页面刷新后通过 `/auth/refresh` 获取新的短时 Access Token。

Cookie 示例（由 API 响应设置）：

```http
Set-Cookie: refresh_token=<opaque-token>; Path=/api/v1/auth; HttpOnly; Secure; SameSite=Lax; Max-Age=1209600
```

注意：
- `example.com` 下的 `www.example.com` 和 `api.example.com` 通常属于 same-site，但仍是 cross-origin；Cookie 请求依然需要 CORS credentials。
- Cookie `Domain` 默认建议不设置，使用 API 主机的 host-only Cookie，减少子域泄露面。
- 如果 Refresh Cookie 只用于 `/auth/refresh` 和 `/auth/logout`，可将 `Path` 限制到认证路径；实际路径需与接口路由一致。
- Cookie 认证接口需做 CSRF 防护：对状态变更请求验证 CSRF Token，并校验 `Origin`/`Referer`；不能仅依赖 `SameSite`。
- 登录、刷新、登出接口设置严格限流；Refresh Token 轮换应在数据库事务中完成。
- 若前后端将来使用不同注册域名（例如 Pages 默认域名），Cookie 可能需要 `SameSite=None; Secure`，并受浏览器第三方 Cookie 策略影响。优先使用同一自有主域名的子域。

### 另一种方案：纯 Bearer Token

若不使用 Cookie，可采用短时 Access Token + Refresh Token（仅内存或更谨慎的存储方式），并通过 `Authorization` 请求头传递。此模式降低传统 Cookie CSRF 风险，但若把长期 Token 放进 Web Storage，会增加 XSS 后的令牌窃取风险。不要将 JWT 当作无需撤销的长期登录凭证。

### 密码与权限

- 密码使用 Argon2id（优先）或经评估的 bcrypt。
- 管理员强制 MFA；高风险操作要求重新认证。
- 后端逐请求执行 RBAC/Permission 检查，前端路由守卫仅用于用户体验。
- 登录失败、注册、验证码、刷新 Token、上传和管理接口分层限流。
- 账号状态（pending/active/disabled）与角色权限均以数据库为准。

## B6. 宝塔 Nginx API 站点配置

在宝塔创建 `api.example.com` 站点并安装 HTTPS 证书。宝塔生成的站点配置路径因版本不同可能不同，优先使用宝塔站点配置界面管理；不要直接覆盖主配置文件。

以下为**站点级配置示意**，按宝塔实际路径、证书路径和已有配置调整：

```nginx
server {
    listen 80;
    server_name api.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate     /path/to/fullchain.pem;
    ssl_certificate_key /path/to/privkey.pem;

    # 证书和 TLS 参数以宝塔/证书服务实际配置为准
    ssl_protocols TLSv1.2 TLSv1.3;

    server_tokens off;
    client_max_body_size 20m;
    client_body_timeout 30s;
    keepalive_timeout 30s;

    # API 不允许被浏览器跨域嵌入
    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header X-Frame-Options DENY always;

    # 仅在 HTTPS 全站验证无误后启用 HSTS：
    # add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Request-ID $request_id;

        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        proxy_buffering on;
        proxy_request_buffering on;
    }

    # 登录、验证码、刷新令牌等接口可按业务增加更严格的限流规则。
    # 不建议在未经压测的情况下直接套用过低的全局限流值。
}
```

配置说明：
- `client_max_body_size` 应与业务上传策略一致。大文件优先直传 COS，不应经过 API Nginx。
- 不要在 Nginx 配置里写 COS、数据库或应用 Secret。
- 若使用 Nginx 限流，需先定义 `limit_req_zone`，并在登录/验证码等路径独立设置；上线前测试正常用户是否被误伤。
- `X-Forwarded-For` 只有来自可信 Nginx 的值才可使用。Uvicorn 的 `--forwarded-allow-ips` 只信任 `127.0.0.1`。
- 不要无条件添加 `Access-Control-Allow-Origin: *`；CORS 由 FastAPI 配置。
- 生产环境不开放 `/docs`、`/redoc` 或 OpenAPI Schema，或通过管理员认证/内网访问控制保护。
- 配置修改后执行宝塔 Nginx 配置测试并 reload，确认 API、上传、登录和 OPTIONS 预检均正常。

## B7. FastAPI systemd 服务

服务目录建议：

```text
/opt/furry-zjut/
├── backend/
│   ├── app/
│   ├── venv/
│   ├── releases/
│   └── current -> releases/<release-id>
├── config/
│   └── furry-zjut-api.env
└── shared/
    ├── tmp/
    └── logs/
```

建议 API 使用专用非登录账号 `furry` 运行。环境文件放在 Web 根目录之外，例如 `/etc/furry-zjut/api.env`，避免被 Nginx 静态访问。

`/etc/systemd/system/furry-zjut-api.service`：

```ini
[Unit]
Description=Furry ZJUT FastAPI API
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=simple
User=furry
Group=furry
WorkingDirectory=/opt/furry-zjut/backend/current
EnvironmentFile=/etc/furry-zjut/api.env
ExecStart=/opt/furry-zjut/backend/current/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=3
TimeoutStopSec=30
KillSignal=SIGTERM
UMask=0027
NoNewPrivileges=true
PrivateTmp=true

# 2C2G 机器上可谨慎启用以下资源限制；先验证兼容性再启用：
# MemoryMax=500M
# TasksMax=128

[Install]
WantedBy=multi-user.target
```

注意：
- PostgreSQL/Redis 的 systemd Unit 名称可能因发行版或宝塔安装方式不同而变化，先用 `systemctl list-units` 确认，不要盲目复制 `After=`。
- 生产环境禁止 `--reload`，初期只使用 1 个 Uvicorn Worker。
- `MemoryMax` 是可选保护措施，设置过低会导致服务被 OOM/系统杀死；先观测真实 RSS 再配置。
- API 应提供 `/health`（只返回健康状态）和内部 `/ready`（检查 DB/Redis），不要返回密钥、连接字符串或详细内部信息。

部署命令：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now furry-zjut-api
sudo systemctl status furry-zjut-api --no-pager
sudo journalctl -u furry-zjut-api -n 100 --no-pager
curl -i http://127.0.0.1:8000/health
```

更新发布建议采用版本目录 + `current` 软链接：
1. 上传新版本到 `releases/<release-id>`。
2. 在新版本虚拟环境安装锁定依赖并运行测试。
3. 执行数据库迁移（先备份，迁移应向前兼容）。
4. 原子切换 `current` 软链接。
5. `systemctl restart furry-zjut-api`。
6. 检查健康状态和日志；失败时切回旧版本软链接并重启。
7. 不要在升级期间删除旧版本或唯一可恢复的备份。

## B8. PostgreSQL 本机配置

### 网络与账号

- PostgreSQL 只监听回环地址：`listen_addresses = '127.0.0.1'`。
- 宝塔防火墙和云安全组均不开放 TCP 5432。
- 应用使用专用非超级用户 `furry_app`；迁移账号与运行账号可分离。
- 不使用 `postgres` 超级用户连接业务 API。
- `pg_hba.conf` 仅允许本机所需认证方式，优先 SCRAM-SHA-256。
- 数据库密码使用随机强密码，保存在 API 环境文件/Secret 中，不写入 Git 或日志。

### 2 GiB 服务器的保守起点

以下仅为小内存主机的初始参考值，应根据 PostgreSQL 版本、宝塔常驻内存、查询和并发情况调整：

```conf
listen_addresses = '127.0.0.1'
max_connections = 30
shared_buffers = 256MB
effective_cache_size = 768MB
work_mem = 4MB
maintenance_work_mem = 64MB
autovacuum_work_mem = 32MB
max_wal_size = 512MB
checkpoint_completion_target = 0.9
max_worker_processes = 4
max_parallel_workers = 2
max_parallel_workers_per_gather = 1
```

特别注意：
- `work_mem` 是每个排序/哈希操作的内存预算，不是数据库全局总上限；并发查询可能放大内存使用。
- `effective_cache_size` 是规划器估算值，不是实际分配的内存。
- 2C2G 主机上应用连接池应小而明确，例如 SQLAlchemy `pool_size=3–5`、`max_overflow=1–2`，结合 1 个 API Worker 先运行。
- 不要同时运行多个重型 PDF/图片处理任务。任务并发应有硬上限。
- 参数修改前备份配置，修改后用 `SHOW` 检查生效情况；只对需要重启的参数安排重启。

### 数据库与角色初始化（示意）

使用 PostgreSQL 管理账号通过本机连接执行：

```sql
CREATE ROLE furry_app LOGIN PASSWORD '替换为强随机密码';
CREATE DATABASE furry_zjut OWNER furry_app;
```

生产中建议：
- 单独建立备份角色 `furry_backup`，只授予备份所需权限。
- Alembic 迁移使用受控账号；不要在 API 运行时自动以超级用户执行迁移。
- 数据库中个人信息按最小化原则保存；限制 DBA/管理员访问并记录敏感操作。
- 定期检查连接数、慢查询、死锁、表膨胀和磁盘增长。

## B9. Redis 本机部署与配置

Redis 用于缓存、限流计数、验证码状态或可重建会话数据。**不要把 Redis 当作唯一业务数据库**；重要会话/Refresh Token 撤销状态应按安全需求持久化到 PostgreSQL 或确保 Redis 持久化和备份策略足够。

配置起点（具体路径以安装版本为准）：

```conf
bind 127.0.0.1
protected-mode yes
port 6379

# 设置强密码；Redis 6+ 优先使用 ACL 用户，而不是仅依赖单一 requirepass。
# requirepass 替换为高熵随机密码

maxmemory 64mb
maxmemory-policy allkeys-lru

# 缓存场景可关闭持久化；若 Redis 存储验证码/会话等不可轻易丢失的数据，
# 应重新评估 AOF/RDB、恢复与失效语义，不要直接套用缓存配置。
```

安全要求：
- Redis 仅监听 `127.0.0.1`，公网安全组/防火墙不开放 6379。
- 启用 ACL 或强密码；密码不放在命令行历史、日志或 Git 中。
- `maxmemory` 结合 2GB 主机实际余量调整，64MB 可作为轻量起点。
- `allkeys-lru` 只适用于允许任意缓存键淘汰的场景。若同一实例保存验证码、限流或会话状态，应使用独立 Redis DB/实例、明确 TTL 和合适的淘汰策略，避免关键状态被随意淘汰。
- 对验证码和限流键设置 TTL；用原子操作或 Lua 脚本防止并发绕过。
- 监控 `used_memory`、`evicted_keys`、命中率和连接数。
- 生产环境不要使用 Redis 无密码公网访问。

## B10. COS / 对象存储与图片域名

建议使用腾讯云 COS（也可通过 Provider 抽象接入其他 S3 兼容服务）。

### Bucket 与权限

- `furry-zjut-public`：公开 Gallery 派生图、公开站点资源；Bucket 本身仍建议保持私有，由 CDN/访问策略提供受控读取。
- `furry-zjut-private`：用户私有相册、课表、私密活动附件。
- 若暂时只使用一个 Bucket，必须使用清晰前缀和 IAM/策略隔离；不同安全级别优先拆分 Bucket。
- COS SecretId/SecretKey 仅保存在 API 服务端 Secret/环境文件中。
- API 使用最小权限子账号：只允许指定 Bucket/前缀读写，不授予整个账号管理权限。
- 数据库只保存 `provider`、`bucket`、`object_key`、`visibility`、`mime_type`、`size_bytes`、`checksum` 等元数据，不保存固定 CDN URL。

### 上传流程

1. 前端请求 `POST /api/v1/images/upload-intent`。
2. API 校验身份、角色、配额、文件大小、MIME 和用途。
3. API 生成随机 Object Key，返回短时效、限定对象 Key/方法/大小的预签名上传 URL。
4. 浏览器直接上传 COS，避免 API 服务器承担大文件带宽和内存压力。
5. 前端调用 `upload-complete`。
6. API 对 COS 对象进行 HEAD/元数据检查，必要时由轻量后台任务解码/扫描。
7. 通过审核后才允许公开访问；私有文件下载由 API 鉴权后签发短时效 URL。

### 图片域名与缓存

- `img.example.com` 绑定 COS/CDN 自定义域名并启用 HTTPS。
- 公开图片采用版本化/不可变 Object Key，允许长缓存，例如 `Cache-Control: public, max-age=31536000, immutable`（仅对内容不可变的对象）。
- 私有文件不得设置公开长缓存；签名 URL 应短时效，避免泄露后长期可用。
- 删除或替换公开内容时，优先使用新 Object Key；必要时再执行 CDN 刷新。
- COS CORS 只允许实际前端域名，按需要开放 `PUT/POST/GET/HEAD`，允许必要请求头并暴露 ETag 等响应头。COS CORS 与 API CORS 是两套独立配置。
- 上传文件校验真实格式、解码结果、尺寸和像素数；限制 SVG/HTML 等主动内容，清理 EXIF GPS。
- 预签名 URL、对象 Key 和 COS 错误响应不要写入公开日志。

## B11. 备份策略与恢复演练

### 备份范围

| 数据 | 备份方式 | 建议 |
|---|---|---|
| PostgreSQL | `pg_dump` 逻辑备份 | 每日备份，定期恢复演练 |
| PostgreSQL WAL/PITR（可选） | WAL 归档 | 业务要求更低 RPO 时再配置 |
| COS 文件 | COS 版本控制/生命周期/跨桶复制 | 数据库备份不包含文件本体 |
| API 配置 | 加密保存的配置备份 | 不把 Secret 明文放进普通备份包 |
| 前端 | Git 仓库 + EdgeOne Pages 发布记录 | 保存可回滚 commit/tag |

推荐起步保留：
- 每日备份 7 份；
- 每周备份 4 份；
- 每月备份 3 份（按存储成本和数据重要性调整）。

至少保留一份异地/独立权限备份，不能只保存在 API 服务器同一块磁盘上。备份包含个人信息，应加密传输、限制权限和设置过期删除策略。

### PostgreSQL 备份脚本

以下脚本生成本地加密前的逻辑备份文件；**上传 COS 的步骤需按实际 CLI/SDK 补齐**，不能把“本地 dump 成功”误认为异地备份完成。

```bash
#!/usr/bin/env bash
set -euo pipefail
umask 077

BACKUP_DIR="/var/backups/furry-zjut"
STAMP="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 使用权限为 0600 的 .pgpass 或 Secret 管理凭据。
export PGPASSFILE="/root/.pgpass-furry-zjut"

pg_dump \
  --host=127.0.0.1 \
  --username=furry_backup \
  --dbname=furry_zjut \
  --format=custom \
  --file="$BACKUP_DIR/furry_zjut-$STAMP.dump"

# 建议使用 age/gpg 等工具加密后再上传；密钥应与备份文件分开保管。
# 加密与 COS 上传命令需根据部署方工具链补充，并开启失败告警。

find "$BACKUP_DIR" -type f -name 'furry_zjut-*.dump' -mtime +7 -delete
```

备份实施注意：
- `.pgpass` 权限必须为 `0600`；备份脚本与日志不应位于 Web 根目录。
- 备份账号权限需满足 `pg_dump` 要求，但不应是超级用户。
- 备份任务成功条件应包括：数据库 dump 成功、加密成功、异地上传成功、校验成功。
- 不要将 COS Secret 硬编码进脚本；使用最小权限备份凭据。
- COS 备份 Bucket 与业务 Bucket 分开，最好使用不同权限/账号。
- 定期把备份恢复到临时数据库，验证表、用户、关键记录和业务查询。
- 对象存储文件应启用版本控制、生命周期或跨桶复制；数据库与文件备份需要协调时间点。

### 定时任务

确认脚本手动运行成功后，可配置每日凌晨执行：

```cron
20 3 * * * /usr/local/bin/backup-furry-zjut.sh >> /var/log/backup-furry-zjut.log 2>&1
```

配置后应设置备份失败告警（邮件/监控/运维通知），并定期检查磁盘空间。恢复演练建议至少每季度一次，重大版本升级前后也应演练。

## B12. 2C2G 服务器安全与运维基线

### 公网端口

通常只开放：
- TCP 80、443：Nginx HTTP/HTTPS（80 仅用于 HTTPS 跳转或证书验证）。
- TCP 22：SSH，建议限制来源 IP，使用密钥登录。
- 宝塔面板端口：仅运维来源 IP 白名单可访问；不向全网开放。

严禁公网开放：
- TCP 8000：Uvicorn/FastAPI。
- TCP 5432：PostgreSQL。
- TCP 6379：Redis。
- 其他内部任务、数据库管理端口。

### 系统与宝塔

- 系统和宝塔面板保持安全更新；更新前先备份并评估兼容性。
- SSH 使用密钥认证；条件允许时禁用密码登录、限制 root 远程登录。
- 宝塔面板启用强密码、MFA（若支持）和 IP 白名单，修改默认端口只能降低扫描噪音，不能替代访问控制。
- 不安装不需要的宝塔插件；2GB 内存避免常驻重型监控/扫描服务。
- API 使用非 root 用户；目录权限最小化，禁止 `chmod 777`。
- `.env` 放在站点 Web 根目录之外，建议 `root:furry` 或受控属主、权限 `640`/`600`。
- 使用 `fail2ban` 或云厂商安全防护保护 SSH（按系统能力配置）。
- 定期检查 `ss -lntup`、云安全组和宝塔防火墙规则。
- 对登录、OTP、刷新 Token、上传、搜索、报名和管理接口做分层限流。
- 生产环境关闭 FastAPI debug、reload 和公开 API 文档。
- 日志必须脱敏：不记录密码、OTP、Cookie、Authorization、Refresh Token、完整签名 URL、COS Secret。
- 个人信息最小化收集；后台敏感访问、管理员操作和权限变更必须审计。
- 安全响应头与 CSP 需结合实际前端资源域名制定；不要未经验证直接启用会导致网站功能失效的严格 CSP。
- HSTS 仅在 HTTPS、证书和所有相关子域确认正确后启用。

## B13. 2C2G 资源与任务策略

2 GiB 是整台服务器总内存。宝塔面板、Nginx、PostgreSQL、Redis、Python、系统缓存和瞬时任务都共享内存。

建议起步：
- FastAPI：1 Worker。
- PostgreSQL：`shared_buffers` 约 128–256MB 起步。
- Redis：`maxmemory` 约 64MB 起步。
- SQLAlchemy：小连接池（例如 `pool_size=3–5`，`max_overflow=1–2`）。
- 图片原图和附件：直传 COS，不经过 API 服务器。
- PDF 课表解析、图片转码：限并发；必要时拆成低优先级任务或外部 Worker。
- 不在 2C2G 主机运行 Elasticsearch、MinIO、多个 Celery Worker、完整 Prometheus/Grafana 等重型组件。

监控：
```bash
free -h
df -h
uptime
ps aux --sort=-rss | head
systemctl status furry-zjut-api
journalctl -u furry-zjut-api --since "1 hour ago"
```

如果持续 OOM 或频繁 Swap：
1. 降低图片/PDF 任务并发；
2. 检查 Python 进程 RSS 和连接池；
3. 降低 PostgreSQL 连接与内存参数；
4. 检查 Redis 是否存入了不可淘汰的大对象；
5. 精简宝塔插件与服务；
6. 优先升级 RAM 或迁移托管数据库，而不是依赖 Swap 长期运行。

## B14. 上线验收清单

- [ ] `www.example.com` 已绑定 EdgeOne Pages，HTTPS 和 SPA 刷新正常。
- [ ] `api.example.com` DNS 指向宝塔 API 服务器，HTTPS 正常。
- [ ] 前端 API Base URL 指向正式 API 域名，没有混入测试环境地址。
- [ ] CORS 只允许真实前端 Origin，预检 OPTIONS 正常。
- [ ] Cookie/Bearer 认证方案已明确；Cookie 模式具备 CSRF 防护。
- [ ] Access Token 短时效；Refresh Token 可轮换、撤销和复用检测。
- [ ] FastAPI 只监听 `127.0.0.1:8000`，公网无法直连。
- [ ] Nginx 代理头配置正确，Uvicorn 只信任本机代理。
- [ ] PostgreSQL 只监听本机，5432 未对公网开放。
- [ ] Redis 只监听本机，6379 未对公网开放，认证与内存上限生效。
- [ ] COS Bucket 默认私有；上传使用短时效预签名 URL。
- [ ] 私有图片/课表无法通过猜测 URL 或 Object Key 访问。
- [ ] `img.example.com` HTTPS、CDN 回源和缓存策略验证完成。
- [ ] 备份已加密并上传到独立存储，完成恢复演练。
- [ ] `.env`、数据库密码、COS Secret 和第三方密钥未进入 Git/前端构建。
- [ ] 宝塔面板和 SSH 已限制访问来源。
- [ ] 管理员 MFA、审计日志、限流、日志脱敏和告警已启用。
- [ ] 2C2G 正常负载下内存有余量，无持续 OOM/Swap 抖动。
- [ ] API、数据库、Redis、对象存储和 EdgeOne Pages 均有独立发布/回滚方案。

## B15. 最终部署决策摘要

| 组件 | 最终选择 | 关键约束 |
|---|---|---|
| 前端 | 腾讯云 EdgeOne Pages | 静态 SPA；自定义 `www` 域名；SPA fallback |
| API | 宝塔 2C2G 服务器 | FastAPI + Uvicorn 1 Worker + systemd |
| 反向代理 | 宝塔 Nginx | 只代理 API；TLS、请求限制、安全头 |
| 数据库 | PostgreSQL 本机部署 | 仅回环监听；不开放公网 5432 |
| 缓存 | Redis 本机部署 | 回环监听、认证、内存上限；不作为唯一数据源 |
| 文件 | 腾讯云 COS/S3 兼容存储 | Bucket 私有、预签名 URL、最小权限 |
| 图片 CDN | `img.example.com`（可选） | HTTPS、公开内容缓存、私有资源短签名 |
| 备份 | PostgreSQL dump + COS 文件策略 | 异地备份、加密、定期恢复演练 |
| 安全 | CORS + 认证 + CSRF + 限流 + MFA | 不能把 CORS 当作认证；密钥不进前端 |

**推荐上线形态：EdgeOne Pages（前端） + 宝塔 Nginx（API 入口） + FastAPI systemd + PostgreSQL/Redis 本机 + COS（文件）**。该方案保持前后端分离，同时避免 2C2G 服务器承担静态前端和大文件分发压力。
