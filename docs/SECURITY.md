# 安全基线

上线前至少完成以下检查（对应架构文档「十二、安全基线」）：

1. 全站 HTTPS，HSTS 按部署情况启用。
2. CORS 只允许正式前端来源，生产禁用 `*` 搭配凭证。
3. Cookie 认证启用 CSRF 防护；JWT 刷新令牌可撤销、轮换。
4. 密码使用 Argon2id/bcrypt；管理员强制 MFA。
5. 邮箱/手机验证码哈希存储、短时效、单次使用、用途隔离。
6. CDN/WAF + API 层 + Redis 应用层多层限流。
7. 文件类型、大小、内容解码校验；对象存储默认私有。
8. SQL 使用 ORM 参数化查询；输出上下文安全转义。
9. 动态页面采用白名单 Schema；禁止任意脚本执行。
10. 管理操作、登录失败、权限变更、配置修改有审计日志。
11. `.env`、Secret、私钥、备份文件不进入 Git。
12. 数据库和对象存储有备份、恢复演练和生命周期策略。
13. 依赖定期更新，生产镜像固定版本并扫描漏洞。
14. 生产关闭 debug、限制 API 文档访问、隐藏内部异常。
15. 个人信息最小化收集、访问控制、脱敏、保留和删除。

## 当前会话与 OAuth 实现

- Access Token 默认 15 分钟，仅保存在前端内存；Refresh Token 默认 7 天，由后端写入 `HttpOnly` Cookie（`Path=/api/v1/auth`，生产 `Secure`，默认 `SameSite=Lax`），前端不读取、不持久化令牌。
- 前端只保存 `localStorage.auth_session=1` 作为“可能已登录”的标记；退出登录、刷新失败或服务端撤销会话后清除。
- 前后端跨 `www.furzl.cn` 与 `api.furzl.cn` 时，CORS 必须限定来源并允许凭据，禁止 `* + credentials`；Cookie 认证接口须配合 CSRF 防护，不能只依赖前端路由守卫。
- QQ OAuth 使用 Redis 保存 10 分钟有效、一次性消费的 `state` 和未绑定临时凭证；回调地址固定为 `https://www.furzl.cn/oauth/qq`，`return_to` 只接受站内绝对路径。
- `QQ_APP_ID` / `QQ_APP_KEY` 只从环境变量或 Secret 注入，不写入 `site_settings`、不返回前端；后台 Provider 测试只返回是否配置与回调地址。
- 登录、绑定、解绑和 OAuth 开始/完成均要校验账号状态；未审批/禁用账号不能通过 QQ 绕过审批。

## 图片代理域风险

- 公开图、私有缩略图、下载和头像的展示 URL 统一走 `PUBLIC_ASSET_BASE_URL`，当前代码返回代理域 URL，不包含 COS 签名。
- 因此访问控制必须落在代理/CDN 回源策略：`private/` 路径不能被公开读；不要为了省事把整个 COS 桶设为公有读。
- COS 原生预签名 URL 只用于浏览器上传直传；展示/下载接口不应把 COS 原生地址返回给前端。
- 后端仍必须校验图片归属、审核状态和公开状态；URL 可访问不等于资源应被任意用户获取。若需要真正短时、不可猜测的私有链接，应在代理层重新引入签名票据。

## 法律与数据留存

- 注册必须分别同意《用户协议》和《隐私政策》，后端记录 `terms_version`、`privacy_version` 与 `legal_accepted_at`，不能只依赖前端勾选。
- 涉嫌违法、侵权、危害网络安全或社区安全的内容，可依法删除、下架、限制功能或封禁账号，并保存必要记录。
- 公安机关、检察院、法院、网信、市场监管等有权机关依法定程序提出要求时，依法保存并提供必要的账号信息、联系方式、登录日志、发布记录和文件元数据；无关第三方不得获取。
- 第三方服务（EdgeOne、腾讯云 COS、QQ 互联、阿里云短信、飞书企业邮箱、Microsoft Bing、Google Fonts）的处理目的和官方隐私政策链接必须与实际接入保持一致，服务变更时同步更新法律页面。

## 敏感信息脱敏

- 日志不记录密码、OTP、Cookie、Authorization、Refresh Token、QQ App Key、完整预签名 URL 与 Secret。
- 邮箱/手机号/IP 输出前脱敏（见 `app/utils/__init__.py`）。

## 认证选择

默认采用「短时 Access Token + HttpOnly Refresh Cookie」组合；纯 Bearer 方案作为备选。
详见架构文档附录 B5。

## 信任代理

只信任来自本机 Nginx 的 `X-Forwarded-For`，无条件信任客户端转发头会被利用。
