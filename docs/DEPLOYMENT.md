# 部署说明（EdgeOne Pages + 宝塔 2C2G + PostgreSQL/Redis 本机）

最终部署形态：前端 EdgeOne Pages，API 由宝塔 Nginx 反代至本机 FastAPI（systemd），
PostgreSQL/Redis 本机、仅回环监听，文件走 COS。

详细逐条配置见架构文档的**附录 B（最终部署方案，优先级最高）**。本文件列出关键文件与步骤索引。

## 关键文件

- Nginx API 站点：`deploy/nginx/api.example.com.conf`
- systemd 服务：`deploy/systemd/furry-zjut-api.service`
- EdgeOne Pages：`deploy/edgeone/README.md`
- 加密备份及隔离恢复验证：`deploy/scripts/backup-furry-zjut.sh`、`deploy/scripts/verify-backup-furry-zjut.sh`

## 步骤概览

1. 数据库：本机装 PostgreSQL，`listen_addresses='127.0.0.1'`，建库 `furry_zjut` 与最小权限账号 `furry_app`。
2. Redis：本机装 Redis，`bind 127.0.0.1`、认证、`maxmemory 64mb`。
3. 后端：`python3 -m venv venv && ./venv/bin/pip install -e .`（开发/测试环境再加 `.[dev]`）；`alembic upgrade head`。
4. 服务：`deploy/systemd/furry-zjut-api.service` 复制到 `/etc/systemd/system/`，`systemctl enable --now furry-zjut-api`。
5. Nginx：宝塔创建 `api.example.com` 站点，反代 `127.0.0.1:8000`，配 TLS。
6. CORS：在 `.env` 的 `FRONTEND_ORIGINS` 配真实前端来源。
7. 前端：`npm run build` 后发布到 EdgeOne Pages，配 SPA fallback 与自定义域名；后端已通过 HttpOnly Cookie 跨标签页保持登录。
8. 备份：配置 age 接收者和异地上传钩子，先手动验证备份与隔离恢复，再接定时任务并配置失败告警。

## 域名、端口与第三方回调

| 项目 | 值 |
|---|---|
| 前端站点 | `https://www.furzl.cn`（EdgeOne Pages） |
| 后端 API | `https://api.furzl.cn/api/v1`（Nginx → `127.0.0.1:8000`） |
| QQ 前端回调路由 | `/oauth/qq` |
| QQ 互联登记的回调域/地址 | `https://www.furzl.cn/oauth/qq` |
| 用户协议 / 隐私政策 | `/legal/terms` / `/legal/privacy` |
| 版权声明 / 联系我们 | `/legal/copyright` / `/legal/contact` |

QQ 回调先落到前端 EdgeOne 站点，再由前端携带 `code` 和 `state` 调后端 `GET /api/v1/auth/oauth/qq/callback`。因此 Cookies 必须允许 `www.furzl.cn` 页面携带对 `api.furzl.cn` 的请求（Axios 已启用 `withCredentials`），后端 CORS 必须把正式前端来源加入 `FRONTEND_ORIGINS`，不能使用 `*` 搭配凭据。

## OAuth 与 Cookie 上线配置

```dotenv
OAUTH_FRONTEND_BASE_URL=https://www.furzl.cn
QQ_APP_ID=<QQ_APP_ID>
QQ_APP_KEY=<QQ_APP_KEY>
QQ_REDIRECT_URI=https://www.furzl.cn/oauth/qq
REFRESH_TOKEN_TTL_DAYS=7
AUTH_COOKIE_NAME=refresh_token
AUTH_COOKIE_SAMESITE=lax
```

- 生产环境 `APP_ENV=production` 时 Refresh Cookie 自动带 `Secure`；必须全站 HTTPS。
- 前端站点和 API 同属 `furzl.cn` 时默认 `SameSite=Lax` 可用于顶层导航；若后续拆到不同可注册域，改 Cookie/CSRF 方案前不要直接改成 `None` 就上线。
- QQ App Key 只放后端 `/etc/furry-zjut/api.env` 或 Secret 管理，不写入 `site_settings`，不在后台页面回显。
- 后台「网站设置 → 第三方登录」写入 `oauth_config`（`enabled` / `qq_enabled`），前端与后端都会读取；关闭后 OAuth 开始接口返回 503。
- QQ 授权 state 和未绑定临时凭证存 Redis，10 分钟过期且一次性消费；`/api/v1/ready` 同时检查 Redis 和 PostgreSQL，任一失败返回 HTTP 503。

## 备份与恢复

备份脚本需要 `pg_dump`、`age`、`sha256sum`，使用 PostgreSQL 标准环境变量（如 `PGHOST`、`PGPORT`、`PGUSER`、`PGDATABASE`、`PGPASSFILE`）。不要把密码写在命令行；凭据文件应限制权限。`BACKUP_AGE_RECIPIENT` 是 age 公钥，解密身份文件与备份分开保存。

```bash
export PGHOST=127.0.0.1 PGUSER=furry_backup PGDATABASE=furry_zjut
export PGPASSFILE=/root/.pgpass-furry-zjut
export BACKUP_AGE_RECIPIENT='<age 公钥>'
export BACKUP_DIR=/var/backups/furry-zjut
export REQUIRE_OFFSITE=1
export BACKUP_UPLOAD_HOOK=/usr/local/bin/upload-furry-backup
bash deploy/scripts/backup-furry-zjut.sh
```

`BACKUP_UPLOAD_HOOK` 必须由部署方提供为可执行文件，接收两个参数：加密备份文件和 SHA-256 文件的绝对路径；上传失败必须返回非零。`REQUIRE_OFFSITE=1` 时缺少钩子会失败；默认 `0` 时只生成本地加密备份并提示没有异地上传。脚本不自动配置上传、告警或删除旧备份；需要在部署侧设置独立存储、保留策略和失败告警，并确认远端完整性。

恢复演练先使用独立权限**手动创建空数据库** `furry_restore_check_<唯一标识>`，不要指向正式库，再执行：

```bash
export VERIFY_DATABASE=furry_restore_check_example
export BACKUP_AGE_IDENTITY=/secure/path/age-identity.txt
bash deploy/scripts/verify-backup-furry-zjut.sh /secure/backups/example.age
```

恢复脚本先验证 SHA-256，只接受上述名称格式、拒绝源数据库或非空验证库；验证库含个人数据，演练后由运维按权限清理。脚本使用相同 PostgreSQL 连接环境变量，私钥文件不可提交 Git。实际加密、异地上传和生产恢复需要部署方配置与演练；本地仅已验证 Docker PostgreSQL 的 dump 和隔离恢复，尚未实测 age 或远端钩子。

图片任务在 PostgreSQL 中持久化，最多尝试 5 次，重启后过期租约可恢复；管理员可在图片管理的“处理任务”中查看和重试失败任务。处理是至少一次语义，不保证跨 COS 和数据库的严格原子性；运维仍需监控失败任务和日志。

## 图片代理域

`PUBLIC_ASSET_BASE_URL` 用于公开图和头像；个人相册通过后端短期票据代理。上传仍由浏览器用 COS 预签名 URL 直传。生产建议：

```dotenv
PUBLIC_ASSET_BASE_URL=https://img.furzl.cn
PUBLIC_API_BASE_URL=https://api.furzl.cn
```

跨域部署必须设置 `PUBLIC_API_BASE_URL` 为浏览器可访问的 HTTPS API 源；留空只适用于前端同源代理 `/api/v1` 的部署。必须禁止 COS 与 CDN 直接读取 `private/` 和带开发前缀的私有路径，并验收旧链接不能绕过 API。API/CDN/反向代理日志不得记录图片票据查询字符串；不要缓存图片代理响应。代理读取原图目前占用单张文件的内存，上线时应设置并发限制并评估大图资源消耗。升级前执行 Alembic；旧 Access Token 会在刷新后恢复。

## 环境变量

见根目录 `.env.example`；生产敏感项由 `/etc/furry-zjut/api.env`（systemd EnvironmentFile）注入，不放 Git。

## 2C2G 资源预算

- FastAPI 1 Worker；SQLAlchemy 连接池 `pool_size=5`、`max_overflow=2`。
- PostgreSQL `shared_buffers=256MB`（起步）；Redis `maxmemory=64mb`。
- 图片/PDF 解析限并发，不进 API 进程做高分辨率转码。

## 上线验收清单

见架构文档附录 B14。

## 多人开发 COS 隔离

多人共用同一个 COS 测试桶时，为避免上传/派生文件互相覆盖，在 `.env` 中设置：

```
COS_DEV_PREFIX=dev-你的标识-时间戳
```

- 例如 `COS_DEV_PREFIX=dev-alice-20261115-171059`，则所有对象实际写入 `dev-alice-20261115-171059/public/...` 下。
- 数据库始终存储**逻辑 key**（如 `public/gallery/original/2026/11/abc`），不含此前缀。
- `CosStorageProvider` 在与 COS 交互时透明追加前缀；生产环境不设此变量则逻辑 key 即物理 key。
- 每次开发部署到共享桶前务必把 `COS_DEV_PREFIX` 改成新的时间戳，确保与其他开发者不冲突。
- 对象存储脚本（`setup_cos_cors.py`、`setup_cos_public_read.py` 等）需手动传入带前缀的路径或更新脚本支持前缀。
