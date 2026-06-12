"""
元数据服务模块
管理照片元数据（JSON 文件存储）
"""
import os
import json
import logging
import tempfile
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS
import re

logger = logging.getLogger(__name__)

# 全局元数据文件路径
METADATA_FILE: str = "metadata.json"


def set_metadata_file(filepath: str):
    """设置元数据文件路径"""
    global METADATA_FILE
    METADATA_FILE = filepath


class PhotoMetadataService:
    """
    照片元数据服务
    负责加载、保存、提取照片元数据
    """

    _metadata: Dict[str, Any] = {}
    _lock = threading.RLock()  # 保护 _metadata 的并发读写

    @classmethod
    def load(cls, filepath: Optional[str] = None) -> Dict[str, Any]:
        """
        从 JSON 文件加载元数据

        Args:
            filepath: 元数据文件路径，如不传则使用全局 METADATA_FILE

        Returns:
            元数据字典
        """
        file_path = filepath or METADATA_FILE

        if not os.path.exists(file_path):
            with cls._lock:
                cls._metadata = {}
            logger.info("Metadata file not found, starting with empty metadata")
            return cls._metadata

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            with cls._lock:
                cls._metadata = data
            logger.info(f"Metadata loaded from {file_path}")
            return cls._metadata
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")
            with cls._lock:
                cls._metadata = {}
            return cls._metadata

    @classmethod
    def save(cls, filepath: Optional[str] = None) -> bool:
        """
        保存元数据到 JSON 文件

        Args:
            filepath: 元数据文件路径

        Returns:
            是否保存成功
        """
        file_path = filepath or METADATA_FILE

        try:
            with cls._lock:
                data_copy = cls._metadata.copy()
            # 原子写入：先写临时文件，再 os.replace() 原子替换，防止写入中断导致文件损坏
            dir_name = os.path.dirname(os.path.abspath(file_path))
            with tempfile.NamedTemporaryFile(
                mode='w', encoding='utf-8', dir=dir_name,
                delete=False, suffix='.tmp'
            ) as tmp_f:
                tmp_path = tmp_f.name
                json.dump(data_copy, tmp_f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, file_path)
            logger.info(f"Metadata saved to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
            return False

    @classmethod
    def get(cls, url: str) -> Optional[Dict[str, Any]]:
        """获取指定照片的元数据"""
        with cls._lock:
            return cls._metadata.get(url)

    @classmethod
    def set(cls, url: str, metadata: Dict[str, Any]):
        """设置指定照片的元数据"""
        with cls._lock:
            cls._metadata[url] = metadata

    @classmethod
    def update(
        cls,
        url: str,
        date: Optional[str],
        tags: str,
        note_title: Optional[str] = None,
        note_body: Optional[str] = None
    ):
        """
        更新照片元数据

        Args:
            url: 照片相对路径
            date: 拍摄日期
            tags: 标签字符串
            note_title: 便签标题（None 表示不更新）
            note_body: 便签正文（None 表示不更新）
        """
        with cls._lock:
            if url not in cls._metadata:
                cls._metadata[url] = {}

            cls._metadata[url]['date'] = date
            cls._metadata[url]['tags'] = tags
            if note_title is not None:
                cls._metadata[url]['note_title'] = str(note_title).strip()
            if note_body is not None:
                cls._metadata[url]['note_body'] = str(note_body).strip()

    @classmethod
    def extract_date(cls, file_path: str) -> Optional[str]:
        """
        从图片文件中提取拍摄日期

        优先级：
        1. EXIF DateTimeOriginal
        2. 文件名中的日期模式（如 2024-01-15_photo.jpg）

        Args:
            file_path: 图片文件路径

        Returns:
            日期字符串 YYYY-MM-DD，如无法提取则返回 None
        """
        # 1. Try EXIF Logic
        try:
            # 使用上下文管理器确保文件句柄及时释放，防止长时间运行时 fd 耗尽
            with Image.open(file_path) as image:
                exif_data = image.getexif()  # 使用公开 API，而非 _getexif()
                if exif_data:
                    for tag_id, value in exif_data.items():
                        tag_name = TAGS.get(tag_id, tag_id)
                        if tag_name == 'DateTimeOriginal':
                            # Value format: YYYY:MM:DD HH:MM:SS
                            return value.replace(':', '-', 2)[:10]
        except Exception as e:
            logger.debug(f"EXIF extraction failed: {e}")

        # 2. Try Filename Regex Fallback
        try:
            filename = os.path.basename(file_path)
            match = re.search(r'(20\d{2}|19\d{2})[-_]?(\d{2})[-_]?(\d{2})', filename)
            if match:
                year, month, day = match.groups()
                if 1 <= int(month) <= 12 and 1 <= int(day) <= 31:
                    return f"{year}-{month}-{day}"
        except Exception as e:
            logger.debug(f"Filename regex extraction failed: {e}")

        return None

    @classmethod
    def clear(cls):
        """清空元数据"""
        with cls._lock:
            cls._metadata = {}

    @classmethod
    def all(cls) -> Dict[str, Any]:
        """获取所有元数据"""
        with cls._lock:
            return cls._metadata.copy()
