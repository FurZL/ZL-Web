# 浙江理工福瑞圈（Furry ZJUT）

面向浙江理工大学相关 Furry 社群的门户、图片展示、成员空间、课表工具与活动运营平台。

> 本仓库为工程骨架（framework），依据 `ARCHITECTURE-EdgeOnePages-宝塔API-PostgreSQL-Redis部署版.md` 搭建，遵循其中定义的目录结构、分层约定、数据模型与 API 清单。

## 部署边界

- 前端：Vue 3 + TypeScript + Vite，构建后部署至腾讯云 EdgeOne Pages。
- 后端：FastAPI，部署在同一台宝塔 2C2G 服务器，由 Nginx 反向代理 + systemd 管理。
- 数据：PostgreSQL（业务数据）与 Redis（缓存/限流）本机部署，仅监听 `127.0.0.1`。
- 文件：腾讯云 COS 对象存储，通过 Provider 抽象接入，数据库仅存对象 Key 与元数据。
- 本地开发可用 `docker-compose.yml` 启动 PostgreSQL + Redis，生产不使用 Docker。

## 目录结构

```text
furry-zjut/
├── frontend/      # Vue 3 SPA
├── backend/       # FastAPI 模块化单体
├── deploy/        # Nginx / EdgeOne / 脚本 / systemd 配置模板
├── docs/          # API、安全、部署文档
├── .env.example
├── docker-compose.yml   # 仅本地开发
└── README.md
```

## 快速开始（本地开发）

### 1. 启动依赖（PostgreSQL + Redis）

```bash
docker compose up -d
```

### 2. 后端

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate   Linux/macOS: source venv/bin/activate
pip install -e ".[dev]"
cp ../.env.example .env            # 按需修改 DATABASE_URL / REDIS_URL / COS_*
alembic upgrade head
uvicorn app.main:app --reload
```

> 对象存储使用腾讯云 COS（单桶模式，公开与私有内容靠 object_key 的 `public/`、`private/` 前缀隔离）。需在 `.env` 配置 `COS_SECRET_ID` / `COS_SECRET_KEY` / `COS_REGION` / `COS_BUCKET`。未配置时仅影响上传/下载接口，不影响应用启动。

API 文档（仅开发环境）：http://127.0.0.1:8000/docs

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器：http://localhost:5173

## 开发进度

按架构文档「十七、开发实施顺序」分阶段推进。当前状态：**工程骨架已完成、基础设施已跑通，业务端点多为占位实现**。

| 阶段 | 内容 | 状态 |
|---|---|---|
| 1 基础工程 | Vue + FastAPI + PostgreSQL + Alembic + Redis + COS | ✅ 完成 |
| 2 认证安全 | 注册 / 登录 / 审批 / 刷新令牌 / MFA / 限流 | ⬜ 未开始（端点占位） |
| 3 对象存储 | Provider 抽象 + 上传凭证 + 图片处理 | 🟡 抽象与 COS 链路已通，上传端点待实现 |
| 4 核心业务 | Gallery / 个人空间 / 课表解析对比 | 🟡 课表算法已实现并测试，相册端点待实现 |
| 5 运营内容 | 社团介绍 / 公告 / 网站设置 / 页脚 | ⬜ 未开始（端点占位） |
| 6 活动系统 | 活动 / 报名 / 候补 / 签到 / 通知 | ⬜ 未开始（端点占位） |
| 7 动态页面 | Schema 编辑器 / 发布 / 回滚 | ⬜ 未开始（端点占位） |
| 8 上线加固 | WAF / 备份 / 压测 / 安全检查 | ⬜ 未开始 |

### 已就绪的关键事实

- 数据库：PostgreSQL 已建表（15 张业务表 + `alembic_version`），Alembic 迁移 `81c6d451559a` 已到 head。
- 缓存：Redis 已连通（`/api/v1/ready` 返回 `redis: true`）。
- 对象存储：腾讯云 COS 单桶（ap-shanghai），预签名上传/下载全链路实测通过。
- API：51 个路径全部注册，OpenAPI 可生成。
- 测试：`pytest` 11 个用例通过（课表解析/对比 + 权限矩阵）。

> 图例：✅ 完成　🟡 部分完成　⬜ 未开始

## 分层约定

- Router：只处理 HTTP 层（参数、认证依赖、响应码）。
- Service：业务规则。
- Provider：对象存储、邮件、短信、验证码等外部服务。
- Model：数据库实体；Schema：API 输入输出；二者不混用。

## 环境划分

- `development`：本地开发，用 Docker 起 PostgreSQL/Redis。
- `staging`：预发布，独立数据库、Bucket、域名。
- `production`：生产，独立密钥与第三方服务。

生产部署详见 `docs/DEPLOYMENT.md` 与 `deploy/`。