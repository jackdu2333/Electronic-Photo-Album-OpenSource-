"""
Pytest 测试夹具和共享配置
"""
import os
import pytest
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope='session')
def test_env():
    """设置测试环境变量"""
    # 保存原始环境变量
    original_env = {
        'FLASK_DEBUG': os.environ.get('FLASK_DEBUG'),
        'SECRET_KEY': os.environ.get('SECRET_KEY'),
        'ADMIN_USERS': os.environ.get('ADMIN_USERS'),
    }

    # 设置测试环境
    os.environ['FLASK_DEBUG'] = 'true'
    os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only-12345678'
    os.environ['ADMIN_USERS'] = 'admin:TestPass123!'

    yield

    # 恢复原始环境变量
    for key, value in original_env.items():
        if value is not None:
            os.environ[key] = value
        elif key in os.environ:
            del os.environ[key]


@pytest.fixture
def app_instance(test_env):
    """创建 Flask 应用实例"""
    import importlib
    import app
    importlib.reload(app)

    app.app.config['TESTING'] = True
    app.app.config['UPLOAD_FOLDER'] = '/tmp/test-uploads'
    app.app.config['DATABASE_FILE'] = '/tmp/test-photos.db'

    # 创建上传目录
    os.makedirs('/tmp/test-uploads', exist_ok=True)

    yield app.app

    # 清理
    import shutil
    for path in ['/tmp/test-uploads', '/tmp/test-photos.db']:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)


@pytest.fixture
def client(app_instance):
    """创建 Flask 测试客户端"""
    with app_instance.test_client() as c:
        yield c


@pytest.fixture
def auth_headers():
    """Basic Auth 请求头"""
    import base64
    credentials = 'admin:TestPass123!'
    encoded = base64.b64encode(credentials.encode()).decode()
    return {'Authorization': f'Basic {encoded}'}
