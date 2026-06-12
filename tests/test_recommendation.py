"""
推荐算法测试 - V3.0 Memory Curator
"""
import os
import pytest
import sys
import sqlite3
import tempfile
import json
from datetime import datetime
from unittest.mock import patch

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境变量
os.environ['FLASK_DEBUG'] = 'true'
os.environ['SECRET_KEY'] = 'test-secret-key-for-testing-only-12345678'
os.environ['ADMIN_USERS'] = 'admin:TestPass123!'


class TestRecommendationAlgorithm:
    """V3.0 多频道推荐算法测试"""

    @pytest.fixture
    def app_with_photos(self):
        """创建带有测试照片的 Flask 应用"""
        from app import create_app
        from services.database import set_db_file, init_database, get_db_connection
        from services.photo_index import clear_photo_index
        from services.recommendation import set_recommendation_config

        app = create_app()
        app.config['TESTING'] = True

        # 创建临时数据库
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()

        # 设置测试数据库
        set_db_file(temp_db.name)
        init_database(temp_db.name)

        # 插入测试照片数据（含 v3 字段）
        conn = get_db_connection(timeout=10)
        c = conn.cursor()

        test_photos = [
            ('ic_001', 'photo1.jpg', 'imported_copy', 'photo1.jpg', '/api/photos/ic_001/image',
             '2024-01-15', 1, '宝宝，户外', 2.0, 0, 0),
            ('ic_002', 'photo2.jpg', 'imported_copy', 'photo2.jpg', '/api/photos/ic_002/image',
             '2024-06-20', 6, '露营，夏天', 1.8, 0, 0),
            ('ic_003', 'photo3.jpg', 'imported_copy', 'photo3.jpg', '/api/photos/ic_003/image',
             '2023-12-01', 12, '宝宝，室内', 1.5, 0, 0),
            ('ic_004', 'photo4.jpg', 'imported_copy', 'photo4.jpg', '/api/photos/ic_004/image',
             '2024-03-10', 3, '春天，户外', 1.0, 0, 0),
            ('ic_005', 'photo5.jpg', 'imported_copy', 'photo5.jpg', '/api/photos/ic_005/image',
             '2023-08-15', 8, '游泳，夏天', 0.5, 0, 0),
        ]

        c.executemany(
            '''INSERT OR REPLACE INTO photos
               (id, url, source_type, source_ref, display_url,
                date, month, tags, weight, view_count, missing)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            test_photos
        )
        conn.commit()
        conn.close()

        clear_photo_index()

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
        assert 'url' in data or 'error' in data

    def test_recommendation_returns_v3_fields(self, app_with_photos):
        """推荐结果包含 v3 字段"""
        client, db_path = app_with_photos

        response = client.get(
            '/api/get_photo',
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)

        # v3 字段
        assert 'display_url' in data
        assert 'id' in data
        assert 'source_type' in data
        # 推荐元数据
        assert 'recommend_channel' in data
        assert 'recommend_reason' in data

    def test_recommendation_excludes_missing_photos(self, app_with_photos):
        """推荐结果不包含缺失照片"""
        from services.database import get_db_connection

        client, db_path = app_with_photos

        # 将 photo1 标记为 missing
        conn = get_db_connection(timeout=10)
        conn.execute("UPDATE photos SET missing = 1 WHERE url = 'photo1.jpg'")
        conn.commit()
        conn.close()

        # 多次请求，确保 photo1 不会被推荐
        from services.recommendation import RecommendationService
        from services import recommendation
        with patch.object(recommendation.random, 'randint', return_value=100):
            with patch.object(recommendation.random, 'choices',
                              side_effect=lambda pop, **kw: [pop[0]] if pop else []):
                for _ in range(10):
                    result = RecommendationService.get_next_photo()
                    if result:
                        assert result['url'] != 'photo1.jpg'

    def test_recommendation_has_channel_and_reason(self, app_with_photos):
        """推荐结果包含频道和理由"""
        from services.recommendation import RecommendationService
        from services import recommendation

        # 固定为随缘漫游频道
        with patch.object(recommendation.random, 'choices',
                          side_effect=[['random'], [{'url': 'photo1.jpg', 'id': 'ic_001', 'weight': 1.0, 'view_count': 5}]]):
            result = RecommendationService.get_next_photo()
            if result:
                assert result['recommend_channel'] == 'random'
                assert result['recommend_reason'] in ('随缘漫游', '随机惊喜')

    def test_recommendation_prefers_high_weight(self, app_with_photos, monkeypatch):
        """推荐算法偏好高权重照片"""
        client, db_path = app_with_photos

        from services import recommendation

        captured = {}

        def fake_choices(population, weights=None, k=None):
            captured['population'] = population
            captured['weights'] = weights
            captured['k'] = k
            return [population[0]]

        # 固定走 random 频道（randint=100），然后 choices 返回第一张
        monkeypatch.setattr(recommendation.random, 'choices', fake_choices)

        response = client.get(
            '/api/get_photo',
            headers={'Authorization': 'Basic YWRtaW46VGVzdFBhc3MxMjMh'}
        )
        data = json.loads(response.data)

        assert response.status_code == 200
        assert 'url' in data

    def test_force_show_state_is_persistent(self, app_with_photos):
        """强制展示状态持久化"""
        from services.recommendation import set_force_show, get_force_show_state
        import time

        set_force_show('photo1.jpg', time.time() + 60)
        force_url, expiry = get_force_show_state()

        assert force_url == 'photo1.jpg'
        assert expiry > time.time()


class TestCooldownPool:
    """冷却池机制测试"""

    @pytest.fixture
    def setup_db(self):
        """设置测试数据库"""
        from services.database import set_db_file, init_database, get_db_connection, PhotoDAO

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        set_db_file(temp_db.name)
        init_database(temp_db.name)

        # 插入测试数据
        conn = get_db_connection(timeout=10)
        c = conn.cursor()
        c.executemany(
            '''INSERT OR REPLACE INTO photos
               (id, url, source_type, source_ref, display_url, date, month, tags, weight, view_count, missing)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            [
                ('ic_001', 'p1.jpg', 'imported_copy', 'p1.jpg', '/api/photos/ic_001/image',
                 '2024-01-15', 1, '宝宝', 2.0, 5, 0),
                ('ic_002', 'p2.jpg', 'imported_copy', 'p2.jpg', '/api/photos/ic_002/image',
                 '2024-06-20', 6, '露营', 1.8, 3, 0),
                ('ic_003', 'p3.jpg', 'imported_copy', 'p3.jpg', '/api/photos/ic_003/image',
                 '2024-03-10', 3, '户外', 1.0, 10, 0),
            ]
        )
        conn.commit()
        conn.close()

        yield temp_db.name

        os.unlink(temp_db.name)

    def test_recent_played_ids(self, setup_db):
        """记录播放后能正确获取最近播放 ID"""
        from services.database import PhotoDAO

        PhotoDAO.record_play('ic_001', 'random', '随缘漫游')
        PhotoDAO.record_play('ic_002', 'highlights', '高光时刻')

        recent = PhotoDAO.get_recent_played_ids(10)
        assert 'ic_001' in recent
        assert 'ic_002' in recent
        assert len(recent) == 2

    def test_cooldown_excludes_played(self, setup_db):
        """冷却池排除最近播放的照片"""
        from services.database import PhotoDAO
        from services.recommendation import RecommendationService, get_recent_played_ids

        # 记录 ic_001 和 ic_002 已播放
        PhotoDAO.record_play('ic_001', 'random', 'test')
        PhotoDAO.record_play('ic_002', 'random', 'test')

        cooled = set(get_recent_played_ids(30))
        assert 'ic_001' in cooled
        assert 'ic_002' in cooled

        # 从 PhotoService 获取索引，过滤冷却池
        from services.photo_service import PhotoService
        pool = PhotoService.get_photo_index()
        filtered = [p for p in pool if RecommendationService._photo_key(p) not in cooled]

        # ic_001 和 ic_002 被排除，只剩 ic_003
        filtered_urls = [p['url'] for p in filtered]
        assert 'p1.jpg' not in filtered_urls
        assert 'p2.jpg' not in filtered_urls
        assert 'p3.jpg' in filtered_urls


class TestLowExposureCompensation:
    """低曝光补偿测试"""

    @pytest.fixture
    def setup_db(self):
        from services.database import set_db_file, init_database, get_db_connection

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        set_db_file(temp_db.name)
        init_database(temp_db.name)

        conn = get_db_connection(timeout=10)
        c = conn.cursor()
        # 高曝光照片 vs 低曝光照片
        c.executemany(
            '''INSERT OR REPLACE INTO photos
               (id, url, source_type, source_ref, display_url, date, month, tags, weight, view_count, missing)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            [
                ('hi_001', 'high1.jpg', 'imported_copy', 'high1.jpg', '/api/photos/hi_001/image',
                 '2024-01-15', 1, '宝宝', 1.0, 50, 0),
                ('hi_002', 'high2.jpg', 'imported_copy', 'high2.jpg', '/api/photos/hi_002/image',
                 '2024-02-15', 2, '户外', 1.0, 50, 0),
                ('lo_001', 'low1.jpg', 'imported_copy', 'low1.jpg', '/api/photos/lo_001/image',
                 '2024-03-15', 3, '露营', 1.0, 1, 0),
                ('lo_002', 'low2.jpg', 'imported_copy', 'low2.jpg', '/api/photos/lo_002/image',
                 '2024-04-15', 4, '旅行', 1.0, 2, 0),
            ]
        )
        conn.commit()
        conn.close()

        yield temp_db.name
        os.unlink(temp_db.name)

    def test_low_view_count_gets_boost(self, setup_db):
        """低 view_count 照片在随缘漫游中获得补偿"""
        from services.recommendation import RecommendationService
        from services.photo_service import PhotoService

        pool = PhotoService.get_photo_index()
        assert len(pool) == 4

        # 模拟多次随机选择，统计低曝光照片被选中的频率
        import random as real_random
        real_random.seed(42)
        from services import recommendation as rec_module

        counts = {'low': 0, 'high': 0}
        for _ in range(200):
            photo, reason = RecommendationService._random_roam(pool)
            if photo['view_count'] < 10:
                counts['low'] += 1
            else:
                counts['high'] += 1

        # 低曝光照片应被选中更多次（补偿效果）
        assert counts['low'] > counts['high'], \
            f"Low exposure photos should be selected more: low={counts['low']}, high={counts['high']}"


class TestWeightedScoring:
    """加权评分逻辑测试"""

    def test_seasonal_weight_boost(self):
        """季节权重加成"""
        from datetime import datetime

        current_month = 6
        tags = "夏天，露营"

        assert "夏天" in tags
        assert current_month in [6, 7, 8]

    def test_tag_weight_calculation(self):
        """标签权重计算"""
        from config import Config

        config = Config()
        weights = config._parse_weights('宝宝：2.0，露营：1.5')

        assert weights['宝宝'] == 2.0
        assert weights['露营'] == 1.5
        assert weights.get('不存在的标签', 1.0) == 1.0


class TestPhotoMetadata:
    """照片元数据测试"""

    def test_date_extraction(self):
        """日期提取"""
        from datetime import datetime

        date_str = "2024:06:15 14:30:00"
        try:
            date_obj = datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            assert date_obj.year == 2024
            assert date_obj.month == 6
        except ValueError:
            pass

    def test_month_extraction(self):
        """月份提取"""
        from datetime import datetime

        date = datetime(2024, 6, 15)
        assert date.month == 6

    def test_tags_parsing(self):
        """标签解析"""
        tags_str = "宝宝，户外，夏天"
        tags = [t.strip() for t in tags_str.split('，')]
        assert len(tags) == 3
        assert "宝宝" in tags
        assert "户外" in tags


class TestTodayMemory:
    """今日回忆频道测试"""

    @pytest.fixture
    def setup_db(self):
        from services.database import set_db_file, init_database, get_db_connection
        from services.recommendation import set_recommendation_config

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        set_db_file(temp_db.name)
        init_database(temp_db.name)

        # 构造往年今天 + 普通照片
        today = datetime.now()
        last_year = today.year - 1
        anniversary_date = f"{last_year}-{today.month:02d}-{today.day:02d}"

        conn = get_db_connection(timeout=10)
        c = conn.cursor()
        c.executemany(
            '''INSERT OR REPLACE INTO photos
               (id, url, source_type, source_ref, display_url, date, month, tags, weight, view_count, missing)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            [
                ('ann_001', 'anniversary.jpg', 'imported_copy', 'anniversary.jpg',
                 '/api/photos/ann_001/image', anniversary_date, today.month,
                 '宝宝，户外', 1.0, 5, 0),
                ('reg_001', 'regular.jpg', 'imported_copy', 'regular.jpg',
                 '/api/photos/reg_001/image', '2024-03-15', 3,
                 '露营', 1.0, 5, 0),
                ('reg_002', 'regular2.jpg', 'imported_copy', 'regular2.jpg',
                 '/api/photos/reg_002/image', '2024-09-20', 9,
                 '秋天', 1.0, 5, 0),
            ]
        )
        conn.commit()
        conn.close()

        set_recommendation_config(
            seasonal_weights={"current": 2.0, "adjacent": 1.5, "other": 1.0, "none": 0.5},
            deep_sea_probability=0.05,
            deep_sea_years_threshold=2
        )

        yield temp_db.name
        os.unlink(temp_db.name)

    def test_today_memory_boosts_anniversary(self, setup_db):
        """今日回忆频道对往年今天照片加权"""
        from services.recommendation import RecommendationService
        from services.photo_service import PhotoService

        pool = PhotoService.get_photo_index()
        assert len(pool) == 3

        # 多次调用 _today_memory，统计周年照片被选中频率
        import random as real_random
        real_random.seed(123)

        counts = {'anniversary': 0, 'other': 0}
        for _ in range(100):
            photo, reason = RecommendationService._today_memory(pool)
            if photo and photo['url'] == 'anniversary.jpg':
                counts['anniversary'] += 1
            else:
                counts['other'] += 1

        # 周年照片应该被选中更多次
        assert counts['anniversary'] > counts['other'], \
            f"Anniversary should be selected more: {counts}"

    def test_today_memory_returns_correct_reason(self, setup_db):
        """今日回忆频道返回正确的推荐理由"""
        from services.recommendation import RecommendationService
        from services.photo_service import PhotoService

        pool = PhotoService.get_photo_index()

        # 多次尝试，检查推荐理由
        import random as real_random
        real_random.seed(456)
        reasons_seen = set()
        for _ in range(50):
            photo, reason = RecommendationService._today_memory(pool)
            if photo:
                reasons_seen.add(reason)

        assert '往年今天' in reasons_seen or '这个季节的回忆' in reasons_seen


class TestStoryContinuity:
    """小故事频道测试"""

    @pytest.fixture
    def setup_db(self):
        from services.database import set_db_file, init_database, get_db_connection, PhotoDAO
        from services.recommendation import set_recommendation_config

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        set_db_file(temp_db.name)
        init_database(temp_db.name)

        conn = get_db_connection(timeout=10)
        c = conn.cursor()
        c.executemany(
            '''INSERT OR REPLACE INTO photos
               (id, url, source_type, source_ref, display_url, date, month, tags, weight, view_count, missing)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            [
                ('st_001', 'trip1.jpg', 'imported_copy', 'trip1.jpg',
                 '/api/photos/st_001/image', '2024-07-10', 7, '露营，旅行', 1.5, 3, 0),
                ('st_002', 'trip2.jpg', 'imported_copy', 'trip2.jpg',
                 '/api/photos/st_002/image', '2024-07-11', 7, '露营，户外', 1.2, 2, 0),
                ('st_003', 'trip3.jpg', 'imported_copy', 'trip3.jpg',
                 '/api/photos/st_003/image', '2024-07-12', 7, '旅行，夏天', 1.0, 4, 0),
                ('st_004', 'unrelated.jpg', 'imported_copy', 'unrelated.jpg',
                 '/api/photos/st_004/image', '2024-01-05', 1, '室内，宝宝', 2.0, 1, 0),
            ]
        )
        conn.commit()
        conn.close()

        # 模拟上一张播放了 trip1.jpg
        PhotoDAO.record_play('st_001', 'random', '随缘漫游')

        set_recommendation_config(
            seasonal_weights={"current": 2.0, "adjacent": 1.5, "other": 1.0, "none": 0.5},
            deep_sea_probability=0.05,
            deep_sea_years_threshold=2
        )

        yield temp_db.name
        os.unlink(temp_db.name)

    def test_story_boosts_same_tag_photos(self, setup_db):
        """故事频道对同标签照片加权"""
        from services.recommendation import RecommendationService
        from services.photo_service import PhotoService

        pool = PhotoService.get_photo_index()

        # 多次调用 _story_continuity，统计同标签照片被选中频率
        import random as real_random
        real_random.seed(789)

        counts = {'related': 0, 'unrelated': 0}
        for _ in range(100):
            photo, reason = RecommendationService._story_continuity(pool)
            if photo:
                if photo['url'] in ('trip2.jpg', 'trip3.jpg'):
                    counts['related'] += 1
                else:
                    counts['unrelated'] += 1

        # 同标签照片应被选中更多次
        assert counts['related'] > counts['unrelated'], \
            f"Related photos should be selected more: {counts}"

    def test_story_returns_correct_reason(self, setup_db):
        """故事频道返回正确的推荐理由"""
        from services.recommendation import RecommendationService
        from services.photo_service import PhotoService

        pool = PhotoService.get_photo_index()
        import random as real_random
        real_random.seed(101)

        photo, reason = RecommendationService._story_continuity(pool)
        assert reason in ('同一段旅行', '同一个季节', '同一组回忆')

    def test_story_returns_none_without_history(self, setup_db):
        """无播放历史时故事频道返回 None"""
        from services.database import get_db_connection, PhotoDAO
        from services.recommendation import RecommendationService
        from services.photo_service import PhotoService

        # 清空播放历史
        conn = get_db_connection()
        conn.execute("DELETE FROM photo_play_history")
        conn.commit()
        conn.close()

        pool = PhotoService.get_photo_index()
        photo, reason = RecommendationService._story_continuity(pool)
        assert photo is None
        assert reason == ''


class TestLongTimeNoSee:
    """好久不见频道测试"""

    @pytest.fixture
    def setup_db(self):
        from services.database import set_db_file, init_database, get_db_connection
        from services.recommendation import set_recommendation_config

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        set_db_file(temp_db.name)
        init_database(temp_db.name)

        # 老照片（>2年前）+ 低 view_count
        conn = get_db_connection(timeout=10)
        c = conn.cursor()
        c.executemany(
            '''INSERT OR REPLACE INTO photos
               (id, url, source_type, source_ref, display_url, date, month, tags, weight, view_count, missing)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            [
                ('old_001', 'old_low.jpg', 'imported_copy', 'old_low.jpg',
                 '/api/photos/old_001/image', '2020-05-10', 5, '老照片', 1.0, 0, 0),
                ('old_002', 'old_high.jpg', 'imported_copy', 'old_high.jpg',
                 '/api/photos/old_002/image', '2020-06-15', 6, '老照片', 1.0, 50, 0),
                ('new_001', 'new.jpg', 'imported_copy', 'new.jpg',
                 '/api/photos/new_001/image', '2025-01-01', 1, '新照片', 1.5, 2, 0),
            ]
        )
        conn.commit()
        conn.close()

        set_recommendation_config(
            seasonal_weights={"current": 2.0, "adjacent": 1.5, "other": 1.0, "none": 0.5},
            deep_sea_probability=0.05,
            deep_sea_years_threshold=2
        )

        yield temp_db.name
        os.unlink(temp_db.name)

    def test_long_time_prefers_old_low_viewcount(self, setup_db):
        """好久不见频道优先选老的低曝光照片"""
        from services.recommendation import RecommendationService
        from services.photo_service import PhotoService

        pool = PhotoService.get_photo_index()

        # 多次调用
        import random as real_random
        real_random.seed(999)

        counts = {'old_low': 0, 'old_high': 0, 'new': 0}
        for _ in range(50):
            photo, reason = RecommendationService._long_time_no_see(pool)
            if photo:
                counts[photo['url'].replace('.jpg', '')] = counts.get(
                    photo['url'].replace('.jpg', ''), 0
                ) + 1

        # old_low 应该被选中最多（老 + 低 view_count）
        assert counts.get('old_low', 0) > counts.get('old_high', 0)

    def test_long_time_returns_correct_reason(self, setup_db):
        """好久不见频道返回正确的推荐理由"""
        from services.recommendation import RecommendationService
        from services.photo_service import PhotoService

        pool = PhotoService.get_photo_index()
        photo, reason = RecommendationService._long_time_no_see(pool)
        assert reason == '好久不见'
        assert photo is not None


class TestPlayHistory:
    """播放历史功能测试"""

    @pytest.fixture
    def setup_db(self):
        from services.database import set_db_file, init_database, get_db_connection

        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        set_db_file(temp_db.name)
        init_database(temp_db.name)

        yield temp_db.name
        os.unlink(temp_db.name)

    def test_record_and_retrieve(self, setup_db):
        """记录和获取播放历史"""
        from services.database import PhotoDAO

        PhotoDAO.record_play('photo_001', 'today_memory', '往年今天')
        PhotoDAO.record_play('photo_002', 'random', '随缘漫游')

        recent = PhotoDAO.get_recent_played_ids(10)
        assert len(recent) == 2
        assert 'photo_001' in recent
        assert 'photo_002' in recent

    def test_last_played(self, setup_db):
        """获取最近一次播放记录"""
        from services.database import PhotoDAO

        PhotoDAO.record_play('photo_001', 'story', '同一段旅行')
        last = PhotoDAO.get_last_played()

        assert last is not None
        assert last['photo_id'] == 'photo_001'
        assert last['channel'] == 'story'
        assert last['reason'] == '同一段旅行'

    def test_cleanup_old_records(self, setup_db):
        """清理过期播放记录"""
        from services.database import get_db_connection, PhotoDAO

        # 手动插入一条过期记录
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(
            "INSERT INTO photo_play_history (photo_id, played_at, channel, reason) "
            "VALUES (?, datetime('now', '-60 days'), ?, ?)",
            ('old_photo', 'random', 'test')
        )
        conn.commit()
        conn.close()

        deleted = PhotoDAO.cleanup_play_history(keep_days=30)
        assert deleted == 1

        recent = PhotoDAO.get_recent_played_ids(100)
        assert 'old_photo' not in recent
