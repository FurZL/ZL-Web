# WHATAPI.md — 全部 API 接口文档（交接用）

> 本文件整理了项目中**全部 74 个 API 接口**，供团队交接和查阅。
> 统一前缀：`/api/v1`，统一响应格式：`{"success": bool, "data": ..., "error": {"code", "message"}, "request_id": str}`

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
| POST | `/auth/password/reset` | 无 | 重置密码（验证码 + 新密码） |
| GET | `/auth/me` | Bearer | 获取当前用户信息 |

---

## 三、用户管理 `/admin/users`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/admin/users/` | 管理员 | 用户列表 |
| GET | `/admin/users/pending` | 管理员 | 待审批用户列表 |
| GET | `/admin/users/{user_id}` | 管理员 | 用户详情 |
| POST | `/admin/users/{user_id}/approve` | 管理员 | 审批通过（激活账号） |
| POST | `/admin/users/{user_id}/reject` | 管理员 | 拒绝注册申请 |
| PATCH | `/admin/users/{user_id}/role` | 管理员 | 修改用户角色 |
| PATCH | `/admin/users/{user_id}/status` | 管理员 | 修改用户状态（启用/禁用） |

---

## 四、公开图片 `/images`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/images/` | 无 | 公开图片列表（分页，支持 `page`/`page_size` 参数） |
| GET | `/images/{image_id}` | 无 | 图片详情（含 URL/描述/标签/拍摄者） |
| POST | `/images/upload-intent` | 摄影师+ | 申请上传凭证（返回预签名上传 URL） |
| POST | `/images/upload-complete` | 摄影师+ | 上传完成（后端 HEAD 复核 + 落库） |
| GET | `/images/{image_id}/download` | Bearer | 签发原图下载签名 URL |
| DELETE | `/images/{image_id}` | 管理员 | 删除图片 |
| POST | `/images/{image_id}/report` | Bearer | 举报图片 |

**上传流程**：`upload-intent` → 前端直传 COS → `upload-complete` → 后台 worker 生成缩略图（800px）/展示图（2000px）WebP。

---

## 五、个人空间 `/profile`

| 方法 | 路径 | 认证 | 说明 |
|---|---|---|---|
| GET | `/profile/me` | Bearer | 获取个人信息 |
| PUT | `/profile/me` | Bearer | 修改个人信息 |
| GET | `/profile/me/images` | Bearer | 私有相册列表（仅本人可见） |
| POST | `/profile/me/images/upload-intent` | Bearer | 私有图片上传凭证 |
| POST | `/profile/me/images/upload-complete` | Bearer | 私有图片上传完成 |
| GET | `/profile/me/images/{image_id}/url` | Bearer | 签发短时效签名 URL（私有图下载） |
| DELETE | `/profile/me/images/{image_id}` | Bearer | 删除私有图片 |
| GET | `/profile/{user_id}` | 无 | 公开用户资料（昵称/角色，不含隐私） |

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
| 报名活动/签到 | — | ✓ | ✓ | ✓ |
| 审批用户/管理内容/网站设置 | — | — | — | ✓ |

---

## 前端 API 封装对照

| 前端文件 | 对应后端模块 |
|---|---|
| `src/api/client.ts` | 通用请求封装（Bearer 注入、401 刷新、统一解包） |
| `src/api/token.ts` | Token 管理（内存 + sessionStorage） |
| `src/api/schedule.ts` | 课表 API（7 个接口） |
| `src/api/site.ts` | 站点/公告 API（11 个接口） |
| `src/api/events.ts` | 活动 API（10 个接口） |
| `src/api/pages.ts` | 动态页面 API（9 个接口） |
| `src/api/adminImages.ts` | 图片管理 API（6 个接口） |
