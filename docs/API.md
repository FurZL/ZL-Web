# Furry ZJUT API 规范

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

## 接口清单

见架构文档「十、API 接口清单」，当前骨架已在 `app/api/v1/endpoints/` 下按模块落位：

| 模块 | 前缀 | 文件 |
|---|---|---|
| 健康检查 | `/health` `/ready` | health.py |
| 认证 | `/auth` | auth.py |
| 图片 | `/images` | images.py |
| 个人空间 | `/profile` | profile.py |
| 课表 | `/schedule` | schedule.py |
| 页面 | `/pages` | pages.py |
| 活动 | `/events` | events.py |
| 站点 | `/site` | site.py |
| 社团 | `/club` | club.py |
| 用户管理 | `/admin/users` | admin_users.py |
| 设置管理 | `/admin/settings` | admin_settings.py |