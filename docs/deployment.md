# 部署指南

本文档介绍 Digital Photo Frame 的多种部署方式。

---

## 方式一：Docker 部署（推荐）

### 前置要求
- Docker 20.10+
- Docker Compose 2.0+

### 步骤

#### 1. 克隆项目
```bash
git clone https://github.com/YOUR_USERNAME/digital-photo-frame.git
cd digital-photo-frame
```

#### 2. 配置环境变量
```bash
cp .env.example .env
```

编辑 `.env` 文件，至少修改以下配置：
```bash
# 生成安全的 SECRET_KEY
# 在终端运行：python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-secret-key-here

# 修改管理员账户和密码
ADMIN_USERS=admin:your-secure-password

# 可选：宝宝信息
BABY_NAME=宝宝名字
BABY_BIRTHDAY=YYYY-MM-DD
```

#### 3. 创建数据目录
```bash
mkdir -p data logs
```

#### 4. 启动容器
```bash
docker-compose up -d
```

#### 5. 验证运行状态
```bash
docker-compose ps
docker-compose logs -f
```

#### 6. 访问应用
打开浏览器访问 `http://localhost:5000`（或你配置的端口）

---

## 方式二：本地运行

### 前置要求
- Python 3.9+
- pip

### 步骤

#### 1. 克隆项目
```bash
git clone https://github.com/YOUR_USERNAME/digital-photo-frame.git
cd digital-photo-frame
```

#### 2. 创建虚拟环境（推荐）
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

#### 3. 安装依赖
```bash
pip install -r requirements.txt
```

#### 4. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件
```

#### 5. 运行应用
```bash
python app.py
```

或使用 gunicorn（生产环境）：
```bash
gunicorn --bind 0.0.0.0:5000 --workers 2 app:app
```

#### 6. 访问应用
打开浏览器访问 `http://localhost:5000`

---

## 方式三：Railway 云平台部署

### 步骤

#### 1. 准备 Railway 账户
访问 [Railway](https://railway.app/) 注册并登录

#### 2. 创建新项目
1. 点击 "New Project"
2. 选择 "Deploy from GitHub repo"
3. 授权并选择你的仓库

#### 3. 配置环境变量
在 Railway 面板中添加以下变量：
- `SECRET_KEY`: 随机生成的密钥
- `ADMIN_USERS`: 管理员账户
- `BABY_NAME`: 宝宝名字（可选）
- `BABY_BIRTHDAY`: 宝宝生日（可选）
- `WEATHER_LAT`: 纬度
- `WEATHER_LON`: 经度

#### 4. 配置持久化存储
添加 Volume：
- Mount Path: `/app/data`
- 或添加 PostgreSQL/Railway 数据库

#### 5. 部署
Railway 会自动构建和部署，完成后会提供公网 URL

---

## 方式四：Render 云平台部署

### 步骤

#### 1. 准备 Render 账户
访问 [Render](https://render.com/) 注册并登录

#### 2. 创建 Web Service
1. 点击 "New +" → "Web Service"
2. 连接你的 GitHub 仓库

#### 3. 配置
- **Name**: digital-photo-frame
- **Region**: 选择最近的地区
- **Branch**: main
- **Root Directory**: 留空
- **Runtime**: Python 3
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT app:app`

#### 4. 环境变量
添加与 Railway 相同的环境变量

#### 5. 部署
点击 "Create Web Service"，等待部署完成

---

## 反向代理配置（可选）

### Nginx 配置示例

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Caddy 配置示例

```caddyfile
your-domain.com {
    reverse_proxy localhost:5000
}
```

---

## HTTPS 配置

### 使用 Let's Encrypt

```bash
# 安装 certbot
sudo apt install certbot python3-certbot-nginx

# 获取证书
sudo certbot --nginx -d your-domain.com
```

---

## 数据备份

### Docker 部署
```bash
# 备份数据目录
tar -czf backup-$(date +%Y%m%d).tar.gz data/
```

### 本地部署
备份以下文件和目录：
```bash
# 数据库
photos.db
photo_metadata.json
messages.json

# 照片文件
static/photos/

# 日志（可选）
logs/
```

---

## 故障排查

### 容器无法启动
```bash
# 查看日志
docker-compose logs

# 检查端口占用
docker-compose ps
```

### 数据库错误
```bash
# 删除并重建数据库（注意备份！）
rm photos.db
docker-compose restart
```

### 权限问题
```bash
# 修复目录权限
sudo chown -R $USER:$USER data/ logs/
```

---

## 性能优化

### 生产环境建议
1. 使用 gunicorn 代替 Flask 内置服务器
2. 配置 Nginx 作为反向代理
3. 启用 Redis 缓存（如支持）
4. 定期备份数据

### 资源配置
| 规模 | CPU | 内存 | 适用场景 |
|------|-----|------|----------|
| 小型 | 1 核 | 512MB | 家庭使用，<1000 张照片 |
| 中型 | 2 核 | 1GB  | 小型企业，<10000 张照片 |
| 大型 | 4 核 | 2GB  | 多用户使用，>10000 张照片 |

---

## 更新应用

### Docker 部署
```bash
git pull
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### 本地部署
```bash
git pull
pip install -r requirements.txt
# 重启服务
```

---

如有问题，请在 GitHub 提交 Issue 或查看 [常见问题](../README.md#常见问题)
