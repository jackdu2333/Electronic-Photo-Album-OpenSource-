# 生产环境部署分析报告

> 分析时间：2026-06-02
> 目标环境：阿里云 2核2G + 宝塔面板 + Nginx
> 基于代码版本：v2.1.0（全局优化后）

---

## 一、现有生产环境架构

### 1.1 服务器规格

| 项目 | 配置 |
|------|------|
| 云服务商 | 阿里云 |
| CPU | 2 核 |
| 内存 | 2 GB |
| 部署方式 | 宝塔面板 Python 项目管理器 |
| 进程管理 | Supervisor (守护进程) |
| Web 服务器 | Nginx 反向代理 |
| 应用端口 | 5000 (内网) → 80/443 (外网) |

### 1.2 历史故障记录

| 故障类型 | 原因 | 解决方案 |
|----------|------|----------|
| 夜间 OOM | 高并发读取致 RAM 耗尽 | Gunicorn gthread 异步 + Nginx 前置阻断 |
| 线程耗尽 | Bot 恶意扫描非标端口 | Nginx 前置防护 + 限制访问 |
| ERR_EMPTY_RESPONSE | 端口被幽灵进程占用 | `fuser -k -9 5000/tcp` 强杀 |
| 守护进程冲突 | 宝塔 Python管理器 + Supervisor 双重接管 | 仅使用 Python 项目管理器 |
| 面板 404 | 未输入安全入口后缀 | `bt 14` 查看安全链接 |

---

## 二、本次优化与生产环境的差距分析

### 2.1 已修复的关键差距

| 差距项 | 问题描述 | 修复方案 |
|--------|----------|----------|
| **worker_class** | 生产文档要求 `gthread`，Dockerfile 默认 `sync` | 添加 `GUNICORN_WORKER_CLASS=gthread` |
| **workers 数量** | 2核服务器公式 (CPU×2+1)=5，但需预留 Nginx/OS | 默认 3，可通过环境变量覆盖 |
| **绑定地址** | 宝塔部署需 `127.0.0.1:5000`（Nginx 前置） | 添加 `GUNICORN_BIND` 环境变量 |

### 2.2 已验证的兼容性

| 项目 | 状态 | 说明 |
|------|------|------|
| Python 3.11 | ✅ OK | 宝塔 Python 项目管理器支持 |
| SQLite WAL 模式 | ✅ OK | 2核2G 足够，无外部 DB 依赖 |
| 内存占用 | ✅ OK | gthread 共享 worker 内存，3 workers × ~50MB = ~150MB |
| 启动时间 | ✅ OK | timeout=120s 覆盖首次索引构建 |
| Nginx 反向代理 | ✅ OK | bind 127.0.0.1:5000 仅内网访问 |

---

## 三、生产环境部署方案

### 方案 A：宝塔 Python 项目管理器（推荐，与现有环境一致）

#### 3.1 部署步骤

```bash
# 1. SSH 进入服务器
ssh root@your-server

# 2. 备份现有代码
cp -r /www/wwwroot/photo_frame /www/wwwroot/photo_frame_backup_$(date +%Y%m%d)

# 3. 拉取最新代码（或上传修改文件）
cd /www/wwwroot/photo_frame
git pull origin main

# 4. 确保 .env 配置正确
cat /www/wwwroot/photo_frame/.env
# 必须包含：SECRET_KEY, ADMIN_USERS, GUNICORN_* 配置

# 5. 进入虚拟环境安装依赖（如有新增）
source /www/wwwroot/photo_frame/venv/bin/activate
pip install -r requirements.txt

# 6. 在宝塔面板重启 Python 项目
# 或使用命令行：
cd /www/wwwroot/photo_frame && \
  /www/wwwroot/photo_frame/venv/bin/gunicorn \
    -b 127.0.0.1:5000 \
    -w 3 \
    --threads 4 \
    --worker-class gthread \
    --timeout 120 \
    --pid /www/wwwroot/photo_frame/logs/photo_frame.pid \
    --access-logfile /www/wwwroot/photo_frame/logs/access.log \
    --error-logfile /www/wwwroot/photo_frame/logs/error.log \
    app:app
```

#### 3.2 宝塔面板配置

| 配置项 | 值 |
|--------|-----|
| 项目路径 | `/www/wwwroot/photo_frame` |
| 启动文件 | `app.py` 或 `wsgi.py` |
| Python 版本 | 3.11 |
| 运行用户 | `www` |
| 端口 | `5000` |
| 是否开启守护进程 | ✅ 是 |

#### 3.3 Nginx 反向代理配置

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # 安全头
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-Content-Type-Options "nosniff";
    
    # 上传大小限制（与 MAX_UPLOAD_SIZE_MB 匹配）
    client_max_body_size 200M;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 超时配置（与 Gunicorn timeout 匹配）
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }
    
    # 静态文件直接访问，不走 Python
    location /static/ {
        alias /www/wwwroot/photo_frame/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
```

### 方案 B：Docker 部署（适用于新服务器或容器化迁移）

```bash
# 1. 准备 .env 文件
cp .env.example .env
vim .env  # 修改 SECRET_KEY, ADMIN_USERS 等

# 2. 构建镜像
docker-compose build --no-cache

# 3. 启动容器
docker-compose up -d

# 4. 查看日志
docker-compose logs -f --tail=50
```

---

## 四、关键环境变量配置清单

### 4.1 必需配置

| 变量 | 示例值 | 说明 |
|------|--------|------|
| `SECRET_KEY` | `a1b2c3d4e5f6...` | Flask 会话加密密钥，**必须设置** |
| `ADMIN_USERS` | `jackdu:password123` | 管理员账户，格式 `用户名:密码` |

### 4.2 推荐配置（2核2G 服务器）

| 变量 | 推荐值 | 说明 |
|------|--------|------|
| `FLASK_DEBUG` | `false` | 生产环境必须关闭 |
| `GUNICORN_WORKERS` | `3` | 2核推荐值，预留 Nginx/OS 算力 |
| `GUNICORN_THREADS` | `4` | 异步多线程，提升并发 |
| `GUNICORN_WORKER_CLASS` | `gthread` | **关键！** 根治 I/O 阻塞 |
| `GUNICORN_TIMEOUT` | `120` | 首次启动索引构建需要 |
| `GUNICORN_BIND` | `127.0.0.1:5000` | 仅内网，Nginx 前置 |

### 4.3 可选配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEATHER_LAT` | `31.3041` | 苏州纬度 |
| `WEATHER_LON` | `120.5954` | 苏州经度 |
| `BABY_NAME` | 空 | 宝宝昵称 |
| `BABY_BIRTHDAY` | 空 | 格式 YYYY-MM-DD |
| `SLIDE_DURATION_SECONDS` | `300` | 每张照片展示时长 |

---

## 五、升级验证 Checklist

### 5.1 部署前检查

- [ ] `.env` 文件已配置 `SECRET_KEY`
- [ ] `.env` 文件已配置 `ADMIN_USERS`
- [ ] `.env` 文件已配置 `GUNICORN_*` 参数
- [ ] `.env` 不在 `.gitignore` 中被忽略（本地有，服务器也有）
- [ ] 已备份现有代码和数据库

### 5.2 部署后验证

| 检查项 | 验证方法 | 预期结果 |
|--------|----------|----------|
| Gunicorn 启动 | `docker ps` 或宝塔面板查看 | 显示 running/healthy |
| SSL 正常 | 访问首页，查看天气/一言 | 数据正常加载 |
| 认证正常 | 访问 `/admin` | 跳转登录页，登录后正常 |
| 上传正常 | 上传一张照片 | 成功，照片出现在管理后台 |
| 推荐正常 | 访问首页等待轮播 | 照片正常切换，不卡在某张 |
| 留言正常 | 发送一条留言 | 即时上墙，含 `&` 显示正确 |
| Nginx 代理 | 外网访问域名 | 正常返回，无 502/504 |

### 5.3 性能验证（2核2G）

```bash
# 检查 Gunicorn 进程数
ps aux | grep gunicorn
# 预期：1 master + 3 workers = 4 个进程

# 检查内存占用
free -h
# 预期：Gunicorn 占用 ~150-200MB

# 检查端口监听
netstat -tlnp | grep 5000
# 预期：127.0.0.1:5000 (仅内网)

# 压力测试（可选）
wrk -t2 -c10 -d30s http://127.0.0.1:5000/api/status
```

---

## 六、回滚方案

### 6.1 宝塔环境回滚

```bash
# 1. 停止当前服务
# 在宝塔面板点击"停止"，或：
kill -TERM $(cat /www/wwwroot/photo_frame/logs/photo_frame.pid)

# 2. 恢复备份代码
rm -rf /www/wwwroot/photo_frame
mv /www/wwwroot/photo_frame_backup_YYYYMMDD /www/wwwroot/photo_frame

# 3. 重启服务
# 在宝塔面板点击"启动"
```

### 6.2 Docker 环境回滚

```bash
# 1. 停止当前容器
docker-compose down

# 2. 切换到旧版本
git revert HEAD
# 或：git checkout v2.0.3

# 3. 重建并启动
docker-compose build
docker-compose up -d
```

---

## 七、已知技术债（非本次修复范围）

| 技术债 | 优先级 | 说明 |
|--------|--------|------|
| CSS 拆分重构 | Medium | index.html 2500+ 行内联 CSS，等 V1.0 稳定后执行 |
| 元数据双存储 | Low | JSON + SQLite 双写，建议统一到 SQLite |
| 连接池 | Low | 每次操作新建连接，可引入 Flask `g` 请求级连接 |
| CI/CD | High | 当前无 Python 测试流水线，建议添加 pytest + lint |

---

## 八、安全加固建议（额外）

| 措施 | 说明 |
|------|------|
| Nginx 限流 | `limit_req_zone` 限制 /api/* 请求频率 |
| Bot 阻断 | 屏蔽非浏览器 User-Agent，限制异常 IP |
| HTTPS | Let's Encrypt 免费证书，强制 HTTPS |
| 日志轮转 | Nginx + Gunicorn 日志定期压缩归档 |
| 防火墙 | 仅开放 80/443，关闭 5000 外网访问 |

---

## 九、前端 CSS 批量修复部署说明（114 项 / 16 文件）

> 修复时间：2026-06-02
> 范围：纯前端（模板 + 静态文件），不涉及后端逻辑或数据库

### 9.1 修复概览

本次共完成 **114 项 CSS/样式修复**（含 review 补修 13 项），覆盖 **16 个文件**，分为四组：

| 分组 | 涉及文件 | 修复数 | 关键修复内容 |
|------|----------|--------|-------------|
| **A. index.html** | `templates/index.html` | 26 | 死代码清理（~125 行）、`100vw`→`100%` / `100vh`→`--vh` 变量修复、`pointer-events` 穿透修正、触控目标 ≥ 44px、`z-index` 层级整理、`transition:all`→具体属性、`color-scheme` 声明、`overflow-wrap` 防溢出、响应式 `padding`、`viewport-fit=cover` |
| **B. admin + login + manage** | `templates/admin.html`、`templates/login.html`、`templates/manage.html`、`static/style.css` | 23 | Design Token 基础（`--app-*` CSS 自定义属性）、`box-sizing` 全局重置、Flex 子元素 `min-width:0` 溢出修复、`viewport-fit=cover`、Toast `z-index` 统一至 10000、触控反馈、iOS 输入框 16px 防缩放、`target="_blank"` 安全属性 |
| **C. 沉浸式主题 style7-12** | `templates/style7-zen.html` ~ `templates/style12-floating.html`（6 个独立文件） | 33 | `clip-path` 与 `border` 冲突移除、`background-size:contain` 适配、动画性能（`box-shadow`→`filter:drop-shadow`、`top`→`translateY`）、`100dvh` fallback、`safe-area-inset`、`orientation` 横竖屏处理、`flex`→`grid` 防溢出、`rAF` 节流视差、`will-change` 清理、`encodeURI` URL 编码、`color-scheme` 声明、`transition:all` 收窄 |
| **D. 策展主题 style13-16 + shared** | `templates/style13-waterfall.html` ~ `templates/style16-gallery.html`（4 个独立文件）+ `static/unified-style-menu.js` | 32 | `z-index` 穿透修复（`MutationObserver` 动态降层）、`.empty-state`→`.curation-empty-state` 类名隔离、`encodeURI` URL 编码、`IntersectionObserver` 懒加载替代原生 `loading=lazy`、`backdrop-filter` 替代逐卡片 `blur` GPU 优化、拖拽 5px 阈值、编辑器 Modal `opacity+scale` 过渡、`cardPhotoMap.clear()` 内存泄漏修复、`viewport-fit=cover` + `safe-area-inset`、`100dvh` fallback |

### 9.2 部署影响评估

| 维度 | 影响 |
|------|------|
| 数据库迁移 | **无** — 本次修复不涉及 Schema 变更 |
| 后端重启 | **建议重启** — Flask 模板按请求读取，替换后自动生效，但重启 Gunicorn 可确保 worker 缓存清除 |
| 静态文件缓存 | **需刷新** — Nginx `expires 7d` 可能导致旧 CSS 残留，部署后建议手动清除浏览器缓存或临时调短 `expires` |
| 涉及文件 | `templates/` 和 `static/` 目录下的 16 个文件 |

**部署方式**：替换模板和静态文件，建议重启 Gunicorn worker。

```bash
# 宝塔环境：替换文件 + 重启
scp templates/*.html user@server:/path/to/project/templates/
scp static/*.css static/*.js user@server:/path/to/project/static/
# 在宝塔面板点击"重启"，或：
kill -HUP $(cat /www/wwwroot/photo_frame/logs/photo_frame.pid)

# Docker 环境：模板打包在镜像内需重建
docker-compose build
docker-compose up -d
```

### 9.3 部署后验证 Checklist

#### 首页样式（style-1 ~ style-6）

- [ ] 在手机浏览器逐一测试 6 种首页风格（style-1 到 style-6），切换正常
- [ ] 确认触控目标 ≥ 44px（风格切换按钮、菜单项）
- [ ] 确认无水平滚动条（`100vw` 修复验证）

#### 沉浸式主题（style7 ~ style12）

- [ ] iPhone 测试全部 6 种沉浸式主题
- [ ] Android 测试全部 6 种沉浸式主题
- [ ] 确认 `100vh` → `100dvh` 后内容不被 iOS 地址栏遮挡
- [ ] 确认 `safe-area-inset` 在刘海/灵动岛设备上正常
- [ ] 确认横竖屏切换后布局正确（`orientation` 处理验证）
- [ ] 确认动画流畅，无掉帧（`transform` 替代 `top`/`box-shadow` 验证）

#### 策展主题（style13 ~ style16）

- [ ] 测试全部 4 种策展主题，照片懒加载正常（`IntersectionObserver` 验证）
- [ ] 确认编辑器 Modal 打开/关闭过渡动画正常（`z-index` 修复验证）
- [ ] 确认风格菜单不遮挡编辑器弹窗（`z-index` 穿透修复验证）
- [ ] 确认拖拽操作有合理阈值，不会误触发

#### 管理页面（admin / login / manage）

- [ ] 登录页正常显示，输入框不被 iOS 自动放大
- [ ] 管理后台布局正常，Flex 子元素不溢出
- [ ] Toast 提示层级正确，不被其他元素遮挡
- [ ] 触控反馈（按下高亮）正常

#### 通用项

- [ ] 确认无水平滚动条（所有页面，移动端）
- [ ] 确认 `backdrop-filter` 毛玻璃效果在 iOS Safari 正常
- [ ] 长时间挂机 10 分钟，确认无内存泄漏（`MutationObserver` / `IntersectionObserver` 已 `disconnect()`）

### 9.4 回滚方案

本次修复为纯前端变更，回滚成本极低：

```bash
# 宝塔环境：用备份替换
cp -r /www/wwwroot/photo_frame_backup_YYYYMMDD/templates/* /www/wwwroot/photo_frame/templates/
cp -r /www/wwwroot/photo_frame_backup_YYYYMMDD/static/* /www/wwwroot/photo_frame/static/

# Docker 环境：Git 回退模板和静态文件
git checkout HEAD~1 -- templates/ static/
docker-compose build
docker-compose up -d
```

| 回滚维度 | 操作 |
|----------|------|
| 数据库回滚 | **不需要** |
| 后端回滚 | **不需要** |
| 仅需操作 | 将 `templates/` 和 `static/` 目录恢复到上一版本 |
