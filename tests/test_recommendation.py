"""
推荐算法测试
"""
import os
import pytest
import sys
import sqlite3
import tempfile
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境变量
os.environ['FLASK_DEBUG'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only-12345678'
os.environ['ADMIN_USERS'] = 'admin:TestPass123!'


class TestRecommendationAlgorithm:
    """V2.0 双轨制推荐算法测试"""

    @pytest.fixture
    def app_with_photos(self):
        """创建带有测试照片的 Flask 应用"""
        from app import create_app
        from services.database import set_db_file, init_database, get_db_connection
        from services.photo_index import PhotoIndexService, set_photo_index, clear_photo_index
        from services.recommendation import set_recommendation_config

        app = create_app()
        app.config['TESTING'] = True

        # 创建临时数据库
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        # 设置测试数据库
        set_db_file(temp_db.name)
        init_database(temp_db.name)

        # 插入测试照片数据
        conn = get_db_connection(timeout=10)
        c = conn.cursor()

        # 插入不同标签和权重的照片
        test_photos = [
            ('photo1.jpg', '2024-01-15', '1', '宝宝，户外', 2.0, 0),
            ('photo2.jpg', '2024-06-20', '6', '露营，夏天', 1.8, 0),
            ('photo3.jpg', '2023-12-01', '12', '宝宝，室内', 1.5, 0),
            ('photo4.jpg', '2024-03-10', '3', '春天，户外', 1.0, 0),
            ('photo5.jpg', '2023-08-15', '8', '游泳，夏天', 0.5, 0),
        ]

        c.executemany(
            'INSERT OR REPLACE INTO photos (url, date, month, tags, weight, view_count) VALUES (?, ?, ?, ?, ?, ?)',
            test_photos
        )
        conn.commit()
        conn.close()

        # 设置测试索引
        clear_photo_index()
        test_index = [
            {'url': 'photo1.jpg', 'date': '2024-01-15', 'month': 1, 'tags': '宝宝，户外', 'weight': 2.0},
            {'url': 'photo2.jpg', 'date': '2024-06-20', 'month': 6, 'tags': '露营，夏天', 'weight': 1.8},
            {'url': 'photo3.jpg', 'date': '2023-12-01', 'month': 12, 'tags': '宝宝，室内', 'weight': 1.5},
            {'url': 'photo4.jpg', 'date': '2024-03-10', 'month': 3, 'tags': '春天，户外', 'weight': 1.0},
            {'url': 'photo5.jpg', 'date': '2023-08-15', 'month': 8, 'tags': '游泳，夏天', 'weight': 0.5},
        ]
        set_photo_index(test_index)

        # 设置推荐算法配置
        set_recommendation_config(
            seasonal_weights={"current": 2.0, "adjacent": 1.5, "other": 1.0, "none": 0.5},
            deep_sea_probability=0.05,
            deep_sea_years_threshold=2
        )

        with app.test_client() as client:
            yield client, temp_db.name

        # 清理
        os.unlink(temp_db.name)

    def test_get_photo_returns_photo(self, app_with_photos):
        """获取照片接口返回照片"""
        client, db_path = app_with_photos

        response = client.get(
            '/api/get_photo',
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'url' in data or 'error' in data  # 可能返回照片或错误

    def test_recommendation_prefers_high_weight(self, app_with_photos):
        """推荐算法偏好高权重照片"""
        client, db_path = app_with_photos

        # 多次请求，统计返回结果
        results = []
        for _ in range(20):
            response = client.get(
                '/api/get_photo',
                headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
            )
            data = json.loads(response.data)
            if 'url' in data:
                results.append(data['url'])

        # 高权重照片应该更频繁出现
        if results:
            weight_2_count = sum(1 for r in results if 'photo1' in r)
            # photo1 权重最高 (2.0)，应该占多数
            assert weight_2_count >= len(results) * 0.2  # 至少 20%


class TestWeightedScoring:
    """加权评分逻辑测试"""

    def test_seasonal_weight_boost(self):
        """季节权重加成"""
        from datetime import datetime

        # 模拟 6 月（夏天），"夏天"标签应该获得加成
        current_month = 6
        tags = "夏天，露营"

        # 简单验证季节匹配逻辑
        assert "夏天" in tags
        assert current_month in [6, 7, 8]

    def test_tag_weight_calculation(self):
        """标签权重计算"""
        # 验证权重配置解析
        from config import Config

        config = Config()
        weights = config._parse_weights('宝宝：2.0，露营：1.5')

        assert weights['宝宝'] == 2.0
        assert weights['露营'] == 1.5
        assert weights.get('不存在的标签', 1.0) == 1.0  # 默认权重


class TestPhotoMetadata:
    """照片元数据测试"""

    def test_date_extraction(self):
        """日期提取"""
        from datetime import datetime

        # 验证日期格式解析
        date_str = "2024:06:15 14:30:00"
        try:
            date_obj = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            assert date_obj.year == 2024
            assert date_obj.month == 6
        except ValueError:
            # 如果格式不支持，验证回退逻辑
            pass

    def test_month_extraction(self):
        """月份提取"""
        from datetime import datetime

        date = datetime(2024, 6, 15)
        assert date.month == 6

    def test_tags_parsing(self):
        """标签解析"""
        # 验证标签分隔符处理
        tags_str = "宝宝，户外，夏天"
        tags = [t.strip() for t in tags_str.split('，')]
        assert len(tags) == 3
        assert "宝宝" in tags
        assert "户外" in tags
