"""
数据库操作测试
"""
import os
import pytest
import sqlite3
import tempfile
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境变量
os.environ['FLASK_DEBUG'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only-12345678'


class TestDatabaseInit:
    """数据库初始化测试"""

    def test_init_db_creates_table(self):
        """初始化数据库创建表"""
        from services.database import init_database, set_db_file

        # 创建临时数据库
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        try:
            init_database(temp_db.name)

            # 验证表存在
            conn = sqlite3.connect(temp_db.name)
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='photos'")
            result = c.fetchone()

            assert result is not None
            assert result[0] == 'photos'

            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='app_state'")
            assert c.fetchone() is not None

            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
            assert c.fetchone() is not None
            conn.close()
        finally:
            os.unlink(temp_db.name)

    def test_init_db_wal_mode(self):
        """初始化数据库开启 WAL 模式"""
        from services.database import init_database

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        try:
            init_database(temp_db.name)

            # 验证 WAL 模式
            conn = sqlite3.connect(temp_db.name)
            c = conn.cursor()
            c.execute("PRAGMA journal_mode")
            result = c.fetchone()
            conn.close()

            assert result[0].lower() == 'wal'
        finally:
            os.unlink(temp_db.name)

    def test_init_db_applies_pragmas(self):
        """初始化数据库应用稳定性 PRAGMA"""
        from services.database import init_database, set_db_file, get_db_connection

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        try:
            init_database(temp_db.name)
            set_db_file(temp_db.name)
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("PRAGMA synchronous")
            synchronous = c.fetchone()[0]
            c.execute("PRAGMA foreign_keys")
            foreign_keys = c.fetchone()[0]
            conn.close()

            assert synchronous in (1, 2, 3)
            assert foreign_keys == 1
        finally:
            os.unlink(temp_db.name)

    def test_init_db_idempotent(self):
        """初始化数据库幂等性"""
        from services.database import init_database

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        try:
            # 多次初始化
            init_database(temp_db.name)
            init_database(temp_db.name)
            init_database(temp_db.name)

            # 应该不报错，且表存在
            conn = sqlite3.connect(temp_db.name)
            c = conn.cursor()
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='photos'")
            result = c.fetchone()
            conn.close()

            assert result is not None
        finally:
            os.unlink(temp_db.name)


class TestBuildPhotoIndex:
    """构建照片索引测试"""

    @pytest.fixture
    def test_upload_folder(self):
        """创建测试上传目录"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        # 清理
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_build_index_empty_folder(self, test_upload_folder):
        """构建索引 - 空目录"""
        from services.photo_index import PhotoIndexService, clear_photo_index, get_photo_index
        from services.database import init_database, set_db_file
        import tempfile

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        try:
            set_db_file(temp_db.name)
            init_database(temp_db.name)
            clear_photo_index()

            count = PhotoIndexService.build(test_upload_folder, {})

            # 验证数据库为空
            conn = sqlite3.connect(temp_db.name)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM photos")
            count = c.fetchone()[0]
            conn.close()

            assert count == 0
        finally:
            os.unlink(temp_db.name)

    def test_build_index_with_photos(self, test_upload_folder):
        """构建索引 - 有照片"""
        from services.photo_index import PhotoIndexService, clear_photo_index
        from services.database import init_database, set_db_file
        from PIL import Image
        import tempfile

        # 创建测试照片
        img = Image.new('RGB', (100, 100), color='blue')
        test_photo_path = os.path.join(test_upload_folder, 'test_photo.jpg')
        img.save(test_photo_path)

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        try:
            set_db_file(temp_db.name)
            init_database(temp_db.name)
            clear_photo_index()

            count = PhotoIndexService.build(test_upload_folder, {})

            # 验证数据库有记录
            conn = sqlite3.connect(temp_db.name)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM photos")
            count = c.fetchone()[0]
            conn.close()

            assert count >= 1
        finally:
            os.unlink(temp_db.name)


class TestMetadataOperations:
    """元数据操作测试"""

    def test_load_metadata_returns_dict(self):
        """加载元数据返回字典"""
        from services.metadata import PhotoMetadataService
        metadata = PhotoMetadataService.load()
        assert isinstance(metadata, dict)

    def test_save_and_load_metadata(self):
        """保存和加载元数据"""
        from services.metadata import PhotoMetadataService, set_metadata_file
        import tempfile

        # 创建临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.json')
        temp_file.close()

        try:
            set_metadata_file(temp_file.name)

            # 保存测试数据
            PhotoMetadataService.clear()
            PhotoMetadataService.set('photo1.jpg', {'date': '2024-01-15', 'tags': 'test'})
            PhotoMetadataService.set('photo2.jpg', {'date': '2024-02-20', 'tags': 'demo'})
            PhotoMetadataService.save()

            # 加载验证
            loaded = PhotoMetadataService.load()
            assert len(loaded) == 2
            assert loaded['photo1.jpg']['date'] == '2024-01-15'
        finally:
            os.unlink(temp_file.name)


class TestSmartCompress:
    """智能压缩测试"""

    def test_smart_compress_jpeg(self):
        """智能压缩 JPEG"""
        from services.image import ImageProcessor
        from PIL import Image
        import io

        # 创建测试图片
        img = Image.new('RGB', (500, 500), color='red')
        img_io = io.BytesIO()
        img.save(img_io, format='JPEG', quality=95)
        img_io.seek(0)

        original_size = len(img_io.getvalue())

        # 压缩
        result = ImageProcessor.smart_compress(img_io)

        # 验证压缩后大小
        compressed_size = len(result.getvalue())
        # 压缩后应该更小或相近
        assert compressed_size <= original_size * 1.1  # 允许 10% 误差

    def test_smart_compress_preserves_format(self):
        """压缩保留图片格式"""
        from services.image import ImageProcessor
        from PIL import Image
        import io

        # 创建 PNG 图片
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
        img_io = io.BytesIO()
        img.save(img_io, format='PNG')
        img_io.seek(0)

        # 压缩
        result = ImageProcessor.smart_compress(img_io)

        # 验证可以打开
        result.seek(0)
        compressed_img = Image.open(result)
        assert compressed_img.format in ['JPEG', 'PNG', 'WebP']  # 可能被转换


class TestDatabaseConcurrency:
    """数据库并发测试"""

    def test_concurrent_reads(self):
        """并发读取测试"""
        from services.database import init_database, set_db_file, get_db_connection
        import threading
        import tempfile

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        try:
            set_db_file(temp_db.name)
            # 初始化和填充数据
            init_database(temp_db.name)
            conn = get_db_connection()
            c = conn.cursor()
            for i in range(10):
                c.execute(
                    'INSERT INTO photos (url, date, month, tags, weight, view_count) VALUES (?, ?, ?, ?, ?, ?)',
                    (f'photo{i}.jpg', '2024-01-01', '1', 'test', 1.0, 0)
                )
            conn.commit()
            conn.close()

            # 并发读取
            results = []
            errors = []

            def reader():
                try:
                    for _ in range(5):
                        conn = get_db_connection()
                        c = conn.cursor()
                        c.execute('SELECT COUNT(*) FROM photos')
                        results.append(c.fetchone()[0])
                        conn.close()
                except Exception as e:
                    errors.append(str(e))

            threads = [threading.Thread(target=reader) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            # 验证所有读取成功
            assert len(errors) == 0
            assert all(r == 10 for r in results)
        finally:
            os.unlink(temp_db.name)


class TestAppStateDAO:
    """应用状态存储测试"""

    def test_force_show_state_persists_in_db(self):
        from services.database import init_database, set_db_file, AppStateDAO
        import tempfile

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        try:
            set_db_file(temp_db.name)
            init_database(temp_db.name)

            AppStateDAO.set_json('force_show', {'img_url': 'photo.jpg', 'expiry_timestamp': 12345})
            state = AppStateDAO.get_json('force_show')

            assert state['img_url'] == 'photo.jpg'
            assert state['expiry_timestamp'] == 12345
        finally:
            os.unlink(temp_db.name)


class TestMessageDAO:
    """留言存储测试"""

    def test_insert_message_keeps_recent_records(self):
        from services.database import init_database, set_db_file, MessageDAO
        import tempfile

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        try:
            set_db_file(temp_db.name)
            init_database(temp_db.name)

            for i in range(3):
                MessageDAO.insert_message(
                    {
                        'id': str(i),
                        'content': f'msg-{i}',
                        'sender': 'tester',
                        'timestamp': '03-19 12:00',
                    },
                    keep_last=2
                )

            messages = MessageDAO.get_recent(limit=10)
            assert len(messages) == 2
            assert [m['id'] for m in messages] == ['1', '2']
        finally:
            os.unlink(temp_db.name)


class TestBackgroundRebuilder:
    """后台自修复线程测试"""

    def test_background_rebuilder_disabled_by_config(self, monkeypatch):
        from services import photo_index

        monkeypatch.setattr(photo_index.config, 'ENABLE_BACKGROUND_INDEX_REBUILD', False)
        monkeypatch.setattr(photo_index, '_background_rebuilder_started', False)

        photo_index.PhotoIndexService.start_background_rebuilder('/tmp/none', {}, None)

        assert photo_index._background_rebuilder_started is False
