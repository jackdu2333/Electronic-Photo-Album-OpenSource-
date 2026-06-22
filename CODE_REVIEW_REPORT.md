# 电子相框项目代码审查报告

> 审查时间：2026-06-02
> 审查版本：v2.0.3 + 最新提交 (63be7e4)
> 最后更新：2026-06-22（v3.0.1 开源准备）

---

## Critical 修复状态

| # | 问题 | 状态 | 说明 |
|---|------|------|------|
| 1 | SSL 证书验证被禁用 | ✅ 已修复 | `routes/api.py` 默认使用系统证书链，仅 debug 下跳过 |
| 2 | Jinja2 XSS 漏洞 | ✅ 已修复 | 使用 `tojson` 过滤器 |
| 3 | innerHTML XSS（文件名） | ✅ 已修复 | 改用 DOM API + textContent |
| 4 | innerHTML XSS（日期） | ✅ 已修复 | 改用 textContent + DOM API |
| 5 | 明文密码时序攻击 | ✅ 已修复 | 使用 `hmac.compare_digest` |
| 6 | Python CI 缺失 | ✅ 已修复 | 新增 `.github/workflows/python-ci.yml`（ruff + pytest） |
| 7 | SECRET_KEY 不安全默认值 | ✅ 已修复 | docker-compose 使用 `?` 语法，缺少时启动失败 |

---

## 总览

| 严重度 | 数量 | 核心问题 |
|--------|------|----------|
| Critical | 7 | SSL 禁用、XSS 漏洞、认证绕过风险、CI 缺失 |
| High | 13 | 性能瓶颈、内存泄漏、数据库连接管理、内联 CSS 膨胀 |
| Medium | 17 | 全局状态管理、线程安全、代码重复、测试质量 |
| Low | 12 | 命名规范、无障碍、手动版本号、文档占位符 |

---

## Critical（必须立即修复）

### 1. SSL 证书验证被禁用
**位置**: `routes/api.py:41`, `routes/api.py:324`

```python
request_context = ssl._create_unverified_context()
```

每日一言和天气 API 的所有外部 HTTP 请求都跳过了 TLS 证书验证，生产环境下存在中间人攻击风险。攻击者可注入恶意 API 响应。

**建议**: 移除 `_create_unverified_context()`，使用系统默认证书链。如遇证书问题应安装 CA 包而非禁用验证。

---

### 2. Jinja2 模板注入导致的 XSS 漏洞
**位置**: `templates/index.html:2755`

```html
const CURRENT_USER = "{{ username }}";
```

`username` 直接嵌入 `<script>` 标签，Flask 默认的 HTML auto-escape 会破坏 JavaScript 语法，某些特殊字符组合仍可能导致注入。

**建议**: 使用 `|tojson` 过滤器：
```html
const CURRENT_USER = {{ username | tojson }};
```

---

### 3. 文件名未转义的 innerHTML XSS
**位置**: `static/script.js:726`

```javascript
card.innerHTML = `...${file.name}...`;
```

`file.name` 来自用户本地文件系统，包含 `<img onerror=alert(1)>` 类文件名时可直接执行脚本。

**建议**: 用 `textContent` 设置文件名，用 `style.backgroundImage` 设置背景图。

---

### 4. 日期叠加层 innerHTML 未转义
**位置**: `static/script.js:282-293`

```javascript
dateEl.innerHTML = htmlContent;
```

`date` 来自后端 API，若后端数据被篡改可导致存储型 XSS。

**建议**: 用 `textContent` + DOM API 构建内容，或对 `date` 做 `escapeHtml()` 处理。

---

### 5. 明文密码回退逻辑存在时序攻击
**位置**: `auth.py:206-211`

```python
if not password_hash.startswith('pbkdf2:'):
    if password_hash == password:  # 明文比较！
        self._users[username] = hash_password(password)
        return True
```

字符串 `==` 比较会在第一个不匹配字符处短路返回，攻击者可通过精确计时逐字符猜解密文。

**建议**: 使用 `hmac.compare_digest(password_hash, password)` 做常量时间比较。

---

### 6. CI 完全没有 Python 测试流水线
**位置**: `.github/workflows/build.yml`

当前唯一的 CI workflow 只构建 Android APK，Python 后端（项目核心）没有任何自动化测试、lint、安全扫描。

**建议**: 新增 `python-ci.yml`，包含 `pytest`、`ruff check`、`docker build` 三个 stage。

---

### 7. 生产环境默认 SECRET_KEY 为不安全值
**位置**: `docker-compose.yml:26`

```yaml
SECRET_KEY=${SECRET_KEY:-change-me-in-production}
```

如果部署者忘记设置 `.env`，Flask session 签名密钥就是一个公开可预测的字符串，攻击者可伪造 session cookie。

**建议**: 去掉 fallback 默认值，让容器在缺少 `SECRET_KEY` 时直接启动失败。

---

## High（建议尽快修复）

### 性能问题

| 问题 | 位置 | 描述 | 建议 |
|------|------|------|------|
| 每次 DAO 调用都创建新连接 | `services/database.py:94-119` | 连接创建/销毁开销显著 | 引入连接池或请求级连接 |
| `get_photo_index()` 全量查库 | `services/photo_index.py:77-100` | 每次推荐都全量 SELECT + 全量替换内存 | 改为缓存 + 脏标记机制 |
| 推荐流程中多次调用 `get_photo_index()` | `services/recommendation.py:91-164` | 单次推荐最多 3 次全量查库 | 入口处调用一次并传递引用 |
| 每次请求都重新加载 JSON 元数据 | `routes/api.py:145-160` | `PhotoMetadataService.load()` 每次从磁盘读取 | 添加文件 mtime 检查 |

### 安全问题

| 问题 | 位置 | 描述 | 建议 |
|------|------|------|------|
| 上传文件无大小预检 | `routes/upload.py:48-78` | 压缩循环可能耗尽内存 | 入口加文件大小检查 |
| `isolation_level=None` 导致 autocommit | `services/database.py:35-38` | SELECT + UPDATE 不在显式事务内，存在竞态 | 包在 `BEGIN IMMEDIATE` 事务内 |

### 前端问题

| 问题 | 位置 | 描述 | 建议 |
|------|------|------|------|
| 2500+ 行内联 CSS 阻塞渲染 | `templates/index.html:34-2534` | 无法利用浏览器 CSS 缓存 | 提取为独立的 `frame.css` 文件 |
| 定时器泄漏 | `script.js:207,646`, `index.html:2823,2880` | 返回值未存储，无法清除 | 所有定时器 ID 存入变量 |
| 重复的 MutationObserver | `script.js:968-1012` | 每张照片触发两次方向分类逻辑 | 删除外部 observer |
| 全局命名空间污染 | `script.js:517-528` | 为兼容 Android TV 暴露全局函数 | 使用 `window.PhotoFrame` 命名空间 |

### 部署问题

| 问题 | 位置 | 描述 | 建议 |
|------|------|------|------|
| 全量 COPY 无 .dockerignore | `Dockerfile:34` | ~~`.git/`、`.env`、`*.db` 全部打入镜像~~ ✅ 已修复（已创建 `.dockerignore`） |
| 无锁文件，依赖版本约束过宽 | `requirements.txt` | 不同环境安装可能得到不同版本 | 生成 `requirements.lock` |

---

## Medium（建议后续优化）

### 架构问题

| 问题 | 位置 | 描述 |
|------|------|------|
| 全局可变状态通过 `global` 设置 | `services/database.py:14-21` | 多 worker 场景下可能不一致 |
| 类变量 `_metadata` 无线程保护 | `services/metadata.py:33` | 后台 rebuild 和请求线程可能并发修改 |
| 内存索引 + SQLite 双写 | `services/photo_index.py:290-295` | 先写内存再写 DB，不一致风险 |
| 登录失败记录仅在内存中 | `auth.py:100` | 重启后锁定计数器丢失 |

### 测试覆盖盲区

| 未覆盖模块 | 风险 |
|---|---|
| 照片删除 API (含路径穿越防护) | 安全边界未验证 |
| 登录失败锁定 (5次/5分钟) | 暴力破解防护失效 |
| `get_deep_sea_candidate` | 深海打捞核心逻辑 |
| EXIF 日期提取 | 日期提取失败无感知 |

### 代码重复

| 函数 | 重复位置 |
|------|----------|
| `showToast` | `script.js:20-40`, `manage.html:786-801` |
| `photoStaticUrl` | `script.js:42-47`, `manage.html:436-441` |
| `.salvage-filter` 样式 | `index.html:2504-2533`, `style.css:619-652` |

### 其他问题

| 问题 | 位置 | 描述 |
|------|------|------|
| Migration 异常被静默吞掉 | `services/database.py:80-83` | 应只捕获 `sqlite3.OperationalError` |
| 批量上传失败不中断 | `routes/upload.py:48-53` | 前 2 个已保存文件不会被清理 |
| 留言轮询无错误退避 | `script.js:559-647` | 固定 30 秒，网络异常时浪费带宽 |
| 冗余的条件分支 | `index.html:2783-2789` | 两个分支完全相同 |
| manage.html 双 `<body>` 标签 | `manage.html:1-392` | HTML 结构错误 |

---

## Low（可择机修复）

| 问题 | 位置 | 描述 |
|------|------|------|
| SHA1 生成锁文件名 | `services/photo_index.py:38` | 建议统一使用 SHA256 |
| 使用 Pillow 私有方法 `_getexif()` | `services/metadata.py:150` | 使用 `image.getexif()` 公开 API |
| timeout 计算逻辑有误 | `services/database.py:108` | `max()` 应为 `min()` 或直接使用传入值 |
| `lang="en"` 属性不一致 | `index.html:2` | 应统一为 `zh-CN` |
| 动态创建的图片缺少 alt 属性 | `script.js:260` | 对屏幕阅读器不友好 |
| 手动版本号 cache busting | `index.html:2757` | 建议使用文件哈希自动 busting |
| Gunicorn worker 数硬编码 | `Dockerfile:51` | 通过环境变量配置 |
| 项目 URL 为占位符 | `pyproject.toml:49` | ~~替换为实际仓库地址~~ ✅ 已修复 |
| 根目录存在孤儿测试文件 | `test_route.py` | ~~调试残留，建议删除~~ ✅ 已从仓库移除 |
| manage.html 独立完整内联样式 | `manage.html` | 设计风格与其他页面不一致 |

---

## 架构级建议

| 维度 | 现状 | 建议 |
|------|------|------|
| 数据源双写 | 内存 `_photo_index` + SQLite 双写 | 以 SQLite 为唯一数据源，去掉内存索引 |
| 连接管理 | 每次操作新建连接 | 请求级连接（Flask `g`）或简单连接池 |
| 全局状态 | `global` 变量散落各模块 | 封装为 App 级配置对象，通过 `current_app` 访问 |
| 元数据双存储 | JSON 文件 + SQLite 各存一份 | 统一到 SQLite，JSON 仅作导入/导出用 |
| 认证方式 | Basic Auth + Session 混合 | API 场景考虑 Bearer Token |
| CI/CD | 仅 Android APK 构建 | 新增 pytest + lint + docker build 流水线 |

---

## 优先修复顺序

**第一批（安全 + 基础设施）**：
1. 修复 SSL 验证禁用（Critical 1）
2. 修复 XSS 漏洞（Critical 2-4）
3. 修复明文密码时序攻击（Critical 5）
4. 添加 Python CI 流水线（Critical 6）
5. 修复 SECRET_KEY 默认值（Critical 7）

**第二批（性能 + 稳定性）**：
6. 引入数据库连接池
7. 优化 `get_photo_index()` 全量查库
8. 添加 `.dockerignore`
9. 生成依赖锁文件

**第三批（代码质量）**：
10. 提取 2500 行内联 CSS
11. 清理定时器泄漏
12. 统一全局状态管理
13. 补充核心模块测试
