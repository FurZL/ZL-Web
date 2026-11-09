# EdgeOne Pages 部署说明

## 绑定与配置

1. 在 EdgeOne Pages 控制台新建项目，绑定 Git 仓库或上传构建产物。
2. 构建命令：`npm run build`；输出目录：`dist`。
3. 添加自定义域名 `www.example.com`，按控制台完成 DNS 验证与 HTTPS。

## SPA 路由回退

Vue Router 使用 `createWebHistory()`，需将未知前端路由回退到 `index.html`：

```text
/*  → /index.html   （仅前端站点）
```

不要将 API 域名配置成 SPA fallback。

## 环境变量

生产构建前在控制台或 `.env.production` 配置：

```dotenv
VITE_API_BASE_URL=https://api.example.com/api/v1
```

`VITE_*` 只会进入浏览器构建产物，禁止放数据库密码、JWT Secret、COS Secret 等敏感信息。

## 发布流程

1. `npm ci`
2. `npm run build`，确认产物为 `dist/`
3. 先发布预览环境，验证路由、登录、上传、API CORS 和缓存
4. 正式发布后确认 HTTPS、缓存刷新和回滚能力