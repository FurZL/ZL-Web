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

按架构文档「十七、开发实施顺序」分阶段推进。当前状态：**阶段 1–7 全部完成（认证、图片、个人空间、课表、运营内容、活动系统、动态页面全链路已打通）**。

| 阶段 | 内容 | 状态 |
|---|---|---|
| 1 基础工程 | Vue + FastAPI + PostgreSQL + Alembic + Redis + COS | ✅ 完成 |
| 2 认证安全 | 注册 / 登录 / 审批 / 刷新令牌 / 权限 | ✅ 完成 |
| 3 对象存储 | 预签名直传 + 公开读 + 图片处理（缩略图/展示图） | ✅ 完成 |
| 4 核心业务 | Gallery 公开相册 | ✅ 完成 |
| 4 核心业务 | 个人空间私有相册 | ✅ 完成 |
| 4 核心业务 | 课表解析（ICS/TXT）+ 对比 + 分享 | ✅ 完成（PDF 占位） |
| 5 运营内容 | 社团介绍 / 公告 / 网站设置 / 页脚 | ✅ 完成 |
| 6 活动系统 | 活动 / 报名 / 候补 / 签到 | ✅ 完成 |
| 7 动态页面 | Schema 编辑器 / 发布 / 回滚 | ✅ 完成 |
| 8 上线加固 | WAF / 备份 / 压测 / 安全检查 | ⬜ 未开始 |

### 前端页面设计（已完成）

- 视觉体系：清爽紫罗兰（主色 `#6B5CE7`）+ 玻璃拟态卡片（详见 `DESIGN-BRIEF.md`）。
- 核心页面：首页 / 图片展示（瀑布流+详情+上传弹窗）/ 课表工具 / 个人空间（自己/他人视角）/ 登录 / 注册（含摄影师申请）/ 等待审批 / 找回密码 / 社团介绍 / 404。
- 管理后台界面：侧边栏布局 + 用户审批 + 仪表盘 + 公告管理 + 网站设置 + 活动管理 + 页面管理 + 图片管理（均已接真实接口）。
- 公共组件：`ImageLightbox`（图片详情弹窗，Gallery 与私有相册共用）、`UserAvatar`、`ImagePlaceholder`。
- 导航栏按角色动态变化；窄屏横滑可见全部入口；logo 为「FUR」。
- 顶栏下拉菜单：`Teleport to body` + `fixed` 定位，CSS 三角箭头旋转动画，点击外部自动关闭。
- 首页 Hero：流动渐变背景（12s 往返动画）+ 双按钮（已登录隐藏「加入我们」）。
- 可点击链接（了解故事/查看全部/进入图片展示/去注册）统一圆角矩形控件。

### 视觉规范 — 控件风格

全站控件按**交互意图**分为两种风格，新增组件请根据用途选择对应 class 组合。

#### 1. 选择类控件（半透明 / 主题色减淡）

用于**切换视图、筛选选项、选中态**等不产生数据变更的控件——Tab 标签、筛选按钮、导航选中项、上传入口等。视觉上轻盈、不抢内容。

```html
<!-- 未选中 -->
class="text-sm font-medium text-primary-700 rounded-full px-5 py-2
       bg-primary/5 border border-primary/10 hover:bg-primary/15 transition"

<!-- 选中 -->
class="text-sm font-medium text-primary-700 rounded-full px-5 py-2
       bg-primary/30 border border-primary/30 shadow-glass text-primary-800 transition"
```

| 状态 | 底色 | 边框 | 文字 |
|---|---|---|---|
| 未选中 | `bg-primary/5` | `border-primary/10` | `text-primary-700` |
| 选中 | `bg-primary/30` | `border-primary/30` | `text-primary-800` + `shadow-glass` |

> 玻璃拟态容器（卡片、弹窗、下拉菜单）使用 `.glass-card`（`bg-white/70 backdrop-blur-xl border-white/60`），与选择类控件配合使用。
> 下拉菜单等 Teleport 到 body 的元素，`backdrop-filter` 必须写入 inline style（Tailwind 类在 Teleport + transition 下可能失效）。

#### 2. 操作类控件（实色块）

用于**确认、提交、删除、保存、报名**等产生数据变更或不可逆操作的控件。视觉上明确、有重量感，让用户清楚"点击会执行动作"。

```html
<!-- 主操作（确认/提交/保存） -->
class="btn-primary"  <!-- 实色主题底 + 白字 -->

<!-- 次操作（取消/返回） -->
class="btn-ghost"    <!-- 白底 + 主题色边框 + 主题色文字 -->

<!-- 危险操作（删除/拒绝） -->
class="text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-500 hover:bg-red-50 transition"
```

| 类型 | 样式类 | 用途 |
|---|---|---|
| 主操作 | `btn-primary` | 确认、提交、保存、报名、签到 |
| 次操作 | `btn-ghost` | 取消、返回、上一步 |
| 危险操作 | 红色边框 + 红字 | 删除、拒绝、取消报名 |

> 操作类控件**不使用半透明底色**，始终为实色块，确保用户能清晰区分"选择"和"执行"。

#### 3. 玻璃模糊（容器级背景）

卡片、弹窗、页脚、遮罩等**容器级**元素使用模糊背景，营造深度层次：

```css
background: rgba(255, 255, 255, 0.7);
backdrop-filter: blur(24px);
-webkit-backdrop-filter: blur(24px);
border: 1px solid rgba(255, 255, 255, 0.6);
```

#### 注意事项

- `.topbar` 的模糊背景由 `::before` 伪元素承担（`z-index: -1`），避免 `backdrop-filter` 在导航栏本体创建层叠上下文导致下拉菜单被遮挡。
- 下拉菜单通过 `<Teleport to="body">` + `fixed` 定位脱离顶栏层叠上下文，`z-index: 200`。
- 半透明底色搭配 `backdrop-blur` 使用，避免仅降低透明度导致文字与背景对比度不足。
- **选择类 ≠ 操作类**：筛选按钮可以用半透明，但「确认上传」「立即报名」等必须用实色块。

### 本地联调速查

- 测试账号：管理员 `admin` / `admin123456`（由 `backend/scripts/create_admin.py` 创建）。
- OTP 开发模式：`.env` 中 `OTP_DEV_MODE=true` 时，验证码直接返回在响应的 `dev_code` 字段（不发真实邮件/短信）。
- COS 桶配置脚本：`backend/scripts/setup_cos_cors.py`（CORS）、`setup_cos_public_read.py`（public/ 前缀公有读），换桶后需重跑。
- 本地开发端口：前端 Vite `5173`（strictPort），后端 uvicorn `8000`；注意 5273 等端口可能被 MiMo 主进程占用。

### 已就绪的关键事实

- 数据库：PostgreSQL 已建表（15 张业务表 + `alembic_version`），Alembic 迁移 `0addd5ed14cc` 已到 head。
- 缓存：Redis 已连通（`/api/v1/ready` 返回 `redis: true`）。
- 对象存储：腾讯云 COS 单桶（ap-shanghai，`public/`/`private/` 前缀隔离），CORS + public 读策略已配置，预签名上传/下载全链路实测通过。
- 认证：注册（邮箱/手机 OTP）→ 待审批 → 管理员审批 → 登录/刷新令牌轮换，完整闭环已打通。
- 图片处理：后台 worker 生成缩略图（800px）/展示图（2000px）WebP，含防解压炸弹。
- API：全部业务端点已注册，OpenAPI 可生成（含管理后台 `/admin/users/*`）。
- 测试：`pytest` 23 个用例通过（认证/权限/课表解析与对比/图片处理）。
- 管理后台：用户审批、仪表盘、公告管理、网站设置、活动管理、页面管理、图片管理已接真实接口。

> 图例：✅ 完成　🟡 部分完成　⬜ 未开始

## 变更记录

- **移除 `PUBLIC_API_BASE_URL`**：该环境变量从未被后端或前端代码消费（前端实际使用 `VITE_API_BASE_URL`），属于死配置，已从 `config.py`、`.env.example`、`backend/.env` 中删除。将来如需拼接对外 API 链接（如邮件中的跳转链接），再按实际需求引入。
- **移除前端 `VITE_PUBLIC_ASSET_BASE_URL`**：前端图片 URL 全部来自后端 API 响应的 `thumb_url` / `display_url` 字段（后端已根据 `PUBLIC_ASSET_BASE_URL` 生成完整 URL），前端不需要自己拼图片域名，该变量从未被 `src/` 消费。已从 `frontend/.env.development`、`frontend/.env.production`、`deploy/edgeone/README.md` 中删除。
- **图片域名 `PUBLIC_ASSET_BASE_URL` 仅后端使用**：唯一消费方是 `providers/storage/cos.py` 的 `public_url()`，由后端在 API 响应中生成完整图片 URL。当前值含 `example.com` 时自动回退 COS 默认域名；将来绑定 `img.example.com` 等自定义 CDN 域名时，只需改后端 `.env` 的 `PUBLIC_ASSET_BASE_URL` 一个值，历史图片记录无需变更。
- **Bug 修复：首页精选图片无法加载**：`Home.vue` 的 `ImagePlaceholder` 未传 `:src`，图片只显示文件名占位；已补上 `thumb_url → display_url → url` 三级回退。
- **Bug 修复：图片面板展示描述而非文件名**：后端上传时文件名经 `sanitize_filename()` 清理后以 **base64 编码** 存储（不再明文）；`title` 字段改为 **描述优先 → 兜底"未命名"**。Gallery / Home / Profile 所有面板统一展示图片描述。
- **Bug 修复：标签被描述挤出**：图片卡片布局改为两行结构——描述独占第一行（截断），标签独立第二行（最多 3 个）。
- **Bug 修复：下拉菜单遮挡顶栏 + 模糊失效**：`backdrop-filter` 在 `.topbar` 上创建层叠上下文，下拉菜单无法突破；改为 `::before` 伪元素承担模糊，菜单用 `<Teleport to="body">` + `fixed` 定位脱离层叠，`z-index: 200`。
- **优化：消除刷新页面 401 噪音**：新增 `ensureAccessToken()`，`App.vue` 启动时先静默刷新 access token 再请求 `/auth/me`，不再产生首个 401。
- **优化：Hero 背景流动渐变**：CSS `background-position` 动画循环流动（12s 往返），`prefers-reduced-motion` 下自动停止。
- **UI 统一：圆角矩形控件规范**：导航选中态、上传按钮、登录/注册、Hero 按钮、页面内链接统一套用主题色减淡 `bg-primary/10~15 border-primary/20 rounded-full` 风格；登录后隐藏首页「加入我们」和社团介绍「怎么加入我们」栏目。
- **UI 统一：控件风格规范**（选择类半透明 / 操作类实色块）：所有 Tab/筛选控件（Gallery 标签、Events 筛选、AdminImages、AdminSettings、AdminUsers、AdminLayout）统一为 `bg-primary/5`（未选中）/ `bg-primary/30`（选中）；操作按钮（确认/保存/删除/报名等）保留实色块 `btn-primary`/`btn-ghost`。
- **UI 统一：顶栏导航更新**：新增「活动」入口（所有人可见）；「课表工具」改名「课表」且仅登录后可见；`navLinks` 改为 `computed` 响应式；下拉菜单内外圆角统一 `rounded-xl2`。
- **UI 修复：管理后台侧边栏对齐**：图标固定 `w-5 h-5` 容器居中，选中态套用主题色减淡规范；移动端横滑 Tab 同步统一。
- **视觉规范重写**：README 按交互意图（选择类/操作类/容器级）重写控件风格规范。
- **离线字体 + CDN 回退**：全站字体统一为鸿蒙 HarmonyOS Sans SC（子集化 woff2，15.8MB → 306KB，仅保留项目用到的 803 个字符）。`loader.js` 实现 Google Fonts (Noto Sans SC) 优先加载，失败/超时自动回退本地鸿蒙字体；CSS 字体栈 `Noto Sans SC → HarmonyOS Sans SC → 系统字体`，渲染无感知切换，全程 `font-display: swap` 不白屏。
- **移除多余字体**：删除 Quicksand、站酷快乐体等临时字体，仅保留鸿蒙子集 woff2。
- **下拉菜单修复**：`backdrop-filter` 层叠上下文问题（`::before` 伪元素 + Teleport body）；菜单圆角统一 `rounded-xl2`；CSS 三角箭头旋转动画；点击外部自动关闭。
- **上传图片入口**：移除顶栏「上传图片」按钮，Gallery 页面内保留上传入口。
- **顶栏导航优化**：页面切换按钮改为更紧凑的圆角矩形（`rounded-lg`、13px 字号、`px-3 py-1.5`），选中态加深底色（`bg-primary/40` + `text-primary-900`），按钮间距增大。
- **`docs/API.md` 扩充为完整交接文档**：合并原 WHATAPI 内容，整理全部 74 个 API 接口（认证/图片/课表/活动/公告/页面/管理后台），含认证说明、权限矩阵、前后端函数参考、类型定义。
- **修复全部假功能占位（6 处）**：`DELETE /images/{id}` 真实删除（权限校验+派生图清理）、`POST /images/{id}/report` 真实举报（Report 表+防重复）、`POST /auth/password/reset` 真实更新密码+撤销全部会话、`PUT /profile/me` 真实编辑昵称/简介、`PATCH /admin/users/{id}/role` 真实修改角色（防自改+super_admin 授权限制）、`PATCH /admin/users/{id}/status` 真实启用/禁用（防自改+禁用强制下线）。
- **修复 `await db.delete()` 运行时炸弹（11 处）**：SQLAlchemy 的 `db.delete()` 是同步方法，误加 `await` 会在运行时抛 TypeError；影响 6 个服务文件的全部删除操作（删活动/公告/页面/课表/私有图/图片），之前调用即 500。已全部移除 `await`。
- **修复 N+1 查询**：`admin_events.py` 活动列表对每个活动逐个查报名统计；改为 `GROUP BY` 批量查询（`_batch_counts`），21 次查询 → 2 次。
- **新增 `bio`/`avatar_url` 用户字段**：Alembic 迁移 `0addd5ed14cc`，`GET /profile/me` 返回 bio/avatar_url，`PUT /profile/me` 支持字段级更新；前端 Profile 页新增编辑资料弹窗。

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