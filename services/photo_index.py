"""
照片索引服务模块
管理内存中的照片索引，构建和同步照片数据
"""
import os
import logging
import threading
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

from config import config
from .database import PhotoDAO, init_database
from .metadata import PhotoMetadataService
from .image import ImageValidator

logger = logging.getLogger(__name__)

# 全局照片索引
_photo_index: List[Dict[str, Any]] = []
# RLock 保护 _photo_index 的并发读写（build/add/remove 会整体替换列表，需要互斥）
_index_lock = threading.RLock()
_rebuild_lock = threading.Lock()
_background_rebuilder_started = False


def set_photo_index(index: List[Dict[str, Any]]):
    """设置照片索引（用于测试）"""
    global _photo_index
    with _index_lock:
        _photo_index = index


def get_photo_index() -> List[Dict[str, Any]]:
    """获取照片索引副本，优先以数据库为真实来源，避免多 worker 内存不一致"""
    try:
        db_rows = PhotoDAO.get_all()
        normalized = [
            {
                'url': row['url'],
                'date': row.get('date'),
                'month': row.get('month'),
                'tags': row.get('tags', ''),
                'weight': row.get('weight', 1.0),
                'view_count': row.get('view_count', 0),
            }
            for row in db_rows
        ]
        with _index_lock:
            global _photo_index
            _photo_index = normalized
            return _photo_index.copy()
    except Exception as e:
        logger.warning(f"Falling back to in-memory photo index: {e}")

    with _index_lock:
        return _photo_index.copy()


def clear_photo_index():
    """清空照片索引"""
    global _photo_index
    with _index_lock:
        _photo_index = []


class PhotoIndexService:
    """
    照片索引服务
    负责构建内存索引并同步到数据库
    """

    @staticmethod
    def build(upload_folder: str, tag_weights: Dict[str, float]) -> int:
        """
        重建照片索引并同步到数据库

        元数据优先级：
        1. 手动编辑的 JSON 元数据（最高优先级）
        2. EXIF / 文件名正则提取（兜底）

        Args:
            upload_folder: 照片上传目录
            tag_weights: 标签权重配置

        Returns:
            索引的照片数量
        """
        global _photo_index
        with _rebuild_lock:
            return PhotoIndexService._build_unlocked(upload_folder, tag_weights)

    @staticmethod
    def _build_unlocked(upload_folder: str, tag_weights: Dict[str, float]) -> int:
        global _photo_index

        # 重新加载 JSON 元数据
        PhotoMetadataService.load()
        metadata = PhotoMetadataService.all()

        new_index = []
        db_records = []

        logger.info("Building Photo Index...")

        for root, dirs, files in os.walk(upload_folder):
            for filename in files:
                if ImageValidator.is_allowed(filename):
                    full_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(full_path, upload_folder)
                    rel_path = rel_path.replace('\\', '/')

                    # 优先级 1：手动编辑的 JSON 元数据
                    meta = metadata.get(rel_path, {})
                    date_str = meta.get('date')
                    tags = meta.get('tags', '')

                    # 优先级 2：EXIF / 文件名正则（无手动日期时）
                    if not date_str:
                        date_str = PhotoMetadataService.extract_date(full_path)

                    month = None
                    if date_str:
                        try:
                            dt = datetime.strptime(date_str, '%Y-%m-%d')
                            month = dt.month
                        except ValueError:
                            pass

                    # 计算静态标签权重（取最高命中权重）
                    weight = 1.0
                    if tags:
                        for tag_key, w_val in tag_weights.items():
                            if tag_key in tags and w_val > weight:
                                weight = w_val

                    entry = {
                        'url': rel_path,
                        'date': date_str,
                        'month': month,
                        'tags': tags,
                        'weight': weight
                    }
                    new_index.append(entry)
                    db_records.append((rel_path, date_str, month, tags, weight))

        # 同步到数据库（在锁外执行，避免长时间持锁）
        PhotoIndexService._sync_to_database(db_records)

        # 原子替换内存索引
        with _index_lock:
            _photo_index = new_index

        logger.info(f"Index build complete. Indexed {len(new_index)} photos.")
        return len(new_index)

    @staticmethod
    def start_background_rebuilder(upload_folder: str, tag_weights: Dict[str, float], app_logger=None) -> None:
        """启动后台索引自修复线程，定期将磁盘/元数据/数据库重新对齐"""
        global _background_rebuilder_started
        if _background_rebuilder_started or not config.ENABLE_BACKGROUND_INDEX_REBUILD:
            return

        logger_obj = app_logger or logger
        interval = config.INDEX_REBUILD_INTERVAL_SECONDS

        def _runner():
            logger_obj.info(
                f"Background photo index rebuilder started (interval={interval}s)"
            )
            while True:
                time.sleep(interval)
                try:
                    count = PhotoIndexService.build(upload_folder, tag_weights)
                    logger_obj.info(
                        f"Background photo index rebuild completed ({count} photos)"
                    )
                except Exception as e:
                    logger_obj.error(f"Background photo index rebuild failed: {e}")

        thread = threading.Thread(
            target=_runner,
            name="photo-index-rebuilder",
            daemon=True
        )
        thread.start()
        _background_rebuilder_started = True

    @staticmethod
    def _sync_to_database(records: List[tuple]):
        """
        同步索引到 SQLite 数据库

        策略：
        1. INSERT OR IGNORE 新增照片（保留旧记录的 view_count）
        2. 单一事务批量 UPDATE 更新现有照片的元数据（避免 N 个独立连接）
        3. DELETE 移除文件系统已不存在的照片

        Args:
            records: [(url, date, month, tags, weight), ...]
        """
        try:
            # 防御性调用，确保表与列都存在
            init_database()

            # 1. 插入新照片（已有的跳过，view_count 保持不变）
            inserted = PhotoDAO.insert_or_ignore(records)
            if inserted > 0:
                logger.info(f"Inserted {inserted} new photos to database")

            # 2. 单一事务批量更新元数据（P2 修复：原来每条记录各开一个连接/事务）
            PhotoDAO.bulk_update_metadata(records)

            # 3. 删除文件系统中已不存在的照片记录
            current_urls = tuple(r[0] for r in records)
            deleted = PhotoDAO.delete_missing(current_urls)
            if deleted > 0:
                logger.info(f"Deleted {deleted} photos from database")

            logger.info("Database sync completed")

        except Exception as e:
            logger.error(f"Database sync error: {e}")
            raise

    @staticmethod
    def add_photo(url: str, date: Optional[str], month: Optional[int],
                  tags: str, weight: float):
        """
        添加单张照片到索引

        Args:
            url: 照片相对路径
            date: 拍摄日期
            month: 拍摄月份
            tags: 标签字符串
            weight: 权重
        """
        entry = {
            'url': url,
            'date': date,
            'month': month,
            'tags': tags,
            'weight': weight
        }
        with _index_lock:
            _photo_index.append(entry)

        # 同时插入数据库
        PhotoDAO.insert_or_ignore([(url, date, month, tags, weight)])
        PhotoDAO.update_metadata(url, date, month, tags, weight)

    @staticmethod
    def remove_photo(url: str):
        """从索引中移除照片"""
        global _photo_index
        with _index_lock:
            _photo_index = [p for p in _photo_index if p['url'] != url]
        PhotoDAO.delete_by_url(url)

    @staticmethod
    def update_photo(url: str, date: Optional[str], month: Optional[int],
                     tags: str, weight: float):
        """更新照片元数据"""
        with _index_lock:
            for entry in _photo_index:
                if entry['url'] == url:
                    entry['date'] = date
                    entry['month'] = month
                    entry['tags'] = tags
                    entry['weight'] = weight
                    break

        # 同时更新数据库
        PhotoDAO.update_metadata(url, date, month, tags, weight)

    @staticmethod
    def calculate_weight(tags: str, tag_weights: Optional[Dict[str, float]] = None) -> float:
        """根据标签计算静态权重"""
        weights = tag_weights if tag_weights is not None else config.TAG_WEIGHTS
        weight = 1.0
        if tags:
            for tag_key, w_val in weights.items():
                if tag_key in tags and w_val > weight:
                    weight = w_val
        return weight

    @staticmethod
    def get_count() -> int:
        """获取索引中的照片数量"""
        try:
            return PhotoDAO.get_count()
        except Exception:
            with _index_lock:
                return len(_photo_index)

    @staticmethod
    def get_by_url(url: str) -> Optional[Dict[str, Any]]:
        """根据 URL 获取照片信息"""
        try:
            photo = PhotoDAO.get_by_url(url)
            if photo:
                return {
                    'url': photo['url'],
                    'date': photo.get('date'),
                    'month': photo.get('month'),
                    'tags': photo.get('tags', ''),
                    'weight': photo.get('weight', 1.0),
                    'view_count': photo.get('view_count', 0),
                }
        except Exception:
            pass

        with _index_lock:
            for photo in _photo_index:
                if photo['url'] == url:
                    return photo.copy()
        return None

    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """获取所有照片索引"""
        return get_photo_index()
