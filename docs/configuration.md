# 配置说明

本文档详细介绍 Digital Photo Frame 的所有配置项。

---

## 配置文件位置

复制 `.env.example` 为 `.env` 并修改配置：
```bash
cp .env.example .env
```

---

## 基础配置

### FLASK_DEBUG
- **类型**: 布尔值
- **默认**: `false`
- **说明**: 是否启用调试模式。生产环境务必设为 `false`

```bash
FLASK_DEBUG=false
```

### SECRET_KEY
- **类型**: 字符串
- **默认**: 无（必须设置）
- **说明**: Flask 会话加密密钥，用于保护用户 session

```bash
# 生成安全密钥
python -c "import secrets; print(secrets.token_hex(32))"

# 示例
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

---

## 用户认证配置

### ADMIN_USERS
- **类型**: 字符串
- **格式**: `用户名：密码，用户名 2:密码 2`
- **默认**: 空
- **说明**: 管理员账户列表，多个账户用逗号分隔

```bash
# 单用户
ADMIN_USERS=admin:secure-password

# 多用户
ADMIN_USERS=admin:password1,user2:password2
```

---

## 宝宝/家庭配置（可选）

### BABY_NAME
- **类型**: 字符串
- **默认**: 空（不显示宝宝信息）
- **说明**: 宝宝昵称。留空则不显示宝宝相关功能

```bash
BABY_NAME=木木
```

### BABY_BIRTHDAY
- **类型**: 日期（YYYY-MM-DD）
- **默认**: 空
- **说明**: 宝宝出生日期，用于计算并显示年龄

```bash
BABY_BIRTHDAY=2025-08-10
```

---

## 天气配置

### WEATHER_LAT
- **类型**: 浮点数
- **默认**: `31.3041`（苏州）
- **说明**: 天气 API 使用的纬度坐标

```bash
WEATHER_LAT=39.9042  # 北京
```

### WEATHER_LON
- **类型**: 浮点数
- **默认**: `120.5954`（苏州）
- **说明**: 天气 API 使用的经度坐标

```bash
WEATHER_LON=116.4074  # 北京
```

**获取经纬度**: 访问 https://www.latlong.net/ 查询你所在位置的坐标

### WEATHER_ENABLED
- **类型**: 布尔值
- **默认**: `true`
- **说明**: 是否启用天气显示功能

```bash
WEATHER_ENABLED=true
```

---

## 照片推荐算法配置

### TAG_WEIGHTS
- **类型**: 字符串
- **格式**: `标签 1:权重 1，标签 2:权重 2`
- **默认**: `木木：1.8，露营：1.5，旅行：1.3`
- **说明**: 标签权重配置，权重越高越容易被展示

```bash
# 示例：宝宝照片权重最高
TAG_WEIGHTS=宝宝：2.0，家庭：1.5，旅行：1.3，宠物：1.2

# 单个标签
TAG_WEIGHTS=宝宝：1.8

# 不留空（逗号分隔）
TAG_WEIGHTS=
```

### SEASONAL_WEIGHT_CURRENT
- **类型**: 浮点数
- **默认**: `1.8`
- **说明**: 当月拍摄照片的权重倍率

### SEASONAL_WEIGHT_ADJACENT
- **类型**: 浮点数
- **默认**: `1.4`
- **说明**: 相邻月份拍摄照片的权重倍率

### SEASONAL_WEIGHT_OTHER
- **类型**: 浮点数
- **默认**: `0.85`
- **说明**: 其他月份拍摄照片的权重倍率

### SEASONAL_WEIGHT_NONE
- **类型**: 浮点数
- **默认**: `0.5`
- **说明**: 无拍摄日期照片的权重倍率

### DEEP_SEA_PROBABILITY
- **类型**: 浮点数（0-1）
- **默认**: `0.05`（5%）
- **说明**: "深海打捞"模式触发概率

```bash
# 增加老照片出现频率
DEEP_SEA_PROBABILITY=0.1  # 10%

# 减少老照片出现频率
DEEP_SEA_PROBABILITY=0.02  # 2%
```

### DEEP_SEA_YEARS_THRESHOLD
- **类型**: 整数
- **默认**: `2`
- **说明**: 老照片判定阈值（多少年前的照片算老照片）

```bash
DEEP_SEA_YEARS_THRESHOLD=3  # 3 年前的照片算老照片
```

---

## 上传配置

### MAX_UPLOAD_SIZE_MB
- **类型**: 整数
- **默认**: `200`
- **说明**: 单张照片最大上传大小（MB）

```bash
MAX_UPLOAD_SIZE_MB=100  # 限制 100MB
```

### COMPRESS_TARGET_SIZE_MB
- **类型**: 整数
- **默认**: `3`
- **说明**: 压缩目标大小（MB）

```bash
COMPRESS_TARGET_SIZE_MB=5  # 压缩至 5MB 以内
```

### MAX_RESOLUTION_PX
- **类型**: 整数
- **默认**: `3840`（4K）
- **说明**: 图片长边最大分辨率（像素）

```bash
MAX_RESOLUTION_PX=1920  # 1080P
MAX_RESOLUTION_PX=2560  # 2K
```

---

## 幻灯片配置

### SLIDE_DURATION_SECONDS
- **类型**: 整数
- **默认**: `300`（5 分钟）
- **说明**: 每张照片展示时长（秒）

```bash
SLIDE_DURATION_SECONDS=60   # 1 分钟
SLIDE_DURATION_SECONDS=180  # 3 分钟
```

---

## 数据库配置

### DATABASE_FILE
- **类型**: 字符串
- **默认**: `photos.db`
- **说明**: SQLite 数据库文件路径（相对于项目根目录）

```bash
DATABASE_FILE=data/photos.db
```

### METADATA_FILE
- **类型**: 字符串
- **默认**: `photo_metadata.json`
- **说明**: 照片元数据 JSON 文件路径

```bash
METADATA_FILE=data/photo_metadata.json
```

### MESSAGES_FILE
- **类型**: 字符串
- **默认**: `messages.json`
- **说明**: 留言板数据文件路径

```bash
MESSAGES_FILE=data/messages.json
```

---

## 日志配置

### LOG_MAX_SIZE_MB
- **类型**: 整数
- **默认**: `10`
- **说明**: 单个日志文件最大大小（MB）

### LOG_BACKUP_COUNT
- **类型**: 整数
- **默认**: `5`
- **说明**: 日志文件备份数量

---

## 完整配置示例

```bash
# ====================
# 基础配置
# ====================
FLASK_DEBUG=false
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6

# ====================
# 用户认证
# ====================
ADMIN_USERS=admin:MySecurePassword123

# ====================
# 宝宝配置
# ====================
BABY_NAME=木木
BABY_BIRTHDAY=2025-08-10

# ====================
# 天气配置（北京）
# ====================
WEATHER_LAT=39.9042
WEATHER_LON=116.4074
WEATHER_ENABLED=true

# ====================
# 推荐算法配置
# ====================
TAG_WEIGHTS=木木：1.8，露营：1.5，旅行：1.3
SEASONAL_WEIGHT_CURRENT=1.8
SEASONAL_WEIGHT_ADJACENT=1.4
SEASONAL_WEIGHT_OTHER=0.85
SEASONAL_WEIGHT_NONE=0.5
DEEP_SEA_PROBABILITY=0.05
DEEP_SEA_YEARS_THRESHOLD=2

# ====================
# 上传配置
# ====================
MAX_UPLOAD_SIZE_MB=200
COMPRESS_TARGET_SIZE_MB=3
MAX_RESOLUTION_PX=3840

# ====================
# 幻灯片配置
# ====================
SLIDE_DURATION_SECONDS=300

# ====================
# 数据库配置
# ====================
DATABASE_FILE=photos.db
METADATA_FILE=photo_metadata.json
MESSAGES_FILE=messages.json

# ====================
# 日志配置
# ====================
LOG_MAX_SIZE_MB=10
LOG_BACKUP_COUNT=5
```

---

## 环境变量优先级

配置加载优先级（从高到低）：
1. 系统环境变量
2. `.env` 文件配置
3. 代码默认值

例如，设置 `SLIDE_DURATION_SECONDS`：
```bash
# 方式 1：系统环境变量（优先级最高）
export SLIDE_DURATION_SECONDS=600
python app.py

# 方式 2：.env 文件
echo "SLIDE_DURATION_SECONDS=600" >> .env
python app.py
```

---

## 配置验证

启动应用后，访问以下 API 检查配置是否生效：

```bash
# 检查天气配置
curl http://localhost:5000/api/weather-config

# 检查应用状态
curl -u admin:password http://localhost:5000/api/status
```

---

如有问题，请查看日志：
```bash
# Docker 部署
docker-compose logs -f

# 本地运行
tail -f logs/app.log
```
