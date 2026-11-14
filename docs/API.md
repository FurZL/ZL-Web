# Furry ZJUT API 文档

> 本分支 OpenAPI 已注册 **79 个 API 路径（94 个方法端点）**，供团队交接和查阅；个人主页待实现接口另列，不计入上述数量。
> 统一前缀：`/api/v1`，统一响应格式：`{"success": bool, "data": ..., "error": {"code", "message"}, "request_id": str}`

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

- 所有列表接口支持分页，限制最大 page size。
- 写操作使用权限校验；报名等关键操作用幂等键。
- API 文档仅在开发环境或管理员授权后公开；生产禁用。

## 接口清单（模块 → 文件对照）

| 模块 | 前缀 | 后端文件 |
|---|---|---|
| 健康检查 | `/health` `/ready` | `endpoints/health.py` |
| 认证 | `/auth` | `endpoints/auth.py` |
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
| 网站设置 | `/admin/settings` | `endpoints/admin_settings.py` |

---

## 认证说明

| 认证方式 | 说明 |
|---|---|
| **无需认证** | 游客可访问（如公开图片、健康检查、站点配置） |
| **Bearer Token** | 请求头 `Authorization: Bearer <access_token>`，登录后获取 |
| **管理权限** | 需管理员/超管角色，端点内做逐请求 RBAC 校验 |

**Token 机制**：短时效 Access Token（15 分钟）+ Refresh Token（14 天，HttpOnly Cookie / sessionStorage）。前端 `client.ts` 拦截 401 自动刷新重试。

---

## 一、健康检查

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/health` | 无 | 存活检查，返回 `{status: "ok"}` |
| GET | `/ready` | 无 | 就绪检查，返回 `{status, redis}`（DB/Redis 连通性） |

---

## 二、认证 `/auth`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| POST | `/auth/register` | 无 | 注册（用户名/昵称/邮箱/手机/密码，可选摄影师申请） |
| POST | `/auth/verify/email` | 无 | 邮箱 OTP 验证 |
| POST | `/auth/verify/phone` | 无 | 手机 OTP 验证 |
| POST | `/auth/login` | 无 | 登录，返回 `{access_token, refresh_token, user}` |
| POST | `/auth/refresh` | Refresh Token | 刷新 Access Token（轮换 Refresh Token） |
| POST | `/auth/logout` | Bearer | 登出（撤销当前 Refresh Token） |
| POST | `/auth/logout-all` | Bearer | 登出所有设备（撤销全部会话） |
| POST | `/auth/password/forgot` | 无 | 找回密码（发送验证码） |
| POST | `/auth/password/reset` | 无 | 重置密码（验证码 + 新密码；真实更新密码 + 撤销全部会话） |
| GET | `/auth/me` | Bearer | 获取当前用户信息（含 bio/avatar_url） |

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
| GET | `/images/{image_id}/download` | Bearer | 签发原图下载签名 URL |
| DELETE | `/images/{image_id}` | Bearer | 删除图片（仅上传者本人或有 gallery.image.delete.any 权限；含派生图清理） |
| POST | `/images/{image_id}/report` | Bearer | 举报图片（不能举报自己的图片；同一图片仅一条未处理举报） |

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
| PATCH | `/profile/me/images/{image_id}` | Bearer | 更新本人私有图的展示授权 is_displayable（已实现） |
| POST | `/profile/me/images/upload-intent` | Bearer | 私有图片上传凭证 |
| POST | `/profile/me/images/upload-complete` | Bearer | 私有图片上传完成 |
| GET | `/profile/me/images/{image_id}/url` | Bearer | 签发短时效签名 URL（私有图下载） |
| DELETE | `/profile/me/images/{image_id}` | Bearer | 删除私有图片 |
| POST | `/profile/me/avatar/upload-intent` | Bearer | 头像上传凭证（返回 COS 预签名 URL，限 5MB） |
| POST | `/profile/me/avatar/upload-complete` | Bearer | 头像上传完成（验证对象存在，自动清理旧头像） |
| DELETE | `/profile/me/avatar` | Bearer | 删除头像 |
| GET | `/profile/members` | 无 | 公开成员列表（active 用户昵称/简介/头像，不含隐私） |
| GET | `/profile/{user_id}` | 无 | 公开用户资料（昵称/角色，不含隐私） |

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

照片和背景素材必须是本人的 `ProfileImage`、已开启 `is_displayable`，且对象 Key 位于 `private/profiles/{当前用户 id}/` 前缀下。`media` 按 object_key 映射 `{thumb_url, display_url, width, height}`，仅包含符合这些条件的引用素材；处理就绪时返回缩略图签名，展示图暂使用原图的短时签名 URL。图库统计只计算本人 `approved` 且 `is_public=true` 的公开图片。

`PATCH /profile/me/images/{image_id}` 接受严格请求体 `{"is_displayable": true}`，拒绝额外字段和字符串/整数布尔值，成功返回 `{"id": "图片 UUID", "is_displayable": true}`。此标记默认 `false`，不会自动发布主页或把私有相册整体公开。

| HTTP | 错误码/响应 | 触发条件 |
|---|---|---|
| 401 | 现有认证错误 | 缺少/无效凭证或账号未启用 |
| 422 | `detail.code=PROFILE_LAYOUT_INVALID` | 布局结构、数量、模块字段/宽度或素材归属/展示权限不符；块级错误消息包含块 id |
| 422 | `detail.code=PROFILE_LAYOUT_TOO_LARGE` | 布局超过 256 KiB 或无法按有效 JSON 编码 |
| 422 | FastAPI 请求校验错误 | PATCH 严格布尔值/额外字段校验失败 |
| 404 | `detail.code=PROFILE_IMAGE_NOT_FOUND` | 图片 UUID 非法、不存在或不属于当前用户 |

### 前端已预留、真实后端尚未实现

| 方法 | 预留路径 | 前端函数 | 当前状态 |
|---|---|---|---|
| GET | `/profile/{username}/page` | getProfilePage | 仅开发 mock 提供访客主页 |
| POST | `/profile/me/layout/publish` | publishMyLayout | 仅开发 mock 提供发布 |
| POST | `/profile/me/layout/discard` | discardMyDraft | 仅开发 mock 提供丢弃草稿 |
| PUT | `/profile/me/theme` | saveMyTheme | 仅开发 mock 提供主题持久化 |
| GET | `/profile/me/media` | getMyMedia | 仅开发 mock 提供可选素材清单 |

以上不是已注册的 FastAPI 端点。真实后端模式下，编辑器 `saveDraft()` 先 PUT 布局再 PUT 主题，后一步当前返回 404，可能出现布局保存成功但 UI 提示失败；发布、丢弃、素材选择和访客页也尚未完成真实链路。`getMyLayout` / `saveMyLayout` / `setProfileImageDisplayable` 已有真实后端实现。迁移 `4f8a2c7d91b3` 新增 `profile_layouts` 和图片展示标记，上线此分支前需执行 `alembic upgrade head`。

---

## 六、课表 `/schedule`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/schedule/mine` | Bearer | 我的课表列表 |
| POST | `/schedule/upload-intent` | Bearer | 课表上传凭证 |
| POST | `/schedule/upload-complete` | Bearer | 上传完成（后端下载+解析 ICS/TXT） |
| GET | `/schedule/{schedule_id}` | Bearer | 课表详情（含解析后的课程列表） |
| POST | `/schedule/compare` | Bearer | 两人课表对比（空闲/同教室/冲突） |
| GET | `/schedule/shared/{username}` | Bearer | 获取对方公开的课表 |
| PATCH | `/schedule/{schedule_id}/visibility` | Bearer | 课表公开/私有开关 |
| DELETE | `/schedule/{schedule_id}` | Bearer | 删除课表 |

**对比结果**：返回 `same_classroom`（同教室）、`both_free`（共同空闲）、`overlaps`（时间冲突），均按周次交集计算。

---

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
| GET | `/admin/images/` | 管理员 | 图片列表（支持 status/is_public 筛选 + 分页） |
| PATCH | `/admin/images/{id}/moderation` | 管理员 | 审核（pending → approved / rejected） |
| PATCH | `/admin/images/{id}/visibility` | 管理员 | 公开/私有开关 |
| PUT | `/admin/images/{id}/tags` | 管理员 | 编辑标签 |
| DELETE | `/admin/images/{id}` | 管理员 | 删除图片（含派生图清理） |

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
| GET | `/site/public-config` | 无 | 公开配置（网站名称/Logo/备案号等） |
| GET | `/site/footer` | 无 | 页脚配置（版权/链接/备案号） |
| GET | `/site/legal` | 无 | 法律信息（协议/隐私/版权/联系方式） |

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

---

## 权限矩阵速查

| 操作 | 游客 | 成员 | 摄影师 | 管理员 |
|---|:---:|:---:|:---:|:---:|
| 查看公开图片/公告/活动 | ✓ | ✓ | ✓ | ✓ |
| 注册/登录/找回密码 | ✓ | ✓ | ✓ | ✓ |
| 上传公开图片 | — | — | ✓ | ✓ |
| 上传私有图片/课表 | — | ✓ | ✓ | ✓ |
| 读取/保存本人布局、设置本人图片展示授权 | — | ✓ | ✓ | ✓ |
| 报名活动/签到 | — | ✓ | ✓ | ✓ |
| 审批用户/管理内容/网站设置 | — | — | — | ✓ |

---

## 前端 API 封装对照

| 前端文件 | 对应后端模块 |
|---|---|
| `src/api/client.ts` | 通用请求封装（Bearer 注入、401 刷新、统一解包） |
| `src/api/token.ts` | Token 管理（内存 + sessionStorage） |
| `src/api/bootstrap.ts` | 共享登录态恢复，供首屏与受保护路由调用 |
| `src/api/profile.ts` | 个人主页：3 个已实现端点的封装与 5 个待接通端点的调用；头像上传/删除 |
| `src/api/schedule.ts` | 课表 API（7 个接口） |
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
| `ensureAccessToken()` | `async function(): Promise<string \| null>` | 确保内存有有效 access token；页面刷新后用 refresh token 静默换取新 token，避免首个 401 |
| `setUnauthorizedHandler(fn)` | `function(fn: (() => void) \| null): void` | 注册 401 登出回调（由 auth store 注册，避免循环依赖） |

**内部流程**：请求拦截器注入 `Authorization: Bearer <token>` → 响应拦截器检测 401 → 自动调 `/auth/refresh` 换新 token → 重试一次 → 失败则 `clearTokens()` + 触发 `onUnauthorized`。

错误提取优先读取响应信封 `error.message`，再读取 `detail.message` 或字符串 `detail`，供页面显示业务校验错误。

## 前端 `src/api/token.ts` — Token 管理

| 函数 | 签名 | 说明 |
|---|---|---|
| `getAccessToken()` | `(): string \| null` | 获取内存中的 access token |
| `setTokens(access, refresh)` | `(access: string, refresh: string): void` | 同时保存 access（内存）和 refresh（sessionStorage） |
| `getRefreshToken()` | `(): string \| null` | 获取 refresh token |
| `clearTokens()` | `(): void` | 清除全部 token（登出/刷新失败） |

## 前端 `src/api/bootstrap.ts` — 登录态恢复

| 函数 | 签名 | 说明 |
|---|---|---|
| `bootstrapAuth()` | `(): Promise<void>` | 同一次页面生命周期仅初始化一次，并发调用共享 Promise；存在 Refresh Token 时先 ensureAccessToken 再 fetchMe，失败保持未登录。App 首屏与 requiresAuth 守卫共用 |

## 前端 `src/api/profile.ts` — 个人主页 API

| 函数 | 参数 / 返回 | 对应接口及状态 |
|---|---|---|
| `getMyLayout()` | `Promise<ProfileLayoutResponse>` | GET /profile/me/layout，已实现 |
| `saveMyLayout(payload)` | `{blocks: ProfileBlock[], is_public?: boolean}` → `Promise<ProfileLayoutResponse>` | PUT /profile/me/layout，已实现 |
| `setProfileImageDisplayable(id, is_displayable)` | `(string, boolean)` → `Promise<{id, is_displayable}>` | PATCH /profile/me/images/{id}，已实现 |
| `getProfilePage(username)` | string → `Promise<ProfilePageResponse>` | GET /profile/{username}/page，待后端实现 |
| `publishMyLayout()` | `Promise<{published_at}>` | POST /profile/me/layout/publish，待后端实现 |
| `discardMyDraft()` | `Promise<ProfileLayoutResponse>` | POST /profile/me/layout/discard，待后端实现 |
| `saveMyTheme(theme)` | ProfileTheme → `Promise<{theme: ProfileTheme}>` | PUT /profile/me/theme，待后端实现 |
| `getMyMedia()` | `Promise<{items: ProfileMediaOption[]}>` | GET /profile/me/media，待后端实现 |

## 前端主页编辑器与渲染辅助函数

| 文件 / 导出 | 说明 |
|---|---|
| `stores/profileLayout.ts`：`useProfileLayoutStore()` | 保存 blocks/theme/media/stats、已发布版本、上限、dirty/hasUnpublished/canUndo/canRedo 及加载/保存状态 |
| store：`load()` / `loadMediaOptions()` | 读取本人布局、可选素材；素材清单失败时显示空列表 |
| store：`addBlock(type)` / `removeBlock(id)` / `duplicateBlock(id)` | 新增/删除/复制模块；新增和复制受 maxBlocks 限制 |
| store：`moveBlock(from, to)` / `setSpan(id, span)` / `updateProps(id, patch)` | 修改排序、宽度和属性 |
| store：`applyThemePreset(id)` / `undo()` / `redo()` | 应用主题预设，撤销/重做模块及主题编辑 |
| store：`saveDraft()` / `publish()` / `discard()` | 持久化操作；主题/发布/丢弃接口仍待接通，限制见上文 |
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
| `compareSchedules(slotsA, slotsB)` | `(slotsA: ScheduleSlot[], slotsB: ScheduleSlot[]): Promise<ScheduleCompareResult>` | `POST /schedule/compare` |
| `setScheduleVisibility(scheduleId, isPublic)` | `(scheduleId: string, isPublic: boolean): Promise<ScheduleRecord>` | `PATCH /schedule/{id}/visibility` |
| `deleteSchedule(scheduleId)` | `(scheduleId: string): Promise<{message: string}>` | `DELETE /schedule/{id}` |

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
| `register_user(db, ...) -> User` | 注册用户（创建 pending 状态，含摄影师申请） |
| `login(db, account, password) -> dict` | 登录（校验密码 → 生成 token 对 → 记录会话） |
| `refresh_tokens(db, refresh_token) -> dict` | 刷新令牌（轮换 + 旧令牌复用检测 → 撤销会话族） |
| `revoke_session(db, refresh_token)` | 撤销单个会话（登出） |
| `revoke_all_sessions(db, user_id)` | 撤销全部会话（登出所有设备） |
| `approve_user(db, user_id) -> User` | 审批通过（激活账号） |
| `reject_user(db, user_id) -> User` | 拒绝注册 |

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
| `list_my_profile_images(db, user) -> dict` | 私有相册列表（含签名缩略图 URL） |
| `get_profile_image_signed_url(db, *, user, image_id) -> dict` | 签发短时效下载签名 URL |
| `delete_profile_image(db, *, user, image_id)` | 删除私有图片 |

### `services/profile_layout.py` — 布局草稿与展示授权

| 函数 / 常量 | 说明 |
|---|---|
| `validate_blocks(raw) -> list[dict[str, Any]]` | 校验模块数组、数量、唯一 id、类型、span、props；按白名单重新序列化，丢弃未知字段 |
| `get_layout_payload(db, user) -> dict[str, Any]` | 组装主题/草稿/已发布块/公开开关/上限/已授权素材/签名 TTL/统计；GET 与 PUT 共用 |
| `put_layout(db, user, body) -> dict[str, Any]` | 校验大小、结构、素材本人归属和展示权限；创建或替换草稿及可选 is_public，提交后返回同形布局 |
| `set_image_displayable(db, user, image_id, is_displayable) -> dict[str, Any]` | 仅更新本人私有图展示标记；非法目标返回 404 |
| `ProfileLayoutError(code, message, status_code=422)` | 业务错误，经 error_to_http 转为 HTTPException detail 响应 |
| `DEFAULT_THEME` / `ALLOWED_SPANS` | 默认主题与按模块类型划分的允许宽度 |
| `MAX_LAYOUT_BYTES` / `MAX_HTML_LENGTH` | 布局重新编码后最多 256 KiB；HTML 字符数最多 24576 |

`schemas/profile_layout.py` 的 `ProfileImageDisplayPatch` 使用 `StrictBool`，配置 `extra="forbid", strict=True`。模型 `ProfileLayout` 预留发布/主题字段，当前服务只实现草稿读写和图片展示授权，未提供发布/主题更新服务函数。

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
| `compare(slots_a, slots_b) -> dict` | 对比两人课表 → `{same_classroom, both_free, overlaps}` |
| `parse_schedule(data, filename) -> dict` | 按文件名识别格式解析（ICS/TXT，PDF 占位报错） |
| `parse_ics(data) -> list[CourseSlot]` | ICS 课表解析（VEVENT → CourseSlot） |
| `parse_txt(data) -> list[CourseSlot]` | ZJUT TXT 课表解析 |
| `ScheduleParseError` | 解析异常（code + message） |

### `services/schedule_service.py` — 课表业务服务

| 函数 | 说明 |
|---|---|
| `create_schedule_upload_intent(...) -> dict` | 课表上传凭证 |
| `complete_schedule_upload(db, ...) -> Schedule` | 上传完成（下载文件 + 解析 + 落库） |
| `get_my_schedules(db, user) -> dict` | 我的课表列表 |
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
| `send_otp(db, target, purpose, channel) -> dict` | 发送验证码（哈希存储、频率限制） |
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
| `ProfileMedia` / `ProfileMediaOption` | 已解析签名 URL 的素材、带归属标识与展示授权的可选图片 |
| `ProfileBackgroundType` / `ProfileCardStyle` / `ProfileTheme` | 背景/卡片类型及主题颜色、图片背景、模糊等字段 |
| `ProfilePageUser` / `ProfilePageResponse` | 访客主页预留响应契约（真实后端待实现） |
| `ProfileLayoutResponse` | 已实现 GET/PUT 布局的同形响应（theme/draft_blocks/published_blocks/is_public/max_blocks/media/media_expires_in/stats） |
