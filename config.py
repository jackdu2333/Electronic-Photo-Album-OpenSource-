"""
配置管理模块

从环境变量和 .env 文件加载配置，提供统一的配置访问接口。
所有配置项都有合理的默认值，确保开箱即用。
"""

import os
import sys
from typing import Dict, Optional


def load_env_file():
    """手动加载 .env 文件（避免依赖 python-dotenv）"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())


# 启动时加载 .env 文件
load_env_file()


class ConfigError(Exception):
    """配置错误异常"""
    pass


class Config:
    """应用配置类"""

    def __init__(self):
        # 基础配置
        self.DEBUG = self._get_bool('FLASK_DEBUG', False)

        # SECRET_KEY: 生产环境必须设置
        secret_key = os.environ.get('SECRET_KEY')
        if not secret_key:
            # 调试模式下生成临时密钥
            if self.DEBUG:
                import secrets
                secret_key = secrets.token_hex(32)
                print("⚠️  WARNING: SECRET_KEY not set, using temporary key (debug mode only)")
            else:
                raise ConfigError(
                    "SECRET_KEY 未设置！\n"
                    "请通过以下方式之一设置：\n"
                    "1. 在 .env 文件中添加 SECRET_KEY=your-secret-key\n"
                    "2. 设置环境变量：export SECRET_KEY=your-secret-key\n\n"
                    "生成安全密钥：python -c \"import secrets; print(secrets.token_hex(32))\""
                )

        # 生产环境弱密钥检查
        if not self.DEBUG and len(secret_key) < 32:
            print(f"⚠️  WARNING: SECRET_KEY length ({len(secret_key)}) is less than 32 characters")
            print("Consider using a longer key for production: python -c \"import secrets; print(secrets.token_hex(32))\"")

        self.SECRET_KEY = secret_key

        # 用户认证
        self.ADMIN_USERS = self._parse_users(os.environ.get('ADMIN_USERS', ''))

        # 宝宝/家庭配置（可选）
        self.BABY_NAME = os.environ.get('BABY_NAME', '')
        self.BABY_BIRTHDAY = os.environ.get('BABY_BIRTHDAY', '')  # YYYY-MM-DD

        # 天气配置
        self.WEATHER_LAT = self._get_float('WEATHER_LAT', 31.3041, min_val=-90.0, max_val=90.0)
        self.WEATHER_LON = self._get_float('WEATHER_LON', 120.5954, min_val=-180.0, max_val=180.0)
        self.WEATHER_ENABLED = self._get_bool('WEATHER_ENABLED', True)

        # 标签权重配置
        self.TAG_WEIGHTS = self._parse_weights(os.environ.get('TAG_WEIGHTS', '宝宝：1.8，露营：1.5，旅行：1.3'))

        # 季节权重配置
        self.SEASONAL_WEIGHT_CURRENT = self._get_float('SEASONAL_WEIGHT_CURRENT', 1.8, min_val=0.0, max_val=10.0)
        self.SEASONAL_WEIGHT_ADJACENT = self._get_float('SEASONAL_WEIGHT_ADJACENT', 1.4, min_val=0.0, max_val=10.0)
        self.SEASONAL_WEIGHT_OTHER = self._get_float('SEASONAL_WEIGHT_OTHER', 0.85, min_val=0.0, max_val=10.0)
        self.SEASONAL_WEIGHT_NONE = self._get_float('SEASONAL_WEIGHT_NONE', 0.5, min_val=0.0, max_val=10.0)

        # 深海打捞配置
        self.DEEP_SEA_PROBABILITY = self._get_float('DEEP_SEA_PROBABILITY', 0.05, min_val=0.0, max_val=1.0)
        self.DEEP_SEA_YEARS_THRESHOLD = self._get_int('DEEP_SEA_YEARS_THRESHOLD', 2, min_val=0, max_val=100)

        # 上传配置
        self.MAX_UPLOAD_SIZE_MB = self._get_int('MAX_UPLOAD_SIZE_MB', 200, min_val=1, max_val=1000)
        self.COMPRESS_TARGET_SIZE_MB = self._get_int('COMPRESS_TARGET_SIZE_MB', 3, min_val=1, max_val=50)
        self.MAX_RESOLUTION_PX = self._get_int('MAX_RESOLUTION_PX', 3840, min_val=100, max_val=16384)

        # 幻灯片配置
        self.SLIDE_DURATION_SECONDS = self._get_int('SLIDE_DURATION_SECONDS', 300, min_val=10, max_val=3600)

        # 数据库配置
        self.DATABASE_FILE = os.environ.get('DATABASE_FILE', 'photos.db')
        self.METADATA_FILE = os.environ.get('METADATA_FILE', 'photo_metadata.json')
        self.MESSAGES_FILE = os.environ.get('MESSAGES_FILE', 'messages.json')

        # 日志配置
        self.LOG_MAX_SIZE_MB = self._get_int('LOG_MAX_SIZE_MB', 10, min_val=1, max_val=100)
        self.LOG_BACKUP_COUNT = self._get_int('LOG_BACKUP_COUNT', 5, min_val=1, max_val=30)

        # 上传文件夹
        self.UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'static/photos')

    def _get_bool(self, key: str, default: bool) -> bool:
        """获取布尔值配置"""
        value = os.environ.get(key, '').lower()
        if value == '':
            return default
        return value in ('true', '1', 'yes', 'on')

    def _get_int(self, key: str, default: int, min_val: Optional[int] = None, max_val: Optional[int] = None) -> int:
        """获取整数配置，支持范围验证"""
        value = os.environ.get(key, '')
        if value == '':
            return default
        try:
            result = int(value)
            # 范围验证
            if min_val is not None and result < min_val:
                print(f"⚠️  WARNING: {key} ({result}) is less than minimum {min_val}, using {min_val}")
                return min_val
            if max_val is not None and result > max_val:
                print(f"⚠️  WARNING: {key} ({result}) is greater than maximum {max_val}, using {max_val}")
                return max_val
            return result
        except ValueError:
            return default

    def _get_float(self, key: str, default: float, min_val: Optional[float] = None, max_val: Optional[float] = None) -> float:
        """获取浮点数配置，支持范围验证"""
        value = os.environ.get(key, '')
        if value == '':
            return default
        try:
            result = float(value)
            # 范围验证
            if min_val is not None and result < min_val:
                print(f"⚠️  WARNING: {key} ({result}) is less than minimum {min_val}, using {min_val}")
                return min_val
            if max_val is not None and result > max_val:
                print(f"⚠️  WARNING: {key} ({result}) is greater than maximum {max_val}, using {max_val}")
                return max_val
            return result
        except ValueError:
            return default

    def _parse_users(self, value: str) -> Dict[str, str]:
        """解析用户配置（格式：user1:pass1,user2:pass2）"""
        users = {}
        if not value:
            return users

        for pair in value.split(','):
            if ':' in pair:
                u, p = pair.split(':', 1)
                users[u.strip()] = p.strip()
        return users

    def _parse_weights(self, value: str) -> Dict[str, float]:
        """解析权重配置（格式：标签 1:1.8，标签 2:1.5）"""
        weights = {}
        if not value:
            return weights

        for pair in value.split(','):
            if ':' in pair:
                k, v = pair.split(':', 1)
                try:
                    weights[k.strip()] = float(v.strip())
                except ValueError:
                    pass
        return weights

    @property
    def max_content_length(self) -> int:
        """最大上传字节数"""
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def compress_target_bytes(self) -> int:
        """压缩目标字节数"""
        return self.COMPRESS_TARGET_SIZE_MB * 1024 * 1024

    @property
    def slide_duration_ms(self) -> int:
        """幻灯片展示时长（毫秒）"""
        return self.SLIDE_DURATION_SECONDS * 1000


# 全局配置实例
config = Config()
