"""
服务层模块
封装业务逻辑，供路由层调用
"""
from .database import PhotoDAO, get_db_connection, init_database
from .image import ImageProcessor, ImageValidator
from .metadata import PhotoMetadataService
from .photo_index import PhotoIndexService, get_photo_index
from .photo_service import PhotoService
from .photo_source import (
    DesktopFolderPhotoSource,
    ImportedCopyPhotoSource,
    PhotoSource,
    PhotoSourceRegistry,
    get_photo_source_registry,
)

__all__ = [
    'init_database',
    'get_db_connection',
    'PhotoDAO',
    'PhotoMetadataService',
    'PhotoIndexService',
    'get_photo_index',
    'ImageValidator',
    'ImageProcessor',
    # v3.0
    'PhotoSource',
    'DesktopFolderPhotoSource',
    'ImportedCopyPhotoSource',
    'PhotoSourceRegistry',
    'get_photo_source_registry',
    'PhotoService',
]
