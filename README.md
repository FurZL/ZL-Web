# 浙江理工福瑞圈（Furry ZSTU）

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
├── docs/          # API、文件索引、安全、部署文档
├── AGENTS.md      # 项目架构与实施规范
├── DESIGN-BRIEF.md # 页面设计说明书
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
python scripts/create_admin.py admin admin123456 --reset-password
python run.py                       # Windows 下必须用 run.py（避免 psycopg 事件循环问题）
# 开发环境监听所有接口：python run.py --host 0.0.0.0
# 热重载：python run.py --reload
# 生产 Linux 可直接用：uvicorn app.main:app --host 127.0.0.1 --port 8000
```

> 对象存储使用腾讯云 COS（单桶模式，公开与私有内容靠 object_key 的 `public/`、`private/` 前缀隔离）。需在 `.env` 配置 `COS_SECRET_ID` / `COS_SECRET_KEY` / `COS_REGION` / `COS_BUCKET`。未配置时仅影响上传/下载接口，不影响应用启动。

API 文档（仅开发环境）：http://127.0.0.1:8000/docs

生产环境将 `APP_ENV=production`：后端会同时关闭 `/docs`、`/redoc`、`/openapi.json`。

### 3. 前端

```bash
cd frontend
npm install
npm run dev
```

前端开发服务器：http://localhost:5173

## 登录保持（7 天滑动会话）

- Access Token 默认 15 分钟有效，仅保存在前端内存；Refresh Token 默认 7 天，由后端写入 `HttpOnly` Cookie，跨标签页共享。
- 新标签页打开时，前端用 Cookie 静默刷新 Access Token；7 天内每活动一次，会话窗口就顺延一次。超过 7 天未访问则 Refresh Token 过期，需要重新登录。
- Cookie 默认 `SameSite=Lax`，生产环境自动 `Secure`；通过 `REFRESH_TOKEN_TTL_DAYS` 调整有效期，通过 `AUTH_COOKIE_NAME`/`AUTH_COOKIE_SAMESITE` 调整 Cookie 行为。

## 第三方登录、法律页面与图片代理

- QQ 登录采用「后端生成授权地址 → QQ 回调前端 `/oauth/qq` → 前端携带 `code/state` 调后端换取登录态」流程。登录、发起绑定和绑定已有账号都要先通过滑块拼图验证。
- 已绑定 QQ 直接登录；未绑定 QQ 进入绑定页，用已审批的本站账号密码完成绑定并登录；已登录用户可在个人主页绑定或解绑 QQ。
- 后台「网站设置 → 第三方登录」提供总开关与 QQ 子开关。QQ 的 App ID / App Key 只放后端环境变量，不写入 `site_settings`。
- 注册必须分别勾选《用户协议》和《隐私政策》。后端记录协议版本与同意时间；用户协议和隐私政策包含第三方服务清单、官方隐私政策链接、违法信息处置及依法配合有权机关的条款。
- 用户图片的展示、私有缩略图和下载都走 `PUBLIC_ASSET_BASE_URL` 代理域；COS 原生预签名地址只用于浏览器上传直传，不返回给展示/下载接口。

| 项目 | 本地开发 | 生产/上线 |
|---|---|---|
| 前端 SPA | `http://localhost:5173`（Vite strictPort） | `https://www.furzl.cn` |
| 后端 API | `http://127.0.0.1:8000` | Nginx 反代至 `127.0.0.1:8000` |
| API 前缀 | `/api/v1` | `/api/v1` |
| QQ 前端回调 | `/oauth/qq` | `https://www.furzl.cn/oauth/qq` |
| 用户协议 | `/legal/terms` | `https://www.furzl.cn/legal/terms` |
| 隐私政策 | `/legal/privacy` | `https://www.furzl.cn/legal/privacy` |
| 版权声明 | `/legal/copyright` | `https://www.furzl.cn/legal/copyright` |
| 联系我们 | `/legal/contact` | `https://www.furzl.cn/legal/contact` |
| 联系邮箱 | `contact@furzl.cn` | `contact@furzl.cn` |

### 本次变更总览（2026-11-19）

| 类别 | 新增 | 修改/替换 | 删除或废弃 |
|---|---|---|---|
| 认证 | 7 天 HttpOnly Refresh Cookie；跨标签页会话恢复；协议同意字段与落库记录 | Access Token 仍为 15 分钟内存令牌；刷新令牌有效期由 14 天改 7 天 | 前端不再把 Refresh Token 写入 `sessionStorage` |
| 第三方登录 | QQ Provider、OAuth 端点、绑定表、登录/绑定页面、后台开关 | 登录页增加 QQ 入口，个人主页增加账号绑定区 | 无已上线的第三方登录方案可迁移 |
| 图片 | 代理域统一承载公开图、私有缩略图和下载 | `presign_download → public_url`；测试如实断言代理域 | 展示/下载不再返回 COS 原生预签名 URL |
| 数据 | `user_third_parties` 表；`users` 协议版本/同意时间字段 | 迁移链新增 `e7f3a91b2d44`、`2b7e4c9d1a60`，当时 head 为 `2b7e4c9d1a60`（后续已推进到 `a7d2e9c14b83`） | 无表或字段删除 |
| 页面 | `/oauth/qq`、`/legal/:slug`、四个法律页面、页脚链接回退 | 注册页协议勾选；登录页 QQ 登录；个人主页绑定；后台设置新增第三方登录 Tab | 无页面删除 |
| API | 5 个 QQ/OAuth 端点、2 个个人绑定端点、1 个后台 OAuth 测试端点 | 登录/刷新/登出改用 Cookie；注册和图片/主页响应调整 | 没有删除路由；旧登录客户端契约不再兼容 |
| 配置 | `AUTH_COOKIE_NAME`、`AUTH_COOKIE_SAMESITE`、`OAUTH_FRONTEND_BASE_URL`、`QQ_APP_ID`、`QQ_APP_KEY`、`QQ_REDIRECT_URI` | `REFRESH_TOKEN_TTL_DAYS` 默认 14 → 7；法律默认值和页脚默认值补齐 | 未新增数据库端口；Redis 仍为 `6379`，PostgreSQL 仍为 `5432` |

## 开发进度

按架构文档「十七、开发实施顺序」分阶段推进。当前状态：**阶段 1–7 全部完成（认证、图片、个人空间、课表、运营内容、活动系统、动态页面全链路已打通）**。管理员初始化脚本已支持幂等执行、账号激活和显式密码重置。

| 阶段 | 内容 | 状态 |
|---|---|---|
| 1 基础工程 | Vue + FastAPI + PostgreSQL + Alembic + Redis + COS | ✅ 完成 |
| 2 认证安全 | 注册 / 登录 / 审批 / 刷新令牌 / 权限 / 人机验证 / 阿里云短信 | ✅ 完成 |
| 3 对象存储 | 预签名直传 + 公开读 + 图片处理（缩略图/展示图） | ✅ 完成 |
| 4 核心业务 | Gallery 公开相册 | ✅ 完成 |
| 4 核心业务 | 个人空间私有相册 | ✅ 完成 |
| 4 扩展功能 | 个人主页编辑器 / 草稿发布 / 主题 / 素材 / 访客主页 | ✅ 前后端接口已接通 |
| 4 核心业务 | 课表解析（ICS/TXT/PDF）+ 网格编辑（拖动/拉伸/内嵌加节/时段边界）+ 课表架（命名/存档/排序）+ 群组对比（邀请码/审批/逐人忙闲）+ 网格点选空闲格约时间 + 个人日程 + 按周对比 + 消息铃铛 + 分享 | ✅ 已支持日期日程与固定时间约定；PDF 预览导入、持久群组已支持；旧约饭后端保留但页面不再提供发起入口；群体约饭未实现 |
| 5 运营内容 | 社团介绍 / 公告 / 网站设置 / 页脚 | ✅ 完成 |
| 6 活动系统 | 活动 / 报名 / 候补 / 签到 | ✅ 完成 |
| 7 动态页面 | Schema 编辑器 / 发布 / 回滚 | ✅ 完成 |
| 8 上线加固 | WAF / 备份 / 压测 / 安全检查 | ⬜ 未开始 |

### 历史分支进度：个人主页客制化初版（截至 2026-11-13，已由后续补齐）

- 新增 `/profile/me/edit` 编辑器：8 种模块、12 栅格布局、拖拽/按钮排序、复制/删除、撤销/重做、主题预设和预览。自定义 HTML 点击后在 `sandbox="allow-scripts"` 的 iframe 中运行，配套 CSP 限制资源加载。
- 后端已实现 `GET/PUT /api/v1/profile/me/layout` 与 `PATCH /api/v1/profile/me/images/{image_id}`：布局草稿持久化、白名单校验、图片归属与展示授权校验、代理域素材 URL。默认最多 16 个模块，可通过 `PROFILE_LAYOUT_MAX_BLOCKS` 调整。
- 数据库新增 `profile_layouts` 表和 `profile_images.is_displayable`（默认 `false`），对应迁移 `4f8a2c7d91b3`；后续又新增 QQ 绑定表与用户协议同意字段。拉取本分支后先在后端执行 `alembic upgrade head`；截至本节时 head 为 `2b7e4c9d1a60`，现已推进到 `e9b2f7c4a1d0`。
- 前端当时已预留发布、丢弃草稿、主题保存、素材清单和访客主页的调用；这 5 个后端接口在 2026-11-13 尚未实现，已于 2026-11-15 补齐（见下节）。
- **当时的限制（已解决）**：真实后端模式下，“保存草稿”曾先保存布局再请求主题接口，可能提示失败但布局已落库；发布、丢弃、主题持久化、素材选择及访客主页当时尚未形成完整真实链路，2026-11-15 后已接通。
- 登录态恢复改为共享 `bootstrapAuth()`：直接打开或刷新需要登录的页面时，路由守卫先等待会话恢复。API 客户端增加业务错误信封的消息提取。
- 当时已验证：前端 `npm run build` 通过；后端 `pytest` **30 passed**（原有 23 + 新增 7）；新增后端模块及相关配置/模型的定向 Ruff 检查通过。真实 API 验证了布局读取 200、非法布局 422、不存在图片 404 和匿名访问 401；浏览器验证编辑器直链访问及刷新恢复登录态正常。图片存储真实读写与完整发布链路未在本轮验证。
- 本节反映 2026-11-13 当日状态；当时未实现的发布、丢弃、主题、素材清单和公开主页接口已于 2026-11-15 补齐，见下节。

### 本分支进度：个人主页后端链路补齐（2026-11-15）

- 补齐 `POST /profile/me/layout/publish`、`POST /profile/me/layout/discard`、`PUT /profile/me/theme`、`GET /profile/me/media`、匿名 `GET /profile/{username}/page`。发布时重新校验模块和图片授权；主题颜色、枚举、背景模糊度与素材归属均由后端校验。
- 公开主页仅对 active 用户且已发布、公开的页面返回；不存在、未发布、隐藏或未启用统一返回 404。公开响应不含用户 UUID、邮箱和手机号，图片媒体映射再次检查本人前缀与 `is_displayable`。
- 前端社团成员头像悬停放大并可点击进入成员主页；本人主页公开并发布后可复制分享链接。前端通过既有 `/profile/members`、`/profile/me/layout` 和 `/profile/{username}/page` API 工作，本次没有新增后端接口。
- 主页数据卡在前台每分钟重读现有接口；“公开照片”只统计本人审核通过且公开的图库图片，不包含私有相册或待审核图片。
- 无新增数据库迁移。验证：后端 `pytest -q -p no:cacheprovider` **48 passed**；相关 Ruff 检查通过。路由测试使用替身数据库与对象存储，未验证真实 COS 读写。

开发演示：在 `frontend/.env.profile-mock` 中写入以下内容，再执行 `npm run dev:mock`。该文件是本地配置，需自行创建；普通 `npm run dev` 默认调用真实后端，mock 插件仅作用于开发服务器。

```dotenv
VITE_API_BASE_URL=/api/v1
VITE_PROFILE_MOCK=1
```

mock 会拦截个人主页及会话恢复接口，数据仅驻留 Vite 进程内。演示会话可在该站点浏览器控制台执行 `localStorage.setItem('auth_session', '1')`，刷新后打开 `/profile/me/edit`；结束演示时清除此项并重启普通开发服务。

### 本分支进度：注册配置、邮件通知与验证码体验（2026-11-15）

- 后台「网站设置」新增「注册设置」Tab：`registration_enabled` / `require_email_verification` / `require_phone_verification` 三个开关；`GET /site/public-config` 输出 `registration_config`，前端顶栏、登录页、注册页实时联动。
- 注册接口增加后端强制门控：关闭注册时返回 403；关闭邮箱或手机验证时跳过对应 OTP 校验。注册页同步隐藏对应表单项，登录页/顶栏在关闭注册时隐藏注册入口。
- 密码策略升级：注册和找回密码都要求两次输入一致，且密码必须同时包含大小写字母和数字；后端 `RegisterRequest`/`PasswordResetRequest` 有 Pydantic 校验，前端表单也做即时提示。
- 注册表单补充用户名/昵称/密码长度、邮箱格式、验证码位数等提交前校验；API 客户端会将 FastAPI 422 字段错误转换成带字段名的中文提示，避免页面只显示 `Request failed with status code 422`。具体触发字段需依据实际响应确认；本次未新增或修改后端接口。
- 邮箱/手机验证码增加 60 秒发送冷却，后端返回 `COOLDOWN` 错误，前端两个验证码按钮独立倒计时禁用。
- 新增 `SmtpEmailProvider` 接入飞书企业邮箱 SMTP（`EMAIL_PROVIDER=smtp` + `SMTP_*`），发件名跟随 `APP_NAME`；注册提交发「等待审批」，管理员审批通过/拒绝分别发结果通知，邮件发送失败不阻塞注册或审批。
- `About.vue` 社团介绍成员列表修复头像展示：有 `avatar_url` 显示头像，没有则回退首字母。
- 新增 `COS_DEV_PREFIX` 多人开发隔离，后端 `CosStorageProvider` 与 COS 交互时透明追加前缀；`.env` 使用当前时间戳前缀。
- `backend/run.py` 支持 `--host` 参数，便于开发环境监听 `0.0.0.0`。

### 前端页面设计（已完成）

- 视觉体系：清爽紫罗兰（主色 `#6B5CE7`）+ 玻璃拟态卡片（详见 `DESIGN-BRIEF.md`）。
- 核心页面：首页 / 图片展示（瀑布流+详情+上传弹窗）/ 活动列表（报名/签到/候补）/ 课表 / 个人空间（自己/他人视角）/ 登录 / 注册（含摄影师申请）/ 等待审批 / 找回密码 / 社团介绍 / 动态页面（`/p/:slug`）/ 404。
- 管理后台界面：侧边栏布局 + 用户审批 + 仪表盘 + 公告管理 + 网站设置 + 活动管理 + 页面管理 + 图片管理（均已接真实接口）。
- 公共组件：`ImageLightbox`（图片详情弹窗，Gallery 与私有相册共用）、`UserAvatar`、`ImagePlaceholder`、`AppDialog`（全局 Toast/Confirm 对话框）。
- 导航栏按角色动态变化；桌面显示横向导航，移动端与窄屏使用右侧抽屉菜单（含主导航、账号入口、登录/注册或退出登录）；顶栏、页脚与登录页品牌位使用 M 形 logo。
- 移动端表单控件统一使用至少 16px 字号，避免 iOS Safari 聚焦输入框时自动放大页面；滑块验证码弹窗自适应窄屏、打开时主动收起软键盘，并支持触摸拖动。
- SEO 基础设施：构建时生成 `/sitemap.xml` 与 `/robots.txt`，只收录公开静态页面；站点地址可用 `SITE_URL` 覆盖，EdgeOne 需确保这两个文件不被 SPA fallback 覆盖。
- 站点图标：浏览器 favicon / iOS 主屏 / PWA 使用蓝绿 M 形 logo 生成的一套静态资源（见 `frontend/public/favicon.ico` 等）。
- 顶栏账号菜单：`Teleport to body` + `fixed` 定位，CSS 三角箭头旋转动画，点击外部自动关闭；`lg` 以下切换为右侧抽屉，支持遮罩关闭、Esc 关闭、路由切换自动关闭和背景滚动锁定。
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

#### 4. 全局对话框（Toast / Confirm）

替代原生 `alert()` / `confirm()`，全站统一使用 `useDialog` 组合式函数：

```ts
import { useDialog } from '@/composables/useDialog'
const { showToast, showConfirm } = useDialog()

showToast('操作成功')                            // 轻量提示，3 秒自动消失
if (await showConfirm('确定删除吗？')) { ... }    // 确认弹窗，返回 Promise<boolean>
```

| 组件 | 用途 | 视觉 |
|---|---|---|
| **Toast** | 错误/成功提示 | 深色底（`bg-ink`）、白色文字、`rounded-xl2`、顶部滑入，3 秒消失 |
| **Confirm** | 确认/取消操作 | 玻璃卡片弹窗（`glass-card`）、半透明遮罩（`bg-black/40`）、按钮用 `btn-primary`/`btn-ghost` |

UI 组件在 `components/AppDialog.vue`，挂载在 `App.vue` 根部，无需每个页面单独引入。

#### 5. 复用样式类（`main.css` 通用组件类）

全站高频 UI 模式统一定义为 `@layer components` 类，**禁止在 `.vue` 中重复拼写内联 class**：

| 类名 | 用途 | 样式摘要 |
|---|---|---|
| `.glass-card` | 玻璃拟态卡片/弹窗容器 | `bg-white/70 backdrop-blur-xl border-white/60 rounded-xl2` |
| `.dialog-overlay` | 弹窗半透明遮罩 | `fixed inset-0 z-50 bg-black/40`，配合 `flex items-center justify-center p-4` |
| `.spinner` | 加载中旋转指示 | `border-primary-200 border-t-primary rounded-full animate-spin` |
| `.btn-primary` / `.btn-ghost` | 主/次操作按钮（实色块） | 见「操作类控件」 |
| `.btn-sm` / `.btn-sm-danger` / `.btn-sm-primary` / `.btn-sm-success` / `.btn-sm-warning` | 小操作按钮（`text-xs`） | `rounded-lg border` + 语义色 |
| `.btn-xs` / `.btn-xs-danger` / `.btn-xs-success` / `.btn-xs-warning` | 超小操作按钮（`text-[11px]`） | 同上，更紧凑 |
| `.tag-badge` / `.tag-badge-sm` / `.tag-badge-lg` | 标签徽章（3 种尺寸） | `text-primary-700 bg-primary-50 rounded-full` |
| `.status-badge` | 状态徽章外框 | `text-xs font-medium rounded-full px-2.5 py-0.5`，配色由 `statusStyles.ts` 决定 |
| `.input` / `.label` | 表单输入/标签 | 统一焦点态与间距 |

**状态徽章配色**统一定义在 `utils/statusStyles.ts`，各组件直接 `import`：

| 常量 | 用途 | 示例 |
|---|---|---|
| `MODERATION_STATUS` | 图片审核状态 | pending / approved / rejected |
| `EVENT_STATUS` | 活动状态 | draft / published / cancelled |
| `PAGE_STATUS` | 页面状态 | draft / published / archived |
| `REG_STATUS` | 报名状态 | registered / waitlisted / cancelled / checked_in |
| `ANNOUNCEMENT_STATUS` | 公告状态 | draft / published / expired |

> **规则**：弹窗遮罩 → `.dialog-overlay`；加载动画 → `.spinner`；操作按钮 → `.btn-sm*` / `.btn-xs*`；标签 → `.tag-badge*`；状态色 → `statusStyles.ts`。新增 UI 先检查是否已有对应类，避免重复拼写。


#### 注意事项

- `.topbar` 的模糊背景由 `::before` 伪元素承担（`z-index: -1`），避免 `backdrop-filter` 在导航栏本体创建层叠上下文导致下拉菜单被遮挡。
- 下拉菜单通过 `<Teleport to="body">` + `fixed` 定位脱离顶栏层叠上下文，`z-index: 200`。
- 半透明底色搭配 `backdrop-blur` 使用，避免仅降低透明度导致文字与背景对比度不足。
- **选择类 ≠ 操作类**：筛选按钮可以用半透明，但「确认上传」「立即报名」等必须用实色块。

### 本地联调速查

- 本地初始化管理员：`python scripts/create_admin.py admin admin123456 --reset-password`。账号已存在时，只有显式追加 `--reset-password` 才会重置密码；生产环境请改用随机强密码。
- OTP 开发模式：`.env` 中 `OTP_DEV_MODE=true` 时验证码直接返回在 `dev_code` 字段（不发真实邮件/短信）；`OTP_DEV_MODE=false` 时走 SMTP 真实发信（需配置 `SMTP_HOST` 等）。
- 邮件：.env 配置 EMAIL_PROVIDER=smtp + SMTP_HOST/PORT/USER/PASSWORD/FROM 接入飞书企业邮箱；OTP_DEV_MODE=false 开启真实发信。
- COS 多人隔离：.env 设 COS_DEV_PREFIX=dev-你的标识-时间戳 避免共用测试桶时文件冲突；生产留空。
- COS 桶配置脚本：`backend/scripts/setup_cos_cors.py`（CORS）、`setup_cos_public_read.py`（public/ 前缀公有读），换桶后需重跑。
- 本地开发端口：前端 Vite `5173`（strictPort），后端 uvicorn `8000`；注意 5273 等端口可能被 MiMo 主进程占用。

### 已就绪的关键事实

- 数据库：个人主页布局表、QQ 账号绑定表、用户协议同意字段和课表群组表均已落库；Alembic 当前 head 为 `a7d2e9c14b83`（课表群组），迁移链为 `81c6d451559a → 9394e2a89de2 → 64b8838cd73c → 131029fbb8f9 → 0addd5ed14cc → 4f8a2c7d91b3 → e7f3a91b2d44 → 2b7e4c9d1a60 → af1c280b769e（汇合 7b3d1c8a4f20）→ c4a91e7d2b60 → e9b2f7c4a1d0 → a7d2e9c14b83`。
- 缓存：本地 Redis 已连通；2026-11-19 验证 `/api/v1/ready` 返回 `{"status":"ready","redis":true}`。验证码、限流与 QQ OAuth state 都依赖 Redis，部署时必须先确认该接口。
- 对象存储：腾讯云 COS 单桶（`public/`/`private/` 前缀隔离），CORS 与 public 读策略已配置；浏览器上传使用预签名直传，展示/下载改为代理域 URL。
- 认证：注册（邮箱/手机 OTP）→ 待审批 → 管理员审批 → 登录/刷新令牌轮换，完整闭环已打通。
- 图片处理：后台 worker 生成缩略图（800px）/展示图（2000px）WebP，含防解压炸弹。
- API：当前代码 OpenAPI 注册 117 个路径 / 139 个方法端点，包含日期日程与一对一约饭、课表对比页直接约时间、课表架重命名/存档/拖动排序、PDF 课表预览、课表群组（创建/邀请码/审批/共享课表/逐人忙闲）、人机验证滑块、个人主页发布/丢弃/主题/素材、匿名公开页、QQ 登录/绑定及 OAuth Provider 测试接口。
- 测试：`pytest -q -p no:cacheprovider` 默认 88 passed / 3 skipped（未启用本机 PostgreSQL 约饭/约定/群组事务测试时）；设置 `MEAL_TEST_LOCAL_DB=1` 后 91 passed，覆盖个人主页、课表编辑、课表架命名/存档/排序、PDF 单元格与跨页解析、时段边界，以及群组创建/邀请码加入/审批/共享课表/权限、逐人忙闲统计和对比页固定时间约定。前端生产构建通过。
- 管理后台：用户审批、仪表盘、公告管理、网站设置、活动管理、页面管理、图片管理已接真实接口。
- 管理员初始化：`backend/scripts/create_admin.py` 已合并到 `main`；账号已存在时默认不覆盖密码，使用 `--reset-password` 才会显式重置，并自动确保管理员角色和启用状态。
- QQ 第三方登录：登录页与个人主页绑定均先通过滑块拼图验证，回调统一落回 `https://www.furzl.cn/oauth/qq`；后台「网站设置 → 第三方登录」控制登录入口开关，`QQ_APP_ID` / `QQ_APP_KEY` 只从后端环境变量读取。

> 图例：✅ 完成　🟡 部分完成　⬜ 未开始

## 课表怎么对比与约时间

登录后打开「课表」。周网格表头会显示当前查看周的星期和日期，全学期视图按当前教学周标注日期。课表架保存每一学期的课表，可随时命名、切换或把旧课表存档到历史，拖动卡片可调整课表架顺序；课程和按节次重复的安排放在周课表；一次性的班会、看诊或约定放在「我的日程」。周网格底部可直接添加一节；鼠标或触控笔拖动课程卡片可换星期/节次，拖卡片底部可调整结束节次，保存后立即生效。作息设置里可以调整上午/中午/下午/晚上的时间边界，网格分段随之更新。

想和一群同学互相看忙闲：在「寻找搭子」页创建群组或输入邀请码加入，成员各选一份课表共享给群，群组页逐个显示你们俩的共同空闲/共同忙碌等统计；点成员可进入双人周课表。群主可设审批、移除成员或解散群组，成员可随时切换共享的课表或退群。

在对比结果页，周网格会显示双方忙闲和同教室格子；课程按双方占用合并成一块共享块，左侧紫色表示我、右侧粉色表示对方，同一门课只显示一次。鼠标悬停或触屏点按某一列表头，整列会浮起绿框。把鼠标移到绿色空闲格上会出现「邀约名称 / 参与人 / 邀请」浮窗；按住空闲格拖动可以自由选择连续节次，松手后浮窗显示拖出的时间段（单击则选 1 节），改好名称后点「邀请」发给对方。对方在课表网格里点邀请卡片接受后，双方「我的日程」会同时写入这个约定。自己发出的邀请不会在自己的铃铛/课表里冒充新通知。全学期视图不自动猜日期，需要先在网格上方选一个具体周次。

约饭后端接口仍保留，但课表页已不再提供发起约饭的表单；日常找搭子优先使用群组对比和对比页的固定时间约定。

### 教务系统课表辅助导入

Edge / Chrome 可加载仓库中的 `browser-extension/` 扩展。用户在学校教务系统登录并打开个人课表后，点击扩展“重新读取课表”才授权本次读取；扩展显示课程预览，发送到本站后再次预览，确认后以私有课表保存。扩展不读取账号密码或 Cookie。安装步骤、权限范围和兼容字段见 [browser-extension/README.md](browser-extension/README.md)。教务实际响应结构需要在已登录浏览器中验收；无法识别时可继续上传 ICS / TXT / PDF。PDF 会在本站先解析成预览，确认后才保存，原文件不落库。

## 变更记录

- **2026-11-25：对比页第二版——合并课程块 + 紧凑周次条**：对比网格不再左右各画一张课程卡，而是按双方占用合并成一块共享块：左侧紫条/右侧粉条表示人，同一门课只显示一次，双方课程不同时补一行「TA · …」；同教室点直接落到合并块右上角。周次选择压缩成一行「‹ / 全学期下拉 / ›」，不再占一条大横幅。桌面/触屏邀约冒烟和全部既有冒烟通过。

- **2026-11-25：对比页视觉减法（第一版）**：去掉顶部三张大统计卡，改成一行「共同空闲 N 段 · 同教室 N 节 · 冲突 N 处」小标签；对比课表压低课程卡饱和度，改成低饱和底色 + 左侧紫色/右侧粉色细色条，并隐藏地点/周次等次要字段，完整信息保留在卡片 title 里；空闲格扁平化、去掉逐格重边框；同教室从整块琥珀底改成右下角小圆点；绿框和阴影减弱。拖动选时间、邀约浮窗、通知等交互不变。视觉截图见 `.local-dev/redesign-compare-rich.png`；全部 UI 冒烟通过。

- **2026-11-25：空闲格支持拖动自由选择**：在对比周网格里按住绿色空闲格向下/向上拖动，会实时高亮连续空闲段；松手后二级邀约浮窗显示拖出的范围（如第 1-4 节），可编辑名称再发送。单击只选 1 节，不再固定按 2 节拆分；拖到非空闲格会自动截断，不能跨越忙碌格。`meetup-ui-smoke.cjs` 从第 1 节拖到第 4 节，断言浮窗“第 1-4 节”、请求也只发 1-4 节。

- **2026-11-25：邀约时段按 2 节拆分**（最初的固定小段规则，后续已被拖动自由选择取代）：点击空闲格不再把整段连续空闲（例如周六第 1–12 节）一次邀请出去，而是按空闲段起点每 2 节拆成一小段，浮窗显示并发送该小段；奇数长度末尾保留 1 节，单节空闲仍为 1 节。`meetup-ui-smoke.cjs` 用 1–12 节空闲段验证点击第 5 节时浮窗显示“第 5-6 节”、请求也只发 5-6 节。

- **2026-11-25：修复邀请自通知/重复发送，并加邀约二级窗口**：铃铛和课表网格现在只统计/显示“别人邀请我”的待处理约定，自己发出的邀请不再给自己红点或卡片；后端对同一发起人、同一参与人、同一固定时间在 pending/confirmed 状态重复发送返回 409 `INVITATION_EXISTS`，前端在等待对方接受时禁用继续点格。对比页空闲格新增二级浮窗：鼠标悬停显示「邀约名称」「参与人」「邀请」按钮，点按格子固定浮窗后可编辑名称并发送；点击后不再立即发送。`meetup-ui-smoke.cjs` 与 `meetup-touch-ui-smoke.cjs` 覆盖悬停/固定浮窗、自定义名称和防重复；所有既有冒烟 PASS。

- **2026-11-25：修复选中列后表头错位/最后一天消失**：列高亮浮框作为跨行网格项插入后，星期表头原本靠自动排布，被浮框占位挤到下一列，导致标题整体错位、周日超出网格。现在给左上角、7 个星期表头显式设置 `grid-column/grid-row`，浮框不再影响表头排布；`meetup-ui-smoke.cjs` 增加“选中列后仍有 7 个正确顺序的表头”断言。

- **2026-11-25：推荐时段与同教室列表整合进周网格**：删除对比页底部的「推荐空闲时段」「同教室时段」「同时忙碌」三张列表卡；周网格现在支持鼠标悬停或触屏点按表头选中整列，绿色浮框带动画框住该列；点绿色空闲格直接发出固定时间约定，选中列后同教室仍以网格内琥珀色标记。约定周次选择和邀请状态移到网格上方。`meetup-ui-smoke.cjs` 与 `meetup-touch-ui-smoke.cjs` 覆盖列框选和点格发起；所有既有冒烟 PASS。

- **2026-11-25：移除约饭大面板，邀请进课表、头像旁加铃铛**：删除课表页“约饭与约定邀请”面板、发起约饭表单和多候选确认 UI；固定时间约定的通知改为课表网格里的虚线邀请卡片，点卡片打开接受/婉拒对话框，接受后自动写双方日程。顶部头像旁新增消息铃铛：有未读公告或待处理邀请时显示红点，点开列出待处理邀请入口和最新公告。约饭后端接口保留，页面不再提供入口。`meetup-invitee-ui-smoke.cjs` 覆盖网格邀请卡片与接受，`bell-ui-smoke.cjs` 覆盖公告/邀请红点和通知面板；所有既有 UI 冒烟继续 PASS。

- **2026-11-25：周网格表头显示日期**：周一–周日下方新增 `M/D` 日期；切到具体周次显示该周日期，全学期视图按当前教学周显示并在左上角标注“第 N 周”；没有填写学期第一周周一时隐藏日期。`dates-ui-smoke.cjs` PASS；所有既有 UI 冒烟仍 PASS。

- **2026-11-25：推荐空闲时段可直接约成日程**（最早的列表按钮形式，后续已整合进周网格）：对比结果页的“推荐空闲时段”现在每行可点「邀请 TA」；全学期视图先选一个具体周次，系统把该周、星期和节次换算成北京时间，向对方发出固定时间约定。对方在课表网格里点邀请卡片接受，同一事务把约定写入双方「我的日程」；拒绝/取消不写；取消已确认约定会同步移除双方日程。新增 `POST /schedule/appointments/fixed`，复用现有邀请表与冲突复核，不新增表、不改迁移。`meetup-ui-smoke.cjs` 与被邀请方 `meetup-invitee-ui-smoke.cjs` 覆盖选择、发起、接受和状态刷新；后端本机 DB 全量 91 passed。

- **2026-11-25：课表群组对比**：课表页新增“群组对比”。创建私密群组或用 8 位邀请码加入，群主可要求审批、同意/拒绝申请、移除成员、解散群组；成员各自选择一份自己的课表共享给群（个人日程只显示占用，不显示名称/地点）。群组页以“我”为基准，逐个成员显示共同空闲、共同忙碌、你忙 TA 空、TA 忙你空和同教室节数，点成员进入现有双人周课表对比；按设计不做全组共同空闲。新增 `schedule_groups`、`schedule_group_members` 表和 7 个群组路径 / 10 个方法（迁移 `a7d2e9c14b83`）；`group-ui-smoke.cjs` 覆盖创建群组、共享课表、逐人统计和进入对比；后端本机 DB 全量 90 passed。

- **2026-11-24：课表时段边界可调**：作息设置新增“上午结束 / 中午开始、中午结束 / 下午开始、下午结束 / 晚上开始”三个时间，课表按每节课开始时间自动归入上午、中午、下午、晚上；默认 12:00 / 14:00 / 18:00，旧课表缺少该字段时自动补默认。仍通过 `PUT /schedule/{schedule_id}/timing` 保存，没有数据库迁移；`segment-ui-smoke.cjs` 覆盖保存、网格分段变化、重新打开回显和乱序边界拦截；后端全量 87 passed / 1 skipped。

- **2026-11-24：PDF 课表导入**：课表页可选择/拖入教务打印的 PDF，后端用 `pdfplumber` 解析文字层表格，支持同格多课、合并节次、跨页续接（第 2 页 10–12 节详情与上一页课程名拼接）；先返回预览，用户确认后才以私有课表保存。原始 PDF 只在内存解析，不写对象存储、不记录原文，页眉姓名/学号不入库；PDF 只有节次没有具体时间，预览时仍用默认 12 节作息，用户可在作息设置里核对。新增 `POST /schedule/pdf-preview` 与 `pdfplumber` / `python-multipart` 依赖；`pdf-ui-smoke.cjs` 覆盖文件选择、multipart 预览、警告展示、确认保存；后端全量 86 passed / 1 skipped。扫描件不支持，解析失败会提示改用 ICS / TXT。

- **2026-11-23：课表架（命名 / 存档 / 拖动排序）**：课表列表改为“课表架”，每张卡带迷你周网格预览、名称、来源、时段数和创建日期；支持给任意课表改名，把旧学期课表存档到“历史课表”并随时恢复。课表卡支持拖动排序：拖右上角把手或卡片预览即可交换位置，也可用方向键移动；在用课表与历史课表各自组内排序。新增 `PATCH /schedule/{schedule_id}`、`PUT /schedule/order` 与 `schedules.is_archived`、`schedules.sort_order` 列（迁移 `c4a91e7d2b60 → e9b2f7c4a1d0`）；存档自动撤销公开，公开课表查询和约饭选表都会排除存档课表。前端 `npm run build` 通过；`shelf-ui-smoke.cjs` 覆盖命名、拖动/键盘排序、存档/恢复、存档当前课表后的自动切换、约饭选表过滤与 390px 无整页溢出；后端全量 79 passed / 1 skipped。

- **2026-11-23：课表网格内添加节次 + 拖动课程**：周网格底部直接显示“添加一节”（沿用当前课时与节间隔生成下一节，当天时间不足时禁用），仍调用 `PUT /schedule/{schedule_id}/timing` 并走 revision 校验，不必先打开作息窗格；课程/日程卡片支持鼠标或触控笔拖动到其他星期/节次，拖卡片底部调整结束节次，拖动时有落点幽灵提示；保存失败（如版本冲突）会回滚位置并提示。触屏暂不启用拖拽，避免与课表横向滚动冲突。未新增接口或数据库迁移；`npm run build` 通过，`drag-ui-smoke.cjs` 覆盖添加节次、跨星期拖动、拉伸、冲突回滚与 390px 无整页溢出。

- **2026-11-19：一对一多候选约饭**：基于双方明确接受的课表与日期日程推荐时间，最终双确认后才生成两条关联日程。新增站内提醒、取消与冲突重算；接口见 docs/API.md。
- **2026-11-20：课表可变节数**：课表作息支持 1–24 节，设置窗格可添加或删除最后一节；网格行数、节次时间、上午/中午/下午/晚上分段、课程编辑选项和约饭时间计算跟随当前节数变化。已有课程使用的节次会阻止误删，接口见 `PUT /schedule/{schedule_id}/timing`。
- **2026-11-20：教务课表浏览器扩展**：新增 Edge / Chrome Manifest V3 助手，用户点击扩展后才授权一次读取；扩展与本站双重预览，确认后通过 `POST /schedule/manual` 私有保存。扩展不读取或保存 SSO 凭据；实际教务响应格式仍需真实账号现场验收。
- **2026-11-19：课表作息与时间显示**：新增课表作息配置和 `PUT /schedule/{schedule_id}/timing`。网格直接显示每节课的起止时间；统一参数可生成默认 12 节，再逐节调整特殊间隔；约饭读取双方当前课表配置，不再在约饭表单重复填写。

- **2026-11-18：安全加固 + 私有图片访问回归（部分方案已被 2026-11-19 取代）**：修复注册角色注入（`applied_role` 仅允许 `photographer`，注册始终落为 `member`）；修复审核员可越权修改用户角色/状态（改角色/状态仅管理员可操作，管理员与审核员仅超级管理员可修改）；修复未公开图片可匿名读取的 IDOR（仅公开且审核通过的图片可访问/下载）。登录、OTP 发送、刷新、密码重置增加 Redis 应用层限流，触发返回 429。当时私有图使用短时效签名 URL；2026-11-19 已改回 `PUBLIC_ASSET_BASE_URL` 代理域方案。修复 `backend/pyproject.toml` 依赖列表误写入 `` `r`n `` 导致 pip 解析失败的 TOML 语法问题。生产环境关闭 `/docs`、`/redoc`、`/openapi.json`。
- **2026-11-19：QQ 第三方登录、7 天 Cookie 会话、法律页面与代理域回归**：新增 `user_third_parties` 绑定表（迁移 `e7f3a91b2d44`）和用户协议同意字段（迁移 `2b7e4c9d1a60`）；QQ 授权码流程回调到前端 `/oauth/qq`，已绑定 QQ 直接登录，未绑定走「绑定已有账号」页；个人主页可绑定/解绑 QQ；后台新增第三方登录开关。登录、绑定与 QQ 授权开始入口均要求滑块拼图验证。Refresh Token 改由 7 天 HttpOnly Cookie 承载，前端不再写 `sessionStorage`。图片展示、私有缩略图和下载恢复为代理域 `public_url`，COS 原生预签名只用于上传。新增 `/legal/terms`、`/legal/privacy`、`/legal/copyright`、`/legal/contact`，注册页改为两个独立协议勾选，后端校验并记录版本与时间。
- **2026-11-18：可编辑课表与个人日程**：沿用周次/星期/节次模型，新增空白课表、点击格子添加课程或日程、编辑导入课程、删除条目；支持单周、多周、单双周，保存到 PostgreSQL 后刷新仍保留。双方共同空闲计算纳入个人日程，切换周次后重新读取与计算。公开课表里的个人日程只显示“已有安排”和时间，隐藏名称/地点/校区。保存采用版本校验，拒绝覆盖其他页面的更新。新增 `POST /schedule/manual`、`PUT /schedule/{id}/slots`，对比接口增加可选 week；旧课表兼容，无需数据库迁移。日程归属于选中的学期课表，暂不支持具体日期/分钟或拖拽。（2026-11-23 已支持拖动与网格内加节，见上文两条 11-23 记录。）
- **2026-11-18：更正课表删除的异步调用**：实测当前 SQLAlchemy `AsyncSession.delete` 是协程，课表删除恢复 `await db.delete(...)`，已用 PostgreSQL 回滚事务验证。下方旧记录中“db.delete 是同步方法”的说法对 AsyncSession 不成立；本次只修正课表服务。
- **2026-11-15：注册配置、邮件通知、密码强度与验证码冷却**：后台新增「注册设置」Tab（开启注册/要求邮箱验证/要求手机验证），前端顶栏/登录页/注册页联动隐藏注册入口，后端 /auth/register 强制门控。新增 SmtpEmailProvider 接入飞书企业邮箱 SMTP，HTML 卡片模板，发件名跟随 APP_NAME；注册提交后发「等待审批」通知，审批通过/拒绝各发通知，fire-and-forget 异步不阻塞。注册和找回密码均要求密码含大小写字母和数字，前后端双重校验；注册表单新增确认密码字段。OTP 发送新增 60 秒冷却（OTP_COOLDOWN_SECONDS），前端按钮倒计时禁用。社团介绍页成员头像修复（补传 `avatar_url`）。新增 COS_DEV_PREFIX 多人开发隔离前缀。`run.py` 支持 --host 参数。
- **2026-11-16：人机验证 + 阿里云短信 + 图片域名隐藏 + 头像同步 + OTP 风控**：新增滑块拼图人机验证（GET /captcha/challenge + POST /captcha/verify，Canvas 拼图 + Bing 壁纸背景，±6px 容差，验证 token 一次性消耗），验证通过后才可获取邮箱/手机验证码。接入阿里云短信服务（AliyunSmsProvider，签名"杭州轻绒文化"，模板 SMS_512658529）。所有图片/文件 URL 统一走 EdgeOne 代理域名 zl.test.tiking.top（公有读、私有缩略图、下载、头像），仅上传预签名 URL 保留 COS 原生域名（桶私有读写，签名保障安全）。OTP 发送冷却从 60s 提升到 120s，邮箱/手机号格式前端强校验（+86 锁死 + 11 位数字 / 邮箱正则），格式不符不可获取验证码。修复 Profile 页面自己视角头像不显示问题，UserAvatar 组件 src 更新时重置 imgError 状态。新增 COS 代理域名客户端（后因 EdgeOne 不支持 PUT 回退），presign_download 全部改为 public_url 走代理域名。

- **2026-11-15：头像上传 + 动态站点名称**：新增头像上传全链路（浏览器端 128×128 裁剪压缩 → COS 预签名直传 → 动态公开 URL），右上角/图片展示/个人页统一显示真实头像；站点名称和副标题改为后端动态拉取，后台修改立即同步前端。登录响应补全 `avatar_url`/`bio` 字段，退出登录强制刷新回首页。
- **2026-11-13：个人主页客制化阶段更新（历史状态）**：新增模块编辑器、渲染器、主题与素材选择组件、会话恢复初始化及开发 mock；后端接通布局草稿读写和图片展示授权，新增迁移与 7 个测试。当时尚未实现的发布、丢弃、主题、素材清单和公开主页端点已于 2026-11-15 补齐，详见上方进度与 `docs/API.md`。
- **修复管理员初始化流程**：`create_admin.py` 现在支持幂等初始化；已存在账号会自动恢复 `admin` 角色、`active` 状态和 `is_active=true`，只有显式传入 `--reset-password` 才会覆盖密码。修复了账号已存在但密码不正确时脚本直接跳过、导致 `admin` 无法登录的问题。
- **新增站点 favicon 全套资源**：由蓝绿 M 形 logo 生成并放入 `frontend/public/`——`favicon.ico`（16–64 多尺寸）、`favicon-32x32.png`、`favicon.png`、`apple-touch-icon.png`（180）、`icon-192.png` / `icon-512.png`、`site.webmanifest`（主题色 `#6B5CE7`）；`index.html` 补充 `rel="icon"` / `apple-touch-icon` / `manifest` 引用。原 `/favicon.ico` 仅有链接、文件缺失，现已补齐。
- **顶栏 / 页脚 / 登录页品牌位换 M 形 logo**：`AppHeader.vue`、`AppFooter.vue`、`Login.vue` 原「FUR」渐变字标改为 `<img>` 引用 `/logo-m-96.png`（顶栏/页脚）或 `/logo-m.png`（登录页 72px）；配套源图 `logo-m.png`（512）。
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
- **`docs/API.md` 扩充为完整交接文档**：合并原 WHATAPI 内容，整理全部 75 个 API 接口（认证/图片/课表/活动/公告/页面/管理后台），含认证说明、权限矩阵、前后端函数参考、类型定义。
- **修复全部假功能占位（6 处）**：`DELETE /images/{id}` 真实删除（权限校验+派生图清理）、`POST /images/{id}/report` 真实举报（Report 表+防重复）、`POST /auth/password/reset` 真实更新密码+撤销全部会话、`PUT /profile/me` 真实编辑昵称/简介、`PATCH /admin/users/{id}/role` 真实修改角色（防自改+super_admin 授权限制）、`PATCH /admin/users/{id}/status` 真实启用/禁用（防自改+禁用强制下线）。
- **修复 `await db.delete()` 运行时炸弹（11 处）**：SQLAlchemy 的 `db.delete()` 是同步方法，误加 `await` 会在运行时抛 TypeError；影响 6 个服务文件的全部删除操作（删活动/公告/页面/课表/私有图/图片），之前调用即 500。已全部移除 `await`。
- **修复 N+1 查询**：`admin_events.py` 活动列表对每个活动逐个查报名统计；改为 `GROUP BY` 批量查询（`_batch_counts`），21 次查询 → 2 次。
- **新增 `bio`/`avatar_url` 用户字段**：Alembic 迁移 `0addd5ed14cc`，`GET /profile/me` 返回 bio/avatar_url，`PUT /profile/me` 支持字段级更新；前端 Profile 页新增编辑资料弹窗。
- **移除全部 `alert()`/`confirm()`（21 处）**：改用全局对话框 `useDialog`（`showToast` 轻量提示 + `showConfirm` 确认弹窗），UI 组件 `AppDialog.vue` 挂载于 `App.vue`，风格与全站玻璃拟态统一。
- **mock 残留清除**：`Gallery.vue` 标签改为从真实图片动态提取；`About.vue` 成员列表走 `GET /profile/members` 公开端点（返回 active 用户昵称/简介，不含隐私）。
- **提取公共辅助函数**：`api/response.py` 新增 `parse_uuid()` 和 `error_to_http()`，清理 10 个端点文件中的 17 处重复 `_parse_uuid`/`_img_error`/`_handle_error` 定义。
- **清理函数内导入（19 处）**：`images.py`/`admin_settings.py`/`auth.py` 中的函数体 `import` 全部移至文件顶部。
- **吞异常改为记日志（6 处）**：`except Exception: pass` 全部改为 `logger.warning(..., exc_info=True)`，删除对象存储文件等"尽力而为"操作不再无声丢失错误。
- **新增 `admin_list_events` 批量统计**：活动管理列表用 `GROUP BY` 一次性查询报名/候补数，消除 N+1。
- **大文件拆分（6 个文件）**：`Schedule.vue`（471→187 行 + 3 个子组件）、`AdminEvents.vue`（386→253 行 + 2 个）、`AdminImages.vue`（348→262 行 + 2 个）、`AdminPages.vue`（340→256 行 + 2 个）、`Gallery.vue`（295→180 行 + 1 个）、`Profile.vue`（346→200 行 + 2 个）；子组件归入 `components/schedule/`、`components/admin/`、`components/gallery/`、`components/profile/`。
- **重复样式去重（70+ 处）**：弹窗遮罩 → `.dialog-overlay`（7 处）、加载 spinner → `.spinner`（8 处）、状态徽章配色 → `utils/statusStyles.ts` 共享常量（30+ 处）、标签徽章 → `.tag-badge*`（8 处）、小操作按钮 → `.btn-sm*`/`.btn-xs*`（16 处）；统一视觉规范已补入 README「复用样式类」章节。
- **修复 `/auth/me` 响应格式不一致**：原来用 `response_model=UserOut` 返回裸对象不走 `ok()` 信封，前端 `request()` 解包会抛「请求失败」，导致刷新页面后登录态恢复失败。已统一为 `ok()` 包装。
- **清理死代码**：删除 7 个零消费者 Schema（`UploadIntentResponse`/`ImageOut`/`EventOut`/`AnnouncementOut`/`ScheduleJobOut`/`CompareResult`/`ScheduleOut`）、清理 4 处未使用导入、删除死文件 `mock.ts`。

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
