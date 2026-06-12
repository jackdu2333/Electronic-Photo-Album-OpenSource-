# 全局优化升级清单 v2.1.0

> 优化时间：2026-06-02
> 基于版本：v2.0.3 (commit 63be7e4)
> 目标：安全加固 + 性能优化 + 架构改进
> **已生产环境 Review 通过，Python/JS 语法验证 OK**

---

## 一、修改文件清单（需替换）

### 后端 Python 文件

| 文件路径 | 修改内容 | 严重度 |
|----------|----------|--------|
| `routes/api.py` | SSL 证书验证修复、元数据 mtime 缓存、排序 key 修复 | Critical |
| `routes/messages.py` | sender/content XSS 转义 | Medium |
| `routes/upload.py` | （未修改，保留原样） | - |
| `auth.py` | 明文密码时序攻击修复（hmac.compare_digest） | Critical |
| `services/database.py` | Migration 异常处理精确化、timeout 逻辑修复、深海打捞事务保护 | High |
| `services/metadata.py` | 线程安全（RLock）、公开 API `getexif()` 替换私有方法 | Medium |
| `services/photo_index.py` | SHA256 替换 SHA1、add_photo 先写 DB 再写内存 | Medium |
| `services/recommendation.py` | 单次 `get_photo_index()` 调用，传递引用避免重复查库 | High |
| `services/image.py` | 移除 smart_compress 重复 resize，节省内存 | Medium |

### 前端 JavaScript/HTML 文件

| 文件路径 | 修改内容 | 严重度 |
|----------|----------|--------|
| `static/script.js` | XSS 修复（innerHTML→textContent）、定时器 ID 存储、PhotoFrame 命名空间、消息轮询指数退避、移除冗余 MutationObserver、fg.onerror 兜底 | Critical/High |
| `templates/index.html` | username 使用 `tojson` 过滤器、lang="zh-CN"、删除冗余条件分支、定时器 ID 存储 | Critical/Low |

### 部署配置文件

| 文件路径 | 修改内容 | 严重度 |
|----------|----------|--------|
| `.dockerignore` | **新建** - 排除 .git/.env/__pycache__/tests 等 | High |
| `docker-compose.yml` | SECRET_KEY 不设默认值、移除过时 version 字段 | Critical |
| `Dockerfile` | Gunicorn workers/threads/timeout 改为环境变量配置 | Medium |

---

## 二、具体变更详情

### 2.1 安全修复（Critical）

#### SSL 证书验证恢复
**文件**: `routes/api.py`
- `_fetch_json()`: 生产环境使用 `ssl.create_default_context()`，仅 DEBUG 模式允许 unverified
- `weather_config()`: 同上

#### XSS 漏洞修复
**文件**: `static/script.js`
- 日期叠加层：`innerHTML` → `textContent` + DOM API
- 文件预览：`innerHTML` → `textContent` 渲染文件名

**文件**: `templates/index.html`
- `CURRENT_USER`: `"{{ username }}"` → `{{ username | tojson }}`

**文件**: `routes/messages.py`
- sender/content 入库前 `html.escape()` 转义

#### 明文密码时序攻击修复
**文件**: `auth.py`
- `password_hash == password` → `hmac.compare_digest(password_hash, password)`

#### SECRET_KEY 默认值移除
**文件**: `docker-compose.yml`
- `${SECRET_KEY:-change-me-in-production}` → `${SECRET_KEY:?请在 .env 中设置 SECRET_KEY}`

### 2.2 性能优化（High）

#### 推荐算法单次查库
**文件**: `services/recommendation.py`
- `get_next_photo()` 仅在入口调用一次 `get_photo_index()`，传递给 `_regular_selection(photo_index)`
- 单次推荐最多 3 次全量查库 → 1 次

#### 元数据 mtime 缓存
**文件**: `routes/api.py`
- `_merge_note_fields()` 添加文件 mtime 检查，仅在 JSON 文件变化时重新加载

#### 图片压缩内存优化
**文件**: `services/image.py`
- 移除 `original_for_round2 = resize_to_limit(img, max_resolution_px)` 的重复调用
- 改为引用 `_round2_source = current_img`，第一轮 quality 循环不修改 current_img

#### 深海打捞事务保护
**文件**: `services/database.py`
- `get_deep_sea_candidate()` 的 SELECT + UPDATE 包在 `BEGIN IMMEDIATE` 事务内
- 避免并发场景下的 TOCTOU 竞态

### 2.3 架构改进（Medium）

#### 线程安全
**文件**: `services/metadata.py`
- `PhotoMetadataService._lock = threading.RLock()` 保护 `_metadata` 读写

#### 双写一致性
**文件**: `services/photo_index.py`
- `add_photo()`: 先写 DB，成功后再更新内存索引

#### 异常处理精确化
**文件**: `services/database.py`
- Migration 从 `except Exception: pass` → `except sqlite3.OperationalError` 并检查错误消息
- timeout 从 `max()` → 直接使用传入值

#### 公开 API 替换
**文件**: `services/metadata.py`
- `image._getexif()` → `image.getexif()` (Pillow >= 6.0 公开 API)

### 2.4 前端优化（High）

#### 定时器泄漏修复
**文件**: `static/script.js`, `templates/index.html`
- 所有 `setInterval` 返回值存入变量：`forceShowTimer`, `clockTimer`, `weatherTimer`, `messageTimer`
- 消息轮询改为 `setTimeout` 链式调用 + 指数退避

#### 全局命名空间保护
**文件**: `static/script.js`
- Android TV 函数改为 `window.PhotoFrame.prevImage` / `window.PhotoFrame.nextImage`
- 保留 `window.prevImage` / `window.nextImage` 向后兼容

#### 冗余代码清理
**文件**: `static/script.js`
- 移除 `initSlideClassObserver()` 和重复的 MutationObserver（已在 `fg.onload` 中处理）

**文件**: `templates/index.html`
- 删除问候语 `if/else` 两个分支完全相同的冗余判断
- `lang="en"` → `lang="zh-CN"`

#### 图片加载失败兜底
**文件**: `static/script.js`
- 前景图添加 `fg.onerror`，加载失败时 3 秒后跳到下一张

### 2.5 部署优化

#### .dockerignore 新建
**文件**: `.dockerignore`（新建）
- 排除 `.git/`、`.env`、`__pycache__/`、`tests/`、`*.db`、`logs/` 等
- 减少镜像体积，防止敏感信息泄露

#### Gunicorn 可配置化
**文件**: `Dockerfile`
- `--workers 2 --threads 4` → `--workers ${GUNICORN_WORKERS:-2} --threads ${GUNICORN_THREADS:-4}`
- 新增 `--timeout ${GUNICORN_TIMEOUT:-120}` 防止启动慢时被 kill

#### Compose 版本声明移除
**文件**: `docker-compose.yml`
- 删除过时的 `version: '3.8'`，使用 Compose V2 语法

---

## 三、云端升级操作步骤

### 方式一：替换文件（推荐，保留现有数据）

```bash
# 1. SSH 进入服务器
ssh your-server

# 2. 进入项目目录
cd /path/to/digital-photo-frame

# 3. 备份当前代码
cp -r . ../digital-photo-frame-backup-$(date +%Y%m%d)

# 4. 上传修改的文件（共 13 个）
# 后端 (9 个)
scp routes/api.py user@server:/path/to/project/routes/api.py
scp routes/messages.py user@server:/path/to/project/routes/messages.py
scp auth.py user@server:/path/to/project/auth.py
scp services/database.py user@server:/path/to/project/services/database.py
scp services/metadata.py user@server:/path/to/project/services/metadata.py
scp services/photo_index.py user@server:/path/to/project/services/photo_index.py
scp services/recommendation.py user@server:/path/to/project/services/recommendation.py
scp services/image.py user@server:/path/to/project/services/image.py

# 前端 (2 个)
scp static/script.js user@server:/path/to/project/static/script.js
scp templates/index.html user@server:/path/to/project/templates/index.html

# 部署配置 (3 个)
scp .dockerignore user@server:/path/to/project/.dockerignore
scp docker-compose.yml user@server:/path/to/project/docker-compose.yml
scp Dockerfile user@server:/path/to/project/Dockerfile

# 5. 确保 .env 中有 SECRET_KEY
grep SECRET_KEY .env

# 6. 重建并重启
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 7. 检查日志
docker-compose logs -f --tail=50
```

### 方式二：Git Pull（如果云端已关联远程仓库）

```bash
cd /path/to/digital-photo-frame
git pull origin main
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 方式三：宝塔面板部署

1. 通过宝塔文件管理器上传 13 个修改文件到对应目录
2. 确保 `.env` 配置了 `SECRET_KEY`
3. 在 Docker 管理中重建镜像
4. 重启容器

---

## 四、升级后验证清单

| 检查项 | 验证方法 |
|--------|----------|
| SSL 正常 | 天气 API 和每日一言能正常拉取 |
| 认证正常 | 登录页面能正常登录，密码验证正确 |
| XSS 防护 | 上传文件名含 `<script>` 时不会执行 |
| 推荐算法 | 照片轮播正常，不卡在某一张 |
| 留言功能 | 发送/接收留言正常，内容正确显示 |
| 深海打捞 | 老照片能正常被打捞展示 |
| Docker 健康检查 | `docker ps` 显示 healthy |
| Gunicorn 启动 | 日志显示 worker 正常启动 |

---

## 五、Review 修复补充

> 以下为生产环境 Review 发现并修复的额外问题

| 文件 | 问题 | 修复 |
|------|------|------|
| `auth.py` | 明文密码校验失败未调用 `_record_failure()`，暴力破解不受限 | 补充失败记录和成功记录 |
| `routes/messages.py` | `html.escape()` 与前端 `textContent` 双重转义，`&` 显示为 `&amp;` | 移除服务端转义，依赖前端 textContent |
| `services/metadata.py` | `get()`/`set()`/`update()`/`clear()`/`all()` 未获取 `_lock` | 全部补上 `with cls._lock:` |
| `templates/index.html` | BABY_CONFIG 同 CURRENT_USER 存在模板注入风险 | 改为 `|tojson` 过滤器 |
| `static/script.js` | `fg.onerror` 设置在 `fg.src` 之后，可能竞态 | 移到 src 之前，补充 isNavigating 检查 |
| `services/photo_index.py` | `add_photo` 内存 append 无去重 | 追加前先移除同 URL 旧条目 |
| `services/recommendation.py` | `locals().get()` 可读性差 | 改为显式 `photo_index = None` 哨兵变量 |
| `.dockerignore` | `.gitkeep` 文件名不匹配（实际为 `.keep`） | 修正为 `!static/photos/.keep` |

---

| 操作 | 说明 |
|------|------|
| 删除 `test_route.py` | 项目根目录调试残留文件 |
| 删除 `Gemini_Generated_Image_*.png` | 272KB 测试图片，非项目必需 |
| 清理 `tests/__pycache__/` | 如已被 git 追踪，执行 `git rm -r --cached tests/__pycache__` |
| 更新 `pyproject.toml` URL | 替换 `YOUR_USERNAME` 为实际 GitHub 用户名 |

---

## 六、环境变量新增说明

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `GUNICORN_WORKERS` | 2 | Gunicorn worker 进程数，树莓派可设 1，NAS/云服务器可设 4 |
| `GUNICORN_THREADS` | 4 | 每个 worker 的线程数 |
| `GUNICORN_TIMEOUT` | 120 | Worker 超时秒数，首次启动索引大量照片时可适当增大 |

---

## 七、回滚方案

如果升级后出现问题，可快速回滚：

```bash
# 方式一：使用备份
cp -r ../digital-photo-frame-backup-YYYYMMDD/* .
docker-compose build
docker-compose up -d

# 方式二：Git 回滚
git revert HEAD
docker-compose build
docker-compose up -d
```
