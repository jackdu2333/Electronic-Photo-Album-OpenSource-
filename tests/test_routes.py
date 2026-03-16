"""
API 路由测试
"""
import os
import io
import json
import pytest
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境变量
os.environ['FLASK_DEBUG'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only-12345678'
os.environ['ADMIN_USERS'] = 'admin:TestPass123!'


class TestIndexRoute:
    """首页路由测试"""

    @pytest.fixture
    def client(self):
        """创建 Flask 测试客户端"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_index_returns_200(self, client):
        """首页返回 200"""
        response = client.get('/')
        assert response.status_code == 200

    def test_index_contains_html(self, client):
        """首页返回 HTML 内容"""
        response = client.get('/')
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data

    def test_index_cache_control(self, client):
        """首页设置 Cache-Control: no-store"""
        response = client.get('/')
        assert response.headers.get('Cache-Control') == 'no-store'


class TestAuthRequired:
    """认证保护的路由测试"""

    @pytest.fixture
    def client(self):
        """创建 Flask 测试客户端"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_admin_requires_auth(self, client):
        """/admin 需要认证"""
        response = client.get('/admin')
        assert response.status_code == 401

    def test_upload_requires_auth(self, client):
        """/upload 需要认证"""
        response = client.post('/upload')
        assert response.status_code == 401

    def test_api_status_requires_auth(self, client):
        """/api/status 需要认证"""
        response = client.get('/api/status')
        assert response.status_code == 401

    def test_admin_with_auth(self, client):
        """/admin 有认证时访问成功"""
        response = client.get(
            '/admin',
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}  # admin:TestPass123!
        )
        assert response.status_code == 200


class TestMessageAPI:
    """留言板 API 测试"""

    @pytest.fixture
    def client(self):
        """创建 Flask 测试客户端"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_get_messages_returns_list(self, client):
        """获取消息返回列表"""
        response = client.get(
            '/api/messages',
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_send_message_requires_auth(self, client):
        """发送消息需要认证"""
        response = client.post(
            '/api/send',
            json={'content': 'Test message'}
        )
        assert response.status_code == 401

    def test_send_message_success(self, client):
        """发送消息成功"""
        response = client.post(
            '/api/send',
            json={'content': 'Test message'},
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'content' in data
        assert data['content'] == 'Test message'

    def test_send_message_empty_content(self, client):
        """发送空内容失败"""
        response = client.post(
            '/api/send',
            json={'content': ''},
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )
        assert response.status_code == 400

    def test_send_message_missing_content(self, client):
        """发送缺少 content 字段失败"""
        response = client.post(
            '/api/send',
            json={'other': 'data'},
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )
        assert response.status_code == 400


class TestWeatherAPI:
    """天气 API 测试"""

    @pytest.fixture
    def client(self):
        """创建 Flask 测试客户端"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_weather_config_returns_response(self, client):
        """天气配置接口返回响应"""
        response = client.get('/api/weather-config')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'enabled' in data


class TestImageAPI:
    """图片 API 测试"""

    @pytest.fixture
    def client(self):
        """创建 Flask 测试客户端"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as client:
            yield client

    def test_api_all_photos_requires_auth(self, client):
        """/api/all_photos 需要认证"""
        response = client.get('/api/all_photos')
        assert response.status_code == 401

    def test_api_images_requires_auth(self, client):
        """/api/images 需要认证"""
        response = client.get('/api/images')
        assert response.status_code == 401

    def test_get_photo_requires_auth(self, client):
        """/api/get_photo 需要认证"""
        response = client.get('/api/get_photo')
        assert response.status_code == 401
