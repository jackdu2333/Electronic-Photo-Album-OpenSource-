"""
上传功能测试
"""
import os
import io
import pytest
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMIMEValidation:
    """MIME 类型验证测试"""

    def test_validate_jpeg(self):
        """JPEG 图片验证"""
        from app import validate_image_mime

        # JPEG 魔数：FF D8 FF
        jpeg_data = b'\xff\xd8\xff\xe0\x00\x10JFIF'
        jpeg_io = io.BytesIO(jpeg_data)

        is_valid, result = validate_image_mime(jpeg_io)
        assert is_valid == True
        assert 'jpeg' in result.lower()

    def test_validate_png(self):
        """PNG 图片验证"""
        from app import validate_image_mime

        # PNG 魔数：89 50 4E 47 0D 0A 1A 0A
        png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
        png_io = io.BytesIO(png_data)

        is_valid, result = validate_image_mime(png_io)
        assert is_valid == True
        assert 'png' in result.lower()

    def test_validate_gif(self):
        """GIF 图片验证"""
        from app import validate_image_mime

        # GIF 魔数：47 49 46 38
        gif_data = b'GIF89a\x01\x00\x01\x00'
        gif_io = io.BytesIO(gif_data)

        is_valid, result = validate_image_mime(gif_io)
        assert is_valid == True
        assert 'gif' in result.lower()

    def test_validate_invalid_file(self):
        """无效文件验证"""
        from app import validate_image_mime

        # 文本文件
        text_data = b'This is not an image'
        text_io = io.BytesIO(text_data)

        is_valid, result = validate_image_mime(text_io)
        assert is_valid == False
        assert '无法识别' in result or '验证失败' in result or 'not an image' in result.lower()

    def test_validate_empty_file(self):
        """空文件验证"""
        from app import validate_image_mime

        empty_io = io.BytesIO()

        is_valid, result = validate_image_mime(empty_io)
        assert is_valid == False

    def test_validate_webp(self):
        """WebP 图片验证"""
        from app import validate_image_mime

        # WebP 魔数：RIFF....WEBP
        webp_data = b'RIFF\x00\x00\x00\x00WEBP'
        webp_io = io.BytesIO(webp_data)

        is_valid, result = validate_image_mime(webp_io)
        assert is_valid == True
        assert 'webp' in result.lower()


class TestFileUpload:
    """文件上传功能测试（需要 Flask 测试客户端）"""

    @pytest.fixture
    def client(self):
        """创建 Flask 测试客户端"""
        # 设置测试环境变量
        os.environ['FLASK_DEBUG'] = 'true'
        os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only-12345'
        os.environ['ADMIN_USERS'] = 'admin:TestPass123!'

        import importlib
        import app
        importlib.reload(app)

        app.app.config['TESTING'] = True
        app.app.config['WTF_CSRF_ENABLED'] = False
        app.app.config['UPLOAD_FOLDER'] = '/tmp/test-uploads'

        # 创建上传目录
        os.makedirs('/tmp/test-uploads', exist_ok=True)

        with app.app.test_client() as client:
            yield client

        # 清理
        import shutil
        if os.path.exists('/tmp/test-uploads'):
            shutil.rmtree('/tmp/test-uploads')

    def test_upload_requires_auth(self, client):
        """上传需要认证"""
        data = {
            'files': [(io.BytesIO(b'test'), 'test.jpg')]
        }
        response = client.post('/upload', data=data)
        assert response.status_code == 302

    def test_upload_valid_image(self, client):
        """上传有效图片"""
        # 创建 JPEG 图片
        from PIL import Image
        img_io = io.BytesIO()
        img = Image.new('RGB', (100, 100), color='red')
        img.save(img_io, format='JPEG')
        img_io.seek(0)

        data = {
            'files': [(img_io, 'test.jpg')]
        }
        response = client.post(
            '/upload',
            data=data,
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}  # admin:TestPass123!
        )
        assert response.status_code == 200

    def test_upload_invalid_extension(self, client):
        """上传无效扩展名"""
        data = {
            'files': [(io.BytesIO(b'not an image'), 'test.txt')]
        }
        response = client.post(
            '/upload',
            data=data,
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )
        assert response.status_code == 400
