# 宝塔生产环境部署手册

> 目标：在一台宝塔 2C2G 服务器上部署 Furry ZJUT 后端 API，对外服务域名 `https://api.furzl.cn`。
> 前端不部署在这台服务器，最终由腾讯云 EdgeOne Pages 托管。
> 本手册可以直接交给宝塔面板内置 AI 执行；所有 ``<尖括号>`` 占位符需在执行前替换为真实值。

## 1. 总体架构

```text
EdgeOne Pages（前端）
        |
        |  https
        v
api.furzl.cn
        |
        |  Nginx 反向代理
        v
http://127.0.0.1:8000
        |
     FastAPI（systemd）
        |
        +---- PostgreSQL（仅监听 127.0.0.1:5432）
        +---- Redis（仅监听 127.0.0.1:6379）
        +---- 腾讯云 COS（对象存储，外部托管）
```

## 2. 部署参数

| 参数 | 示例值 | 说明 |
|---|---|---|
| API 域名 | `api.furzl.cn` | DNS A 记录指向本机公网 IP |
| 前端主域 | `www.furzl.cn`、`furzl.cn` | 用于后端 CORS 白名单 |
| 后端目录 | `/opt/furry-zjut/backend` | Git 拉取 `main` 分支 |
| 环境文件 | `/etc/furry-zjut/api.env` | `chmod 600`，不进 Git |
| 系统用户 | `furry` | systemd 运行用户 |
| PostgreSQL 库 | `furry_zjut` | 应用库 |
| PostgreSQL 用户 | `furry_app` | 最小权限应用账号 |
| Redis | `127.0.0.1:6379/0` | 仅回环监听，生产建议加密码 |

## 3. 前置条件

- `furzl.cn` 已通过 ICP 备案，`api.furzl.cn` 已解析到宝塔服务器。
- 宝塔面板已安装，并已安装 Nginx；推荐在宝塔软件商店安装 PostgreSQL 和 Redis。
- 服务器防火墙只开放 `80`、`443`；`5432`、`6379`、`8000` 不对公网开放。
- 系统 Python 建议使用 `3.11` 或 `3.12`，不要在 Linux 生产环境使用太新的 3.14。

## 4. 创建系统用户和目录

```bash
id furry >/dev/null 2>&1 || useradd -r -m -d /opt/furry-zjut -s /bin/bash furry
mkdir -p /opt/furry-zjut/backend /etc/furry-zjut
chown -R furry:furry /opt/furry-zjut
chmod 700 /etc/furry-zjut
```

## 5. 配置 PostgreSQL

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE furry_app LOGIN PASSWORD '<DB_PASSWORD>';
CREATE DATABASE furry_zjut OWNER furry_app ENCODING 'UTF8' TEMPLATE template0;
SQL
```

推荐限制 PostgreSQL 只监听本机。修改 `postgresql.conf`：

```conf
listen_addresses = '127.0.0.1'
# 2C2G 起步值
shared_buffers = 256MB
effective_cache_size = 768MB
```

修改 `pg_hba.conf`，本机应用账号使用密码认证：

```conf
host    furry_zjut    furry_app    127.0.0.1/32    scram-sha-256
```

## 6. 配置 Redis

修改 `redis.conf`：

```conf
bind 127.0.0.1
protected-mode yes
maxmemory 64mb
maxmemory-policy allkeys-lru
```

如需密码：

```conf
requirepass <REDIS_PASSWORD>
```

对应后端地址为：

```text
redis://:<REDIS_PASSWORD>@127.0.0.1:6379/0
```

## 7. 拉取代码并安装依赖

```bash
cd /opt/furry-zjut/backend
git clone -b main <GIT_REPOSITORY_URL> .
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -e .
```

确认已安装关键依赖：

```bash
python -c "import fastapi, sqlalchemy, psycopg, redis, argon2, qcloud_cos"
```

## 8. 创建生产环境配置

先在本机生成 `SECRET_KEY`：

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

创建 `/etc/furry-zjut/api.env`：

```bash
install -m 600 /dev/null /etc/furry-zjut/api.env
```

内容：

```dotenv
APP_ENV=production
APP_NAME=啫喱小站
DEBUG=false
SECRET_KEY=<GENERATED_SECRET_KEY>
API_V1_PREFIX=/api/v1

DATABASE_URL=postgresql+psycopg://furry_app:<DB_PASSWORD>@127.0.0.1:5432/furry_zjut
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=2

REDIS_URL=redis://127.0.0.1:6379/0

FRONTEND_ORIGINS=https://www.furzl.cn,https://furzl.cn

STORAGE_PROVIDER=cos
COS_SECRET_ID=<COS_SECRET_ID>
COS_SECRET_KEY=<COS_SECRET_KEY>
COS_REGION=<COS_REGION>
COS_BUCKET=<COS_BUCKET>
PUBLIC_ASSET_BASE_URL=https://img.furzl.cn
PRIVATE_URL_TTL_SECONDS=900
PROFILE_LAYOUT_MAX_BLOCKS=16

EMAIL_PROVIDER=smtp
SMTP_HOST=<SMTP_HOST>
SMTP_PORT=465
SMTP_USER=<SMTP_USER>
SMTP_PASSWORD=<SMTP_PASSWORD>
SMTP_FROM=<SMTP_FROM>
SMTP_USE_SSL=true

SMS_PROVIDER=aliyun
SMS_ALIYUN_ACCESS_KEY_ID=<SMS_ALIYUN_ACCESS_KEY_ID>
SMS_ALIYUN_ACCESS_KEY_SECRET=<SMS_ALIYUN_ACCESS_KEY_SECRET>
SMS_ALIYUN_SIGN_NAME=<SMS_ALIYUN_SIGN_NAME>
SMS_ALIYUN_TEMPLATE_CODE=<SMS_ALIYUN_TEMPLATE_CODE>
SMS_ALIYUN_REGION=cn-hangzhou

CAPTCHA_PROVIDER=
HUMAN_VERIFICATION_PROVIDER=

ACCESS_TOKEN_TTL_MINUTES=15
REFRESH_TOKEN_TTL_DAYS=7
AUTH_COOKIE_NAME=refresh_token
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=lax
PASSWORD_HASH_SCHEME=argon2

OAUTH_FRONTEND_BASE_URL=https://www.furzl.cn
QQ_APP_ID=<QQ_APP_ID>
QQ_APP_KEY=<QQ_APP_KEY>
QQ_REDIRECT_URI=https://www.furzl.cn/oauth/qq

OTP_TTL_SECONDS=600
OTP_MAX_ATTEMPTS=5
OTP_COOLDOWN_SECONDS=120
OTP_DEV_MODE=false

UPLOAD_MAX_BYTES=52428800
LOG_LEVEL=INFO
SENTRY_DSN=
COS_DEV_PREFIX=
```

`PUBLIC_ASSET_BASE_URL` 是图片公开访问域名。`img.furzl.cn` 需通过 CDN/EdgeOne/COS 自定义域名回源到对象桶；暂时未准备该域名时，可改为 COS 默认公开域名，或留空让程序回退到 COS 默认域名。

## 9. 执行数据库迁移

```bash
cd /opt/furry-zjut/backend
source venv/bin/activate
set -a
source /etc/furry-zjut/api.env
set +a
alembic -c alembic.ini upgrade head
alembic -c alembic.ini current
```

创建管理员：

```bash
python scripts/create_admin.py admin <ADMIN_PASSWORD>
```

管理员脚本幂等；线上请使用随机强密码，不要继续使用开发密码。

## 10. 创建 systemd 服务

创建 `/etc/systemd/system/furry-zjut-api.service`：

```ini
[Unit]
Description=Furry ZJUT FastAPI API
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=simple
User=furry
Group=furry
WorkingDirectory=/opt/furry-zjut/backend
EnvironmentFile=/etc/furry-zjut/api.env
ExecStart=/opt/furry-zjut/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1
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

启用服务：

```bash
systemctl daemon-reload
systemctl enable --now furry-zjut-api
systemctl status furry-zjut-api
journalctl -u furry-zjut-api -f
```

## 11. 配置宝塔 Nginx 站点

在宝塔中新建纯反向代理站点 `api.furzl.cn`，不要启用 PHP。申请并部署 SSL 证书后，站点配置使用以下内容：

```nginx
server {
    listen 80;
    server_name api.furzl.cn;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.furzl.cn;

    ssl_certificate     <SSL_BUNDLE_PATH>;
    ssl_certificate_key <SSL_KEY_PATH>;
    ssl_protocols TLSv1.2 TLSv1.3;

    server_tokens off;
    client_max_body_size 20m;
    client_body_timeout 30s;

    add_header X-Content-Type-Options nosniff always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;
    add_header X-Frame-Options DENY always;

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
    }
}
```

Nginx 只代理 `api.furzl.cn`，不要配置 SPA `try_files` 回退；SPA 回退属于前端站点。

## 12. 配置 COS 桶策略

换桶或首次上线时执行一次：

```bash
cd /opt/furry-zjut/backend
source venv/bin/activate
set -a
source /etc/furry-zjut/api.env
set +a
python scripts/setup_cos_cors.py
python scripts/setup_cos_public_read.py
```

COS 桶默认私有，公开内容走 `PUBLIC_ASSET_BASE_URL` 代理域。应用返回的私有缩略图/下载 URL 也使用代理域但不带 COS 签名，因此在代理/CDN 层必须限制 `private/` 的访问；不要把 COS 桶改为整桶公有读来“修复”私有图。

## 13. 上线验证清单

本机检查：

```bash
curl -s http://127.0.0.1:8000/api/v1/health
curl -s http://127.0.0.1:8000/api/v1/ready
```

公网检查：

```bash
curl -s https://api.furzl.cn/api/v1/health
curl -s https://api.furzl.cn/api/v1/ready
```

生产安全项：

```bash
curl -s -o /dev/null -w "%{http_code}" https://api.furzl.cn/openapi.json
curl -s -o /dev/null -w "%{http_code}" https://api.furzl.cn/docs
```

两项在生产环境都应返回 `404`；若返回 `200`，检查 `APP_ENV` 是否为 `production` 并重启服务。

登录链路验证：

```bash
curl -s https://api.furzl.cn/api/v1/captcha/challenge
```

应返回 `{success: true, data: {token, gap_x, gap_y, expires_in}}`。

```bash
curl -s https://api.furzl.cn/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"account":"admin","password":"<WRONG_PASSWORD>"}'
```

缺少 `verification_token` 时应返回 `CAPTCHA_REQUIRED`，而不是账号或密码错误。

## 14. EdgeOne Pages 前端配置

| 配置项 | 填写内容 |
|---|---|
| 生产分支 | `main` |
| 框架预设 | `Vue` |
| 根目录 | `frontend` |
| 输出目录 | `dist` |
| 构建命令 | `npm run build` |
| 安装命令 | `npm ci` |

环境变量：

```dotenv
VITE_API_BASE_URL=https://api.furzl.cn/api/v1
```

EdgeOne Pages 需要开启 SPA 回退：

```text
/*  ->  /index.html
```

## 15. 备份与日常维护

数据库备份：

```bash
mkdir -p /opt/furry-zjut/backups
pg_dump -U furry_app -h 127.0.0.1 -d furry_zjut -Fc -f /opt/furry-zjut/backups/furry_zjut_$(date +%F_%H%M).dump
```

更新后端：

```bash
cd /opt/furry-zjut/backend
git pull origin main
source venv/bin/activate
pip install -e .
alembic -c alembic.ini upgrade head
systemctl restart furry-zjut-api
systemctl status furry-zjut-api
```

回滚：

```bash
cd /opt/furry-zjut/backend
git checkout <PREVIOUS_COMMIT>
source venv/bin/activate
pip install -e .
alembic -c alembic.ini downgrade -1
systemctl restart furry-zjut-api
```

## 16. 常见问题

- `/ready` 返回 `degraded`：检查 Redis 是否监听 `127.0.0.1` 且密码配置正确。
- 前端请求跨域失败：确认后端 `FRONTEND_ORIGINS` 只包含真实前端来源，逗号分隔，无 `*`，无末尾斜杠。
- 私有图片打不开：先核对 `PUBLIC_ASSET_BASE_URL`、代理域回源和 EdgeOne/COS 路径映射；当前应用返回代理域 URL，不带 COS 签名。`PRIVATE_URL_TTL_SECONDS` 仍用于上传凭证等兼容字段，不要把它当作私有展示 URL 的签名期限。
- QQ 登录失败：核对 `QQ_APP_ID`/`QQ_APP_KEY`、QQ 互联登记的回调地址 `https://www.furzl.cn/oauth/qq`、`OAUTH_FRONTEND_BASE_URL`，以及 `FRONTEND_ORIGINS` 是否包含 `https://www.furzl.cn`；后台「第三方登录」总开关和 QQ 子开关也必须打开。
- 登录后新标签页掉线：确认浏览器允许 `api.furzl.cn` 的 `HttpOnly` Cookie，生产使用 HTTPS、`AUTH_COOKIE_SAMESITE=lax`，并检查 CORS 是否允许正式前端来源携带凭据。
- `/docs` 能打开：说明 `APP_ENV` 不是 `production`，重启服务前先修正环境文件。
- 报 Python 事件循环错误：检查是否误用了 Windows 的 `run.py`，Linux 生产按本手册直接用 `uvicorn`。
