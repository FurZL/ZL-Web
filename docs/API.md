# Furry ZJUT API 文档

> 当前代码的 OpenAPI 注册 **130 个 API 路径（153 个方法端点）**。本数量包含图片处理任务、仪表盘、举报处理、群组多人邀约、课表运营配置与审计等接口。
> 统一前缀：`/api/v1`。大多数业务接口使用 `{"success": bool, "data": ..., "error": {"code", "message"}, "request_id": str}`；健康检查等接口以各端点说明为准。

## 通用约定

- 统一前缀：`/api/v1`
- 统一响应结构：

```json
{
  "success": true,
  "data": {},
  "error": null,
  "request_id": "server-generated-id"
}
```

- 错误响应：

```json
{
  "success": false,
  "data": null,
  "error": { "code": "RATE_LIMITED", "message": "请求过于频繁，请稍后再试" },
  "request_id": "server-generated-id"
}
```

- 各列表的分页能力以具体端点实现为准；例如用户管理列表当前一次性返回全部记录。
- 写操作使用权限校验；报名等关键操作用幂等键。
- API 文档仅在开发环境或管理员授权后公开；生产禁用。
- 登录、OTP 发送、刷新令牌与密码重置按客户端 IP 做应用层限流，超限返回 HTTP 429 `RATE_LIMITED`。
- 公开图库图片和头像使用 `PUBLIC_ASSET_BASE_URL`；个人相册原图和缩略图通过后端短期票据及 `/profile/media` 代理读取。`PUBLIC_API_BASE_URL` 在跨域部署时应设置为浏览器可访问的 API 源。COS 原生预签名 URL 用于上传直传；COS/CDN 必须禁止直接读取 `private/`，详见 `SECURITY.md`。
- 用户角色与状态变更仅管理员可操作；授予/修改 `admin`、`super_admin`、`moderator` 角色仅 `super_admin` 可执行。
- 生产环境同时关闭 `/docs`、`/redoc`、`/openapi.json`。
- QQ 登录与绑定：`POST /auth/oauth/qq/start`、`POST /auth/oauth/qq/bind-start`、`GET /auth/oauth/qq/callback`、`POST /auth/oauth/qq/bind`、`GET /auth/oauth/providers`；`state`/授权码经 Redis 短时效保存并一次性消费，前端回调页只负责完成登录态。

## 接口清单（模块 → 文件对照）

| 模块 | 前缀 | 后端文件 |
|---|---|---|
| 健康检查 | `/health` `/ready` | `endpoints/health.py` |
| 认证 | `/auth` | `endpoints/auth.py` |
| 第三方登录 | `/auth/oauth` | `endpoints/oauth.py` |
| 人机验证 | `/captcha` | `endpoints/captcha.py` |
| 图片 | `/images` | `endpoints/images.py` |
| 图片管理 | `/admin/images` | `endpoints/admin_images.py` |
| 个人空间 | `/profile` | `endpoints/profile.py` |
| 课表 | `/schedule` | `endpoints/schedule.py` |
| 公告 | `/announcements` | `endpoints/announcements.py` |
| 社团介绍 | `/club` | `endpoints/club.py` |
| 活动 | `/events` | `endpoints/events.py` |
| 活动管理 | `/admin/events` | `endpoints/admin_events.py` |
| 动态页面 | `/pages` | `endpoints/pages.py` |
| 站点配置 | `/site` | `endpoints/site.py` |
| 用户管理 | `/admin/users` | `endpoints/admin_users.py` |
| 课表运营管理 | `/admin/schedule` | `endpoints/admin_schedule.py` |
| 操作审计 | `/admin/audit` | `endpoints/admin_audit.py` |
| 管理仪表盘 | `/admin/dashboard` | `endpoints/admin_dashboard.py` |
| 网站设置 | `/admin/settings` | `endpoints/admin_settings.py` |

---

## 管理操作审计 `/admin/audit`

`GET /admin/audit` 需要 `site_config.manage` 权限。支持 `page`（从 1 开始）、`page_size`（1–100，默认 20）、`target_type`、`action`、`actor_id`（UUID）及带时区的 `start` / `end`；条件精确匹配，时间区间包含边界。响应为 `{items, total, page, page_size}`，按时间和 ID 倒序。每项包含 `id`、`actor_id`、`actor_name`、`action`、`target_type`、`target_id`、`request_id`、`ip_masked`、`changes` 和 `created_at`；历史课表设置审计也可查询。

用户审批/角色/状态、网站设置和社团介绍、图片审核/可见性/标签/删除、公告和活动管理（包括管理员签到）、动态页面及发布/回滚写入同一 PostgreSQL 事务。仅保存白名单状态等前后值和其他修改字段名；正文、联系方式、密码、令牌、任意设置值不写入。注册和 QQ 设置中明确允许的布尔开关例外。无实际业务字段变化不生成新记录。失败请求、登录失败和用户自己的课表/群组操作尚未纳入。数据库变更与记录同事务，但对象存储操作属于外部副作用，不参与数据库事务。

审计表不是防篡改数据库；需要防管理员或数据库操作者篡改时，应配置独立权限、备份或外部日志归档。

## 认证说明

| 认证方式 | 说明 |
|---|---|
| **无需认证** | 游客可访问（如公开图片、健康检查、站点配置） |
| **Bearer Token** | 请求头 `Authorization: Bearer <access_token>`，登录后获取 |
| **管理权限** | 需管理员/超管角色，端点内做逐请求 RBAC 校验 |

**Token 机制**：短时效 Access Token（15 分钟，仅前端内存）+ Refresh Token（默认 7 天，后端 `HttpOnly` Cookie 跨标签页共享）。浏览器请求携带 Cookie；前端 `client.ts` 拦截 401 自动刷新重试，7 天滑动续期。

---

## 一、健康检查

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/health` | 无 | 存活检查，返回 `{status: "ok"}` |
| GET | `/ready` | 无 | 检查 PostgreSQL `SELECT 1` 和 Redis `PING`，返回 `{status, database, redis}`；任一失败或超时返回 503 |

---

## 二、认证 `/auth`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/auth/register` | 无 | 注册（受 registration_config 门控，关闭返回 403；密码须含大小写字母和数字；前端须传 password_confirm；须同意用户协议与隐私政策） |
| POST | `/auth/verify/email` | 无 | 邮箱 OTP 验证（120s 冷却，须先通过人机验证，传入 verification_token） |
| POST | `/auth/verify/phone` | 无 | 手机 OTP 验证（120s 冷却，须先通过人机验证，传入 verification_token） |
| POST | `/auth/login` | 无 | 登录（须先通过人机验证），返回 `{access_token, user}`，Refresh Token 仅写入 HttpOnly Cookie |
| POST | `/auth/refresh` | Refresh Cookie | 轮换 Refresh Token 并检测会话族重放；Cookie 缺失时可传 body.refresh_token，响应不包含 Refresh Token |
| POST | `/auth/logout` | Refresh Cookie | 登出（撤销当前 Refresh Token Cookie） |
| POST | `/auth/logout-all` | Bearer | 登出所有设备（撤销全部会话并清除 Refresh Cookie） |
| POST | `/auth/password/forgot` | 无 | 找回密码（发送验证码） |
| POST | `/auth/password/reset` | 无 | 重置密码（验证码 + 新密码；真实更新密码 + 撤销全部会话） |
| GET | `/auth/me` | Bearer | 获取当前用户信息（含 bio/avatar_url） |

使用 Cookie 的 refresh/logout 必须提供匹配 `FRONTEND_ORIGINS` 的 Origin，缺失 Origin 时可使用同源 Referer；不匹配返回 403。登录请求若带 Origin 也须匹配。旧 Access Token 需通过刷新换取带用途标识的新令牌。Web Locks 可用时前端会串行化跨标签页刷新。

### 阿里云短信（2026-11-16）

- `SMS_PROVIDER=aliyun` 时启用 `AliyunSmsProvider`，封装 `alibabacloud_dysmsapi20170525` SDK
- 配置字段：`SMS_ALIYUN_ACCESS_KEY_ID`、`SMS_ALIYUN_ACCESS_KEY_SECRET`、`SMS_ALIYUN_SIGN_NAME`、`SMS_ALIYUN_TEMPLATE_CODE`、`SMS_ALIYUN_REGION`
- 发送目标为 E.164 格式（`+8613800000000`），短信内容为 `{"code":"123456"}`，由模板 `SMS_512658529` 渲染

### 注册门控、密码强度与 OTP 冷却（2026-11-15）

- `POST /auth/register` 先读取 `registration_config`：`registration_enabled=false` 时返回 403；`require_email_verification` / `require_phone_verification` 为 false 时跳过对应 OTP 校验。
- 注册和找回密码请求体新增 `password_confirm` / `new_password_confirm`，前后端都校验两次密码一致，且密码必须同时包含大小写字母和数字。
- 注册请求新增 `terms_accepted`、`privacy_accepted`（均须为 `true`，否则返回 422 `LEGAL_CONSENT_REQUIRED`）以及 `terms_version`、`privacy_version`；服务端在 `users` 表记录协议版本和 `legal_accepted_at` 同意时间。注册页提供两个独立勾选框，并链接到 `/legal/terms`、`/legal/privacy`。
- 注册请求还校验用户名 3–64 字符、昵称 1–64 字符、密码 8–128 字符；前端同步检查必填项、邮箱格式及验证码格式。FastAPI 422 字段错误会由前端客户端映射为带字段名的中文提示；具体注册失败原因仍以该次响应为准。
- `POST /auth/verify/email`、`POST /auth/verify/phone` 对同一目标、同一用途执行 120 秒发送冷却，未到期返回业务错误码 `COOLDOWN`；前端按钮同时倒计时禁用。
- 注册成功后异步发送「等待审批」邮件；管理员审批通过/拒绝时也会发送对应结果邮件，邮件发送失败不阻塞主流程。

---

## 人机验证 `/captcha`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/captcha/challenge` | 无 | 获取滑块验证挑战，返回 `{token, gap_x, gap_y, expires_in}`（120s 有效），坐标存 Redis |
| POST | `/captcha/verify` | 无 | 校验滑块位置 `{token, x}`，±6px 容差，通过返回 `{verification_token}`（300s 有效，一次性消耗） |

`LoginRequest`、`OtpRequest` 均新增可选字段 `verification_token`；登录和获取验证码都须先通过人机验证，否则返回 400 `CAPTCHA_REQUIRED`。

---

## 第三方登录 `/auth/oauth`

QQ 的 App ID / App Key 只从后端环境变量读取；`state` 与未绑定账号的临时授权凭证都保存在 Redis，默认 10 分钟过期且一次性消费。前端回调页固定为 `/oauth/qq`。

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/auth/oauth/providers` | 无 | 返回可用的第三方登录方式及 `frontend_base_url` |
| POST | `/auth/oauth/{provider}/start` | 无 + 人机验证 | 发起第三方登录，返回 `{authorize_url}`；`provider` 目前仅支持 `qq` |
| POST | `/auth/oauth/{provider}/bind-start` | Bearer + 人机验证 | 已登录用户发起账号绑定，返回 `{authorize_url}` |
| GET | `/auth/oauth/{provider}/callback` | 无 | QQ 回调：消费 `state`，换取 QQ 身份。已绑定时返回 `{bound:true,user,access_token}` 并写入 Refresh Cookie；未绑定时返回 `{bound:false,oauth_token,nickname,return_to}` |
| POST | `/auth/oauth/{provider}/bind` | 人机验证 | 未绑定 QQ 用本站账号密码完成绑定并登录；请求 `{oauth_token,account,password,verification_token}` |

`start` / `bind-start` 请求体为 `{verification_token, return_to?}`。`return_to` 只允许站内绝对路径（必须以 `/` 开头且不能是 `//`），否则返回 400 `INVALID_RETURN_TO`。回调参数为 `code` 与 `state`。

OAuth 登录与绑定均通过 HttpOnly Cookie 返回 Refresh Token，JSON 不包含该令牌。

常见错误：`CAPTCHA_REQUIRED`（未完成拼图验证）、`OAUTH_DISABLED`（后台关闭该方式）、`OAUTH_QQ_UNAVAILABLE`（App ID/Key 未配置）、`OAUTH_STATE_INVALID`（state 过期/已消费）、`OAUTH_ALREADY_BOUND`（该 QQ 已绑定其他账号）、`OAUTH_PENDING_EXPIRED`（未绑定临时凭证过期）、`PENDING_APPROVAL` / `ACCOUNT_DISABLED`。

---

## 三、用户管理 `/admin/users`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/admin/users/` | 管理员 | 用户列表 |
| GET | `/admin/users/pending` | 管理员 | 待审批用户列表 |
| GET | `/admin/users/{user_id}` | 管理员 | 用户详情 |
| POST | `/admin/users/{user_id}/approve` | 管理员 | 审批通过（激活账号） |
| POST | `/admin/users/{user_id}/reject` | 管理员 | 拒绝注册申请 |
| PATCH | `/admin/users/{user_id}/role` | 管理员 | 修改用户角色（禁止改自己；admin/super_admin 仅 super_admin 可授予） |
| PATCH | `/admin/users/{user_id}/status` | 管理员 | 启用/禁用用户（禁止改自己；禁用时自动撤销全部会话；不能禁用 super_admin） |

---

## 四、公开图片 `/images`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/images/` | 无 | 公开图片列表（分页，支持 `page`/`page_size` 参数） |
| GET | `/images/{image_id}` | 无 | 图片详情（含 URL/描述/标签/拍摄者） |
| POST | `/images/upload-intent` | 摄影师+ | 申请上传凭证（返回预签名上传 URL） |
| POST | `/images/upload-complete` | 摄影师+ | 上传完成（后端 HEAD 复核 + 落库） |
| GET | `/images/{image_id}/download` | Bearer | 返回原图代理域下载 URL（不暴露 COS 原生预签名地址） |
| DELETE | `/images/{image_id}` | Bearer | 删除图片（仅上传者本人或有 gallery.image.delete.any 权限；含派生图清理） |
| POST | `/images/{image_id}/report` | Bearer | 举报已公开且审核通过的图片（不能举报自己的图片；同一用户对同一图片仅一条未处理举报） |

**上传流程**：`upload-intent` → 前端直传 COS → `upload-complete` → 后台 worker 生成缩略图（800px）/展示图（2000px）WebP。

---

## 五、个人空间 `/profile`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/profile/me` | Bearer | 获取个人信息（含 bio/avatar_url） |
| PUT | `/profile/me` | Bearer | 修改个人信息（display_name / bio / avatar_url，字段级更新） |
| GET | `/profile/me/images` | Bearer | 私有相册列表（仅本人可见） |
| GET | `/profile/me/layout` | Bearer | 本人布局草稿、已发布块、主题、素材与统计（已实现） |
| PUT | `/profile/me/layout` | Bearer | 整体替换本人草稿及可选公开开关（已实现，不发布、不保存主题） |
| POST | `/profile/me/layout/publish` | Bearer | 校验草稿后发布，返回带时区的 published_at |
| POST | `/profile/me/layout/discard` | Bearer | 丢弃草稿并恢复到已发布版本，返回完整布局 |
| PUT | `/profile/me/theme` | Bearer | 严格校验并保存主题，返回完整布局 |
| GET | `/profile/me/media` | Bearer | 本人所有私有图片素材及后端短期票据 URL（含展示授权状态） |
| PATCH | `/profile/me/images/{image_id}` | Bearer | 更新本人私有图的展示授权 is_displayable（已实现） |
| GET | `/profile/{username}/page` | 无 | 匿名读取已发布且公开的个人主页 |
| POST | `/profile/me/images/upload-intent` | Bearer | 私有图片上传凭证 |
| POST | `/profile/me/images/upload-complete` | Bearer | 私有图片上传完成 |
| GET | `/profile/me/images/{image_id}/url` | Bearer | 校验本人归属后返回带短期票据的后端原图 URL |
| DELETE | `/profile/me/images/{image_id}` | Bearer | 删除私有图片 |
| POST | `/profile/me/avatar/upload-intent` | Bearer | 头像上传凭证（返回 COS 预签名 URL，限 5MB） |
| POST | `/profile/me/avatar/upload-complete` | Bearer | 头像上传完成（验证对象存在，自动清理旧头像） |
| DELETE | `/profile/me/avatar` | Bearer | 删除头像 |
| GET | `/profile/members` | 无 | 公开成员列表（active 用户昵称/简介/头像，不含隐私） |
| GET | `/profile/{user_id}` | 无 | 公开用户资料（昵称/角色，不含隐私） |
| GET | `/profile/me/third-party` | Bearer | 查询本人已绑定的第三方账号（provider / provider_user_id / created_at） |
| DELETE | `/profile/me/third-party/{provider}` | Bearer | 解绑本人第三方账号；目前 `provider` 仅支持 `qq` |

### 头像上传流程（2026-11-15）

前端浏览器端处理：用户选择图片 → `AvatarCropDialog` 弹窗框选正方形区域 → Canvas 两步缩放为 128×128 JPEG（质量 0.85）→ 申请 `upload-intent` → 直传 COS → `upload-complete` 确认。全链路不上传原图。

**响应字段变更（2026-11-15）：**
- `POST /auth/login` 的 `user` 对象新增 `avatar_url`（公开 URL）和 `bio`
- `GET /auth/me` / `GET /profile/me` / `PUT /profile/me` 的 `avatar_url` 改为动态公开 URL
- `GET /images/` / `GET /images/{id}` 新增 `photographer_avatar` 字段（拍摄者头像公开 URL）
- `GET /profile/members` 的 `avatar_url` 改为动态公开 URL

### 本分支新增契约（2026-11-13）

`GET /profile/me/layout` 与成功的 `PUT /profile/me/layout` 返回同形 `data`：

```json
{
  "theme": {
    "primary": "#6B5CE7",
    "accent": "#F0A6C8",
    "background_type": "gradient",
    "background_key": null,
    "background_blur": 0,
    "card_style": "glass"
  },
  "draft_blocks": [],
  "published_blocks": null,
  "is_public": true,
  "max_blocks": 16,
  "media": {},
  "media_expires_in": 900,
  "stats": { "joined_days": 0, "gallery_image_count": 0 }
}
```

`max_blocks` 取自 `PROFILE_LAYOUT_MAX_BLOCKS`（默认 16），`media_expires_in` 取自 `PRIVATE_URL_TTL_SECONDS`（默认 900 秒），示例中的统计值仅为说明。没有布局记录时返回空草稿及默认主题，不创建记录；从未发布时 `published_blocks` 为 `null`。

`PUT /profile/me/layout` 请求示例：

```json
{
  "blocks": [
    { "id": "bio_1", "type": "bio", "span": 8, "props": { "text": "你好，欢迎来到我的主页" } }
  ],
  "is_public": true
}
```

- 请求体必须是对象，`blocks` 为必填数组；`is_public` 可选且必须为布尔值。服务端按 JSON 重新编码后限制在 256 KiB，按白名单重新序列化后落库，未知字段丢弃。`theme` 不在此端点保存。
- `id` 匹配 `^[A-Za-z0-9_-]{1,32}$`，同一布局内唯一；模块数不超过配置上限。`span` 和 `props` 按类型校验：

| type | 允许 span | props 限制 |
|---|---|---|
| `bio` | 4 / 6 / 8 / 12 | text ≤ 500 字符 |
| `quote` | 4 / 6 / 12 | text ≤ 160，author ≤ 40 |
| `featured_photo` | 12 | 非空 object_key ≤ 1024，caption ≤ 80 |
| `photo_wall` | 6 / 8 / 12 | object_keys 最多 12 个非空字符串；columns 仅 2 或 3 |
| `gallery_link` | 3 / 4 / 6 / 12 | tag ≤ 40；非空 label ≤ 20 |
| `links` | 3 / 4 / 6 | items 最多 8 项；非空 label ≤ 20、非空 URL ≤ 300，仅 http/https 且有主机名 |
| `stats` | 3 / 4 / 6 / 12 | items 最多 2 项，仅 joined_days / gallery_image_count |
| `html_block` | 12 | html ≤ 24576 字符；height 仅 200 / 400 / 600；前端使用隔离 iframe 渲染 |

照片和背景素材必须是本人的 `ProfileImage`、已开启 `is_displayable`，且对象 Key 位于 `private/profiles/{当前用户 id}/` 前缀下。`media` 按 object_key 映射 `{thumb_url, display_url, width, height}`；URL 为后端短期签名票据，非 COS 地址。公开票据每次访问时复核主页发布状态、引用和展示授权；本人票据仅通过认证接口签发。`stats` 在每次布局/公开主页读取时重新计算：`joined_days` 为账号创建后经过的完整 24 小时数；`gallery_image_count` 只统计本人 `approved` 且 `is_public=true` 的公开图库图片，不包含个人空间私有相册。

`PATCH /profile/me/images/{image_id}` 接受严格请求体 `{"is_displayable": true}`，拒绝额外字段和字符串/整数布尔值，成功返回 `{"id": "图片 UUID", "is_displayable": true}`。此标记默认 `false`，不会自动发布主页或把私有相册整体公开。

### 个人主页发布与公开读取（2026-11-15）

- `POST /profile/me/layout/publish` 不接受请求体。草稿为空时返回 422 `PROFILE_LAYOUT_EMPTY`；成功时把通过结构与素材授权复核的草稿复制到已发布版本，并返回 `{ "published_at": "ISO-8601 with timezone" }`。
- `POST /profile/me/layout/discard` 不接受请求体。草稿恢复为已发布块；尚无已发布版本时恢复为空数组。响应与 `GET /profile/me/layout` 同形。
- `PUT /profile/me/theme` 请求体为 `ProfileTheme` 对象本身，包含 `primary`、`accent`、`background_type`、`background_key`、`background_blur`、`card_style`。颜色必须为 `#RRGGBB`，类型/卡片样式只能取已定义枚举，模糊度为整数 `0–20`，额外字段拒绝。非空 `background_key` 必须是本人可展示的私有图片。成功响应与 `GET /profile/me/layout` 同形。
- `GET /profile/me/media` 返回 `{ "items": [...] }`。列表包括本人所有私有图片（无论 `is_displayable` 状态），字段为 `id`、`object_key`、`title`、`created_at`、`is_displayable`、`thumb_url`、`display_url`、`width`、`height`。对象 Key 必须位于本人 `private/profiles/{user_id}/` 前缀；URL 的有效期为 `PRIVATE_URL_TTL_SECONDS`。
- `GET /profile/media/{image_id}/{thumb|original}?ticket=...` 验证短期票据并代理图片，过期、篡改或授权撤销返回 404；响应 `Cache-Control: private, no-store`。票据本身是临时访问凭证，日志不得记录查询字符串。
- `GET /profile/{username}/page` 无需登录。仅当用户为 active、存在布局、`is_public=true` 且 `published_blocks` 非 `null` 时返回主页。用户不存在、未发布、设为私有或未启用都统一返回 404 `PROFILE_PAGE_NOT_FOUND` / `该用户还没有公开主页`。响应中的 `user` 只含 `username`、`display_name`、`avatar_url`；公开素材仅返回已发布内容引用且仍为本人授权展示的图片，不返回邮箱、手机号或用户 UUID 字段。

对应服务函数：`publish_layout()`（发布及素材复核）、`discard_layout()`（恢复草稿）、`put_theme()`（主题持久化）、`get_media_options()`（本人素材清单）、`get_public_page_payload()`（公开主页与隐私过滤）。

| HTTP | 错误码/响应 | 触发条件 |
|---|---|---|
| 401 | 现有认证错误 | 缺少/无效凭证或账号未启用 |
| 422 | `detail.code=PROFILE_LAYOUT_INVALID` | 布局结构、数量、模块字段/宽度或素材归属/展示权限不符；块级错误消息包含块 id |
| 422 | `detail.code=PROFILE_LAYOUT_TOO_LARGE` | 布局超过 256 KiB 或无法按有效 JSON 编码 |
| 422 | `detail.code=PROFILE_LAYOUT_EMPTY` | 空草稿发布 |
| 422 | `detail.code=PROFILE_THEME_INVALID` | 主题字段格式、取值范围或背景素材授权无效 |
| 422 | FastAPI 请求校验错误 | PATCH 严格布尔值/额外字段校验失败 |
| 404 | `detail.code=PROFILE_IMAGE_NOT_FOUND` | 图片 UUID 非法、不存在或不属于当前用户 |
| 404 | `detail.code=PROFILE_PAGE_NOT_FOUND` | 公开主页不存在、未发布、已隐藏或用户未启用 |

### 前端个人主页函数

`getProfilePage()`、`publishMyLayout()`、`discardMyDraft()`、`saveMyTheme()` 和 `getMyMedia()` 均已有对应真实 FastAPI 端点；`saveMyTheme()` 的响应包含完整布局数据，前端继续使用其中的 `theme` 字段。`getMyLayout()`、`saveMyLayout()` 与 `setProfileImageDisplayable()` 保持原契约。

---

## 六、课表 `/schedule`

### 课表运营配置

`GET /site/public-config` 包含 `schedule_config`，由四个布尔字段组成，默认均为 `true`：`file_import_enabled`（ICS/TXT 上传与 PDF 预览）、`group_join_enabled`（创建或加入群组）、`public_share_enabled`（新增公开分享）、`fixed_invite_enabled`（发起固定时间邀约）。浏览器扩展和手工创建不受文件导入开关影响。关闭时相应新操作由后端返回 403 `SCHEDULE_FEATURE_DISABLED`；已有公开课表不会自动撤销，用户仍可改回私有；已有群组和邀约仍可管理。配置发生变化后，已打开的课表页面需重新进入或刷新才能读取新配置，服务端立即执行新规则。

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/admin/schedule/config` | `site_config.manage` | 获取四项课表开关 |
| PUT | `/admin/schedule/config` | `site_config.manage` | 完整提交四个严格布尔字段；设置与变更审计在同一事务提交 |
| GET | `/admin/schedule/overview` | `site_config.manage` | 返回课表总数、存档数、公开数、群组数与邀约状态数量；不返回课程或个人日程 |
| GET | `/admin/schedule/audit` | `site_config.manage` | 最近 50 条课表设置变更（操作者、时间、变更前后开关值） |

通用 `PUT /admin/settings/` 拒绝 `schedule_config`，避免绕过专用接口的校验与审计。该概况不包含历史导入成功率，现阶段没有新增导入事件记录。

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/schedule/mine` | Bearer | 我的课表列表（按拖动顺序，含 `is_archived`） |
| PUT | `/schedule/order` | Bearer，本人 | 课表架拖动排序（提交本人全部课表完整顺序） |
| POST | `/schedule/manual` | Bearer | 创建手工课表（默认私有，返回 201） |
| POST | `/schedule/pdf-preview` | Bearer | 解析 PDF 课表并返回预览（multipart，内存解析，不保存原文件） |
| PUT | `/schedule/{schedule_id}/slots` | Bearer，本人 | 保存课程及个人日程；版本冲突返回 409 |
| PUT | `/schedule/{schedule_id}/timing` | Bearer，本人 | 保存当前课表的节次作息；与 slots 共用 revision |
| POST | `/schedule/upload-intent` | Bearer | 课表上传凭证 |
| POST | `/schedule/upload-complete` | Bearer | 上传完成（后端下载+解析 ICS/TXT） |
| GET | `/schedule/{schedule_id}` | Bearer | 课表详情（含解析后的课程列表） |
| POST | `/schedule/compare` | Bearer | 两人课表对比（空闲/同教室/冲突） |
| GET | `/schedule/shared/{username}` | Bearer | 获取对方公开的课表 |
| PATCH | `/schedule/{schedule_id}/visibility` | Bearer | 课表公开/私有开关 |
| PATCH | `/schedule/{schedule_id}` | Bearer，本人 | 课表架：重命名，或存档/恢复到历史 |
| DELETE | `/schedule/{schedule_id}` | Bearer | 删除课表 |

**编辑与日程（2026-11-18）**：

- `POST /schedule/manual` 接受 `{ "name": "我的学期课表", "slots": [], "timing": null }`；名称去首尾空白后 1–255 字符，slots 和 timing 可省略。提供 timing 时按完整作息规则校验，并确认其节数覆盖所有课程；省略时根据课程节次生成默认作息。返回完整 `ScheduleRecord`，`format="manual"`、`is_public=false`、`is_archived=false`、`revision=0`，无需上传文件。
- 课表架（2026-11-23）：`PATCH /schedule/{schedule_id}` 接受 `{ "original_name": "2026 秋 · 大三上" }` 和/或 `{ "is_archived": true }`，至少提供一项；名称去空白后 1–255。存档后课表仍出现在 `GET /schedule/mine` 中并带 `is_archived=true`，但不会再被按用户名/owner 的公开查询返回，也不能设为公开（先恢复，否则 422 `ARCHIVED_SCHEDULE`）；存档会自动撤销 `is_public`。恢复只改变 `is_archived`，公开状态需要重新开启。该状态是新增列 `schedules.is_archived`（Alembic `c4a91e7d2b60`），旧记录默认 false；重命名与存档不递增 revision。
- 课表架拖动排序（2026-11-23）：`PUT /schedule/order` 接受 `{ "ids": ["…", "…"] }`，必须是本人全部课表的完整顺序；遗漏、重复或包含他人课表返回 409 `ORDER_MISMATCH`。服务端按数组位置写入 `schedules.sort_order`（Alembic `e9b2f7c4a1d0`），`GET /schedule/mine` 按 `sort_order ASC, created_at DESC` 返回。新建课表 `sort_order=0`，会排在同为 0 的旧课表之前；排序不递增 revision，也不改变存档或公开状态。
- PDF 课表导入（2026-11-24）：`POST /schedule/pdf-preview` 接收 multipart 字段 `file`（仅 PDF，≤10 MB、≤5 页，需登录），在内存中用 `pdfplumber` 解析教务文字层表格，返回 `{suggested_name, slots, warnings}`。支持同一格多门课、合并节次和跨页续接（第 2 页 10–12 节详情与上一页课程名拼接）；页眉姓名/学号等个人信息不返回。原 PDF 不落库、不写对象存储、不记录原文。解析失败返回 422：`PDF_NO_TEXT`（疑似扫描件）、`PDF_LAYOUT_UNSUPPORTED`、`PDF_NO_COURSE`、`PDF_TOO_LARGE` 等。PDF 只提供节次、没有具体上下课时间，确认预览时仍使用默认作息；保存仍走 `POST /schedule/manual`。
- 教务浏览器扩展不新增后端端点：扩展只把用户确认发送的规范化课程交给本站课表页，本站预览后以 `POST /schedule/manual` 一次保存 `name`、`slots` 和 `timing`。扩展不读取 SSO 凭据；数据在本站确认前不写入账号。
- `PUT /schedule/{schedule_id}/slots` 接受 `{ "revision": 0, "slots": [...] }`，整体替换当前课表的条目，包括导入的课程。允许空数组以删除全部条目。必须本人操作，其他用户返回 404；服务端锁行后比较版本，过期版本返回 409 `SCHEDULE_CONFLICT`，不写入；成功返回完整记录和递增后的 revision。原始导入文件不被覆盖。
- 每条 slots 字段：`name`（非空 ≤255）、`location`（可空 ≤255）、`campus`（可空 ≤128）、`weekday`（0–6）、`lesson_start/lesson_end`（1–24，结束不早于开始）、`weeks`（1–53 的整数列表，保存时至少一周、去重排序）、`kind`（`course` 或 `event`，默认 course）。单条请求最多 500 个条目，编辑请求拒绝未知字段。
- 新增字段保存在现有 `Schedule.parsed_json`，无需为课表编辑单独迁移。课表架的 `is_archived` / `sort_order` 是独立列，迁移见 2026-11-23 两条。旧记录缺失 revision 时按 0、缺失 kind 时按 course、缺失 timing 时返回默认 08:00 起始/45 分钟课程/10 分钟间隔。新建课程和个人日程均参与占用计算。日程属于当前课表，不自动跨学期共享。
- `timing` 包含 `term_start`（学期第一周周一，可空）、`first_start`、`lesson_minutes`、`break_minutes`、`segments` 与 1–24 组 `periods`，默认生成 12 节。`segments` 为 `{ "noon": "12:00", "afternoon": "14:00", "evening": "18:00" }`，分别表示“上午→中午、中午→下午、下午→晚上”的边界，必须严格递增；旧课表缺少时返回默认值。设置窗格可以添加或删除最后一节，逐节修改午休等特殊间隔，并调整时段边界；课表网格的行数、节次时间、上午/中午/下午/晚上分段和约饭匹配均读取同一配置。已有课程使用的最大节次不能被删除。
- 新建或导入课表时，如果课程节次高于默认作息可容纳的当天时间范围，接口返回 `TIMING_REQUIRED`（422），提示先调整开始时间、课时或节间隔；ICS 节次解析上限为 24，不会在第 12 节截断。
- 本人列表、详情和保存响应包含日程详情。其他用户读取公开课表的 ID 端点、按用户名/owner 查询均将 event 名称替换为“已有安排”、location 置空、campus 置 null，仅保留 kind、星期、节次、周次。公开权限可随时撤销，原始文件仍私有。
- `POST /schedule/compare` 接受原有 `slots_a/slots_b`，新增可选 `week`（1–53 或 null）。指定周时只计算该周的课程与日程；省略/null 时 `both_free` 是扣除任意周占用后的**整学期保守空闲**，并非周次交集。历史条目 weeks 为空时保守视为每周占用。
- 响应仍为 `same_classroom`、`both_free`、`overlaps`，新增 `week` 回显。同教室与冲突须星期、节次、周次重叠；只有两个 course 且非空地点一致、已知校区不矛盾时归入同教室。event 即使地点相同也归入冲突，不作为同教室课程。
- 前端切换对比周次会重读双方最新课表，避免使用旧日程。此接口只对比周次与节次；日期日程、路程缓冲与学期映射由下方约饭服务处理。

### 课表群组 `/schedule/groups`（2026-11-25）

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/schedule/groups` | Bearer | 我的群组列表（含待审批状态） |
| POST | `/schedule/groups` | Bearer | 创建群组 `{name, join_mode}`，返回邀请码 |
| POST | `/schedule/groups/join` | Bearer | 用邀请码加入 `{code}`；open 直接进，approval 转待审批 |
| GET | `/schedule/groups/{group_id}` | 群成员 | 群组详情；可选 `week=1–53`，返回成员与逐人忙闲统计 |
| PATCH | `/schedule/groups/{group_id}` | 群主 | 改名或切换 `join_mode` |
| DELETE | `/schedule/groups/{group_id}` | 群主 | 解散群组 |
| PUT | `/schedule/groups/{group_id}/schedule` | 群成员 | 设置本人共享给群的课表 `{schedule_id}`，`null` 取消 |
| POST | `/schedule/groups/{group_id}/availability` | 活跃群成员 | `{week, member_ids}` 查询本人及 1–9 个指定成员的共同空闲 |
| POST | `/schedule/groups/{group_id}/appointments` | 活跃群成员 | `{week, member_ids, weekday, lesson_start, title, location?}` 发起一个单节固定时间的群组邀约 |
| POST | `/schedule/groups/{group_id}/members/{user_id}/approve` | 群主 | 同意待审批成员 |
| POST | `/schedule/groups/{group_id}/members/{user_id}/reject` | 群主 | 拒绝待审批成员 |
| DELETE | `/schedule/groups/{group_id}/members/{user_id}` | 群主/本人 | 移除成员或自己退群 |

- 群组名 1–50 字；邀请码 8 位大写字母/数字（去掉易混淆字符），不区分大小写；`join_mode` 为 `open` / `approval`。每个用户最多同时加入 20 个群组，群组最多 50 名有效成员。
- 成员只能共享自己**未存档**的课表；仅 active 成员可设置共享课表。其他成员看到课程名称/地点/校区，但 event（个人日程）统一脱敏为“已有安排”、地点为空；待审批成员看不到邀请码、成员课表或统计。非成员访问统一 404。
- 群组详情以“我”为基准，逐人返回 `stats`：`both_free`（双方都空闲的 7×节次格数）、`both_busy`、`my_busy_only`、`their_busy_only`、`same_classroom` 和 `lesson_count`；点击成员可进入双人对比。
- 多人查询需要所有所选用户为活跃群成员、账号可用、共享未存档课表且设置学期第一周。返回 `{week, member_count, slots}`，每项只有 `{weekday, lesson, starts_at, ends_at}`；以发起人的真实日期和单节作息为基准，将所有参与者的课程和账号级日期日程换算到实际时间。不会返回个人日程名称、地点或逐人忙闲。不可覆盖的学期或未设置作息返回 409。结果仅作建议，发起和最终接受时会复核。
- 多人邀约最多 10 人（含发起人），遵循 `fixed_invite_enabled`。重复的同一发起人、参与者集合和时段的待处理邀约返回 409；任何受邀人婉拒即整体结束。部分接受时不写日程；最后一人接受时按参与者最新课表及日期日程复核，全部空闲才同一事务写入各自日程，冲突返回 409。任何参与者可取消已确认邀约并删除关联日程。邀约建立后参与者固定，后续退群或解散群组不会自动撤销已发出的邀请；邀请在开始时间或 3 天后（取较早者）到期。列表响应 `mode=fixed` 并带 `is_group=true` 及参与者状态。
- 群主不能直接退群（避免无主群）；可解散群组。当前版本没有邀请链接有效期、二维码、群内备注/显示名和成员上传文件，邀请码即入口；这些可作为后续迭代。

例如仅第 8 周周三第 5–6 节的个人日程：

```json
{"name":"社团拍摄","kind":"event","weekday":2,"lesson_start":5,"lesson_end":6,"weeks":[8],"location":"活动室","campus":null}
```

---

### 具体日期日程与一对一约饭

以下路径以 `/api/v1/schedule` 为前缀，均需登录。日期按北京时间；起止时间使用含偏移的 ISO 8601。旧的 `/compare` 仍使用节次，时间匹配只在服务端读取参与者自己选定的课表和账号下的日期日程。当前前端已移除“约饭与约定邀请”面板；多候选约饭接口保留，现有课表页只创建/接收固定时间约定，并在课表网格内处理邀请。

| 方法与相对路径 | 客户端函数 | 行为 |
|---|---|---|
| GET /calendar | getCalendar | 本人所有一次性日程，包括已确认约饭 |
| POST /calendar · PUT/DELETE /calendar/{id} | saveCalendarEntry / deleteCalendarEntry | 新增（201）、更新、删除私人日程；写入字段 title、可选 location、starts_at、ends_at。约饭产生的条目不能单方改写 |
| POST /appointments | createAppointment | 201；保存邀请，不查看受邀者课表。字段 invitee_username、title、location（选填）、schedule_id、window；作息从发起人选定课表读取 |
| POST /appointments/fixed | createFixedAppointment | 201；从对比页空闲时段直接约具体时间。字段 invitee_username、title、location、schedule_id、week、weekday、lesson_start、lesson_end；后端按发起人作息换算北京时间，创建待接受的固定时间邀请，不新增表 |
| GET /appointments · GET /appointments/{id} | getAppointments / getAppointment | 参与者自己的列表/详情，包括人名、状态、共同选择及自己的提醒；不返回别人的课程、私事、作息或教室。`mode="fixed"` 时另有 `fixed.starts_at/ends_at/week/weekday/lesson_start/lesson_end` |
| POST /appointments/{id}/response | respondAppointment | 接受发 `{accepted:true,schedule_id}`，自选私有或公开课表；作息从该课表读取；拒绝只需 `{accepted:false}` |
| POST /appointments/{id}/choices | chooseAppointmentTimes | candidate_ids 为当前 0–5 个 ID，可撤回自己的选择；变更选项会清除旧确认 |
| POST /appointments/{id}/confirm | confirmAppointment | candidate_id 必须是双方共同选择；只有双方最终确认同一 ID 才写两份日程。重复确认同一已订时段不重复写入 |
| POST /appointments/{id}/cancel | cancelAppointment | 任一参与者取消，已订日程同时从两人账号删除，不动其他安排。改期请取消后重新邀请 |
| GET /meal-notices · POST /appointments/{id}/read | getMealNotices / markMealRead | 查询本人有新消息的邀请数；仅标记本人这一条为已读 |

- 作息不再在约饭表单中重复填写：双方先在各自课表的“作息设置”二级窗格中填写学期第一周周一、课程开始时间、统一课时/间隔，并按需要逐节调整；约饭只传 `schedule_id`，后端读取该课表的 `timing`。现有 ICS 转节次的近似结果可在本人课表中校正。
- `window`：`date_from/date_to` 闭区间（最多 31 天，最晚一年内）；`daily_start/daily_end` 为每天可用范围；`duration_minutes` 为时段长度（15–1440；约饭表单 UI 仍限制 240，对比页固定约定按节次时长）；`buffer_minutes` 为前后各留路程（0–90）。可用时优先覆盖不同日期，靠近窗口中点的优先；最多 5 个，不用冲突时段凑数。候选只含 id、starts_at、ends_at。
- `POST /appointments/fixed`：`week`（1–53）、`weekday`（0–6）、`lesson_start/lesson_end`（1–24）按发起人课表 `timing` 换算为具体日期和北京时间；`date_from=date_to=当天`，`daily_start/daily_end` 为节次起止。创建后状态 `pending`，不立即写日程；受邀者接受时必须带自己的 `schedule_id`，后端重新检查双方占用和该时段，通过后在**同一事务**为双方写 `CalendarEvent` 并置 `confirmed`；冲突返回 409 `APPOINTMENT_STALE`，不会单方写入。同一发起人向同一受邀人重复发送相同 `fixed_start` 且已有 pending/confirmed 邀请时返回 409 `INVITATION_EXISTS`。取消已确认约定会删除双方由该邀请产生的日程。固定约定不经过候选/共同选择，`mode="fixed"`、`selected_candidate_id="fixed"`。
- `pending → choosing → confirming → confirmed`。未成约的邀请三天后过期；拒绝、取消均结束邀请。固定时间约定为 `pending → confirmed`（接受即写入）。最终确认锁住预约、参与账号和选定课表，并重新检查冲突。若碰撞则返回 409 `APPOINTMENT_STALE`，重新获取详情可见新候选。没有候选时可取消并扩大范围重约。
- 后端：`meal_times.busy_intervals/recommend/available` 负责教学周换算、排名和复核；`schedule_appointment.create_appointment/create_fixed_appointment/respond/choose/confirm/cancel` 管理流程；`my_events/edit_event` 管理一次性日程。已确认约饭/约定按 (appointment_id, owner_id) 唯一，与课程 JSON 分开保存。

## 七、公告 `/announcements`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/announcements/published` | 无 | 已发布公告列表（置顶优先，已过期自动过滤） |
| GET | `/announcements/admin` | 管理员 | 全部公告列表（含草稿/过期） |
| POST | `/announcements/admin` | 管理员 | 创建公告（标题/内容/置顶/立即发布/过期时间） |
| PATCH | `/announcements/admin/{id}` | 管理员 | 编辑公告（修改内容/置顶/发布/撤回） |
| DELETE | `/announcements/admin/{id}` | 管理员 | 删除公告 |

---

## 八、社团介绍 `/club`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/club/intro` | 无 | 获取社团介绍（标题+富文本内容） |
| PUT | `/club/intro` | 管理员 | 更新社团介绍 |

---

## 九、活动 `/events`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/events/` | Bearer | 活动列表（含报名状态/人数/候补数） |
| GET | `/events/{event_id}` | Bearer | 活动详情 |
| POST | `/events/{event_id}/register` | Bearer | 报名（满员自动候补，支持幂等键） |
| DELETE | `/events/{event_id}/register` | Bearer | 取消报名（自动递补候补） |
| POST | `/events/{event_id}/checkin` | Bearer | 签到（仅正式报名者） |

**报名规则**：活动须已发布 + 在报名窗口内；满员进候补名单；取消报名后自动递补候补最早的用户。

---

## 十、活动管理 `/admin/events`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/admin/events/` | 管理员 | 活动列表（含报名/候补统计） |
| POST | `/admin/events/` | 管理员 | 创建活动 |
| GET | `/admin/events/{id}` | 管理员 | 活动详情 + 全部报名记录 |
| PATCH | `/admin/events/{id}` | 管理员 | 编辑活动 |
| PATCH | `/admin/events/{id}/status` | 管理员 | 发布/下架/取消活动 |
| DELETE | `/admin/events/{id}` | 管理员 | 删除活动（含报名记录） |
| GET | `/admin/events/{id}/registrations` | 管理员 | 报名列表（含用户信息） |
| POST | `/admin/events/{id}/registrations/{rid}/checkin` | 管理员 | 代签到 |

---

## 十一、图片管理 `/admin/images`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/admin/images/stats` | 管理员 | 图片统计（总数/待审核/已通过/已拒绝） |
| GET | `/admin/images/processing-jobs` | 管理员 | 图片处理任务列表；支持状态筛选和分页，不返回私有图片内容 |
| POST | `/admin/images/processing-jobs/{id}/retry` | 管理员 | 重试失败任务，图片或对象已删除返回 404，任务非失败状态返回 409，操作写入审计 |
| GET | `/admin/images/reports` | 图片管理权限 | 图片举报列表，支持 `status=open/handled/dismissed`、`page`、`page_size`（上限 50） |
| GET | `/admin/images/reports/{id}/image` | 图片管理权限 | 读取举报对应图片的管理详情；图片不存在时返回 404 |
| PATCH | `/admin/images/reports/{id}` | 图片管理权限 | `{outcome: handled/dismissed/hide}`；`hide` 原子地将图片设为拒绝、非公开并处理举报；已处理返回 409 |
| GET | `/admin/images/` | 管理员 | 图片列表（支持 status/is_public 筛选 + 分页） |
| PATCH | `/admin/images/{id}/moderation` | 管理员 | 审核（pending → approved / rejected） |
| PATCH | `/admin/images/{id}/visibility` | 管理员 | 公开/私有开关 |
| PUT | `/admin/images/{id}/tags` | 管理员 | 编辑标签 |
| DELETE | `/admin/images/{id}` | 管理员 | 删除图片（含派生图清理） |

举报处理记录操作者及处理时间，举报状态和图片审核变化进入审计。对已删除图片可标记处理或驳回，不能选择下架。

`GET /admin/dashboard/overview` 需 `site_config.manage`，返回 `users`、`pending_users`、`images`、`registrations`、`open_reports`。报名数只计 `registered` 和 `checked_in`，不计候补和取消；待处理举报只计图片举报。

用户审批仅接受 `pending` 状态；待审批用户不能通过角色/状态接口绕过审批。普通管理员不能修改管理员、超级管理员或审核员的状态，授予或修改这些角色仅超级管理员可操作；不能修改自己的角色或状态，不能禁用超级管理员。

---

## 十二、动态页面 `/pages`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/pages/{slug}` | 无 | 获取已发布页面（Schema JSON，含时间窗口过滤） |
| GET | `/pages/admin/list` | 管理员 | 页面列表 |
| POST | `/pages/admin` | 管理员 | 创建页面（slug/标题/Schema JSON） |
| GET | `/pages/admin/{id}` | 管理员 | 页面详情 |
| PUT | `/pages/admin/{id}` | 管理员 | 编辑页面（自动记版本快照） |
| POST | `/pages/admin/{id}/publish` | 管理员 | 发布页面 |
| POST | `/pages/admin/{id}/unpublish` | 管理员 | 下线页面 |
| DELETE | `/pages/admin/{id}` | 管理员 | 删除页面（含版本记录） |
| GET | `/pages/admin/{id}/versions` | 管理员 | 版本历史列表 |
| POST | `/pages/admin/{id}/rollback/{vid}` | 管理员 | 回滚到指定版本 |

**Schema 渲染**：前端 `DynamicPage.vue` 按白名单组件渲染（hero / rich_text / image / countdown / button / notice / event_info / card / divider），未知组件忽略。

---

## 十三、站点配置 `/site`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/site/public-config` | 无 | 公开配置（网站名称/Logo/备案号/注册门控等，含 `registration_config` 与 `oauth_config`） |
| GET | `/site/footer` | 无 | 页脚配置（版权/链接/备案号） |
| GET | `/site/legal` | 无 | 法律信息（协议/隐私/版权/联系方式） |

法律页面前端路由：`/legal/terms`（用户协议）、`/legal/privacy`（隐私政策）、`/legal/copyright`（版权声明）、`/legal/contact`（联系我们）。隐私政策列出 EdgeOne、腾讯云 COS、QQ 互联、阿里云短信、飞书企业邮箱、Microsoft Bing、Google Fonts 的处理目的与官方隐私政策链接；用户协议包含第三方登录、违法违规信息处置和依法配合有权机关的条款。

`GET /site/public-config` 的 `registration_config` 结构：

```json
{
  "registration_enabled": true,
  "require_email_verification": true,
  "require_phone_verification": true
}
```

后台「网站设置 → 注册设置」保存同一组字段；前端 `useSiteConfig()` 和 `AppHeader/Login/Register` 依据此配置同步隐藏或显示注册、邮箱验证、手机验证区域。

`oauth_config` 结构：

```json
{
  "enabled": false,
  "qq_enabled": false
}
```

后台「网站设置 → 第三方登录」把同一组字段写入 `SiteSetting(key="oauth_config", is_public=true)`。前端仅在 `enabled=true && qq_enabled=true` 时展示 QQ 登录按钮；后端还会在 `/auth/oauth/*` 再次校验，不能仅靠隐藏按钮保护接口。

---

## 十四、网站设置管理 `/admin/settings`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/admin/settings/` | 管理员 | 设置列表（全部 SiteSetting 记录） |
| PUT | `/admin/settings/` | 管理员 | 保存设置（key/value_json/category/is_public） |
| POST | `/admin/settings/storage/test` | 管理员 | 测试对象存储连接 |
| POST | `/admin/settings/email/test` | 管理员 | 测试邮件 Provider |
| POST | `/admin/settings/sms/test` | 管理员 | 测试短信 Provider |
| POST | `/admin/settings/captcha/test` | 管理员 | 测试验证码 Provider |
| POST | `/admin/settings/oauth-provider/{provider}/test` | 管理员 | 检查 QQ Provider 是否已配置，返回 `configured` 与 `redirect_uri`（不回显 App Key） |

---

## 权限矩阵速查

| 操作 | 游客 | 成员 | 摄影师 | 管理员 |
|---|:---:|:---:|:---:|:---:|
| 查看公开图片/公告/活动 | ✓ | ✓ | ✓ | ✓ |
| 注册/登录/找回密码 | ✓ | ✓ | ✓ | ✓ |
| 上传公开图片 | — | — | ✓ | ✓ |
| 上传私有图片/课表 | — | ✓ | ✓ | ✓ |
| 读取/保存本人布局、设置本人图片展示授权 | — | ✓ | ✓ | ✓ |
| 绑定/解绑本人第三方登录 | — | ✓ | ✓ | ✓ |
| 报名活动/签到 | — | ✓ | ✓ | ✓ |
| 审批用户/管理内容/网站设置/第三方登录开关 | — | — | — | ✓ |

---

## 前端 API 封装对照

| 前端文件 | 对应后端模块 |
|---|---|
| `src/api/client.ts` | 通用请求封装（Bearer 注入、401 刷新、统一解包） |
| `src/api/token.ts` | Token 管理（access_token 仅内存；refresh_token 由后端 HttpOnly Cookie 承载） |
| `src/api/bootstrap.ts` | 共享登录态恢复，供首屏与受保护路由调用 |
| `src/api/oauth.ts` | QQ 登录/绑定、回调换会话、本人第三方绑定查询/解绑 |
| `src/api/profile.ts` | 个人主页布局、发布/丢弃、主题、素材、公开页与展示授权 API 封装；另含头像上传/删除 |
| `src/api/schedule.ts` | 课表、日程与约饭 API（见下文） |
| `src/api/site.ts` | 站点/公告 API（11 个接口） |
| `src/api/events.ts` | 活动 API（10 个接口） |
| `src/api/pages.ts` | 动态页面 API（9 个接口） |
| `src/api/adminImages.ts` | 图片管理 API（6 个接口） |

---

# 附录：全部函数与变量参考

> 交接时需要了解的所有导出函数、核心服务函数、关键变量和类型定义。

## 前端 `src/api/client.ts` — 通用请求封装

| 函数/变量 | 签名 | 说明 |
|---|---|---|
| `api` | `axios.AxiosInstance` | 默认导出的 Axios 实例（baseURL、超时 15s、Content-Type: JSON） |
| `request<T>(config)` | `async function(request: AxiosRequestConfig): Promise<T>` | 统一请求封装：注入 Bearer Token、自动解包 `{success, data, error}`、HTTP 异常提取后端错误消息 |
| `formatValidationDetail(detail)` | 内部函数，`unknown -> string \| null` | 将 FastAPI 422 `detail` 校验错误数组转换为中文字段提示；不是对外 API |
| `ensureAccessToken()` | `async function(): Promise<string \| null>` | 确保内存有有效 access token；页面刷新后用 refresh token 静默换取新 token，避免首个 401 |
| `setUnauthorizedHandler(fn)` | `function(fn: (() => void) \| null): void` | 注册 401 登出回调（由 auth store 注册，避免循环依赖） |

**内部流程**：请求拦截器注入 `Authorization: Bearer <token>` → 响应拦截器检测 401 → 自动调 `/auth/refresh` 换新 token → 重试一次 → 失败则 `clearTokens()` + 触发 `onUnauthorized`。

错误提取优先读取响应信封 `error.message`，再读取 `detail.message` 或字符串 `detail`；FastAPI 字段校验错误数组由 `formatValidationDetail()` 映射字段名与校验提示，供页面显示可读的 422 原因。

## 前端 `src/api/token.ts` — Token 管理

| 函数 | 签名 | 说明 |
|---|---|---|
| `getAccessToken()` | `(): string \| null` | 获取内存中的 access token |
| `setAccessToken(access)` | `(access: string): void` | 保存内存 access token，并写入 `localStorage.auth_session` 会话标记 |
| `hasSessionMarker()` | `(): boolean` | 是否存在本地会话标记（避免游客触发无意义的刷新请求） |
| `clearTokens()` | `(): void` | 清除内存 token 与本地会话标记（登出/刷新失败） |

浏览器 Cookie 由后端设置：`key=AUTH_COOKIE_NAME`（默认 `refresh_token`）、`HttpOnly`、`Path=/api/v1/auth`、有效期 `REFRESH_TOKEN_TTL_DAYS`（默认 7 天）、生产环境 `Secure`、`SameSite=AUTH_COOKIE_SAMESITE`（默认 `lax`）。前端保存的 `localStorage.auth_session` 只是“可能已登录”的标记，不包含访问令牌或刷新令牌。

## 前端 `src/api/bootstrap.ts` — 登录态恢复

| 函数 | 签名 | 说明 |
|---|---|---|
| `bootstrapAuth()` | `(): Promise<void>` | 同一次页面生命周期仅初始化一次，并发调用共享 Promise；存在 Refresh Token 时先 ensureAccessToken 再 fetchMe，失败保持未登录。App 首屏与 requiresAuth 守卫共用 |

## 前端 `src/api/oauth.ts` — QQ 登录与绑定

| 函数 | 签名 | 对应接口 |
|---|---|---|
| `getOauthProviders()` | `(): Promise<{providers, frontend_base_url}>` | `GET /auth/oauth/providers` |
| `startQqLogin(verificationToken, returnTo?)` | `(string, string?) => Promise<{authorize_url}>` | `POST /auth/oauth/qq/start` |
| `startQqBind(verificationToken, returnTo?)` | `(string, string?) => Promise<{authorize_url}>` | `POST /auth/oauth/qq/bind-start` |
| `exchangeQqCallback(code, state)` | `(string, string) => Promise<OauthResolveResult>` | `GET /auth/oauth/qq/callback` |
| `bindQqWithAccount(oauthToken, account, password, verificationToken)` | `(string, string, string, string) => Promise<OauthResolveResult>` | `POST /auth/oauth/qq/bind` |
| `getMyThirdPartyBindings()` | `(): Promise<{items: ThirdPartyBinding[]}>` | `GET /profile/me/third-party` |
| `deleteMyThirdPartyBinding(provider)` | `(string) => Promise<{message}>` | `DELETE /profile/me/third-party/{provider}` |

## 前端 `src/api/profile.ts` — 个人主页 API

| 函数 | 参数 / 返回 | 对应接口及状态 |
|---|---|---|
| `getMyLayout()` | `Promise<ProfileLayoutResponse>` | GET /profile/me/layout，已实现 |
| `saveMyLayout(payload)` | `{blocks: ProfileBlock[], is_public?: boolean}` → `Promise<ProfileLayoutResponse>` | PUT /profile/me/layout，已实现 |
| `setProfileImageDisplayable(id, is_displayable)` | `(string, boolean)` → `Promise<{id, is_displayable}>` | PATCH /profile/me/images/{id}，已实现 |
| `getProfilePage(username)` | string → `Promise<ProfilePageResponse>` | GET /profile/{username}/page，已实现（匿名公开） |
| `publishMyLayout()` | `Promise<{published_at}>` | POST /profile/me/layout/publish，已实现 |
| `discardMyDraft()` | `Promise<ProfileLayoutResponse>` | POST /profile/me/layout/discard，已实现 |
| `saveMyTheme(theme)` | ProfileTheme → `Promise<{theme: ProfileTheme}>` | PUT /profile/me/theme，已实现（响应为完整布局，前端读取 theme） |
| `getMyMedia()` | `Promise<{items: ProfileMediaOption[]}>` | GET /profile/me/media，已实现 |

## 前端主页编辑器与渲染辅助函数

| 文件 / 导出 | 说明 |
|---|---|
| `stores/profileLayout.ts`：`useProfileLayoutStore()` | 保存 blocks/theme/media/stats、已发布版本、上限、dirty/hasUnpublished/canUndo/canRedo 及加载/保存状态 |
| store：`load()` / `loadMediaOptions()` | 读取本人布局、可选素材；素材清单失败时显示空列表 |
| store：`addBlock(type)` / `removeBlock(id)` / `duplicateBlock(id)` | 新增/删除/复制模块；新增和复制受 maxBlocks 限制 |
| store：`moveBlock(from, to)` / `setSpan(id, span)` / `updateProps(id, patch)` | 修改排序、宽度和属性 |
| store：`applyThemePreset(id)` / `undo()` / `redo()` | 应用主题预设，撤销/重做模块及主题编辑 |
| store：`saveDraft()` / `publish()` / `discard()` | 草稿、主题、发布与丢弃均走真实后端接口 |
| `components/profile/blocks/registry.ts`：`isBlockType(value)` / `normalizeSpan(type, span)` | 校验模块类型、规范化宽度；共享 BLOCK_COMPONENTS / ALLOWED_SPANS / SPAN_CLASS 白名单 |
| registry：`newBlockId()` / `defaultProps(type)` / `newBlock(type)` | 生成客户端块 id、默认 props 和新模块 |
| `components/profile/blocks/types.ts`：`str()` / `num()` / `strList()` | 按类型读取模块属性并提供回退值；另导出 BlockProps 与 STAT_LABELS |
| `components/profile/theme.ts`：`tint()` / `themeVars()` / `backgroundStyle()` / `cardSurface()` | 主题颜色混合、CSS 变量、背景与卡片表面；另导出 DEFAULT_THEME / THEME_PRESETS |
| `dev/profileMock.ts`：`profileMock()` | Vite 开发插件，显式开关启用后提供内存态演示契约；不构成真实后端实现 |

## 前端 `src/api/schedule.ts` — 课表 API

| 函数 | 签名 | 对应接口 |
|---|---|---|
| `getMySchedules()` | `(): Promise<{items: ScheduleRecord[]}>` | `GET /schedule/mine` |
| `createScheduleUploadIntent(filename, sizeBytes)` | `(filename: string, sizeBytes: number): Promise<ScheduleUploadIntent>` | `POST /schedule/upload-intent` |
| `completeScheduleUpload(intent, originalName)` | `(intent: ScheduleUploadIntent, originalName: string): Promise<ScheduleRecord>` | `POST /schedule/upload-complete` |
| `getSharedSchedule(username)` | `(username: string): Promise<ScheduleRecord>` | `GET /schedule/shared/{username}` |
| `compareSchedules(slotsA, slotsB, week?)` | `week: number \| null = null`，返回 `Promise<ScheduleCompareResult>` | `POST /schedule/compare` |
| `createManualSchedule(name, slots?, timing?)` | `(name: string, slots?: ScheduleSlot[], timing?: ScheduleTiming): Promise<ScheduleRecord>` | `POST /schedule/manual` |
| `previewSchedulePdf(file)` | `(file: File): Promise<{ suggested_name: string; slots: ScheduleSlot[]; warnings: string[] }>` | `POST /schedule/pdf-preview` |
| `createFixedAppointment(data)` | `(data: FixedMeetupInvite): Promise<AppointmentDetail>`；`FixedMeetupInvite` 含 schedule_id、invitee_username、title、location?、week、weekday、lesson_start、lesson_end | `POST /schedule/appointments/fixed` |
| `getScheduleGroups()` | `(): Promise<{items: ScheduleGroupSummary[]}>` | `GET /schedule/groups` |
| `createScheduleGroup(name, joinMode?)` | `(name: string, joinMode?: 'open' \| 'approval'): Promise<ScheduleGroupSummary>` | `POST /schedule/groups` |
| `joinScheduleGroup(code)` | `(code: string): Promise<ScheduleGroupSummary>` | `POST /schedule/groups/join` |
| `getScheduleGroup(groupId, week?)` | `(groupId: string, week?: number \| null): Promise<ScheduleGroupDetail>` | `GET /schedule/groups/{id}` |
| `updateScheduleGroup(groupId, data)` | `(groupId: string, data: {name?: string; join_mode?: 'open' \| 'approval'}): Promise<ScheduleGroupSummary>` | `PATCH /schedule/groups/{id}` |
| `deleteScheduleGroup(groupId)` | `(groupId: string): Promise<{message: string}>` | `DELETE /schedule/groups/{id}` |
| `setScheduleGroupSchedule(groupId, scheduleId)` | `(groupId: string, scheduleId: string \| null): Promise<ScheduleGroupSummary>` | `PUT /schedule/groups/{id}/schedule` |
| `approveScheduleGroupMember(groupId, userId)` | `(groupId: string, userId: string): Promise<ScheduleGroupSummary>` | `POST /schedule/groups/{id}/members/{uid}/approve` |
| `rejectScheduleGroupMember(groupId, userId)` | `(groupId: string, userId: string): Promise<{message: string}>` | `POST /schedule/groups/{id}/members/{uid}/reject` |
| `removeScheduleGroupMember(groupId, userId)` | `(groupId: string, userId: string): Promise<{message: string}>` | `DELETE /schedule/groups/{id}/members/{uid}` |
| `saveScheduleSlots(scheduleId, slots, revision)` | `(string, ScheduleSlot[], number): Promise<ScheduleRecord>` | `PUT /schedule/{id}/slots` |
| `saveScheduleTiming(scheduleId, timing, revision)` | `(string, ScheduleTiming, number): Promise<ScheduleRecord>` | `PUT /schedule/{id}/timing` |
| `setScheduleVisibility(scheduleId, isPublic)` | `(scheduleId: string, isPublic: boolean): Promise<ScheduleRecord>` | `PATCH /schedule/{id}/visibility` |
| `updateScheduleMeta(scheduleId, data)` | `(scheduleId: string, data: { original_name?: string; is_archived?: boolean }): Promise<ScheduleRecord>` | `PATCH /schedule/{id}` |
| `saveScheduleOrder(ids)` | `(ids: string[]): Promise<{ items: ScheduleRecord[] }>` | `PUT /schedule/order` |
| `deleteSchedule(scheduleId)` | `(scheduleId: string): Promise<{message: string}>` | `DELETE /schedule/{id}` |

课表编辑组件辅助函数位于 `components/schedule/calendar.ts`：`defaultScheduleTiming(count)` 生成指定数量的作息（默认 12 节）；`normalizeScheduleTiming(value)` 补齐旧课表缺失字段；`defaultScheduleSegments()` / `normalizeScheduleSegments(value)` 生成或规范化时段边界；`periodSegment(timing, index)` / `periodSegmentLabel(segment)` 按 `segments` 和每节开始时间标记上午、中午、下午或晚上；`scheduleWeeks(slots)` 生成可浏览的连续周次；`parseWeekSelection(text)` 校验并解析 `1-16` / `1,3,5`；`formatWeeks(weeks)` 将周数组压缩为范围文本。它们只用于表单与显示，不承担服务端忙闲计算。

## 前端 `src/api/site.ts` — 站点/公告/设置 API

| 函数 | 签名 | 对应接口 |
|---|---|---|
| `getPublicConfig()` | `(): Promise<PublicConfig>` | `GET /site/public-config` |
| `getFooter()` | `(): Promise<FooterConfig>` | `GET /site/footer` |
| `getLegal()` | `(): Promise<LegalConfig>` | `GET /site/legal` |
| `getClubIntro()` | `(): Promise<ClubIntro>` | `GET /club/intro` |
| `getPublishedAnnouncements()` | `(): Promise<{items: AnnouncementRecord[]}>` | `GET /announcements/published` |
| `getAllAnnouncements()` | `(): Promise<{items: AnnouncementRecord[]}>` | `GET /announcements/admin` |
| `createAnnouncement(data)` | `(data: {title, content, is_pinned?, publish_now?, expires_at?}): Promise<AnnouncementRecord>` | `POST /announcements/admin` |
| `updateAnnouncement(id, data)` | `(id: string, data: {...}): Promise<AnnouncementRecord>` | `PATCH /announcements/admin/{id}` |
| `deleteAnnouncement(id)` | `(id: string): Promise<{message}>` | `DELETE /announcements/admin/{id}` |
| `getAdminSettings()` | `(): Promise<{items: SiteSettingRecord[]}>` | `GET /admin/settings/` |
| `upsertSetting(data)` | `(data: {key, value, category?, is_public?}): Promise<SiteSettingRecord>` | `PUT /admin/settings/` |
| `updateClubIntro(data)` | `(data: ClubIntro): Promise<SiteSettingRecord>` | `PUT /club/intro` |

## 前端 `src/api/events.ts` — 活动 API

| 函数 | 签名 | 对应接口 |
|---|---|---|
| `listEvents()` | `(): Promise<{items: EventRecord[]}>` | `GET /events/` |
| `getEvent(eventId)` | `(eventId: string): Promise<EventRecord>` | `GET /events/{id}` |
| `registerEvent(eventId, idempotencyKey?)` | `(eventId: string, key?: string): Promise<EventRegistration>` | `POST /events/{id}/register` |
| `cancelEventRegistration(eventId)` | `(eventId: string): Promise<{message}>` | `DELETE /events/{id}/register` |
| `eventCheckin(eventId)` | `(eventId: string): Promise<EventRegistration>` | `POST /events/{id}/checkin` |
| `adminListEvents()` | `(): Promise<{items: EventRecord[]}>` | `GET /admin/events/` |
| `adminCreateEvent(data)` | `(data: {title, starts_at, ends_at, ...}): Promise<EventRecord>` | `POST /admin/events/` |
| `adminGetEventDetail(eventId)` | `(eventId: string): Promise<{event, items, registered_count, waitlist_count}>` | `GET /admin/events/{id}` |
| `adminUpdateEvent(eventId, data)` | `(eventId: string, data: {...}): Promise<EventRecord>` | `PATCH /admin/events/{id}` |
| `adminSetEventStatus(eventId, status)` | `(eventId: string, status: string): Promise<EventRecord>` | `PATCH /admin/events/{id}/status` |
| `adminDeleteEvent(eventId)` | `(eventId: string): Promise<{message}>` | `DELETE /admin/events/{id}` |
| `adminListRegistrations(eventId)` | `(eventId: string): Promise<{event, items, ...}>` | `GET /admin/events/{id}/registrations` |
| `adminCheckin(eventId, registrationId)` | `(eventId: string, regId: string): Promise<EventRegistration>` | `POST /admin/events/{id}/registrations/{rid}/checkin` |

## 前端 `src/api/pages.ts` — 动态页面 API

| 函数 | 签名 | 对应接口 |
|---|---|---|
| `getPublishedPage(slug)` | `(slug: string): Promise<PageRecord>` | `GET /pages/{slug}` |
| `adminListPages()` | `(): Promise<{items: PageRecord[]}>` | `GET /pages/admin/list` |
| `adminCreatePage(data)` | `(data: {slug, title, page_schema, ...}): Promise<PageRecord>` | `POST /pages/admin` |
| `adminGetPage(pageId)` | `(pageId: string): Promise<PageRecord>` | `GET /pages/admin/{id}` |
| `adminUpdatePage(pageId, data)` | `(pageId: string, data: {...}): Promise<PageRecord>` | `PUT /pages/admin/{id}` |
| `adminPublishPage(pageId)` | `(pageId: string): Promise<PageRecord>` | `POST /pages/admin/{id}/publish` |
| `adminUnpublishPage(pageId)` | `(pageId: string): Promise<PageRecord>` | `POST /pages/admin/{id}/unpublish` |
| `adminDeletePage(pageId)` | `(pageId: string): Promise<{message}>` | `DELETE /pages/admin/{id}` |
| `adminListVersions(pageId)` | `(pageId: string): Promise<{items: PageVersion[]}>` | `GET /pages/admin/{id}/versions` |
| `adminRollbackPage(pageId, versionId)` | `(pageId: string, vid: string): Promise<PageRecord>` | `POST /pages/admin/{id}/rollback/{vid}` |

## 前端 `src/api/adminImages.ts` — 图片管理 API

| 函数 | 签名 | 对应接口 |
|---|---|---|
| `adminGetImageStats()` | `(): Promise<AdminImageStats>` | `GET /admin/images/stats` |
| `adminListImages(params)` | `(params: {page?, page_size?, status?, is_public?}): Promise<{items: GalleryImage[], pagination}>` | `GET /admin/images/` |
| `adminSetImageModeration(id, status)` | `(id: string, status: string): Promise<GalleryImage>` | `PATCH /admin/images/{id}/moderation` |
| `adminSetImageVisibility(id, isPublic)` | `(id: string, isPublic: boolean): Promise<GalleryImage>` | `PATCH /admin/images/{id}/visibility` |
| `adminSetImageTags(id, tags)` | `(id: string, tags: string[]): Promise<GalleryImage>` | `PUT /admin/images/{id}/tags` |
| `adminDeleteImage(id)` | `(id: string): Promise<{message}>` | `DELETE /admin/images/{id}` |

---

## 后端核心服务函数

### `services/auth.py` — 认证服务

| 函数 | 说明 |
|---|---|
| `create_access_token(user_id, role) -> str` | 生成短时效 JWT Access Token |
| `decode_access_token(token) -> dict` | 解码并验证 JWT |
| `register_user(db, ...) -> User` | 注册用户（创建 pending 状态，含摄影师申请；写入协议版本与 `legal_accepted_at`） |
| `login(db, account, password) -> dict` | 登录（校验密码 → 生成 token 对 → 记录会话） |
| `refresh_tokens(db, refresh_token) -> dict` | 刷新令牌轮换；检测旧令牌重放并撤销整个会话族 |
| `revoke_session(db, refresh_token)` | 撤销单个会话（登出） |
| `revoke_all_sessions(db, user_id)` | 撤销全部会话（登出所有设备） |
| `approve_user(db, user_id) -> User` | 审批通过（激活账号） |
| `reject_user(db, user_id) -> User` | 拒绝注册 |
| `_send_email_notification(to, subject, template, username)` | 注册/审批邮件通知（fire-and-forget，发送失败仅记录日志） |

### `services/third_party_auth.py` — QQ OAuth 与绑定

| 函数 / 常量 | 说明 |
|---|---|
| `OAUTH_STATE_TTL_SECONDS` / `OAUTH_PENDING_TTL_SECONDS` | OAuth state 与未绑定临时凭证的 Redis TTL，均为 600 秒 |
| `SUPPORTED_PROVIDERS` | 当前支持的第三方 Provider 集合，仅 `{"qq"}` |
| `build_authorize_url(provider, mode, user, return_to)` | 生成 QQ 授权地址并把登录/绑定上下文写入 Redis |
| `exchange_and_resolve(db, provider, code, state)` | 消费 state、换取 QQ 身份；已绑定发登录态，未绑定返回短时 `oauth_token` |
| `bind_with_credentials(db, oauth_token, account, password)` | 未绑定 QQ 通过本站账号密码完成绑定并签发会话 |
| `list_bindings(db, user)` | 返回本人第三方绑定列表 |
| `unbind_provider(db, user, provider)` | 删除本人指定 Provider 的全部绑定 |
| `is_oauth_public_enabled(db, provider)` | 读取后台总开关与对应 Provider 子开关 |

Redis Key：`oauth:state:{token}`、`oauth:pending:{token}`，读取后立即删除，避免重放。`UserThirdParty` 保存 `provider`、`provider_user_id`、`unionid`、QQ 令牌及原始资料；数据库只记录绑定关系。

### `providers/qq.py` — QQ 互联 Provider

| 方法 / 属性 | 说明 |
|---|---|
| `configured` | 是否配置 `QQ_APP_ID` 与 `QQ_APP_KEY` |
| `build_authorize_url(state)` | 生成 `graph.qq.com/oauth2.0/authorize` 地址，scope 为 `get_user_info` |
| `exchange_code(code)` | 换取 Access Token、OpenID / UnionID、昵称和头像；失败抛 `QqOAuthError` |

QQ 接口入口：`https://graph.qq.com/oauth2.0/authorize`、`/token`、`/me`、`/user/get_user_info`。前端固定回调 `/oauth/qq`，生产完整地址为 `https://www.furzl.cn/oauth/qq`。

### `services/image.py` — 公开图片服务

| 函数 | 说明 |
|---|---|
| `sanitize_filename(filename) -> str` | 格式化文件名（清理危险字符 + base64 编码） |
| `create_upload_intent(...) -> dict` | 签发上传凭证（随机 Object Key + 预签名 URL） |
| `complete_upload(db, ...) -> Image` | 上传完成（HEAD 复核 + 落库 StoredObject/Image） |
| `list_public_images(db, page, page_size) -> dict` | 公开图片列表（分页，approved + is_public） |
| `_image_to_dict(db, image) -> dict` | Image → API 响应 dict（含 url/display_url/thumb_url） |

### `services/profile_image.py` — 私有相册服务

| 函数 | 说明 |
|---|---|
| `create_profile_upload_intent(...) -> dict` | 私有图片上传凭证 |
| `complete_profile_upload(db, ...) -> ProfileImage` | 私有图上传完成（含缩略图 worker 入队） |
| `list_my_profile_images(db, user) -> dict` | 私有相册列表（缩略图使用后端短期票据 URL） |
| `get_profile_image_signed_url(db, *, user, image_id) -> dict` | 校验本人后返回带短期票据的后端原图 URL |
| `delete_profile_image(db, *, user, image_id)` | 删除私有图片 |

### `services/profile_layout.py` — 布局草稿与展示授权

| 函数 / 常量 | 说明 |
|---|---|
| `validate_blocks(raw) -> list[dict[str, Any]]` | 校验模块数组、数量、唯一 id、类型、span、props；按白名单重新序列化，丢弃未知字段 |
| `get_layout_payload(db, user) -> dict[str, Any]` | 组装主题/草稿/已发布块/公开开关/上限/已授权素材/兼容 TTL/统计；GET 与 PUT 共用 |
| `put_layout(db, user, body) -> dict[str, Any]` | 校验大小、结构、素材本人归属和展示权限；创建或替换草稿及可选 is_public，提交后返回同形布局 |
| `set_image_displayable(db, user, image_id, is_displayable) -> dict[str, Any]` | 仅更新本人私有图展示标记；非法目标返回 404 |
| `ProfileLayoutError(code, message, status_code=422)` | 业务错误，经 error_to_http 转为 HTTPException detail 响应 |
| `DEFAULT_THEME` / `ALLOWED_SPANS` | 默认主题与按模块类型划分的允许宽度 |
| `MAX_LAYOUT_BYTES` / `MAX_HTML_LENGTH` | 布局重新编码后最多 256 KiB；HTML 字符数最多 24576 |

`schemas/profile_layout.py` 的 `ProfileImageDisplayPatch` 使用 `StrictBool`，配置 `extra="forbid", strict=True`。发布、丢弃草稿、主题和公开主页服务已实现，详见前文「个人主页发布与公开读取」。

### `services/image_processing.py` — 图片处理

| 函数 | 说明 |
|---|---|
| `derive_display_key(object_key) -> str` | 推导展示图 Object Key（内嵌尺寸参数） |
| `derive_thumb_key(object_key) -> str` | 推导缩略图 Object Key |
| `derive_profile_thumb_key(object_key) -> str` | 推导私有图缩略图 Key |
| `process_image(db, image_id)` | 后台处理：下载 → 解码校验 → 生成 WebP 派生图 → 上传 |
| `process_profile_image(db, image_id)` | 私有图处理：生成缩略图，更新尺寸 |

### `services/schedule.py` — 课表解析与对比

| 函数/类 | 说明 |
|---|---|
| `CourseSlot`（dataclass） | 统一课程数据结构（name/location/weekday/lesson_start/lesson_end/weeks/campus） |
| `parse_weeks(text) -> list[int]` | 解析周次（`1-16周` 连续 / `1,3,5周` 指定） |
| `parse_zjut_cell(cell, weekday) -> list[CourseSlot]` | 解析 ZJUT 课表单元格 |
| `compare(slots_a, slots_b, week=None) -> dict` | 后端按周对比课程+日程 → `{same_classroom, both_free, overlaps, week}` |
| `parse_schedule(data, filename) -> dict` | 按文件名识别格式解析（ICS/TXT）；PDF 请使用 `schedule_pdf.py` 的预览导入，不经上传接口保存 |
| `parse_ics(data) -> list[CourseSlot]` | ICS 课表解析（VEVENT → CourseSlot） |
| `parse_txt(data) -> list[CourseSlot]` | ZJUT TXT 课表解析 |
| `ScheduleParseError` | 解析异常（code + message） |

### `services/schedule_pdf.py` — PDF 课表解析（2026-11-24）

| 函数/类 | 说明 |
|---|---|
| `parse_pdf_schedule(data) -> PdfParseResult` | 解析教务文字层 PDF 表格；支持同格多课、合并节次、跨页课程名拼接；返回课程、警告与建议名称 |
| `PdfParseResult` | `slots`、`warnings`、`suggested_name` |
| `PdfParseError` | `code` + `message`（如 `PDF_NO_TEXT` 扫描件、`PDF_LAYOUT_UNSUPPORTED`、`PDF_NO_COURSE`） |

### `services/schedule_service.py` — 课表业务服务

| 函数 | 说明 |
|---|---|
| `create_schedule_upload_intent(...) -> dict` | 课表上传凭证 |
| `complete_schedule_upload(db, ...) -> Schedule` | 上传完成（下载文件 + 解析 + 落库） |
| `get_my_schedules(db, user) -> dict` | 我的课表列表 |
| `create_manual_schedule(db, user, body) -> dict` | 创建私有手工课表 |
| `update_schedule_slots(db, schedule_id, user, body) -> dict` | 本人编辑、行锁/版本校验和 JSONB 保存 |
| `_schedule_to_dict(s, include_event_details=True) -> dict` | 序列化及历史字段默认值；公开读调用传 false 脱敏个人日程 |
| `get_schedule(db, schedule_id, user) -> dict` | 课表详情（私有仅本人，公开任何人） |
| `get_public_schedule_by_username(db, username) -> dict` | 按用户名获取公开课表（含公开用户信息） |
| `set_schedule_visibility(db, schedule_id, is_public, user) -> dict` | 公开/私有开关 |
| `delete_schedule(db, schedule_id, user)` | 删除课表（含对象存储清理） |

### `services/event.py` — 活动服务

| 函数 | 说明 |
|---|---|
| `list_events(db, user) -> dict` | 活动列表（含报名状态/人数/候补数） |
| `admin_list_events(db) -> dict` | 管理端活动列表（批量统计，无 N+1） |
| `_batch_counts(db, event_ids) -> dict` | 批量查询活动报名/候补统计（1 次 GROUP BY 查询） |
| `get_event(db, event_id, user) -> dict` | 活动详情 |
| `register(db, event_id, user, idempotency_key) -> dict` | 报名（容量检查、满员候补、幂等键） |
| `cancel_registration(db, event_id, user) -> dict` | 取消报名（自动递补候补） |
| `checkin(db, event_id, user) -> dict` | 签到（仅正式报名者，不可重复） |
| `create_event(db, ...) -> dict` | 创建活动 |
| `update_event(db, event_id, **kwargs) -> dict` | 编辑活动 |
| `set_event_status(db, event_id, status) -> dict` | 发布/下架/取消 |
| `delete_event(db, event_id)` | 删除活动（含报名记录） |
| `list_registrations(db, event_id) -> dict` | 报名列表（含用户信息） |
| `admin_checkin(db, event_id, registration_id) -> dict` | 管理员代签到 |

### `services/announcement.py` — 公告服务

| 函数 | 说明 |
|---|---|
| `list_published(db) -> dict` | 已发布公告列表（置顶优先，过滤过期） |
| `list_all(db) -> dict` | 全部公告列表（管理用） |
| `create(db, ...) -> dict` | 创建公告 |
| `update(db, id, ...) -> dict` | 编辑公告（修改内容/置顶/发布状态） |
| `delete(db, id)` | 删除公告 |

### `services/page.py` — 动态页面服务

| 函数 | 说明 |
|---|---|
| `get_published_page(db, slug) -> dict` | 获取已发布页面（含时间窗口检查） |
| `list_pages(db) -> dict` | 页面列表 |
| `create_page(db, ...) -> dict` | 创建页面（含首次版本快照） |
| `update_page(db, page_id, ...) -> dict` | 编辑页面（自动记版本快照） |
| `publish_page(db, page_id, user) -> dict` | 发布 |
| `unpublish_page(db, page_id, user) -> dict` | 下线 |
| `delete_page(db, page_id)` | 删除（含版本记录清理） |
| `list_versions(db, page_id) -> dict` | 版本历史 |
| `rollback_page(db, page_id, version_id, user) -> dict` | 回滚到指定版本 |

### `services/site_setting.py` — 网站设置服务

| 函数 | 说明 |
|---|---|
| `get_setting(db, key) -> dict \| None` | 读取任意设置 |
| `get_public_setting(db, key) -> dict \| None` | 读取公开设置（is_public=True） |
| `upsert_setting(db, ...) -> dict` | 新增/更新设置 |
| `list_settings(db) -> list[dict]` | 列出全部设置 |
| `get_public_config(db) -> dict` | 公开配置聚合（含默认值） |
| `get_footer_config(db) -> dict` | 页脚配置聚合 |
| `get_legal_config(db) -> dict` | 法律信息聚合 |
| `get_club_intro(db) -> dict` | 社团介绍聚合 |
| `get_registration_config(db) -> dict` | 注册门控聚合（开启注册/邮箱验证/手机验证，含默认值） |
| `get_oauth_config(db) -> dict` | 第三方登录聚合（`enabled` 总开关 / `qq_enabled` 子开关，含默认值） |

### `services/admin_image.py` — 图片管理服务

| 函数 | 说明 |
|---|---|
| `list_all_images(db, ...) -> dict` | 图片列表（筛选/分页） |
| `set_moderation(db, image_id, status) -> dict` | 审核（approved 自动设公开，rejected 设私有） |
| `set_visibility(db, image_id, is_public) -> dict` | 公开/私有开关 |
| `update_tags(db, image_id, tags) -> dict` | 编辑标签 |
| `delete_image(db, image_id)` | 删除图片（含派生图清理） |
| `get_stats(db) -> dict` | 图片统计 |

### `services/otp.py` — OTP 验证码服务

| 函数 | 说明 |
|---|---|
| `send_otp(db, target, purpose, channel) -> dict` | 发送验证码（哈希存储、用途隔离、120 秒冷却、频率限制） |
| `verify_otp(db, target, purpose, code) -> bool` | 校验验证码（单次使用、尝试次数限制） |

---

## 核心基础设施

### `api/deps.py` — 依赖注入

| 函数 | 说明 |
|---|---|
| `get_current_user(request, credentials, db) -> User` | 从 Bearer Token 解析用户（查库校验 status/is_active） |
| `require_role(*roles)` | 角色校验依赖工厂 |
| `require_permission_dep(permission)` | 权限校验依赖工厂（RBAC） |

### `api/response.py` — 统一响应

| 函数 | 说明 |
|---|---|
| `ok(data, request) -> dict` | 成功响应 `{success: true, data, error: null, request_id}` |
| `err(code, message, request) -> dict` | 失败响应 `{success: false, data: null, error: {code, message}, request_id}` |
| `parse_uuid(value, field) -> uuid.UUID` | 统一 UUID 解析，失败抛 400 HTTPException |
| `error_to_http(exc) -> HTTPException` | ServiceError（ImageError/EventError/PageError 等）→ HTTPException 转换 |

### `core/security.py` — 安全工具

| 函数 | 说明 |
|---|---|
| `hash_password(password) -> str` | 密码哈希（Argon2id / bcrypt） |
| `verify_password(password, hashed) -> bool` | 密码校验 |
| `generate_token(nbytes=32) -> str` | 生成 URL 安全随机令牌（Refresh Token） |
| `hash_token(token) -> str` | 令牌哈希（只存哈希防泄露） |
| `hash_code(code) -> str` | 验证码哈希（HMAC-SHA256） |
| `constant_time_equal(a, b) -> bool` | 恒定时间比较（防时序攻击） |

### `core/permissions.py` — RBAC 权限

| 函数/变量 | 说明 |
|---|---|
| `Role`（StrEnum） | GUEST / MEMBER / PHOTOGRAPHER / MODERATOR / ADMIN / SUPER_ADMIN |
| `PERMISSIONS`（dict） | 权限点 → 角色集合映射（14 个权限点） |
| `role_level(role) -> int` | 角色等级（0-5） |
| `has_permission(role, permission) -> bool` | 判断权限（含角色继承） |
| `require_permission(role, permission)` | 校验权限（不通过抛 PermissionError） |

---

## TypeScript 类型定义（`src/types/index.ts`）

| 类型 | 说明 |
|---|---|
| `ApiResponse<T>` | 通用 API 响应 `{success, data, error, request_id}` |
| `Page<T>` | 分页响应 `{items, pagination}` |
| `Role` | 角色联合类型 |
| `User` | 前端用户对象（id/username/displayName/role/avatar/bio） |
| `MeResponse` | `/auth/me` 响应（snake_case，含 bio/avatar_url） |
| `AdminUser` | 管理端用户 |
| `GalleryImage` | 图片（url/display_url/thumb_url/描述/标签/状态） |
| `UploadIntent` | 上传凭证（upload_url/object_key/expires_in） |
| `ProfileImage` | 私有相册图片 |
| `CourseSlot` | 前端课表课程（camelCase） |
| `ScheduleSlot` | 后端课表课程（snake_case） |
| `ScheduleRecord` | 课表记录 |
| `ScheduleUploadIntent` | 课表上传凭证 |
| `ScheduleCompareResult` | 课表对比结果 |
| `CompareFreeSlot` | 对比结果空闲时段 |
| `CompareConflict` | 对比结果冲突记录 |
| `PublicConfig` | 站点公开配置 |
| `RegistrationConfig` | 注册门控配置（registration_enabled / require_email_verification / require_phone_verification） |
| `FooterConfig` | 页脚配置 |
| `FooterLink` | 页脚链接 |
| `LegalConfig` | 法律信息 |
| `ClubIntro` | 社团介绍 |
| `AnnouncementRecord` | 公告 |
| `MemberProfile` | 公开成员信息 |
| `SiteSettingRecord` | 网站设置 |
| `EventRecord` | 活动（含报名统计/我的状态） |
| `EventRegistration` | 活动报名记录 |
| `PageRecord` | 动态页面 |
| `PageVersion` | 页面版本快照 |
| `PageBlock` / `PageSchema` | 动态页面 Schema 组件 |
| `AdminImageStats` | 图片管理统计 |
| `ProfileBlockType` / `ProfileSpan` | 8 种主页模块，栅格宽度联合类型（具体允许值按模块白名单限制） |
| `ProfileBlock` / `ProfileLinkItem` | 模块 id/type/span/props、链接 label/url |
| `ProfileStatsKey` / `ProfileStats` | joined_days / gallery_image_count 及统计值 |
| `ProfileMedia` / `ProfileMediaOption` | 已解析代理域 URL 的素材、带归属标识与展示授权的可选图片 |
| `ProfileBackgroundType` / `ProfileCardStyle` / `ProfileTheme` | 背景/卡片类型及主题颜色、图片背景、模糊等字段 |
| `ProfilePageUser` / `ProfilePageResponse` | 匿名公开主页响应契约（已在真实后端实现） |
| `ProfileLayoutResponse` | 已实现 GET/PUT 布局的同形响应（theme/draft_blocks/published_blocks/is_public/max_blocks/media/media_expires_in/stats） |
| `OauthConfig` / `OauthProviderInfo` | 第三方登录公开开关与 Provider 列表项 |
| `OauthProvidedUser` / `OauthResolveResult` | OAuth 回调返回的本站用户、绑定状态、临时 `oauth_token` 与会话字段 |
| `ThirdPartyBinding` | 本人第三方绑定记录（provider / provider_user_id / created_at） |
