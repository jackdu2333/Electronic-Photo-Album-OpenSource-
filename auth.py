"""
认证模块 - 增强的用户认证系统

支持功能：
- 密码哈希加密（werkzeug）
- 登录失败限制
- Session 超时管理
- 密码强度验证
"""

import os
import time
from typing import Optional, Dict
from werkzeug.security import generate_password_hash, check_password_hash
from flask import session, request, make_response, current_app
from flask_basicauth import BasicAuth


# ==================== 密码哈希工具 ====================

def hash_password(password: str) -> str:
    """
    对密码进行哈希加密

    Args:
        password: 明文密码

    Returns:
        加密后的密码哈希
    """
    return generate_password_hash(password, method='pbkdf2:sha256:600000')


def verify_password(password: str, password_hash: str) -> bool:
    """
    验证密码

    Args:
        password: 明文密码
        password_hash: 存储的密码哈希

    Returns:
        验证是否通过
    """
    return check_password_hash(password_hash, password)


# ==================== 密码策略 ====================

def is_password_strong(password: str) -> tuple[bool, str]:
    """
    检查密码强度

    要求：
    - 至少 8 个字符
    - 包含大小写字母
    - 包含数字或特殊字符

    Args:
        password: 待检查密码

    Returns:
        (是否合格，提示信息)
    """
    if len(password) < 8:
        return False, "密码长度至少 8 位"

    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password)

    if not (has_upper and has_lower):
        return False, "密码需包含大小写字母"

    if not (has_digit or has_special):
        return False, "密码需包含数字或特殊字符"

    return True, "密码强度合格"


# ==================== 增强认证类 ====================

class EnhancedAuth(BasicAuth):
    """增强的认证类，支持密码哈希和安全特性"""

    def __init__(self, app=None, users: Optional[Dict[str, str]] = None):
        """
        初始化认证系统

        Args:
            app: Flask 应用
            users: 用户字典 {username: password_hash}
        """
        self._users = users or {}
        self._login_attempts: Dict[str, list] = {}  # 登录失败记录
        self._lockout_time = 300  # 锁定时间（秒）
        self._max_attempts = 5    # 最大失败次数
        self._exclude_paths = ['/health', '/health/live', '/health/ready', '/login', '/static']  # 豁免路径（仅健康检查、登录页和静态文件）
        super().__init__(app)




    def check_auth(self, username: str, password: str) -> bool:
        """
        检查认证（覆盖父类方法，支持密码哈希）

        Args:
            username: 用户名
            password: 密码

        Returns:
            认证是否通过
        """
        # 检查是否是豁免路径
        from flask import request
        if request.path in self._exclude_paths:
            return True

        # 检查账户锁定
        if self._is_account_locked(username):
            return False

        stored_hash = self._users.get(username)

        if stored_hash is None:
            # 用户不存在，记录失败尝试
            self._record_failed_attempt(username)
            return False

        if verify_password(password, stored_hash):
            # 认证成功，清除失败记录
            self._login_attempts.pop(username, None)
            return True
        else:
            # 认证失败，记录尝试
            self._record_failed_attempt(username)
            return False

    def _is_account_locked(self, username: str) -> bool:
        """检查账户是否被锁定"""
        if username not in self._login_attempts:
            return False

        attempts = self._login_attempts[username]
        # 只检查最近的尝试（在锁定时间窗口内）
        cutoff = time.time() - self._lockout_time
        recent_attempts = [t for t in attempts if t > cutoff]
        self._login_attempts[username] = recent_attempts

        return len(recent_attempts) >= self._max_attempts

    def _record_failed_attempt(self, username: str):
        """记录失败尝试"""
        if username not in self._login_attempts:
            self._login_attempts[username] = []
        self._login_attempts[username].append(time.time())

    def init_app(self, app):
        """初始化应用"""
        # 不调用父类的 init_app，我们自己控制认证逻辑
        app.config['BASIC_AUTH_FORCE'] = True
        app.config['BASIC_AUTH_REALM'] = 'Photo Frame Admin'

        @app.before_request
        def require_basic_auth():
            # 检查是否是豁免路径
            from flask import request
            if request.path in self._exclude_paths:
                return

            # 检查是否需要认证
            if not current_app.config['BASIC_AUTH_FORCE']:
                return
            if not self.authenticate():
                # 区分 API 请求和页面请求
                # API 请求返回 401，页面请求重定向到登录页
                if request.path.startswith('/api/'):
                    return self.challenge()
                else:
                    # 页面请求重定向到登录页
                    from flask import redirect, url_for
                    return redirect(url_for('main.login_page'))

    @property
    def users(self) -> Dict[str, str]:
        """获取用户字典"""
        return self._users

    def set_users(self, users: Dict[str, str], hash_passwords: bool = True):
        """
        设置用户列表

        Args:
            users: 用户字典 {username: password} 或 {username: password_hash}
            hash_passwords: 是否对密码进行哈希加密
        """
        if hash_passwords:
            self._users = {
                username: (
                    password_hash if password_hash.startswith('pbkdf2:')
                    else hash_password(password)
                )
                for username, password in users.items()
                # 兼容旧格式：可能是 user:password 或 user:hash
                for password_hash in [password]
            }
        else:
            self._users = users

    def add_user(self, username: str, password: str):
        """添加用户（自动哈希密码）"""
        is_strong, msg = is_password_strong(password)
        if not is_strong:
            raise ValueError(f"密码强度不足：{msg}")

        self._users[username] = hash_password(password)

    def remove_user(self, username: str):
        """删除用户"""
        if username in self._users:
            del self._users[username]

    def _is_locked_out(self, username: str) -> bool:
        """检查用户是否被锁定"""
        if username not in self._login_attempts:
            return False

        attempts = self._login_attempts[username]
        # 清理超过 5 分钟的记录
        now = time.time()
        attempts = [t for t in attempts if now - t < 300]
        self._login_attempts[username] = attempts

        return len(attempts) >= self._max_attempts

    def _record_failure(self, username: str):
        """记录登录失败"""
        now = time.time()
        if username not in self._login_attempts:
            self._login_attempts[username] = []
        self._login_attempts[username].append(now)

    def _record_success(self, username: str):
        """记录登录成功，清除失败记录"""
        if username in self._login_attempts:
            del self._login_attempts[username]

    def check_credentials(self, username: str, password: str) -> bool:
        """
        验证用户凭证（使用密码哈希）

        Args:
            username: 用户名
            password: 密码（明文）

        Returns:
            验证是否通过
        """
        # 检查是否是豁免路径
        from flask import request
        if request.path in self._exclude_paths:
            return True

        # 检查是否被锁定
        if self._is_locked_out(username):
            return False

        # 检查用户是否存在
        if username not in self._users:
            return False

        password_hash = self._users[username]

        # 兼容旧格式（明文密码）
        if not password_hash.startswith('pbkdf2:'):
            # 旧密码，直接比较并升级为哈希
            if password_hash == password:
                # 升级为哈希存储
                self._users[username] = hash_password(password)
                return True
            return False

        # 新格式，使用哈希验证
        if verify_password(password, password_hash):
            self._record_success(username)
            return True

        # 记录失败
        self._record_failure(username)
        return False

    def challenge(self) -> tuple:
        """
        返回 401 挑战响应

        添加 Cache-Control: no-store 防止 Nginx 缓存
        """
        resp = make_response("Unauthorized", 401)
        resp.headers['WWW-Authenticate'] = 'Basic realm="Photo Frame Admin"'
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
        resp.headers['Pragma'] = 'no-cache'
        return resp

    def authenticate(self) -> bool:
        """
        认证流程

        支持：
        1. Session 认证（已登录用户）
        2. Basic Auth 头认证（首次登录）
        """
        # 1. Session 已认证
        if session.get('_auth_ok'):
            # 检查 session 过期（可选，默认 24 小时）
            login_time = session.get('_login_time', 0)
            if time.time() - login_time < 86400:  # 24 小时
                return True
            else:
                # Session 过期，清除
                session.pop('_auth_ok', None)
                session.pop('_username', None)

        # 2. Basic Auth 头认证
        auth = request.authorization
        if auth and self.check_credentials(auth.username, auth.password):
            session['_auth_ok'] = True
            session['_username'] = auth.username
            session['_login_time'] = time.time()
            return True

        return False

    def get_current_user(self) -> Optional[str]:
        """获取当前登录用户名"""
        if session.get('_auth_ok'):
            return session.get('_username')

        auth = request.authorization
        if auth and auth.username in self._users:
            return auth.username

        return None

    def is_authenticated(self) -> bool:
        """检查是否已认证"""
        return self.authenticate()


# 全局认证实例，供蓝图和应用引用
auth = EnhancedAuth()
