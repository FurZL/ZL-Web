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
python run.py                       # Windows 下必须用 run.py（避免 psycopg 事件循环问题）
# 热重载：python run.py --reload
# 生产 Linux 可直接用：uvicorn app.main:app --host 127.0.0.1 --port 8000
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

按架构文档「十七、开发实施顺序」分阶段推进。当前状态：**认证、图片链路、个人空间已完整打通；课表后端解析已通、前端待接；其余模块未开始**。

| 阶段 | 内容 | 状态 |
|---|---|---|
| 1 基础工程 | Vue + FastAPI + PostgreSQL + Alembic + Redis + COS | ✅ 完成 |
| 2 认证安全 | 注册 / 登录 / 审批 / 刷新令牌 / 权限 | ✅ 完成 |
| 3 对象存储 | 预签名直传 + 公开读 + 图片处理（缩略图/展示图） | ✅ 完成 |
| 4 核心业务 | Gallery 公开相册 | ✅ 完成 |
| 4 核心业务 | 个人空间私有相册 | ✅ 完成 |
| 4 核心业务 | 课表解析（ICS/TXT）+ 对比 | 🟡 后端已通，前端待接（PDF 占位） |
| 5 运营内容 | 社团介绍 / 公告 / 网站设置 / 页脚 | ⬜ 未开始（端点占位） |
| 6 活动系统 | 活动 / 报名 / 候补 / 签到 / 通知 | ⬜ 未开始（端点占位） |
| 7 动态页面 | Schema 编辑器 / 发布 / 回滚 | ⬜ 未开始（端点占位） |
| 8 上线加固 | WAF / 备份 / 压测 / 安全检查 | ⬜ 未开始 |

### 前端页面设计（已完成）

- 视觉体系：清爽紫罗兰（主色 `#6B5CE7`）+ 玻璃拟态卡片（详见 `DESIGN-BRIEF.md`）。
- 核心页面：首页 / 图片展示（瀑布流+详情+上传弹窗）/ 课表工具 / 个人空间（自己/他人视角）/ 登录 / 注册（含摄影师申请）/ 等待审批 / 找回密码 / 社团介绍 / 404。
- 管理后台界面：侧边栏布局 + 用户审批 + 仪表盘（已接真实接口）。
- 公共组件：`ImageLightbox`（图片详情弹窗，Gallery 与私有相册共用）、`UserAvatar`、`ImagePlaceholder`。
- 导航栏按角色动态变化；窄屏横滑可见全部入口；logo 为「FUR」。

### 本地联调速查

- 测试账号：管理员 `admin` / `admin123456`（由 `backend/scripts/create_admin.py` 创建）。
- OTP 开发模式：`.env` 中 `OTP_DEV_MODE=true` 时，验证码直接返回在响应的 `dev_code` 字段（不发真实邮件/短信）。
- COS 桶配置脚本：`backend/scripts/setup_cos_cors.py`（CORS）、`setup_cos_public_read.py`（public/ 前缀公有读），换桶后需重跑。
- 本地开发端口：前端 Vite `5173`（strictPort），后端 uvicorn `8000`；注意 5273 等端口可能被 MiMo 主进程占用。

### 已就绪的关键事实

- 数据库：PostgreSQL 已建表（15 张业务表 + `alembic_version`），Alembic 迁移 `131029fbb8f9` 已到 head。
- 缓存：Redis 已连通（`/api/v1/ready` 返回 `redis: true`）。
- 对象存储：腾讯云 COS 单桶（ap-shanghai，`public/`/`private/` 前缀隔离），CORS + public 读策略已配置，预签名上传/下载全链路实测通过。
- 认证：注册（邮箱/手机 OTP）→ 待审批 → 管理员审批 → 登录/刷新令牌轮换，完整闭环已打通。
- 图片处理：后台 worker 生成缩略图（800px）/展示图（2000px）WebP，含防解压炸弹。
- API：全部业务端点已注册，OpenAPI 可生成（含管理后台 `/admin/users/*`）。
- 测试：`pytest` 23 个用例通过（认证/权限/课表解析与对比/图片处理）。
- 管理后台：用户审批、仪表盘已接真实接口，其余模块占位。

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