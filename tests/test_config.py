"""
配置模块测试
"""
import os
import pytest
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境变量（在导入 config 之前）
os.environ['FLASK_DEBUG'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only-12345678'


class TestConfig:
    """配置类测试"""

    def test_secret_key_required_in_production(self):
        """生产模式下 SECRET_KEY 必须设置"""
        # 保存原始值
        original = os.environ.get('SECRET_KEY')
        original_debug = os.environ.get('FLASK_DEBUG')

        try:
            # 设置为生产模式（debug=false）且没有 SECRET_KEY
            os.environ['SECRET_KEY'] = ''
            os.environ['FLASK_DEBUG'] = 'false'

            # 强制重新导入配置模块
            import importlib
            import config
            importlib.reload(config)

            # 应该抛出异常
            try:
                cfg = config.Config()
                # 如果没有抛异常，说明配置成功（不应该）
                assert False, "Expected ConfigError"
            except config.ConfigError as e:
                # 预期行为
                assert 'SECRET_KEY' in str(e)
        finally:
            # 恢复原始值
            if original:
                os.environ['SECRET_KEY'] = original
            if original_debug:
                os.environ['FLASK_DEBUG'] = original_debug
            # 重新加载配置模块恢复原始状态
            import importlib
            import config
            importlib.reload(config)

    def test_debug_mode_generates_temp_key(self):
        """调试模式下生成临时 SECRET_KEY"""
        original = os.environ.get('SECRET_KEY')
        original_debug = os.environ.get('FLASK_DEBUG')

        try:
            os.environ['SECRET_KEY'] = ''
            os.environ['FLASK_DEBUG'] = 'true'

            import importlib
            import config
            importlib.reload(config)

            assert config.config.DEBUG == True
            assert len(config.config.SECRET_KEY) == 64  # 32 字节 hex = 64 字符
        finally:
            if original:
                os.environ['SECRET_KEY'] = original
            if original_debug:
                os.environ['FLASK_DEBUG'] = original_debug

    def test_parse_users(self):
        """用户配置解析"""
        from config import Config

        config = Config()

        # 测试单个用户
        users = config._parse_users('admin:password123')
        assert users == {'admin': 'password123'}

        # 测试多个用户
        users = config._parse_users('admin:pass1,user2:pass2')
        assert users == {'admin': 'pass1', 'user2': 'pass2'}

        # 测试空字符串
        users = config._parse_users('')
        assert users == {}

    def test_parse_weights(self):
        """权重配置解析"""
        from config import Config

        config = Config()

        # 测试中文标签
        weights = config._parse_weights('宝宝：1.8，露营：1.5')
        assert weights == {'宝宝': 1.8, '露营': 1.5}

        # 测试英文标签
        weights = config._parse_weights('tag1:2.0,tag2:1.5')
        assert weights == {'tag1': 2.0, 'tag2': 1.5}

    def test_boolean_config(self):
        """布尔配置解析"""
        from config import Config

        config = Config()

        assert config._get_bool('NON_EXISTENT', True) == True
        assert config._get_bool('NON_EXISTENT', False) == False
        assert config._get_bool('FLASK_DEBUG', False) == config.DEBUG

    def test_integer_config(self):
        """整数配置解析"""
        from config import Config

        config = Config()

        assert config._get_int('NON_EXISTENT', 100) == 100
        assert config._get_int('MAX_UPLOAD_SIZE_MB', 50) == config.MAX_UPLOAD_SIZE_MB

    def test_float_config(self):
        """浮点配置解析"""
        from config import Config

        config = Config()

        assert config._get_float('NON_EXISTENT', 1.5) == 1.5
        assert config._get_float('WEATHER_LAT', 0.0) == config.WEATHER_LAT


class TestPasswordUtils:
    """密码工具测试"""

    def test_hash_password(self):
        """密码哈希生成"""
        from auth import hash_password

        pwd_hash = hash_password('TestPassword123!')

        # 检查哈希格式
        assert pwd_hash.startswith('pbkdf2:sha256:')
        # 每次生成的哈希应该不同（盐值不同）
        pwd_hash2 = hash_password('TestPassword123!')
        assert pwd_hash != pwd_hash2

    def test_verify_password(self):
        """密码验证"""
        from auth import hash_password, verify_password

        password = 'TestPassword123!'
        pwd_hash = hash_password(password)

        # 正确密码
        assert verify_password(password, pwd_hash) == True
        # 错误密码
        assert verify_password('WrongPassword', pwd_hash) == False

    def test_password_strength(self):
        """密码强度检查"""
        from auth import is_password_strong

        # 强密码
        is_strong, _ = is_password_strong('SecurePass123!')
        assert is_strong == True

        # 太短
        is_strong, msg = is_password_strong('Ab1!')
        assert is_strong == False
        assert '长度' in msg

        # 只有小写
        is_strong, msg = is_password_strong('abcdefgh')
        assert is_strong == False

        # 只有大写
        is_strong, msg = is_password_strong('ABCDEFGH')
        assert is_strong == False

        # 只有数字
        is_strong, msg = is_password_strong('12345678')
        assert is_strong == False
