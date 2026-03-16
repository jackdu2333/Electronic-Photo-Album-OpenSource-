"""
照片索引服务模块
管理内存中的照片索引，构建和同步照片数据
"""
import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .database import PhotoDAO, init_database
from .metadata import PhotoMetadataService
from .image import ImageValidator

logger = logging.getLogger(__name__)

# 全局照片索引
_photo_index: List[Dict[str, Any]] = []


def set_photo_index(index: List[Dict[str, Any]]):
    """设置照片索引（用于测试）"""
    global _photo_index
    _photo_index = index


def get_photo_index() -> List[Dict[str, Any]]:
    """获取照片索引副本"""
    return _photo_index.copy()


def clear_photo_index():
    """清空照片索引"""
    global _photo_index
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

        # 重新加载 JSON 元数据
        PhotoMetadataService.load()
        metadata = PhotoMetadataService.all()

        _photo_index = []
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
                    _photo_index.append(entry)
                    db_records.append((rel_path, date_str, month, tags, weight))

        # 同步到数据库
        PhotoIndexService._sync_to_database(db_records)

        logger.info(f"Index build complete. Indexed {len(_photo_index)} photos.")
        return len(_photo_index)

    @staticmethod
    def _sync_to_database(records: List[tuple]):
        """
        同步索引到 SQLite 数据库

        策略：
        1. INSERT OR IGNORE 新增照片（保留旧记录的 view_count）
        2. UPDATE 更新现有照片的元数据
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

            # 2. 更新已有照片的元数据
            for record in records:
                url, date, month, tags, weight = record
                PhotoDAO.update_metadata(url, date, month, tags, weight)

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
        _photo_index.append(entry)

        # 同时插入数据库
        PhotoDAO.insert_or_ignore([(url, date, month, tags, weight)])

    @staticmethod
    def remove_photo(url: str):
        """从索引中移除照片"""
        global _photo_index
        _photo_index = [p for p in _photo_index if p['url'] != url]

    @staticmethod
    def update_photo(url: str, date: Optional[str], month: Optional[int],
                     tags: str, weight: float):
        """更新照片元数据"""
        global _photo_index
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
    def get_count() -> int:
        """获取索引中的照片数量"""
        return len(_photo_index)

    @staticmethod
    def get_by_url(url: str) -> Optional[Dict[str, Any]]:
        """根据 URL 获取照片信息"""
        for photo in _photo_index:
            if photo['url'] == url:
                return photo.copy()
        return None

    @staticmethod
    def get_all() -> List[Dict[str, Any]]:
        """获取所有照片索引"""
        return _photo_index.copy()
