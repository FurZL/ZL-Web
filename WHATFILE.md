# WHATFILE.md — 项目文件用途索引

> 本文件登记 `furry-zjut/` 项目中**每一个文件**的用途，方便快速定位。
> 修改/新增文件时请同步更新本文件。

---

## 项目根目录

| 文件 | 用途 |
|---|---|
| `README.md` | 项目总览：部署边界、目录结构、快速开始、开发进度表 |
| `AGENTS.md` | 项目架构与实施规范（完整技术约定、数据模型、API 清单、部署方案） |
| `DESIGN-BRIEF.md` | 页面设计说明书（各页面布局、用户角色、导航规则、色彩语义、移动端要求） |
| `WHATFILE.md` | 本文件 — 项目全部文件用途索引 |
| `.env.example` | 环境变量模板（DATABASE_URL、REDIS_URL、COS_*、SECRET_KEY 等占位值，不含真实密钥） |
| `.gitignore` | 项目根 Git 忽略规则（.env、__pycache__、node_modules、venv 等） |
| `docker-compose.yml` | 本地开发用 PostgreSQL 16 + Redis 7 容器编排（生产不使用 Docker） |

---

## frontend/ — Vue 3 + TypeScript + Vite 前端

### 根配置文件

| 文件 | 用途 |
|---|---|
| `package.json` | npm 依赖声明与脚本（build = vue-tsc 类型检查 + vite 打包） |
| `package-lock.json` | npm 依赖版本锁定文件 |
| `vite.config.ts` | Vite 构建配置（strictPort: 5173、别名 @ → src/、API 代理） |
| `tsconfig.json` | TypeScript 编译选项（路径别名、严格模式） |
| `tailwind.config.js` | Tailwind CSS 配置（自定义色板 primary/ink/sub/blush/faint、圆角、字体） |
| `postcss.config.js` | PostCSS 配置（Tailwind CSS 集成） |
| `index.html` | SPA HTML 入口模板（挂载 #app） |
| `env.d.ts` | TypeScript 环境声明（Vite import.meta.env 类型 + *.vue 模块声明） |
| `.env.development` | 开发环境变量（VITE_API_BASE_URL → http://localhost:8000/api/v1） |
| `.env.production` | 生产环境变量（VITE_API_BASE_URL、VITE_PUBLIC_ASSET_BASE_URL） |
| `.gitignore` | 前端 Git 忽略规则（dist、node_modules 等） |
| `vite-server.log` | Vite 开发服务器运行日志（临时文件，可安全删除） |
| `vite-server.err` | Vite 开发服务器错误日志（临时文件，可安全删除） |

### src/ — 源代码

#### src/ 入口与全局

| 文件 | 用途 |
|---|---|
| `src/main.ts` | Vue 应用入口（创建 app、安装 Pinia / Router、导入全局样式） |
| `src/App.vue` | 根组件（AppHeader + RouterView + AppFooter 布局结构） |
| `src/assets/main.css` | 全局样式（Tailwind 导入、CSS 变量、玻璃拟态 glass-card、btn-primary/btn-ghost、input/label 等基础类） |

#### src/api/ — API 请求层

| 文件 | 用途 |
|---|---|
| `client.ts` | Axios 实例封装（自动注入 Bearer Token、401 自动刷新重试、统一解包 {success, data, error}） |
| `token.ts` | Token 管理（access_token 存内存变量，refresh_token 持久化到 sessionStorage） |
| `schedule.ts` | 课表 API（上传意图/上传完成/我的课表/公开课表/对比/可见性开关/删除） |
| `site.ts` | 站点/公告 API（公开配置/页脚/法律/社团介绍/公告 CRUD/管理设置读写） |
| `events.ts` | 活动 API（列表/详情/报名/取消/签到 + 管理 CRUD/报名列表/管理员签到） |
| `mock.ts` | Mock 数据（首页公告、精选图片、成员列表、课表样例）— 部分页面仍在用，待逐步替换 |
| `pages.ts` | 动态页面 API（公开读取 + 管理 CRUD/发布/下线/版本列表/回滚） |
| `adminImages.ts` | 图片管理 API（统计/列表/审核/公开/标签/删除） |
| `index.ts` | API 模块统一导出（re-export client / token / schedule / site / events / pages / adminImages） |

#### src/types/ — 类型定义

| 文件 | 用途 |
|---|---|
| `index.ts` | 全部 TypeScript 接口（ApiResponse、User、GalleryImage、ScheduleSlot/ScheduleRecord、PublicConfig/FooterConfig、AnnouncementRecord、EventRecord/EventRegistration、PageRecord/PageVersion 等） |

#### src/stores/ — Pinia 状态管理

| 文件 | 用途 |
|---|---|
| `auth.ts` | 认证状态（login / logout / fetchMe、角色判断 isAdmin/isPhotographer、401 登出回调注册） |

#### src/router/ — 路由

| 文件 | 用途 |
|---|---|
| `index.ts` | Vue Router 配置（路由表：首页/介绍/图片/课表/个人空间/登录/注册/管理后台等 + 导航守卫 requiresAuth / requiresAdmin） |

#### src/composables/ — 组合式函数

| 文件 | 用途 |
|---|---|
| `index.ts` | 组合式函数统一导出入口（当前为空，预留 composable 挂载点） |

#### src/utils/ — 工具函数

| 文件 | 用途 |
|---|---|
| `index.ts` | 工具函数统一导出入口（当前为空，预留工具函数挂载点） |

#### src/layouts/ — 布局组件

| 文件 | 用途 |
|---|---|
| `AdminLayout.vue` | 管理后台布局（左侧导航栏 + RouterView 内容区） |

#### src/components/ — 公共组件

| 文件 | 用途 |
|---|---|
| `AppHeader.vue` | 顶部导航栏（Logo「FUR」、导航链接、登录/注册按钮、角色动态菜单、窄屏横滑适配） |
| `AppFooter.vue` | 页脚（从 /site/footer API 拉取版权/备案/协议链接，含默认回退值） |
| `UserAvatar.vue` | 用户头像组件（首字母圆形头像、可调尺寸、渐变背景） |
| `ImageLightbox.vue` | 图片详情弹窗（大图展示、描述、拍摄者、下载按钮，Gallery 与私有相册共用） |
| `ImagePlaceholder.vue` | 图片占位符（加载/缺图时的渐变背景 + 首字母占位） |

#### src/views/ — 页面组件

| 文件 | 用途 |
|---|---|
| `Home.vue` | 首页（Hero 横幅、社团简介、最新公告卡片[真实 API]、精选图片瀑布流预览[真实 API]） |
| `About.vue` | 社团介绍（社团故事[从 /club/intro API 拉取，可后台编辑]、成员展示网格、加入方式） |
| `Gallery.vue` | 公开图片展示（标签筛选、瀑布流图片列表、图片详情弹窗、上传入口 [摄影师/管理员]） |
| `Schedule.vue` | 课表对比工具（三步流程：上传课表 → 选对比对象 → 网格可视化对比结果；走真实 API） |
| `Profile.vue` | 个人空间（个人信息、私有相册上传/删除/预览、课表管理；支持自己/他人两种视角） |
| `Login.vue` | 登录页（用户名/密码、登录按钮、去注册链接） |
| `Register.vue` | 注册页（普通成员/摄影师两种类型、邮箱/手机 OTP、摄影师申请理由/作品集） |
| `RegisterPending.vue` | 注册成功等待审批提示页 |
| `ForgotPassword.vue` | 找回密码页（邮箱/手机验证、重置密码） |
| `Events.vue` | 活动页（活动列表、筛选 Tab、报名/取消/签到、候补状态显示） |
| `DynamicPage.vue` | 动态页面渲染器（白名单 Schema 组件：hero/rich_text/image/countdown/button/notice/event_info/card/divider，未知组件忽略） |
| `NotFound.vue` | 404 页面 |

#### src/views/admin/ — 管理后台页面

| 文件 | 用途 |
|---|---|
| `AdminDashboard.vue` | 仪表盘（用户数、待审批数、图片数等数字总览，已接真实接口） |
| `AdminUsers.vue` | 用户管理（待审批列表、审批/拒绝操作、成员列表，已接真实接口） |
| `AdminImages.vue` | 图片管理（统计卡片、审核/拒绝/公开/标签/删除、筛选 Tab、分页、图片详情弹窗） |
| `AdminEvents.vue` | 活动管理（活动 CRUD、发布/取消、报名列表/签到管理弹窗） |
| `AdminPages.vue` | 页面管理（页面列表、JSON Schema 编辑器、发布/下线、版本历史/回滚） |
| `AdminAnnouncements.vue` | 公告管理（公告列表、新建/编辑弹窗、置顶/发布/删除操作） |
| `AdminSettings.vue` | 网站设置（社团介绍/公开配置/页脚信息/法律信息四个 Tab 表单） |
| `PlaceholderView.vue` | 通用占位页面组件（尚未开发的管理子模块共用的空壳视图） |

---

## backend/ — FastAPI 后端

### 根配置文件

| 文件 | 用途 |
|---|---|
| `pyproject.toml` | Python 项目配置（依赖声明、pytest 配置、项目元数据） |
| `alembic.ini` | Alembic 数据库迁移工具配置（迁移脚本目录、日志级别） |
| `run.py` | 启动入口（解决 Windows 上 uvicorn ProactorEventLoop 与 psycopg SelectorEventLoop 冲突） |
| `.env` | 本地开发环境变量（真实密钥：DATABASE_URL、COS_SECRET_* 等；已 gitignore，勿提交） |

### app/ — 应用主体

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `main.py` | FastAPI 应用工厂（CORS 中间件、路由注册、lifespan 启停 worker/Redis、生产关闭 docs） |
| `loops.py` | 自定义事件循环工厂（SelectorEventLoop，修复 Windows + psycopg 兼容问题） |

### app/api/ — HTTP 层

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `deps.py` | FastAPI 依赖注入（get_current_user：从 Bearer Token 解析当前用户） |
| `response.py` | 统一响应封装（ok() / err()：生成 {success, data, error, request_id} JSON） |

### app/api/v1/ — API v1 路由

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `router.py` | v1 路由总注册（include_router 挂载所有 endpoints 子路由到 /api/v1 前缀） |

### app/api/v1/endpoints/ — 各业务模块端点

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `health.py` | 健康检查端点（GET /health 纯存活检查 + GET /ready 检查 DB/Redis 连通性） |
| `auth.py` | 认证端点（POST /auth/register、verify/email、verify/phone、login、refresh、logout、password/forgot、password/reset、GET /me） |
| `images.py` | 公开图片端点（GET /images 列表、GET /images/{id} 详情、POST upload-intent、upload-complete、DELETE 删除、POST 举报、GET 下载） |
| `profile.py` | 个人空间端点（GET/PUT /profile/me、GET /me/images、POST upload-intent、upload-complete、GET 签名 URL、DELETE 删除、GET /{user_id} 公开资料） |
| `schedule.py` | 课表端点（GET /mine、POST upload-intent、upload-complete、GET /{id}、POST /compare、PATCH /{id}/visibility、GET /shared/{username}、DELETE /{id}） |
| `pages.py` | 动态页面端点（GET /{slug} 公开读取、/admin CRUD/发布/下线/版本列表/回滚） |
| `events.py` | 活动端点（列表/详情/报名/取消/签到，含候补、幂等键、容量控制） |
| `site.py` | 站点公开信息端点（GET /public-config、/footer、/legal，从 SiteSetting 读取并返回默认值） |
| `club.py` | 社团介绍端点（GET /intro 公开读取、PUT /intro 管理员写入） |
| `admin_users.py` | 用户管理端点（GET 列表、GET /pending、GET /{id}、POST approve、reject、PATCH role、status） |
| `admin_settings.py` | 网站设置管理端点（GET/PUT 读写 SiteSetting、Provider 测试） |
| `announcements.py` | 公告端点（GET /published 公开列表、/admin CRUD：创建/编辑/置顶/发布/删除） |
| `admin_events.py` | 活动管理端点（创建/编辑/发布/取消/删除/报名列表/管理员签到） |
| `admin_images.py` | 图片管理端点（列表/统计/审核/公开/标签/删除） |

### app/core/ — 核心基础设施

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `config.py` | Pydantic Settings 配置（从 .env 读取：APP_ENV、SECRET_KEY、DATABASE_URL、REDIS_URL、COS_*、TOKEN_TTL、上传限制、CORS 来源） |
| `database.py` | SQLAlchemy 2.x 异步引擎 / Base / get_db 依赖（AsyncSession 工厂） |
| `redis.py` | Redis 连接池（异步 redis.asyncio，限流/缓存用，含 close_redis） |
| `security.py` | 密码哈希（Argon2id）与 JWT 生成/验证（Access Token 签发与解码） |
| `permissions.py` | RBAC 权限定义与校验（角色 → 权限映射、逐请求校验函数） |
| `logging.py` | 结构化日志配置（日志格式、脱敏过滤器：密码/OTP/Cookie/Token 等） |

### app/middleware/ — 中间件

| 文件 | 用途 |
|---|---|
| `__init__.py` | 中间件装配（setup_middleware：注册 request_id 等中间件） |
| `request_id.py` | 请求 ID 中间件（生成/透传 X-Request-ID、注入到 request.state） |

### app/models/ — 数据库模型（SQLAlchemy ORM）

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `base.py` | 通用字段混入（TimestampMixin：created_at / updated_at） |
| `user.py` | User（用户名/邮箱/手机/密码/角色/状态/摄影师申请）、UserSession（刷新令牌会话）、VerificationChallenge（验证码挑战） |
| `image.py` | StoredObject（对象存储元数据）、Image（公开图片：标签/审核/版权）、ProfileImage（私有相册图片） |
| `schedule.py` | Schedule（课表：stored_object_id、original_name、format、parsed_json、is_public、expires_at） |
| `content.py` | DynamicPage（动态页面：slug/schema_json/发布状态）、DynamicPageVersion（版本快照）、Announcement（公告） |
| `event.py` | Event（活动：标题/时间/地点/容量/报名截止）、EventRegistration（报名记录：状态/签到/幂等键） |
| `setting.py` | SiteSetting（网站配置：key/value_json/category/is_public；敏感密钥不入此表） |
| `audit.py` | AuditLog（审计日志：操作者/动作/目标/IP/元数据） |
| `report.py` | Report（内容举报：举报人/目标/原因/处理状态） |

### app/schemas/ — Pydantic Schema（API 输入输出校验）

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `auth.py` | 认证 Schema（注册请求/登录请求/Token 响应/用户信息响应） |
| `image.py` | 图片 Schema（上传意图请求、上传完成请求、ProfileUploadIntentRequest 等） |
| `schedule.py` | 课表 Schema（CourseSlot、CompareRequest、ScheduleUploadIntentRequest、ScheduleUploadCompleteRequest、ScheduleVisibilityRequest） |
| `page.py` | 动态页面 Schema（页面创建/更新/响应、PageSchema/Theme） |
| `event.py` | 活动 Schema（活动创建/报名请求/响应） |
| `setting.py` | 网站设置 Schema（设置读写请求/响应） |
| `common.py` | 通用响应结构 Schema（ApiResponse 泛型、分页结构） |

### app/services/ — 业务逻辑层

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `auth.py` | 认证服务（注册/登录/刷新令牌轮换/审批/复用检测撤销会话族；Argon2id + JWT） |
| `otp.py` | OTP 验证码服务（生成/发送/校验；哈希存储、短时效、单次使用、用途隔离、OTP_DEV_MODE 开发模式） |
| `image.py` | 图片服务（上传意图：MIME 白名单/随机 Object Key/预签名 URL；上传完成：HEAD 复核/落库；列表/删除） |
| `image_processing.py` | 图片处理服务（下载原图 → 解码校验/防解压炸弹 → 生成 2000px 展示图 + 800px 缩略图 WebP → 上传派生图） |
| `profile_image.py` | 私有相册服务（private/profiles/{user_id}/ 前缀、短时效签名 URL、复用 image 校验逻辑） |
| `schedule.py` | 课表解析与对比算法（CourseSlot 数据类、ICS 解析、ZJUT TXT 解析、compare 对比：周次交集/同教室/冲突/空闲时段） |
| `schedule_service.py` | 课表业务服务（上传意图/上传完成[下载+解析+落库]/我的课表/按用户查询公开课表/可见性开关/删除） |
| `rate_limit.py` | 限流服务（Redis 分布式计数器、原子递增+TTL、分层限流规则） |
| `site_setting.py` | 网站设置服务（SiteSetting 读写、公开配置/页脚/法律/社团介绍聚合，敏感密钥不入此表） |
| `announcement.py` | 公告服务（公开列表：已发布+未过期+置顶在前；管理 CRUD：创建/更新/置顶/发布/删除） |
| `event.py` | 活动服务（活动 CRUD、报名/候补/取消/签到，容量控制、幂等键、候补自动递补） |
| `page.py` | 动态页面服务（页面 CRUD、版本快照、发布/下线、版本回滚） |
| `admin_image.py` | 图片管理服务（列表/审核/公开/标签/删除/统计，含派生图清理） |

### app/providers/ — 外部服务适配层

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `factory.py` | Provider 工厂（get_storage_provider / get_email_provider / get_sms_provider / get_captcha_provider / get_human_verification_provider，按配置选择实现） |
| `storage/base.py` | 存储 Provider 抽象基类（presign_upload / presign_download / head_object / delete_object / get_object_bytes / put_object_bytes / public_url） |
| `storage/cos.py` | 腾讯云 COS 实现（单桶 public/private 前缀隔离、asyncio.to_thread 包装同步 SDK） |
| `storage/__init__.py` | Python 包标记（空文件） |
| `email/base.py` | 邮件 Provider 抽象 + LogEmailProvider（开发模式：打印不真发） |
| `email/__init__.py` | Python 包标记（空文件） |
| `sms/base.py` | 短信 Provider 抽象 + LogSmsProvider（开发模式：打印不真发） |
| `sms/__init__.py` | Python 包标记（空文件） |
| `captcha/base.py` | 验证码 Provider 抽象 + NoopCaptchaProvider（占位，未接入真实验证码服务） |
| `captcha/__init__.py` | Python 包标记（空文件） |
| `human_verification/base.py` | 人机验证 Provider 抽象 + NoopHumanVerificationProvider（占位，未接入真实人机验证） |
| `human_verification/__init__.py` | Python 包标记（空文件） |

### app/workers/ — 后台任务

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `image_worker.py` | 图片处理 worker（asyncio.Queue + 固定数量串行 worker、lifespan 启停、upload-complete 入队） |
| `README.md` | 异步任务设计说明（初期不引入 Celery 的原因与约束） |

### app/repositories/ — 数据访问层

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（预留：复杂查询时使用的 Repository 层） |

### app/utils/ — 工具函数

| 文件 | 用途 |
|---|---|
| `__init__.py` | 通用工具（请求 ID 生成、日志脱敏：邮箱/手机号/IP 脱敏函数） |

### migrations/ — Alembic 数据库迁移

| 文件 | 用途 |
|---|---|
| `env.py` | Alembic 迁移环境配置（数据库连接、target_metadata、迁移模式） |
| `script.py.mako` | 迁移脚本自动生成模板 |
| `versions/81c6d451559a_init_tables.py` | 初始建表迁移（15 张业务表 + alembic_version） |
| `versions/64b8838cd73c_add_profile_image_fields.py` | 迁移：添加私有相册图片字段 |
| `versions/9394e2a89de2_add_photographer_application_fields.py` | 迁移：添加摄影师申请字段（applied_role/application_reason/application_portfolio） |
| `versions/131029fbb8f9_add_schedule_name_and_format.py` | 迁移：添加课表 original_name / format 字段（当前 head） |

### scripts/ — 运维/测试脚本

| 文件 | 用途 |
|---|---|
| `create_admin.py` | 创建管理员账号脚本（默认 admin / admin123456） |
| `cos_smoke_test.py` | COS 连通性冒烟测试（验证 SecretId/SecretKey/Bucket 配置正确） |
| `setup_cos_cors.py` | 配置 COS 桶 CORS 规则（允许前端直传 PUT/POST，前端上传必需） |
| `setup_cos_public_read.py` | 配置 COS public/ 前缀公有读策略（公开图片可匿名访问） |
| `verify_cos_cors.py` | 验证 COS CORS 配置是否正确生效 |
| `e2e_auth_test.py` | 认证端到端测试（注册 → 邮箱/手机验证 → 管理员审批 → 登录 → 刷新令牌） |
| `e2e_upload_test.py` | 图片上传端到端测试（预签名直传 → upload-complete → 列表验证） |
| `e2e_processing_test.py` | 图片处理端到端测试（上传 → worker 生成缩略图/展示图 → 派生图验证） |
| `e2e_profile_album_test.py` | 私有相册端到端测试（上传私有图 → 签名 URL 访问 → 隔离验证） |
| `e2e_profile_real_test.py` | 个人空间真实链路端到端测试（完整 Profile 流程验证） |

### tests/ — 单元测试

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `test_auth.py` | 认证测试（注册/登录/Token 刷新/权限） |
| `test_schedule.py` | 课表对比算法测试（周次交集/同教室检测/时间冲突判定） |
| `test_schedule_parser.py` | 课表解析测试（ZJUT TXT 格式/周次范围/节次解析/空格/换行/异常格式） |
| `test_image_processing.py` | 图片处理测试（WebP 生成/尺寸裁剪/防解压炸弹/非法文件拒绝） |
| `test_permissions.py` | 权限矩阵测试（各角色操作权限验证） |

### furry_zjut_backend.egg-info/ — pip 安装元数据（自动生成）

| 文件 | 用途 |
|---|---|
| `PKG-INFO` | 包元数据（pip install -e . 自动生成，描述/版本/依赖） |
| `requires.txt` | 依赖列表（从 pyproject.toml 提取的运行时依赖） |
| `SOURCES.txt` | 源文件清单（pip 收集的全部源文件路径） |
| `top_level.txt` | 顶层模块名（标识包名） |
| `dependency_links.txt` | 依赖链接（通常为空） |

---

## deploy/ — 部署配置

| 文件 | 用途 |
|---|---|
| `nginx/api.example.com.conf` | Nginx API 站点配置模板（HTTPS、反代 127.0.0.1:8000、安全头、请求体限制） |
| `nginx/www.example.com.conf` | Nginx 前端站点配置模板（SPA fallback try_files、静态资源缓存） |
| `systemd/furry-zjut-api.service` | systemd 服务单元（uvicorn 1 Worker、User=furry、NoNewPrivileges、PrivateTmp 等安全加固） |
| `scripts/backup-furry-zjut.sh` | PostgreSQL 备份脚本（pg_dump + 过期清理 + COS 上传占位） |
| `scripts/start-vite.ps1` | Windows 启动 Vite 开发服务器 PowerShell 脚本（设置 NODE 路径、清理日志、后台启动） |
| `edgeone/README.md` | EdgeOne Pages 部署说明（SPA fallback 配置、构建发布流程） |

---

## docs/ — 项目文档

| 文件 | 用途 |
|---|---|
| `API.md` | API 文档（统一响应结构、接口清单索引） |
| `DEPLOYMENT.md` | 部署说明（EdgeOne Pages + 宝塔 2C2G + 本机 PostgreSQL/Redis、关键步骤索引） |
| `SECURITY.md` | 安全基线（上线前 15 项检查清单、日志脱敏规则、认证方案选择） |
