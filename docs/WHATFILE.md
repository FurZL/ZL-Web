# WHATFILE.md — 项目文件用途索引

> 本文件登记 `furry-zjut/` 项目中**每一个文件**的用途，方便快速定位。
> 修改/新增文件时请同步更新本文件。

---

## 项目根目录

| 文件 | 用途 |
|---|---|
| `README.md` | 项目总览：部署边界、目录结构、快速开始、开发进度表与变更记录 |
| `AGENTS.md` | 项目架构与实施规范（完整技术约定、数据模型、API 清单、部署方案） |
| `DESIGN-BRIEF.md` | 页面设计说明书（各页面布局、用户角色、导航规则、色彩语义、移动端要求） |
| `.env.example` | 环境变量模板（DATABASE_URL、REDIS_URL、COS_*、SMTP_*、OTP_*、认证 Cookie、QQ OAuth、COS_DEV_PREFIX、SECRET_KEY、PROFILE_LAYOUT_MAX_BLOCKS 等占位值，不含真实密钥） |
| `.gitignore` | 项目根 Git 忽略规则（.env、__pycache__、node_modules、venv 等） |
| `docker-compose.yml` | 本地开发用 PostgreSQL 16 + Redis 7 容器编排（生产不使用 Docker） |

---

## frontend/ — Vue 3 + TypeScript + Vite 前端

### 根配置文件

| 文件 | 用途 |
|---|---|
| `package.json` | npm 依赖声明与脚本（dev 真实 API、dev:mock 个人主页演示模式；build = vue-tsc 类型检查 + vite 打包 + 生成 sitemap/robots） |
| `package-lock.json` | npm 依赖版本锁定文件 |
| `vite.config.ts` | Vite 配置（strictPort: 5173、别名 @ → src/、`/api` 代理到 `127.0.0.1:8000`；显式 VITE_PROFILE_MOCK=1 时启用开发 mock） |
| `tsconfig.json` | TypeScript 编译选项（路径别名、严格模式） |
| `tailwind.config.js` | Tailwind CSS 配置（自定义色板 primary/ink/sub/blush/faint、圆角、字体） |
| `postcss.config.js` | PostCSS 配置（Tailwind CSS 集成） |
| `index.html` | SPA HTML 入口模板（挂载 #app；声明 favicon / apple-touch-icon / site.webmanifest） |
| `env.d.ts` | TypeScript 环境声明（Vite import.meta.env 类型 + *.vue 模块声明） |
| `.env.development` | 开发环境变量（VITE_API_BASE_URL → http://localhost:8000/api/v1） |
| `.env.production` | 生产环境变量（VITE_API_BASE_URL） |
| `.gitignore` | 前端 Git 忽略规则（dist、node_modules 等） |
| `vite-server.log` | Vite 开发服务器运行日志（临时文件，可安全删除） |
| `vite-server.err` | Vite 开发服务器错误日志（临时文件，可安全删除） |
| `scripts/generate-sitemap.mjs` | 构建后生成 `dist/sitemap.xml` 与 `dist/robots.txt`；只收录首页、社团介绍、图片展示、活动和四个法律页面，排除登录、管理后台、个人主页等私密路由 |

### frontend/public/ — 静态资源（原样输出到 dist/）

| 文件 | 用途 |
|---|---|
| `favicon.ico` | 多尺寸站点图标（16/24/32/48/64，由蓝绿 M 形 logo 生成），浏览器标签页 |
| `favicon-32x32.png` | PNG 版 favicon（32×32），现代浏览器备用 |
| `favicon.png` | PNG 版 favicon 同尺寸副本（兼容部分旧引用） |
| `apple-touch-icon.png` | iOS 主屏图标（180×180） |
| `icon-192.png` | PWA / manifest 图标（192×192） |
| `icon-512.png` | PWA / manifest 图标（512×512） |
| `site.webmanifest` | Web App Manifest（图标、主题色 `#6B5CE7`、standalone 显示） |
| `logo-m.png` | M 形 logo 大图（512×512，顶栏/页脚等 UI 共用源图） |
| `logo-m-96.png` | M 形 logo 小图（96×96），顶栏与页脚品牌位实际引用 |
| `fonts/loader.js` | 字体加载器：Google Fonts (Noto Sans SC) 优先，失败/超时回退本地鸿蒙字体 |
| `fonts/fonts.css` | 本地字体 `@font-face` 声明（HarmonyOS Sans SC，子集化 woff2） |
| `fonts/HarmonyOS_Sans_SC_Regular.woff2` | 鸿蒙简体中文 Regular（子集化 154KB，覆盖项目全部用到的字符） |
| `fonts/HarmonyOS_Sans_SC_Bold.woff2` | 鸿蒙简体中文 Bold（子集化 152KB） |

### dev/ — 开发演示

| 文件 | 用途 |
|---|---|
| `profileMock.ts` | 个人主页 mock：示例模块、图片和会话恢复；覆盖草稿/发布/丢弃/主题/素材/访客页契约，仅在显式开启的 Vite 开发模式生效，数据不持久化 |

### src/ — 源代码

#### src/ 入口与全局

| 文件 | 用途 |
|---|---|
| `main.ts` | Vue 应用入口（创建 app、安装 Pinia / Router、导入全局样式） |
| `App.vue` | 根组件（AppHeader + RouterView + AppFooter + AppDialog 布局结构，调用共享 bootstrapAuth 恢复登录态） |
| `assets/main.css` | 全局样式（Tailwind 导入、CSS 变量、glass-card、btn-primary/btn-ghost、dialog-overlay、spinner、tag-badge、input/label 等基础类） |

#### src/api/ — API 请求层

| 文件 | 用途 |
|---|---|
| `client.ts` | Axios 实例封装（Bearer Token、`withCredentials` Cookie、401 刷新重试、响应解包；提取业务错误和 FastAPI 字段校验错误） |
| `token.ts` | Token 管理（access_token 仅存内存；refresh_token 由后端 HttpOnly Cookie 承载，前端只维护本地会话标记） |
| `bootstrap.ts` | 登录态初始化（bootstrapAuth 共享 Promise，供 App 和路由守卫等待会话恢复） |
| `oauth.ts` | QQ 登录/绑定、回调会话交换、本人第三方绑定查询/解绑 API 封装 |
| `profile.ts` | 个人主页 API 封装（布局读写、发布/丢弃、主题、素材清单、匿名公开页、图片展示授权） |
| `schedule.ts` | 课表 API（上传、手工创建、编辑保存、课表架命名/存档/排序、PDF 预览、群组创建/加入/审批/共享/对比、对比页固定时间约定、读取、按周对比、可见性、删除） |
| `site.ts` | 站点/公告 API（公开配置/页脚/法律/社团介绍/公告 CRUD/管理设置读写） |
| `events.ts` | 活动 API（列表/详情/报名/取消/签到 + 管理 CRUD/报名列表/管理员签到） |
| `index.ts` | API 模块统一导出（re-export client / token / schedule / site / events / pages / adminImages / profile / oauth） |
| `pages.ts` | 动态页面 API（公开读取 + 管理 CRUD/发布/下线/版本列表/回滚） |
| `adminImages.ts` | 图片管理 API（统计/列表/审核/公开/标签/删除） |

#### src/types/ — 类型定义

| 文件 | 用途 |
|---|---|
| `index.ts` | 全部 TypeScript 接口（含 ProfileBlock/Theme/Media/LayoutResponse/PageResponse、RegistrationConfig、OauthConfig/OauthResolveResult/ThirdPartyBinding、模块类型与栅格宽度类型） |

#### src/stores/ — Pinia 状态管理

| 文件 | 用途 |
|---|---|
| `auth.ts` | 认证状态（login 支持可选 captchaToken / setSession 接收 OAuth 登录态 / logout / fetchMe、角色判断 isAdmin/isPhotographer、401 登出回调注册） |
| `profileLayout.ts` | 主页编辑器状态（模块/主题/素材、撤销重做、草稿读写、发布/丢弃；页面可见且数据过期时刷新统计和代理域素材，不覆盖未保存布局） |

#### src/router/ — 路由

| 文件 | 用途 |
|---|---|
| `index.ts` | Vue Router 配置（含 `/profile/me/edit`、`/oauth/qq`、`/legal/:slug`；requiresAuth 守卫先等待 bootstrapAuth，另有 requiresAdmin 校验） |

#### src/composables/ — 组合式函数

| 文件 | 用途 |
|---|---|
| `index.ts` | 组合式函数统一导出入口（预留） |
| `useDialog.ts` | 全局对话框（`showToast` 轻量提示 3 秒消失 + `showConfirm` 确认弹窗 Promise 化，替代 alert/confirm） |
| `useSiteConfig.ts` | 站点配置 composable（从 /site/public-config 拉取站点名称/副标题/注册门控/第三方登录开关，同步 document.title） |

#### src/utils/ — 工具函数

| 文件 | 用途 |
|---|---|
| `index.ts` | 工具函数统一导出入口（预留） |
| `statusStyles.ts` | 全站状态徽章配色共享常量（MODERATION/EVENT/PAGE/REG/ANNOUNCEMENT_STATUS），替代各组件重复 statusMap 定义 |

#### src/layouts/ — 布局组件

| 文件 | 用途 |
|---|---|
| `AdminLayout.vue` | 管理后台布局（左侧导航栏 + RouterView 内容区） |

#### src/components/ — 公共组件

| 文件 | 用途 |
|---|---|
| `SliderCaptcha.vue` | 滑块拼图人机验证组件（Bing 壁纸背景、自适应窄屏尺寸、Pointer Events + 触摸拖拽、打开时收起软键盘、CSS background-image 拼图块） |
| `AppDialog.vue` | 全局对话框 UI（Toast 滑入提示 + Confirm 玻璃卡片弹窗，挂载于 App.vue） |
| `AppHeader.vue` | 顶部导航栏（桌面横向导航与账号下拉菜单；`lg` 以下右侧抽屉导航，含主导航、账号入口、登录/注册/退出，支持遮罩/Esc/路由切换关闭与滚动锁定）；头像旁消息铃铛，公告/待处理邀请未读红点与通知面板 |
| `AppFooter.vue` | 页脚（从 /site/footer API 拉取版权/备案/协议链接；请求失败或链接为空时回退到四个法律页面） |
| `UserAvatar.vue` | 用户头像组件（支持真实头像图片 + 首字母圆形回退、可调尺寸、渐变背景、加载失败自动回退） |
| `ImageLightbox.vue` | 图片详情弹窗（大图展示、描述、拍摄者、下载按钮，Gallery 与私有相册共用） |
| `ImagePlaceholder.vue` | 图片占位符（加载/缺图时的渐变背景 + 首字母占位） |

#### src/components/schedule/ — 课表对比子组件

| 文件 | 用途 |
|---|---|
| `Step1Upload.vue` | Step 1：课表架容器、可编辑周网格、上传/分享/切换；支持 ICS/TXT/PDF 选择，把网格拖动、加节、课表架事件和课表内的约定邀请卡片转给页面处理 |
| `ScheduleGroupPanel.vue` | 群组对比面板：创建群组/邀请码加入/审批/成员共享课表/逐人忙闲统计，点击成员进入双人对比 |
| `ScheduleShelf.vue` | 课表架：卡片式列出在用课表与历史课表，支持内联命名、拖动/方向键排序、存档/恢复、公开开关、切换与删除；新建空白课表入口 |
| `ScheduleMiniPreview.vue` | 课表架卡片的迷你周网格缩略图：按星期/节次比例绘制课程与日程色块 |
| `ScheduleWeekPicker.vue` | 周次选择器；完整模式为学期总览 + 横向周次胶囊，`compact` 模式压缩为「‹ / 全学期下拉 / ›」单行 |
| `ScheduleWeekGrid.vue` | 单人/双人周网格；表头在星期下显示对应日期（具体周取该周，全学期按当前教学周并标注第 N 周）；对比模式把双方课程合并成低饱和共享块（左紫/右粉侧条、同课只显示一次、不同课补 TA 行、同教室琥珀圆点），空闲格平面化，表头可选中整列并浮起绿框；绿色空闲格支持按住拖动选择连续节次（实时高亮、遇忙碌截断），松手抛 freePin；悬停抛 freeHover；同格条目分列，点击空白新增/卡片编辑，日程虚线样式；待处理约定以虚线邀请卡片显示在对应周/节次；按作息时间显示上午/中午/下午/晚上分段（边界来自 timing.segments）；底部内嵌“添加一节”，鼠标/触控笔拖动卡片换星期与节次、拖卡片底部调整结束节次（带落点幽灵与失败回滚） |
| `ScheduleSlotEditor.vue` | 课程/日程编辑弹窗；星期、节次、单周/多周、地点、隐私提示、保存与删除确认 |
| `ScheduleImportDialog.vue` | 课表导入二次预览（浏览器扩展 / PDF）：显示课程、警告与默认作息，编辑课表名/学期起始日后私有保存 |
| `ScheduleTimingEditor.vue` | 课表作息二级窗格；1–24 节动态增删、第一节开始时间、统一课时/间隔、学期第一周、时段边界（中午/下午/晚上开始）、逐节时间预览与特殊间隔调整；追加一节与网格共用 `nextSchedulePeriod` 规则 |
| `calendar.ts` | 默认/兼容课表作息、时段边界默认与规范化、下一节默认时间与追加规则、上午/中午/下午/晚上分段判断、周次范围、单双周用到的周列表、周次文本解析/格式化与节次常量 |
| `Step2Partner.vue` | Step 2：搜索圈友用户名、查看对方课表预览 |
| `Step3Result.vue` | Step 3：对比结果周课表网格；顶部用一行小标签显示共同空闲/同教室/冲突；课程按双方占用合并成共享块，推荐空闲/同教室/冲突全部在网格内呈现，表头可选中整列并浮起绿框；悬停空闲格出邀约二级浮窗，拖动连续空闲格选择多节、松手固定浮窗后发送（单击 1 节）；周次选择用紧凑模式，网格上方放约定周次与邀请状态 |
| `ScheduleInvitationDialog.vue` | 课表网格邀请卡片的接受/婉拒弹窗：展示具体时间、选择参与课表、错误提示 |
| `ScheduleInvitePopover.vue` | 对比页空闲格的二级邀约浮窗：显示邀约名称、参与人、拖动选择后的时间段、邀请按钮，支持悬停预览与点击固定 |
#### browser-extension/ — Edge / Chrome 教务课表导入

| 项目内路径 | 用途 |
|---|---|
| `browser-extension/manifest.json` | Manifest V3 扩展配置及教务、本站站点权限 |
| `browser-extension/portal-hook.js` | 仅在用户显式授权后捕获一次教务课表 JSON 响应；不改写请求、不读取凭据 |
| `browser-extension/portal-bridge.js` | 检查本次读取授权、解析响应并转发规范化课程 |
| `browser-extension/portal-parser.js` | 教务返回字段到 `ScheduleSlot` 的映射和单双周解析 |
| `browser-extension/service-worker.js` | 校验读取授权、管理会话暂存与有效期、投递本站标签页和清理确认数据 |
| `browser-extension/site-bridge.js` | 扩展与本站课表页之间的消息桥接 |
| `browser-extension/popup.html` / `popup.js` / `popup.css` | 扩展弹窗、读取结果预览、站点选择与发送 |
| `browser-extension/tests/portal-parser.test.cjs` | 教务响应映射、单双周和无效数据拒绝测试 |
| `browser-extension/tests/capture-consent.test.cjs` | 验证未授权不读取、扩展后台拒绝未授权捕获及授权只能使用一次 |
| `browser-extension/README.md` | Edge / Chrome 本地安装、授权范围、使用步骤和格式兼容说明 |

#### src/components/admin/ — 管理后台子组件

| 文件 | 用途 |
|---|---|
| `EventFormDialog.vue` | 活动创建/编辑弹窗（标题/描述/地点/时间/容量） |
| `EventRegistrationsDialog.vue` | 活动报名管理弹窗（报名列表/候补/代签到） |
| `ImageCard.vue` | 图片管理卡片（缩略图/状态角标/审核/标签/删除操作） |
| `ImageTagDialog.vue` | 图片标签编辑弹窗 |
| `PageFormDialog.vue` | 动态页面创建/编辑弹窗（slug/标题/JSON Schema 编辑器） |
| `PageVersionsDialog.vue` | 页面版本历史弹窗（版本列表/回滚） |

#### src/components/gallery/ — 图片展示子组件

| 文件 | 用途 |
|---|---|
| `UploadImageDialog.vue` | Gallery 图片上传弹窗（文件选择/预览/描述/标签/预签名直传） |

#### src/components/profile/ — 个人空间子组件

| 文件 | 用途 |
|---|---|
| `UploadPrivateDialog.vue` | 私有图片上传弹窗（文件选择/预览/描述/预签名直传） |
| `EditProfileDialog.vue` | 编辑资料弹窗（昵称/简介/头像上传：选择图片→裁剪弹窗→保存时上传 COS→实时预览） |
| `ProfileRenderer.vue` | 主页白名单模块渲染器（响应式栅格、主题变量、背景及素材） |
| `ProfileMediaPickerDialog.vue` | 主页图片展示授权管理弹窗（依赖待实现的素材清单接口，PATCH 授权端点已实现） |
| `AvatarCropDialog.vue` | 头像裁剪弹窗（拖拽/缩放正方形选区、网格辅助线、128×128 Canvas 预览、两步高质量缩放输出 JPEG） |
| `theme.ts` | 默认主题、5 套主题预设及颜色混合、背景、卡片表面样式函数 |

#### src/components/profile/blocks/ — 主页模块

| 文件 | 用途 |
|---|---|
| `registry.ts` | 8 种模块白名单、组件/名称/图标映射、允许宽度、字面量栅格样式及新模块生成函数 |
| `types.ts` | 模块组件通用 Props 和属性读取辅助函数 |
| `BioBlock.vue` | 个人简介模块 |
| `QuoteBlock.vue` | 一句话与署名模块 |
| `FeaturedPhotoBlock.vue` | 单张主图与说明模块 |
| `PhotoWallBlock.vue` | 照片墙模块（2/3 列瀑布排布，按素材宽高比自适应图片高度） |
| `GalleryLinkBlock.vue` | 按标签跳转图库的入口模块 |
| `LinksBlock.vue` | 外部链接组模块 |
| `StatsBlock.vue` | 入圈天数、公开图库图片数模块 |
| `SandboxBlock.vue` | 点击加载自定义 HTML，使用 iframe sandbox 与 CSP 隔离 |

#### src/components/profile/editor/ — 主页编辑器面板

| 文件 | 用途 |
|---|---|
| `ModuleLibrary.vue` | 模块库与剩余数量提示 |
| `PreviewCanvas.vue` | 编辑画布（选中、排序、复制、删除） |
| `PropertyPanel.vue` | 按模块类型编辑内容及栅格宽度 |
| `ThemePanel.vue` | 主题预设、颜色、背景与卡片样式面板 |
| `MediaPicker.vue` | 编辑器素材选择与展示授权开关（素材清单依赖待实现接口） |

#### src/views/ — 页面组件

| 文件 | 用途 |
|---|---|
| `Home.vue` | 首页（Hero 横幅、社团简介、最新公告卡片[真实 API]、精选图片瀑布流预览[真实 API]） |
| `About.vue` | 社团介绍（社团故事[从 /club/intro API 拉取，可后台编辑]、成员展示网格[头像悬停放大并可进入成员公开主页]、加入方式） |
| `Gallery.vue` | 公开图片展示（标签筛选、瀑布流图片列表、图片详情弹窗、上传入口 [摄影师/管理员]） |
| `Schedule.vue` | 课表对比工具（三步流程：上传课表 → 选对比对象 → 网格可视化对比结果；走真实 API）；课表架命名/存档/排序、PDF 预览导入、群组逐人对比入口、对比页固定时间约定、课表网格内的约定邀请卡片与接受弹窗、网格内添加节次与拖动/拉伸课程在此统一持久化 |
| `Profile.vue` | 个人空间（本人布局与私有相册、公开主页链接分享、QQ 账号绑定/解绑；访客可读取已发布主页，统计在前台每分钟刷新） |
| `ProfileEditor.vue` | 个人主页编辑页（/profile/me/edit，模块库/画布/属性/主题/预览、快捷键、离开前未保存提示、统计在前台每分钟刷新） |
| `Login.vue` | 登录页（用户名/密码、登录按钮[触发滑块人机验证]、注册关闭时隐藏去注册链接、第三方登录开关下显示 QQ 登录并先做拼图验证） |
| `Register.vue` | 注册页（注册配置联动、用户名/昵称/密码长度与格式校验、邮箱/手机 OTP 格式校验、密码确认+强度校验、验证码倒计时、普通成员/摄影师类型及摄影师申请信息、用户协议与隐私政策独立勾选） |
| `RegisterPending.vue` | 注册成功等待审批提示页 |
| `ForgotPassword.vue` | 找回密码页（邮箱/手机验证、密码确认+强度校验、验证码倒计时、重置密码） |
| `Events.vue` | 活动页（活动列表、筛选 Tab、报名/取消/签到、候补状态显示） |
| `DynamicPage.vue` | 动态页面渲染器（白名单 Schema 组件：hero/rich_text/image/countdown/button/notice/event_info/card/divider，未知组件忽略） |
| `LegalPage.vue` | 法律页面（`/legal/:slug`：用户协议、隐私政策、版权声明、联系我们；含 EdgeOne/COS/QQ/阿里云短信/飞书/Bing/Google Fonts 服务清单与官方隐私政策外链、依法配合条款；联系邮箱 contact@furzl.cn） |
| `OAuthCallback.vue` | QQ OAuth 回调页（`/oauth/qq`；已绑定直接完成会话，未绑定进入账号密码绑定，绑定提交前滑块验证） |
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
| `AdminSettings.vue` | 网站设置（社团介绍/公开配置/页脚信息/法律信息/注册设置/第三方登录六个 Tab；第三方登录含总开关与 QQ 子开关） |
| `PlaceholderView.vue` | 通用占位页面组件（尚未开发的管理子模块共用的空壳视图） |

---

## backend/ — FastAPI 后端

### 根配置文件

| 文件 | 用途 |
|---|---|
| `pyproject.toml` | Python 项目配置（依赖声明、pytest 配置、项目元数据；含 pdfplumber、python-multipart） |
| `alembic.ini` | Alembic 数据库迁移工具配置（迁移脚本目录、日志级别） |
| `run.py` | 启动入口（解决 Windows 上 uvicorn ProactorEventLoop 与 psycopg SelectorEventLoop 冲突；--host 参数支持监听所有接口） |
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
| `auth.py` | 认证端点（POST /auth/register[注册门控+密码强度+协议同意]、verify/email、verify/phone、login/refresh/logout 写入或清除 HttpOnly Refresh Cookie、logout-all、password/forgot、password/reset、GET /me） |
| `oauth.py` | QQ OAuth 端点（providers、start、bind-start、callback、bind；state/临时凭证存 Redis，callback 可写 Refresh Cookie） |
| `images.py` | 公开图片端点（GET /images 列表、GET /images/{id} 详情、POST upload-intent、upload-complete、DELETE 删除、POST 举报、GET 下载） |
| `profile.py` | 个人空间端点（资料/相册/头像、布局 GET/PUT/publish/discard、主题 PUT、素材 GET、图片展示授权 PATCH、匿名公开主页 GET、本人第三方绑定 GET/DELETE） |
| `schedule.py` | 课表、约饭与日期日程端点（手工创建、本人编辑保存、上传、读取、按周对比、可见性、公开查询、删除）；课表架重命名/存档/排序（PATCH、PUT /order）；PDF 预览（POST /pdf-preview，内存解析、不落库） |
| `schedule_groups.py` | 课表群组端点：列表/创建/邀请码加入/详情/改名/解散/共享课表/审批/移除（前缀 `/schedule/groups`） |
| `pages.py` | 动态页面端点（GET /{slug} 公开读取、/admin CRUD/发布/下线/版本列表/回滚） |
| `events.py` | 活动端点（列表/详情/报名/取消/签到，含候补、幂等键、容量控制） |
| `site.py` | 站点公开信息端点（GET /public-config[含 registration_config 与 oauth_config]、/footer、/legal，从 SiteSetting 读取并返回默认值） |
| `club.py` | 社团介绍端点（GET /intro 公开读取、PUT /intro 管理员写入） |
| `admin_users.py` | 用户管理端点（GET 列表、GET /pending、GET /{id}、POST approve、reject、PATCH role、status） |
| `admin_settings.py` | 网站设置管理端点（GET/PUT 读写 SiteSetting、Storage/Email/SMS/Captcha/QQ Provider 测试） |
| `announcements.py` | 公告端点（GET /published 公开列表、/admin CRUD：创建/编辑/置顶/发布/删除） |
| `admin_events.py` | 活动管理端点（创建/编辑/发布/取消/删除/报名列表/管理员签到） |
| `captcha.py` | 人机验证端点（滑块挑战/校验，Redis 存储，token 一次性消耗） |
| `admin_images.py` | 图片管理端点（列表/统计/审核/公开/标签/删除） |

### app/core/ — 核心基础设施

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `config.py` | Pydantic Settings 配置（环境变量、连接与第三方服务；含认证 Cookie、QQ OAuth App ID/Key/回调、COS_DEV_PREFIX、SMTP_*、OTP_*；PROFILE_LAYOUT_MAX_BLOCKS 默认 16） |
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
| `__init__.py` | 统一导出业务模型供应用及 Alembic 加载（含 ProfileLayout、UserThirdParty） |
| `base.py` | 通用字段混入（TimestampMixin：created_at / updated_at） |
| `user.py` | User（用户名/邮箱/手机/密码/bio/avatar/角色/状态/摄影师申请、terms_version/privacy_version/legal_accepted_at）、UserSession（刷新令牌会话）、VerificationChallenge（验证码挑战） |
| `third_party.py` | UserThirdParty（用户与 QQ 的绑定关系、OpenID/UnionID、第三方令牌与原始资料、时间戳） |
| `image.py` | StoredObject（对象存储元数据）、Image（公开图片）、ProfileImage（私有相册图片，新增默认 false 的 is_displayable 展示授权） |
| `profile_layout.py` | ProfileLayout 模型（JSONB 草稿、已发布块、主题、公开开关及时间戳，按用户唯一） |
| `schedule.py` | Schedule（课表：stored_object_id、original_name、format、parsed_json、is_public、is_archived、sort_order、expires_at） |
| `schedule_group.py` | ScheduleGroup（群组：名称、8 位邀请码、群主、open/approval）与 ScheduleGroupMember（角色、pending/active、成员共享课表 id） |
| `content.py` | DynamicPage（动态页面：slug/schema_json/发布状态）、DynamicPageVersion（版本快照）、Announcement（公告） |
| `event.py` | Event（活动：标题/时间/地点/容量/报名截止）、EventRegistration（报名记录：状态/签到/幂等键） |
| `setting.py` | SiteSetting（网站配置：key/value_json/category/is_public；敏感密钥不入此表） |
| `audit.py` | AuditLog（审计日志：操作者/动作/目标/IP/元数据） |
| `report.py` | Report（内容举报：举报人/目标/原因/处理状态） |

### app/schemas/ — Pydantic Schema（API 输入输出校验）

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `auth.py` | 认证 Schema（注册请求[密码强度+password_confirm+terms/privacy 同意与版本]/登录请求/Token 响应/用户信息响应/密码重置确认） |
| `image.py` | 图片 Schema（上传意图请求、上传完成请求、ProfileUploadIntentRequest 等） |
| `profile_layout.py` | ProfileImageDisplayPatch（严格布尔 is_displayable，拒绝额外字段） |
| `schedule.py` | 课表 Schema（CourseSlot/EditableSlot、手工创建、版本化保存、选周对比、上传、可见性、课表架元数据重命名/存档、完整顺序排序、时段边界 ScheduleSegments） |
| `page.py` | 动态页面 Schema（页面创建/更新/响应、PageSchema/Theme） |
| `event.py` | 活动 Schema（活动创建/报名请求/响应） |
| `setting.py` | 网站设置 Schema（设置读写请求/响应） |
| `common.py` | 通用响应结构 Schema（ApiResponse 泛型、分页结构） |

### app/services/ — 业务逻辑层

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `auth.py` | 认证服务（注册[记录协议版本与同意时间]/登录/刷新令牌轮换/审批/复用检测撤销会话族；Argon2id + JWT） |
| `third_party_auth.py` | QQ 第三方登录/绑定服务（Redis state 与 pending 凭证、QQ 身份解析、绑定关系查询/解绑、OAuth 开关校验、会话签发） |
| `otp.py` | OTP 验证码服务（生成/发送/校验；哈希存储、短时效、单次使用、用途隔离、OTP_DEV_MODE 开发模式） |
| `image.py` | 图片服务（上传意图：MIME 白名单/随机 Object Key/预签名 URL；上传完成：HEAD 复核/落库；列表/删除） |
| `image_processing.py` | 图片处理服务（下载原图 → 解码校验/防解压炸弹 → 生成 2000px 展示图 + 800px 缩略图 WebP → 上传派生图） |
| `profile_image.py` | 私有相册服务（private/profiles/{user_id}/ 前缀、代理域素材 URL、本人归属校验、复用 image 校验逻辑） |
| `profile_layout.py` | 布局草稿服务（模块白名单/字段清洗/大小校验、本人图片与前缀校验、展示授权、代理域素材及统计） |
| `schedule.py` | 课表解析与对比算法（CourseSlot 数据类、ICS 解析、ZJUT TXT 解析、compare 对比：周次交集/同教室/冲突/空闲时段）；PDF 文件走 `schedule_pdf.py`，上传接口提示使用预览导入 |
| `schedule_pdf.py` | 教务 PDF 课表解析：pdfplumber 表格/列映射、同格多课、合并节次、跨页课程名拼接、页眉页脚与 PII 过滤；返回 slots、warnings、建议名称 |
| `schedule_service.py` | 课表业务服务；手工创建、本人编辑与版本冲突保护、课表架重命名/存档/拖动排序、上传/查询/可见性/删除，公开读取时脱敏个人日程并排除存档课表 |
| `schedule_group.py` | 课表群组服务：创建/邀请码加入/审批/退群/移除/解散、成员共享课表、逐人共同空闲/共同忙碌/单方忙碌/同教室统计，群内事件脱敏 |
| `rate_limit.py` | 限流服务（Redis 分布式计数器、原子递增+TTL、分层限流规则） |
| `site_setting.py` | 网站设置服务（SiteSetting 读写、公开配置/页脚/法律/社团介绍/注册门控/第三方登录开关聚合，敏感密钥不入此表） |
| `announcement.py` | 公告服务（公开列表：已发布+未过期+置顶在前；管理 CRUD：创建/更新/置顶/发布/删除） |
| `event.py` | 活动服务（活动 CRUD、报名/候补/取消/签到，容量控制、幂等键、候补自动递补、批量统计防 N+1） |
| `page.py` | 动态页面服务（页面 CRUD、版本快照、发布/下线、版本回滚） |
| `admin_image.py` | 图片管理服务（列表/审核/公开/标签/删除/统计，含派生图清理） |
| `avatar.py` | 头像上传服务（预签名直传/上传完成验证/旧头像清理/公开 URL 生成；头像存 public/avatars/{user_id}/ 前缀，限 5MB） |

### app/providers/ — 外部服务适配层

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `aliyun.py` | 阿里云短信 Provider（SMS_PROVIDER=aliyun 时启用） |
| `qq.py` | QQ 互联 OAuth Provider（授权地址、code 换 token、OpenID/UnionID 和用户资料解析） |
| `factory.py` | Provider 工厂（get_storage_provider / get_email_provider[EMAIL_PROVIDER=smtp→SmtpEmailProvider] / get_sms_provider / get_captcha_provider / get_human_verification_provider，按配置选择实现） |
| `storage/base.py` | 存储 Provider 抽象基类（presign_upload / presign_download / head_object / delete_object / get_object_bytes / put_object_bytes / public_url） |
| `storage/cos.py` | 腾讯云 COS 实现（单桶 public/private 前缀隔离、asyncio.to_thread 包装同步 SDK） |
| `storage/__init__.py` | Python 包标记（空文件） |
| `email/base.py` | 邮件 Provider 抽象 + LogEmailProvider（开发模式：打印不真发） |
| `email/smtp.py` | SMTP 邮件 Provider（飞书企业邮箱 SSL，HTML 模板：OTP/注册待审批/审批通过/审批拒绝/测试） |
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
| `versions/131029fbb8f9_add_schedule_name_and_format.py` | 迁移：添加课表 original_name / format 字段 |
| `versions/0addd5ed14cc_add_user_bio_avatar.py` | 迁移：添加用户 bio / avatar_url 字段 |
| `versions/4f8a2c7d91b3_add_profile_layout.py` | 新增 profile_layouts 表及 profile_images.is_displayable 列/索引，承接 0addd5ed14cc |
| `versions/e7f3a91b2d44_add_user_third_party.py` | 新增 user_third_parties 表及 provider 身份/UnionID/用户索引，承接 4f8a2c7d91b3 |
| `versions/2b7e4c9d1a60_add_user_legal_consent.py` | users 新增 terms_version / privacy_version / legal_accepted_at，承接 e7f3a91b2d44 |
| `versions/7b3d1c8a4f20_add_schedule_appointments.py` | 节次预约原型的建表迁移（后续由 af1c280b769e 汇合/升级） |
| `versions/af1c280b769e_dated_meals.py` | 汇合 main 迁移，升级到日期日程；遇到非空的旧原型预约会停止 |
| `versions/c4a91e7d2b60_add_schedule_archive.py` | 课表架：schedules.is_archived（默认 false），存档课表不参与公开查询 |
| `versions/e9b2f7c4a1d0_add_schedule_sort_order.py` | 课表架拖动顺序 schedules.sort_order（默认 0），GET /schedule/mine 按此排序 |
| `versions/a7d2e9c14b83_add_schedule_groups.py` | 当前 head：课表群组 schedule_groups / schedule_group_members（邀请码、审批、成员共享课表） |

### scripts/ — 运维/测试脚本

| 文件 | 用途 |
|---|---|
| `create_admin.py` | 管理员初始化脚本：账号不存在时创建；账号已存在时确保 `admin` 角色、`active` 状态和 `is_active=true`；仅传入 `--reset-password` 时重置密码 |
| `cos_smoke_test.py` | COS 连通性冒烟测试（验证 SecretId/SecretKey/Bucket 配置正确） |
| `setup_cos_cors.py` | 配置 COS 桶 CORS 规则（允许前端直传 PUT/POST，前端上传必需） |
| `setup_cos_public_read.py` | 配置 COS public/ 前缀公有读策略（公开图片可匿名访问） |
| `verify_cos_cors.py` | 验证 COS CORS 配置是否正确生效 |
| `e2e_auth_test.py` | 认证端到端测试（含每步滑块验证、协议同意字段；注册 → 邮箱/手机验证 → 管理员审批 → 登录 → 刷新令牌） |
| `e2e_upload_test.py` | 图片上传端到端测试（预签名直传 → upload-complete → 列表验证） |
| `e2e_processing_test.py` | 图片处理端到端测试（上传 → worker 生成缩略图/展示图 → 派生图验证） |
| `e2e_profile_album_test.py` | 私有相册端到端测试（上传私有图 → 代理域 URL 访问 → 隔离验证） |
| `e2e_profile_real_test.py` | 个人空间真实链路端到端测试（完整 Profile 流程验证） |

### tests/ — 单元测试

| 文件 | 用途 |
|---|---|
| `__init__.py` | Python 包标记（空文件） |
| `test_auth.py` | 认证测试（注册/登录/Token 刷新/权限） |
| `test_schedule.py` | 课表对比算法测试（周次交集/同教室检测/时间冲突判定） |
| `test_schedule_editing.py` | 编辑 API 契约测试：保存/重读/删除、版本冲突、本人权限、公开日程隐私、字段边界、旧数据兼容、按周占用，以及课表架重命名/存档/恢复、存档排除公开查询、拖动排序完整顺序校验和时段边界默认/乱序校验 |
| `test_schedule_pdf.py` | PDF 解析测试：同格多课、跨页名称拼接、列映射、缺周次告警、PDF 预览接口响应与错误码 |
| `test_schedule_groups.py` | 群组测试：逐人忙闲统计、真实 PostgreSQL 上的创建/加入/审批/共享/移除/解散流程与隐私脱敏 |
| `test_schedule_parser.py` | 课表解析测试（ZJUT TXT 格式/周次范围/节次解析/空格/换行/异常格式） |
| `test_image_processing.py` | 图片处理测试（WebP 生成/尺寸裁剪/防解压炸弹/非法文件拒绝） |
| `test_permissions.py` | 权限矩阵测试（各角色操作权限验证） |
| `test_profile_layout.py` | 个人主页布局路由/service 契约测试（发布/丢弃、主题范围与素材授权、本人素材清单、匿名公开页隐私与统一 404；DB/存储为测试替身） |

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
| `API.md` | 已实现的 117 个 API 路径 / 139 个方法端点；含人机验证、QQ OAuth、主页与绑定契约、课表架命名/存档/排序、PDF 课表预览、课表群组、对比页固定约定、课表网格邀请通知、安全限流及前后端函数/类型参考 |
| `WHATFILE.md` | 本文件 — 项目全部文件用途索引 |
| `DEPLOYMENT.md` | 部署说明（EdgeOne Pages + 宝塔 2C2G + 本机 PostgreSQL/Redis、关键步骤索引） |
| `SECURITY.md` | 安全基线（上线前 15 项检查清单、日志脱敏规则、HttpOnly Cookie 会话、OAuth/代理域注意事项） |

### docs/ 文档变更记录（2026-11-19，历史）

| 文档 | 当次更新内容 |
|---|---|
| `README.md` | 新增第三方登录/法律页面/图片代理说明、端口与 URL 对照、2026-11-19 变更总览；修正迁移 head 与 API 数量 |
| `API.md` | 新增 QQ OAuth、第三方绑定、后台 OAuth 测试接口；更新 Cookie 会话、协议同意、代理域 URL、前端函数与服务索引 |
| `WHATFILE.md` | 登记 9 个新增文件、6 个新增环境变量、2 个迁移、6 个 Tab 设置页及 QQ/法律页文件 |
| `DEPLOYMENT.md` | 补充 QQ 回调、Cookie 跨域/HTTPS、EdgeOne 前端环境与 OAuth 上线检查 |
| `BT-DEPLOYMENT.md` | 补充生产环境 QQ 变量、回调地址、HttpOnly Cookie 与代理域说明 |
| `SECURITY.md` | 补充 7 天 Cookie、CSRF/CORS、QQ state、回调域名白名单、私有图片代理访问策略 |

后续变更（含课表架命名/存档/排序与课表拖动）以 README「变更记录」和 `docs/API.md` 为准；本表仅保留 2026-11-19 的历史记录。

### 课表约定（旧约饭后端保留）

| 项目内路径 | 用途 |
|---|---|
| backend/app/models/schedule_appointment.py | 预约、参与者（本人课表、选择、最终确认、站内提醒）、账号级日期日程 |
| backend/app/services/meal_times.py | 教学周转日期、合并课程与日程占用、缓冲计算和候选排序 |
| backend/app/services/schedule_appointment.py | 邀约授权与流转、确认写入、取消清理、日程与提醒查询；对比页固定时间约定（按周/星期/节次换算、接受即写双方日程） |
| backend/migrations/versions/7b3d1c8a4f20_add_schedule_appointments.py | 本地节次原型的建表历史 |
| backend/migrations/versions/af1c280b769e_dated_meals.py | 汇合 main 迁移，升级到日期日程；遇到非空的旧原型预约会停止 |
| backend/tests/test_meal_planner.py | 分钟边界、真实 PostgreSQL 上的 API 流程、隐私、失效与回滚验证 |
| backend/tests/test_schedule_meetup.py | 对比页固定时间约定的真实 PostgreSQL 流程：创建、接受即写双方日程、取消清理 |
| frontend/src/components/schedule/CalendarAgenda.vue | 本人按日期查看、新增、编辑、删除一次性日程 |
| backend/app/services/schedule_timing.py | 课表作息 1–24 节的生成/校验、默认 12 节兼容、时段边界默认/规范化，以及给约饭匹配使用的教学日历转换 |
