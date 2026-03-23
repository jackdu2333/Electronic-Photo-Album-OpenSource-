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
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client

    def test_index_returns_200(self, client):
        """首页返回 200"""
        response = client.get('/', follow_redirects=False)
        assert response.status_code == 302

    def test_index_contains_html(self, client):
        """首页返回 HTML 内容"""
        response = client.get('/login')
        assert b'<!DOCTYPE html>' in response.data or b'<html' in response.data

    def test_index_cache_control(self, client):
        """首页设置 Cache-Control: no-store"""
        response = client.get('/login')
        assert response.status_code == 200


class TestAuthRequired:
    """认证保护的路由测试"""

    @pytest.fixture
    def client(self):
        """创建 Flask 测试客户端"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client

    def test_admin_requires_auth(self, client):
        """/admin 需要认证"""
        response = client.get('/admin')
        assert response.status_code == 302

    def test_upload_requires_auth(self, client):
        """/upload 需要认证"""
        response = client.post('/upload')
        assert response.status_code == 302

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
        app.config['WTF_CSRF_ENABLED'] = False
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
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client

    def test_weather_config_returns_response(self, client):
        """天气配置接口返回响应"""
        response = client.get(
            '/api/weather-config',
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'enabled' in data


class TestDailyQuoteAPI:
    """每日一言 API 测试"""

    @pytest.fixture
    def client(self):
        """创建 Flask 测试客户端"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client

    def test_daily_quote_requires_auth(self, client):
        """/api/daily-quote 需要认证"""
        response = client.get('/api/daily-quote')
        assert response.status_code == 401

    def test_daily_quote_returns_payload(self, client, monkeypatch):
        """每日一言返回标准字段"""
        import routes.api as api_module

        fake_payload = {
            'text': '测试句子',
            'source': '测试来源',
            'provider': 'local',
            'lang': 'zh',
            'date': '2026-03-23'
        }
        monkeypatch.setattr(
            api_module,
            '_resolve_daily_quote',
            lambda force_refresh=False: (fake_payload, True)
        )

        response = client.get(
            '/api/daily-quote',
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['text'] == '测试句子'
        assert data['source'] == '测试来源'
        assert data['provider'] == 'local'
        assert data['lang'] == 'zh'
        assert data['cached'] is True


class TestImageAPI:
    """图片 API 测试"""

    @pytest.fixture
    def client(self):
        """创建 Flask 测试客户端"""
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
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

    def test_api_images_includes_note_fields(self, client, monkeypatch):
        """/api/images 返回便签字段（note_title/note_body）"""
        import routes.api as api_module
        from services.metadata import PhotoMetadataService

        monkeypatch.setattr(
            api_module,
            'get_photo_index',
            lambda: [{
                'url': 'demo.jpg',
                'date': '2026-03-23',
                'month': 3,
                'tags': '旅行',
                'weight': 1.0
            }]
        )
        monkeypatch.setattr(
            PhotoMetadataService,
            'load',
            classmethod(lambda cls, filepath=None: {'demo.jpg': {'note_title': '标题', 'note_body': '正文'}})
        )
        monkeypatch.setattr(
            PhotoMetadataService,
            'all',
            classmethod(lambda cls: {'demo.jpg': {'note_title': '标题', 'note_body': '正文'}})
        )

        response = client.get(
            '/api/images',
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, list)
        assert data[0]['note_title'] == '标题'
        assert data[0]['note_body'] == '正文'

    def test_update_photo_supports_note_fields(self, client, monkeypatch):
        """/api/update_photo 支持保存便签字段"""
        from services.metadata import PhotoMetadataService
        from services.photo_index import PhotoIndexService

        captured = {}

        def fake_update(cls, url, date, tags, note_title=None, note_body=None):
            captured['url'] = url
            captured['date'] = date
            captured['tags'] = tags
            captured['note_title'] = note_title
            captured['note_body'] = note_body

        monkeypatch.setattr(PhotoMetadataService, 'update', classmethod(fake_update))
        monkeypatch.setattr(PhotoMetadataService, 'save', classmethod(lambda cls, filepath=None: True))
        monkeypatch.setattr(PhotoIndexService, 'calculate_weight', staticmethod(lambda tags, tag_weights=None: 1.0))
        monkeypatch.setattr(PhotoIndexService, 'update_photo', staticmethod(lambda *args, **kwargs: None))

        response = client.post(
            '/api/update_photo',
            json={
                'filename': 'demo.jpg',
                'date': '2026-03-23',
                'tags': '旅行,家庭',
                'note_title': '我的标题',
                'note_body': '我的正文'
            },
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )

        assert response.status_code == 200
        assert captured['url'] == 'demo.jpg'
        assert captured['note_title'] == '我的标题'
        assert captured['note_body'] == '我的正文'
