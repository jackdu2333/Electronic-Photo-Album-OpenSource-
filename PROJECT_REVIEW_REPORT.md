## 电子相框开源项目 — 全局自审报告

审查时间：2026-06-22，覆盖 CSS/HTML、JS 逻辑、后端、安全、文档 5 个维度。

---

### 一、必须修复（BUG / 安全问题）

**B1. admin.html 文件夹路径 XSS 漏洞**
`templates/admin.html:154` — 文件夹路径 `f` 直接通过 template literal 插入 innerHTML，未做 HTML 转义。攻击者创建名为 `<img src=x onerror=alert(1)>` 的文件夹即可在管理页执行 JS。`escapedF` 只处理了 onclick 属性的引号转义，display span 完全裸露。

**B2. health.py 版本号过期**
`routes/health.py:31` — `'version': '2.0.1'`，当前版本应为 `3.0.1`。生产环境 health 接口暴露过时版本号。

**B3. Dockerfile / docker-compose healthcheck 打错目标**
Dockerfile:56 和 docker-compose.yml:35 的 healthcheck 都请求 `/`（首页），该路径需认证会 302 到 `/login` 然后 200，导致**健康检查永远通过**。应改为 `/health/ready`。

**B4. API 端点未处理空 JSON body**
`routes/api.py:233`（`update_photo`）和 `api.py:383`（`set_theme`）在 `request.get_json()` 返回 `None` 时直接调用 `.get()`，抛出 AttributeError → 500。应提前检查 `if data is None: return 400`。

**B5. 任意文件系统路径可添加为照片源**
`routes/photos_v3.py:274-300` — `add_folder` 接口只校验目录是否存在，不做路径白名单限制。认证管理员可将 `/etc`、`~/.ssh` 等敏感目录添加为照片源，其中任何图片文件都会被索引并通过 API 暴露。

**B6. test_route.py 仍存在于磁盘**
虽然已从 git 追踪移除，但文件仍在项目目录中，暴露了 `/debug/headers` 端点。应物理删除。

---

### 二、应修复（WARNING）

**W1. 展陈设计 token 声明但未使用**
`static/style.css:40-48` 声明了 9 个 showcase token（`--radius-card`、`--shadow-soft`、`--surface-glass` 等），但全项目无任何模板引用。属于 P2-1 改动引入的死代码。

**W2. style-5 死代码约 200 行**
`templates/index.html:1171-1487` 保留了完整的 style-5 CSS 规则集，style-5 已在路由层被废弃并重定向到 style-4。`static/script.js:100,176` 和 `static/unified-style-menu.js:36` 也有 style-5 残留逻辑。

**W3. v3 photo API 零测试覆盖**
`routes/photos_v3.py` 包含 8 个端点（GET/POST/DELETE photos、metadata、photo-sources），是最新的 API 面，但无任何测试。health 端点（3 个）也无测试。

**W4. .dockerignore 缺少 venv/**
Dockerfile `COPY . .` 会将宿主机的 `venv/` 目录（含平台相关二进制文件）复制进镜像，浪费空间且可能干扰容器内 venv。

**W5. docs/deployment.md 占位符未替换**
第 51 行和第 108 行仍有 `YOUR_USERNAME/digital-photo-frame`，应改为 `jackdu2333/Electronic-Photo-Album-OpenSource-`。

**W6. /static 路径排除认证**
`auth.py:105` 将 `/static` 排除在认证之外。上传到 `static/photos/` 的图片可被无认证访问（UUID 文件名降低了猜中概率，但非根本解决方案）。

**W7. 异常详情泄露**
`app.py:196-197` 和 `routes/api.py:350` 在 500 响应中返回 `str(error)`，可能暴露文件路径或 SQL 错误。生产环境应返回通用错误消息。

**W8. FLASK_DEBUG=true 禁用 SSL 验证**
`routes/api.py:42` 在 debug 模式下使用 `ssl._create_unverified_context()`。`.env` 默认 `FLASK_DEBUG=true`，如果意外部署到生产环境，所有出站 HTTPS 请求易受 MITM 攻击。

**W9. 双风格切换器竞态**
`index.html` 的 legacy `#home-style-switcher` 和 `unified-style-menu.js` 并存。页面加载瞬间两套 UI 同时可见（legacy 先渲染，unified 后隐藏它）。在慢网络下可能闪烁。

**W10. docker-compose 文件绑定挂载风险**
`./data/photos.db`、`./data/photo_metadata.json`、`./data/messages.json` 绑定到文件路径。如果宿主机上这些文件不存在，Docker 会创建同名**目录**，导致应用启动失败。应使用 `touch` 或 entrypoint 脚本预创建。

**W11. routes/admin.py 空蓝图**
该文件注册了一个 `admin_bp` 蓝图但无任何路由，所有管理页路由都在 `routes/main.py` 中。死代码。

**W12. tags/note_title/note_body 无长度限制**
`routes/photos_v3.py:160-189` 接受任意长字符串，存在存储型 DoS 风险。

---

### 三、建议改进（SUGGESTION）

**S1.** 展陈 token 要么在模板中实际引用（如 polaroid/zen/waterfall 的卡片圆角统一用 `--radius-card`），要么移除，避免死声明。

**S2.** 旧 API 端点（`/api/all_photos`、`/api/images`、`/api/update_photo`）应加 `Deprecation` 响应头，引导客户端迁移到 v3。

**S3.** 考虑用 `python-dotenv` 替换 `config.py` 中的手工 `.env` 解析器，处理引号、多行值、变量展开等边界情况。

**S4.** `pyproject.toml` 中 `requires-python = ">=3.9"` 但 Python 3.9 已 EOL，建议提至 `>=3.11`。依赖版本也无上限（如 `Flask>=2.3.0` 允许 Flask 3.x），建议加 `<4.0.0`。

**S5.** 上传照片应从 `static/photos/` 迁到 `data/photos/`，通过认证 API 提供，彻底消除未认证访问向量。

**S6.** 数据库 schema 变更应引入简单版本号机制（哪怕只是一个 `schema_version` 行在 `app_state` 表里），避免每次启动跑 11 条 ALTER TABLE。

---

### 四、确认无问题

- SQL 注入：全部使用参数化查询，无风险。
- CSRF：全局启用 CSRFProtect，v3 API 使用 BasicAuth 合理豁免。
- 密码哈希：PBKDF2-SHA256 600,000 轮次，安全。
- Docker 非 root：多阶段构建 + appuser，正确。
- 路径穿越防护：文件删除和文件服务都有 `abspath + startswith` 边界检查。
- manage.html dirty 状态跟踪逻辑：`padStart` 幂等、`|| ''` 防 null、闭包作用域正确，无问题。
- 依赖一致性：requirements.txt / requirements-dev.txt / pyproject.toml 三方同步。
- 测试通过：95 个 pytest 全部绿色。

---

### 五、修复优先级建议

| 优先级 | 编号 | 预估工作量 |
|--------|------|-----------|
| P0 立即修 | B1 XSS、B3 healthcheck、B6 删 test_route.py | 各 5 分钟 |
| P1 本轮修 | B2 版本号、B4 空 body、B5 路径白名单、W4 .dockerignore、W5 占位符 | 各 10 分钟 |
| P2 下轮修 | W1 死 token、W2 style-5 清理、W7 异常泄露、W8 SSL、W9-W12 | 30-60 分钟 |
| P3 路线图 | S1-S6、W3 测试补全 | 1-2 小时 |
