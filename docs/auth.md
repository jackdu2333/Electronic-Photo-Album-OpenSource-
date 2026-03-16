# 认证配置说明

## ⚠️ 重要安全提醒

**首次部署后，请立即修改默认密码！**

默认账户：`admin`
默认密码：`ChangeMe123!`

---

## 密码安全升级

### v2.0.0 认证改进

- ✅ **密码哈希加密**: 使用 PBKDF2-SHA256 算法
- ✅ **登录失败限制**: 5 次失败后锁定 5 分钟
- ✅ **Session 管理**: 24 小时自动过期
- ✅ **密码强度验证**: 至少 8 位，包含大小写字母和数字/特殊字符
- ✅ **兼容旧密码**: 自动将明文密码升级为哈希存储

---

## 快速开始

### 方式 1：使用明文密码（首次部署）

在 `.env` 文件中配置：

```bash
ADMIN_USERS=admin:MySecurePassword123!
```

首次运行时，密码会自动哈希存储。

### 方式 2：使用哈希密码（生产环境推荐）

1. 生成密码哈希：
```bash
python tools/manage_users.py hash "MySecurePassword123!"
```

2. 复制输出的哈希值到 `.env`：
```bash
ADMIN_USERS=admin:$pbkdf2-sha256$600000$...
```

---

## 密码管理工具

### 生成密码哈希

```bash
python tools/manage_users.py hash "YourPassword123!"
```

输出：
```
✅ 密码强度合格
密码哈希:
$pbkdf2-sha256$600000$...

在.env 中使用格式：ADMIN_USERS=admin:$pbkdf2-sha256$...
```

### 检查密码强度

```bash
python tools/manage_users.py check "YourPassword123!"
```

### 验证密码

```bash
python tools/manage_users.py verify "$pbkdf2-sha256$..." "YourPassword123!"
```

### 列出当前用户

```bash
python tools/manage_users.py list
```

---

## 密码策略

### 要求

| 要求 | 说明 |
|------|------|
| 最小长度 | 8 个字符 |
| 大写字母 | 至少 1 个 (A-Z) |
| 小写字母 | 至少 1 个 (a-z) |
| 数字或特殊字符 | 至少 1 个 (0-9 或 !@#$%^&*) |

### 示例强密码

```
✅ ChangeMe123!
✅ SecurePass2024!
✅ PhotoFrame@2026
```

### 示例弱密码

```
❌ password     (太简单)
❌ 12345678     (只有数字)
❌ abcdefgh     (只有小写)
❌ Admin123     (常见密码)
```

---

## 安全特性

### 1. 密码哈希加密

使用 `werkzeug` 的 `generate_password_hash` 函数：
- 算法：PBKDF2-SHA256
- 迭代次数：600,000 次
- 自动盐值生成

### 2. 登录失败限制

- 最大失败次数：5 次
- 锁定时长：5 分钟
- 自动解锁：超时后自动清除失败记录

### 3. Session 管理

- Session 过期：24 小时
- 自动续期：每次认证成功重置计时
- 安全退出：清除 Session 数据

### 4. 防止缓存

- `Cache-Control: no-store`
- `Pragma: no-cache`
- 防止 Nginx 缓存 401 响应

---

## 多用户配置

### 添加多个管理员

```bash
# 格式：用户名 1:密码 1，用户名 2:密码 2
ADMIN_USERS=admin:AdminPass123!,user2:User2Pass456!
```

### 混合使用明文和哈希

```bash
# 新用户用哈希，旧用户保持明文（会自动升级）
ADMIN_USERS=admin:$pbkdf2-sha256$...,legacy_user:oldpassword
```

---

## 迁移指南

### 从旧版本升级

如果你之前使用的是明文密码（如 `admin:oldpassword`）：

1. **立即修改密码**：
```bash
# 生成新密码哈希
python tools/manage_users.py hash "NewSecurePassword123!"
```

2. **更新 .env 文件**：
```bash
# 删除旧账户，使用新密码
ADMIN_USERS=admin:NewSecurePassword123!
```

3. **删除敏感信息**：
```bash
# 确保 .gitignore 包含 .env
echo ".env" >> .gitignore
```

---

## 故障排查

### 问题：无法登录

**可能原因**：
1. 密码错误
2. 账户被锁定（等待 5 分钟）
3. Session 过期（刷新页面重试）

**解决方法**：
```bash
# 验证密码
python tools/manage_users.py verify "$pbkdf2-sha256$..." "YourPassword"

# 查看日志
docker-compose logs | grep auth
```

### 问题：密码强度检查失败

**错误信息**：`密码强度不足：xxx`

**解决方法**：
- 增加密码长度（至少 8 位）
- 添加大写字母
- 添加小写字母
- 添加数字或特殊字符

---

## 最佳实践

### 1. 生产环境

- ✅ 使用哈希密码配置
- ✅ 定期更换密码（每 90 天）
- ✅ 使用密码管理器生成密码
- ✅ 启用 HTTPS

### 2. 开发环境

- ✅ 使用环境变量
- ✅ 不将 .env 提交到 Git
- ✅ 使用不同的测试账户

### 3. 密码管理

```bash
# 定期生成新密码
python tools/manage_users.py hash "$(openssl rand -base64 12)"
```

---

## API 使用认证

### Basic Auth 请求

```bash
# curl 示例
curl -u admin:password http://localhost:5000/api/status
```

### JavaScript fetch

```javascript
// 浏览器会自动使用 session cookie
fetch('/api/status', { credentials: 'same-origin' })
```

---

## 联系方式

如有安全问题，请通过 GitHub Issue 联系。
