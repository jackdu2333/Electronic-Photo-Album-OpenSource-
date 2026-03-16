"""
认证模块测试
"""
import os
import pytest
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境变量（在导入 auth 之前）
os.environ['FLASK_DEBUG'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only-12345678'


class TestAuth:
    """认证功能测试"""

    def test_import_auth_module(self):
        """认证模块可导入"""
        from auth import hash_password, verify_password, is_password_strong
        assert hash_password is not None
        assert verify_password is not None
        assert is_password_strong is not None

    def test_hash_format(self):
        """哈希值格式正确"""
        from auth import hash_password

        pwd_hash = hash_password('TestPassword123!')

        # 检查前缀
        assert pwd_hash.startswith('pbkdf2:sha256:')

        # 检查包含迭代次数
        parts = pwd_hash.split('$')
        assert len(parts) >= 4
        assert parts[1] == 'pbkdf2'
        assert parts[2] == 'sha256'
        # 迭代次数应该是 600000
        assert int(parts[3]) == 600000

    def test_unique_salts(self):
        """相同密码生成不同哈希（盐值不同）"""
        from auth import hash_password

        hash1 = hash_password('SamePassword123!')
        hash2 = hash_password('SamePassword123!')

        assert hash1 != hash2

    def test_verify_same_password(self):
        """验证相同密码成功"""
        from auth import hash_password, verify_password

        password = 'CorrectPassword456!'
        pwd_hash = hash_password(password)

        assert verify_password(password, pwd_hash) == True

    def test_verify_wrong_password(self):
        """验证错误密码失败"""
        from auth import hash_password, verify_password

        password = 'CorrectPassword456!'
        pwd_hash = hash_password(password)

        assert verify_password('WrongPassword', pwd_hash) == False

    def test_password_strength_requirements(self):
        """密码强度要求"""
        from auth import is_password_strong

        # 合格密码：长度 + 大写 + 小写 + 数字/特殊字符
        test_cases = [
            # (password, should_pass, description)
            ('SecurePass123!', True, '合格密码'),
            ('MyP@ssw0rd', True, '含特殊字符'),
            ('TestUser99', True, '含数字'),

            # 太短
            ('Ab1!', False, '太短'),
            ('Short1A', False, '长度不足 7'),

            # 缺少大写
            ('lowercase123!', False, '缺少大写'),

            # 缺少小写
            ('UPPERCASE123!', False, '缺少小写'),

            # 缺少数字或特殊字符
            ('OnlyLetters', False, '只有字母'),
            ('ONLYUPPERLETTERS', False, '只有大写字母'),
            ('onlylowercase', False, '只有小写字母'),
            ('12345678', False, '只有数字'),
            ('!@#$%^&*', False, '只有特殊字符'),
        ]

        for password, should_pass, description in test_cases:
            is_strong, msg = is_password_strong(password)
            assert is_strong == should_pass, f"{description}: {password} - {msg}"

    def test_empty_password(self):
        """空密码检查"""
        from auth import is_password_strong

        is_strong, msg = is_password_strong('')
        assert is_strong == False
        assert '长度' in msg

    def test_unicode_password(self):
        """Unicode 密码支持"""
        from auth import hash_password, verify_password

        # 包含中文的密码
        password = '密码 Password123!'
        pwd_hash = hash_password(password)

        assert verify_password(password, pwd_hash) == True
        assert verify_password('Wrong', pwd_hash) == False


class TestManageUsersCLI:
    """密码管理工具测试"""

    def test_cli_exists(self):
        """CLI 工具存在"""
        import os
        cli_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'tools', 'manage_users.py'
        )
        assert os.path.exists(cli_path)

    def test_cli_hash_command(self, capsys):
        """CLI hash 命令"""
        import subprocess

        result = subprocess.run(
            ['python', 'tools/manage_users.py', 'hash', 'TestPass123!'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        assert result.returncode == 0
        assert '密码哈希' in result.stdout
        assert 'pbkdf2:sha256:' in result.stdout

    def test_cli_check_command(self, capsys):
        """CLI check 命令"""
        import subprocess

        # 强密码
        result = subprocess.run(
            ['python', 'tools/manage_users.py', 'check', 'SecurePass123!'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        assert result.returncode == 0
        assert '✅' in result.stdout

        # 弱密码
        result = subprocess.run(
            ['python', 'tools/manage_users.py', 'check', '123456'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

        assert result.returncode == 0
        assert '❌' in result.stdout
