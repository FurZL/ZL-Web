# 部署说明（EdgeOne Pages + 宝塔 2C2G + PostgreSQL/Redis 本机）

最终部署形态：前端 EdgeOne Pages，API 由宝塔 Nginx 反代至本机 FastAPI（systemd），
PostgreSQL/Redis 本机、仅回环监听，文件走 COS。

详细逐条配置见架构文档的**附录 B（最终部署方案，优先级最高）**。本文件列出关键文件与步骤索引。

## 关键文件

- Nginx API 站点：`deploy/nginx/api.example.com.conf`
- systemd 服务：`deploy/systemd/furry-zjut-api.service`
- EdgeOne Pages：`deploy/edgeone/README.md`
- 备份脚本：`deploy/scripts/backup-furry-zjut.sh`

## 步骤概览

1. 数据库：本机装 PostgreSQL，`listen_addresses='127.0.0.1'`，建库 `furry_zjut` 与最小权限账号 `furry_app`。
2. Redis：本机装 Redis，`bind 127.0.0.1`、认证、`maxmemory 64mb`。
3. 后端：`python3 -m venv venv && ./venv/bin/pip install -r requirements.txt -r requirements-dev.txt` 或 `pip install -e .`；`alembic upgrade head`。
4. 服务：`deploy/systemd/furry-zjut-api.service` 复制到 `/etc/systemd/system/`，`systemctl enable --now furry-zjut-api`。
5. Nginx：宝塔创建 `api.example.com` 站点，反代 `127.0.0.1:8000`，配 TLS。
6. CORS：在 `.env` 的 `FRONTEND_ORIGINS` 配真实前端来源。
7. 前端：`npm run build` 后发布到 EdgeOne Pages，配 SPA fallback 与自定义域名。
8. 备份：`deploy/scripts/backup-furry-zjut.sh` 接 cron，补齐加密与 COS 上传，定期恢复演练。

## 环境变量

见根目录 `.env.example`；生产敏感项由 `/etc/furry-zjut/api.env`（systemd EnvironmentFile）注入，不放 Git。

## 2C2G 资源预算

- FastAPI 1 Worker；SQLAlchemy 连接池 `pool_size=5`、`max_overflow=2`。
- PostgreSQL `shared_buffers=256MB`（起步）；Redis `maxmemory=64mb`。
- 图片/PDF 解析限并发，不进 API 进程做高分辨率转码。

## 上线验收清单

见架构文档附录 B14。