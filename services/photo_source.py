"""
v3.0 照片源适配层（Photo Source Adapter）

抽象不同平台（桌面本地文件夹 / 旧上传目录 / 未来 iOS PhotoKit）的照片来源，
提供统一的扫描、读取、校验能力。

设计原则：
- 原图只读引用，不复制
- photo id 不暴露真实路径
- 删除操作默认只删索引，不删原图
"""
import os
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple

from services.image import ImageValidator

logger = logging.getLogger(__name__)


def _generate_photo_id(source_type: str, source_ref: str) -> str:
    """
    生成稳定的 photo id。

    基于 source_type + source_ref 的 SHA-256 前 16 位，
    加上 source_type 前缀便于调试。

    例: desktop_a3f1b2c4d5e6f7a8
    """
    raw = f"{source_type}::{source_ref}"
    digest = hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]
    return f"{source_type}_{digest}"


class PhotoSource(ABC):
    """
    照片源抽象基类

    每个平台实现自己的 PhotoSource：
    - DesktopFolderPhotoSource: 桌面本地文件夹
    - ImportedCopyPhotoSource: 旧上传目录（向后兼容）
    - (未来) IOSPhotoKitSource: iOS PhotoKit
    """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """源类型标识: desktop_folder / imported_copy / ios_photokit"""
        ...

    @abstractmethod
    def scan(self) -> List[Dict[str, Any]]:
        """
        扫描照片源，返回原始照片信息列表。

        每个元素包含：
        - source_ref: 原始引用（路径/identifier）
        - filename: 文件名
        - width: 图片宽度（可选）
        - height: 图片高度（可选）
        """
        ...

    @abstractmethod
    def resolve_file_path(self, source_ref: str) -> Optional[str]:
        """
        根据 source_ref 解析出实际文件绝对路径。

        安全要求：
        - 必须在授权目录范围内
        - 返回 None 表示文件不存在或越权
        """
        ...

    @abstractmethod
    def is_authorized(self) -> bool:
        """检查照片源是否已授权/可用"""
        ...


class DesktopFolderPhotoSource(PhotoSource):
    """
    桌面本地文件夹照片源

    用户选择一个或多个本地文件夹，App 扫描其中的图片。
    原图只读引用，不复制。
    """

    def __init__(self, folders: Optional[List[str]] = None):
        self._folders: List[str] = []
        if folders:
            for f in folders:
                self.add_folder(f)

    @property
    def source_type(self) -> str:
        return "desktop_folder"

    def add_folder(self, folder_path: str) -> bool:
        """
        添加一个授权文件夹。

        Args:
            folder_path: 文件夹绝对路径

        Returns:
            是否添加成功
        """
        abs_path = os.path.abspath(folder_path)
        if not os.path.isdir(abs_path):
            logger.warning(f"Folder not found: {abs_path}")
            return False
        if abs_path not in self._folders:
            self._folders.append(abs_path)
            logger.info(f"Added desktop folder: {abs_path}")
        return True

    def remove_folder(self, folder_path: str) -> bool:
        """移除一个授权文件夹"""
        abs_path = os.path.abspath(folder_path)
        if abs_path in self._folders:
            self._folders.remove(abs_path)
            logger.info(f"Removed desktop folder: {abs_path}")
            return True
        return False

    def get_folders(self) -> List[str]:
        """获取所有授权文件夹"""
        return list(self._folders)

    def is_authorized(self) -> bool:
        """至少有一个有效文件夹即视为已授权"""
        return any(os.path.isdir(f) for f in self._folders)

    def scan(self) -> List[Dict[str, Any]]:
        """
        扫描所有授权文件夹中的图片文件。

        Returns:
            照片信息列表
        """
        results = []
        for folder in self._folders:
            if not os.path.isdir(folder):
                logger.warning(f"Folder no longer exists: {folder}")
                continue

            for root, dirs, files in os.walk(folder):
                for filename in files:
                    if not ImageValidator.is_allowed(filename):
                        continue

                    full_path = os.path.join(root, filename)
                    # source_ref = 绝对路径（不暴露给前端）
                    results.append({
                        'source_ref': full_path,
                        'filename': filename,
                        'width': None,  # 延迟获取，避免扫描时大量 IO
                        'height': None,
                    })

        logger.info(f"Desktop scan found {len(results)} images in {len(self._folders)} folders")
        return results

    def resolve_file_path(self, source_ref: str) -> Optional[str]:
        """
        解析并校验文件路径。

        安全检查：文件必须在某个授权文件夹内。
        """
        abs_path = os.path.abspath(source_ref)

        # 路径边界校验：必须在某个授权目录内
        authorized = False
        for folder in self._folders:
            safe_root = os.path.abspath(folder) + os.sep
            if abs_path.startswith(safe_root) or abs_path == os.path.abspath(folder):
                authorized = True
                break

        if not authorized:
            logger.warning(f"Unauthorized path access attempt: {abs_path}")
            return None

        if not os.path.isfile(abs_path):
            return None

        return abs_path


class ImportedCopyPhotoSource(PhotoSource):
    """
    旧上传目录照片源（向后兼容）

    兼容 v2.x 时代的 static/photos/ 上传目录。
    功能等同于旧逻辑，但纳入统一照片源框架。
    """

    def __init__(self, upload_folder: str):
        self._upload_folder = os.path.abspath(upload_folder)

    @property
    def source_type(self) -> str:
        return "imported_copy"

    @property
    def upload_folder(self) -> str:
        return self._upload_folder

    def is_authorized(self) -> bool:
        return os.path.isdir(self._upload_folder)

    def scan(self) -> List[Dict[str, Any]]:
        """扫描上传目录"""
        results = []
        if not os.path.isdir(self._upload_folder):
            return results

        for root, dirs, files in os.walk(self._upload_folder):
            for filename in files:
                if not ImageValidator.is_allowed(filename):
                    continue

                full_path = os.path.join(root, filename)
                # source_ref = 相对路径（与旧逻辑一致）
                rel_path = os.path.relpath(full_path, self._upload_folder)
                rel_path = rel_path.replace('\\', '/')
                results.append({
                    'source_ref': rel_path,
                    'filename': filename,
                    'width': None,
                    'height': None,
                })

        logger.info(f"ImportedCopy scan found {len(results)} images in {self._upload_folder}")
        return results

    def resolve_file_path(self, source_ref: str) -> Optional[str]:
        """解析上传目录中的文件路径，带边界校验"""
        file_path = os.path.join(self._upload_folder, source_ref)
        abs_path = os.path.abspath(file_path)

        safe_root = self._upload_folder + os.sep
        if not abs_path.startswith(safe_root):
            logger.warning(f"Path traversal attempt: {source_ref}")
            return None

        if not os.path.isfile(abs_path):
            return None

        return abs_path


class PhotoSourceRegistry:
    """
    照片源注册中心

    管理多个 PhotoSource 实例，提供统一的扫描和查询入口。
    """

    def __init__(self):
        self._sources: Dict[str, PhotoSource] = {}

    def register(self, source: PhotoSource, name: Optional[str] = None) -> str:
        """
        注册一个照片源。

        Args:
            source: PhotoSource 实例
            name: 可选名称，默认用 source_type

        Returns:
            注册名称
        """
        key = name or source.source_type
        self._sources[key] = source
        logger.info(f"Registered photo source: {key} ({source.source_type})")
        return key

    def unregister(self, name: str) -> bool:
        """注销一个照片源"""
        if name in self._sources:
            del self._sources[name]
            return True
        return False

    def get(self, name: str) -> Optional[PhotoSource]:
        """获取指定照片源"""
        return self._sources.get(name)

    def get_by_type(self, source_type: str) -> Optional[PhotoSource]:
        """根据 source_type 获取第一个匹配的照片源"""
        for src in self._sources.values():
            if src.source_type == source_type:
                return src
        return None

    def all_sources(self) -> Dict[str, PhotoSource]:
        """获取所有已注册的照片源"""
        return dict(self._sources)

    def scan_all(self) -> List[Dict[str, Any]]:
        """
        扫描所有照片源，返回统一格式的照片列表。

        每个元素包含：
        - id: 稳定 photo id
        - source_type: 源类型
        - source_ref: 原始引用
        - filename: 文件名
        """
        all_photos = []
        for name, source in self._sources.items():
            if not source.is_authorized():
                logger.warning(f"Photo source '{name}' is not authorized, skipping")
                continue

            try:
                items = source.scan()
                for item in items:
                    item['id'] = _generate_photo_id(source.source_type, item['source_ref'])
                    item['source_type'] = source.source_type
                all_photos.extend(items)
            except Exception as e:
                logger.error(f"Error scanning source '{name}': {e}")

        logger.info(f"Total photos from all sources: {len(all_photos)}")
        return all_photos

    def resolve_file(self, source_type: str, source_ref: str) -> Optional[str]:
        """
        根据 source_type + source_ref 解析文件绝对路径。

        Returns:
            文件绝对路径，或 None（不存在/越权）
        """
        source = self.get_by_type(source_type)
        if not source:
            logger.warning(f"Unknown source type: {source_type}")
            return None
        return source.resolve_file_path(source_ref)


# 全局注册中心实例（由 app.py 初始化）
_registry: Optional[PhotoSourceRegistry] = None


def get_photo_source_registry() -> PhotoSourceRegistry:
    """获取全局照片源注册中心"""
    global _registry
    if _registry is None:
        _registry = PhotoSourceRegistry()
    return _registry


def set_photo_source_registry(registry: PhotoSourceRegistry):
    """设置全局照片源注册中心"""
    global _registry
    _registry = registry
