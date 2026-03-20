# 宝塔面板部署指南

本文档介绍如何在阿里云/腾讯云云服务器上使用宝塔面板部署 Digital Photo Frame。

---

## 前置要求

- 云服务器（阿里云/腾讯云等）
- 宝塔面板 8.0+
- Python 项目管理器插件

---

## 部署步骤

### 1. 安装 Python 3.11

宝塔默认的 Python 版本可能较老（3.8），需要手动安装 3.11：

```bash
# 安装编译依赖
sudo yum install -y gcc zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel libffi-devel

# 下载 Python 3.11
cd /tmp
wget https://www.python.org/ftp/python/3.11.6/Python-3.11.6.tgz
tar -xzf Python-3.11.6.tgz
cd Python-3.11.6

# 编译安装
./configure --prefix=/usr/local/python3.11 --enable-optimizations
make -j4
sudo make install

# 验证
/usr/local/python3.11/bin/python3 --version
```

---

### 2. 克隆项目

```bash
# 进入网站目录
cd /www/wwwroot

# 克隆项目
git clone https://github.com/jackdu2333/-Electronic-Photo-Album-OpenSource-.git photo_frame_v2

# 进入项目目录
cd photo_frame_v2
```

---

### 3. 创建虚拟环境

```bash
# 使用 Python 3.11 创建虚拟环境
/usr/local/python3.11/bin/python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 安装 gunicorn（生产环境）
pip install gunicorn
```

---

### 4. 配置环境变量

```bash
# 复制配置文件
cp .env.example .env

# 编辑配置
vi .env
```

**必须修改的配置**：

```bash
# 生成安全的 SECRET_KEY
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# 管理员账户和密码
ADMIN_USERS=admin:YourSecurePassword123!

# SQLite busy timeout（7x24 运行建议）
SQLITE_BUSY_TIMEOUT_MS=10000
```

---

### 5. 配置宝塔 Python 项目管理器

1. 登录宝塔面板
2. 安装 **Python 项目管理器** 插件
3. 添加项目：
   - **项目名称**: photo_frame_v2
   - **项目路径**: `/www/wwwroot/photo_frame_v2`
   - **Python 版本**: 选择 Python 3.11
   - **端口**: 5000
   - **启动文件**: `app.py`
   - **项目类型**: Flask

4. 设置环境变量（在宝塔面板中添加）：
   - `SECRET_KEY`: 生成的密钥
   - `ADMIN_USERS`: 管理员账户
   - 其他配置...

---

### 6. 配置 Nginx 反向代理

1. 在宝塔面板创建网站
2. 添加反向代理规则：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 静态资源不经过认证层（重要！）
        location ~* ^/static/photos/ {
            proxy_pass http://127.0.0.1:5000;
            proxy_set_header Host $host;
        }
    }
}
```

---

### 7. 数据迁移（从旧版本升级）

如果从旧版本升级，需要迁移数据：

```bash
# 1. 备份旧数据
cp -r /www/wwwroot/photo_frame/static/photos /www/wwwroot/photo_frame_v2/static/photos
cp /www/wwwroot/photo_frame/photos.db /www/wwwroot/photo_frame_v2/
cp /www/wwwroot/photo_frame/photo_metadata.json /www/wwwroot/photo_frame_v2/
cp /www/wwwroot/photo_frame/messages.json /www/wwwroot/photo_frame_v2/

# 2. 或者创建软链接（推荐）
ln -s /www/wwwroot/photo_frame/static/photos /www/wwwroot/photo_frame_v2/static/photos
```

---

### 8. 启动项目

```bash
# 方式 1：使用宝塔 Python 项目管理器启动（推荐）
# 在宝塔面板点击"启动"

# 方式 2：手动使用 gunicorn
source venv/bin/activate
gunicorn --bind 127.0.0.1:5000 --workers 2 --threads 4 app:app

# 方式 3：使用宝塔"永久运行"功能
# 添加启动命令到宝塔 Python 项目管理器
```

---

## 故障排查

### 问题 1：504 Gateway Time-out

**原因**：gunicorn 未启动或端口被占用

**解决方法**：
```bash
# 检查端口占用
netstat -tlnp | grep 5000

# 检查 gunicorn 进程
ps aux | grep gunicorn

# 手动启动测试
source venv/bin/activate
gunicorn --bind 127.0.0.1:5000 app:app
```

### 问题 2：静态资源 401 未授权

**原因**：`/static/photos/` 路径被认证层拦截

**解决方法**：已在 `auth.py` 中修复，确保更新到最新版本

### 问题 3：数据库 locked 错误

**原因**：SQLite 并发访问冲突

**解决方法**：
```bash
# 在.env 中增加 timeout
SQLITE_BUSY_TIMEOUT_MS=20000
```

### 问题 4：Python 项目管理器反复重启

**原因**：启动脚本或配置冲突

**解决方法**：
1. 停止宝塔 Python 项目管理器
2. 手动启动 gunicorn 测试
3. 确认成功后再交给宝塔托管

---

## 数据备份

```bash
# 备份脚本
#!/bin/bash
BACKUP_DIR="/www/backup/photo_frame_$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 备份数据库
cp /www/wwwroot/photo_frame_v2/photos.db $BACKUP_DIR/
cp /www/wwwroot/photo_frame_v2/photo_metadata.json $BACKUP_DIR/
cp /www/wwwroot/photo_frame_v2/messages.json $BACKUP_DIR/

# 备份照片
cp -r /www/wwwroot/photo_frame_v2/static/photos $BACKUP_DIR/

# 压缩
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
rm -rf $BACKUP_DIR

echo "备份完成：$BACKUP_DIR.tar.gz"
```

---

## 监控建议

### 每周检查

```bash
# 查看日志
tail -100 /www/wwwroot/photo_frame_v2/logs/app.log

# 检查进程
ps aux | grep gunicorn

# 检查磁盘空间
df -h
```

### 健康检查接口

```bash
# 访问健康检查接口
curl http://127.0.0.1:5000/health

# 检查 API 状态
curl -u admin:password http://127.0.0.1:5000/api/status
```

---

## 升级步骤

```bash
# 1. 停止项目
# 在宝塔面板点击"停止"

# 2. 备份数据（见上文）

# 3. 拉取最新代码
cd /www/wwwroot/photo_frame_v2
git pull

# 4. 安装新依赖
source venv/bin/activate
pip install -r requirements.txt

# 5. 启动项目
# 在宝塔面板点击"启动"
```

---

## 最佳实践

1. **不要覆盖的数据文件**：
   - `.env`
   - `photos.db`
   - `photo_metadata.json`
   - `messages.json`
   - `static/photos/`

2. **Git 更新时注意**：
   ```bash
   # 只更新代码，保留数据
   git pull
   # 不要 git checkout .env
   ```

3. **日志轮转**：
   - 在宝塔面板配置日志切割
   - 保留最近 7 天日志

---

## 联系方式

如有问题，请通过 GitHub Issue 联系。
