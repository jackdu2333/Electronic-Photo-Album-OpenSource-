"""
v3.0 统一照片服务（PhotoService）

替代旧的 PhotoIndexService 作为照片数据的唯一入口。
整合 PhotoSourceRegistry（照片源扫描）+ PhotoDAO（数据库持久化）+
PhotoMetadataService（JSON 元数据兼容），对上层提供统一的照片 CRUD 和图片读取。

设计目标：
- 前端完全不知道照片来自哪里，只消费统一照片对象
- 推荐引擎继续使用 get_photo_index() 获取标准格式
- 旧接口保持兼容，底层切换到新服务
"""
import os
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from config import config
from services.database import PhotoDAO, init_database
from services.metadata import PhotoMetadataService
from services.photo_source import (
    PhotoSourceRegistry,
    PhotoSource,
    DesktopFolderPhotoSource,
    ImportedCopyPhotoSource,
    get_photo_source_registry,
    set_photo_source_registry,
    _generate_photo_id,
)
from services.image import ImageValidator

logger = logging.getLogger(__name__)


def _make_display_url(photo_id: str) -> str:
    """生成统一 display_url"""
    return f"/api/photos/{photo_id}/image"


class PhotoService:
    """
    v3.0 统一照片服务

    职责：
    1. 管理照片源注册和扫描
    2. 照片索引构建（DB + 内存）
    3. 照片 CRUD（标签/日期/便签/移除引用）
    4. 图片文件读取（受控路径，安全校验）
    5. 兼容旧 PhotoIndexService 接口
    """

    # ──────────────────────────────────────────
    #  照片源管理
    # ──────────────────────────────────────────

    @staticmethod
    def init_sources(
        upload_folder: str,
        desktop_folders: Optional[List[str]] = None,
    ) -> PhotoSourceRegistry:
        """
        初始化照片源注册中心。

        Args:
            upload_folder: 旧上传目录（兼容 ImportedCopyPhotoSource）
            desktop_folders: 桌面端本地文件夹列表（可选）

        Returns:
            PhotoSourceRegistry 实例
        """
        registry = PhotoSourceRegistry()

        # 1. 注册旧上传目录（始终注册，兼容存量数据）
        imported = ImportedCopyPhotoSource(upload_folder)
        registry.register(imported, name='imported_copy')

        # 2. 注册桌面本地文件夹（如果有）
        if desktop_folders:
            desktop = DesktopFolderPhotoSource(desktop_folders)
            registry.register(desktop, name='desktop_folder')

        set_photo_source_registry(registry)
        logger.info(
            f"Photo sources initialized: {list(registry.all_sources().keys())}"
        )
        return registry

    @staticmethod
    def add_desktop_folder(folder_path: str) -> bool:
        """动态添加桌面端本地文件夹"""
        registry = get_photo_source_registry()
        desktop = registry.get('desktop_folder')
        if desktop is None:
            desktop = DesktopFolderPhotoSource()
            registry.register(desktop, name='desktop_folder')
        return desktop.add_folder(folder_path)

    @staticmethod
    def remove_desktop_folder(folder_path: str) -> bool:
        """动态移除桌面端本地文件夹"""
        registry = get_photo_source_registry()
        desktop = registry.get('desktop_folder')
        if desktop:
            return desktop.remove_folder(folder_path)
        return False

    @staticmethod
    def get_desktop_folders() -> List[str]:
        """获取桌面端已授权的文件夹列表"""
        registry = get_photo_source_registry()
        desktop = registry.get('desktop_folder')
        if desktop and isinstance(desktop, DesktopFolderPhotoSource):
            return desktop.get_folders()
        return []

    # ──────────────────────────────────────────
    #  扫描与索引构建
    # ──────────────────────────────────────────

    @staticmethod
    def rescan(tag_weights: Optional[Dict[str, float]] = None) -> Dict[str, int]:
        """
        重新扫描所有照片源，构建索引并同步到数据库。

        这是 v3.0 的核心索引构建方法，替代旧的 PhotoIndexService.build()。

        Args:
            tag_weights: 标签权重配置

        Returns:
            统计信息 {'total': N, 'inserted': N, 'missing_marked': N}
        """
        if tag_weights is None:
            tag_weights = config.TAG_WEIGHTS

        registry = get_photo_source_registry()

        # 重新加载 JSON 元数据
        PhotoMetadataService.load()
        metadata = PhotoMetadataService.all()

        # 扫描所有源
        all_items = registry.scan_all()
        logger.info(f"PhotoService.rescan: found {len(all_items)} photos from all sources")

        # 按 source_type 分组，用于后续 missing 标记
        refs_by_type: Dict[str, set] = {}
        photo_records: List[Dict[str, Any]] = []

        for item in all_items:
            photo_id = item['id']
            source_type = item['source_type']
            source_ref = item['source_ref']
            display_url = _make_display_url(photo_id)

            # ImportedCopyPhotoSource 的 source_ref 是相对路径，也是旧的 url
            if source_type == 'imported_copy':
                url = source_ref
                meta = metadata.get(source_ref, {})
            else:
                # 桌面端：用 photo_id 作为 url 字段（唯一标识）
                url = photo_id
                meta = metadata.get(photo_id, {})

            # 提取日期
            date_str = meta.get('date')
            if not date_str:
                abs_path = registry.resolve_file(source_type, source_ref)
                if abs_path:
                    date_str = PhotoMetadataService.extract_date(abs_path)

            month = None
            if date_str:
                try:
                    month = datetime.strptime(date_str, '%Y-%m-%d').month
                except ValueError:
                    pass

            # 计算权重
            tags = meta.get('tags', '')
            weight = PhotoService._calculate_weight(tags, tag_weights)

            # 便签
            note_title = meta.get('note_title', '')
            note_body = meta.get('note_body', '')

            # 构建照片记录
            photo = {
                'id': photo_id,
                'url': url,
                'source_type': source_type,
                'source_ref': source_ref,
                'display_url': display_url,
                'date': date_str,
                'month': month,
                'tags': tags,
                'weight': weight,
                'view_count': 0,
                'note_title': note_title,
                'note_body': note_body,
                'width': item.get('width'),
                'height': item.get('height'),
                'missing': False,
            }

            photo_records.append(photo)

            # 记录有效 source_ref
            if source_type not in refs_by_type:
                refs_by_type[source_type] = set()
            refs_by_type[source_type].add(source_ref)

        # 批量写入数据库（单事务，解决 N+1 性能问题）
        processed = PhotoDAO.bulk_upsert_v3(photo_records)

        # 标记缺失照片
        missing_marked = 0
        for source_type, valid_refs in refs_by_type.items():
            try:
                count = PhotoDAO.mark_missing_by_source(source_type, valid_refs)
                missing_marked += count
            except Exception as e:
                logger.warning(f"Failed to mark missing for {source_type}: {e}")

        # 存量数据迁移（旧记录没有 id 的）
        try:
            PhotoDAO.migrate_v3_records()
        except Exception as e:
            logger.warning(f"v3 migration check failed: {e}")

        logger.info(
            f"PhotoService.rescan complete: processed={processed}, "
            f"missing_marked={missing_marked}"
        )
        return {
            'total': processed,
            'processed': processed,
            'missing_marked': missing_marked,
        }

    # ──────────────────────────────────────────
    #  照片查询（v3.0 新接口）
    # ──────────────────────────────────────────

    @staticmethod
    def list_photos(
        source_type: Optional[str] = None,
        include_missing: bool = False,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        列出照片（v3.0 统一格式）。

        Returns:
            照片列表，每项包含 id, display_url, date, month, tags,
            note_title, note_body, source_type, missing 等字段
        """
        rows = PhotoDAO.get_all_v3(
            source_type=source_type,
            include_missing=include_missing,
            limit=limit,
            offset=offset,
        )
        return [PhotoService._to_api_dict(row) for row in rows]

    @staticmethod
    def get_photo(photo_id: str) -> Optional[Dict[str, Any]]:
        """根据 photo id 获取单张照片信息"""
        row = PhotoDAO.get_by_id(photo_id)
        if not row:
            return None
        return PhotoService._to_api_dict(row)

    @staticmethod
    def get_image_path(photo_id: str) -> Optional[str]:
        """
        根据 photo id 解析出图片文件绝对路径。

        安全：经过 PhotoSource 的路径边界校验。

        Returns:
            文件绝对路径，或 None
        """
        row = PhotoDAO.get_by_id(photo_id)
        if not row:
            return None

        source_type = row.get('source_type', 'imported_copy')
        source_ref = row.get('source_ref', '')

        registry = get_photo_source_registry()
        return registry.resolve_file(source_type, source_ref)

    # ──────────────────────────────────────────
    #  照片修改
    # ──────────────────────────────────────────

    @staticmethod
    def update_metadata(
        photo_id: str,
        date: Optional[str] = None,
        tags: Optional[str] = None,
        note_title: Optional[str] = None,
        note_body: Optional[str] = None,
    ) -> bool:
        """
        更新照片元数据（不修改原图 EXIF）。

        只更新电子相册本地数据库。

        Returns:
            是否更新成功
        """
        row = PhotoDAO.get_by_id(photo_id)
        if not row:
            return False

        # 使用现有值填充未传入的字段
        final_date = date if date is not None else row.get('date')
        final_tags = tags if tags is not None else row.get('tags', '')
        final_note_title = note_title if note_title is not None else row.get('note_title', '')
        final_note_body = note_body if note_body is not None else row.get('note_body', '')

        month = None
        if final_date:
            try:
                month = datetime.strptime(final_date, '%Y-%m-%d').month
            except ValueError:
                pass

        weight = PhotoService._calculate_weight(final_tags, config.TAG_WEIGHTS)

        # 更新 DB（单事务原子操作）
        PhotoDAO.update_metadata_and_note(
            photo_id, row['url'],
            final_date, month, final_tags, weight,
            final_note_title, final_note_body,
        )

        # 同步到 JSON 元数据（兼容旧逻辑，失败只记 warning）
        try:
            PhotoMetadataService.update(
                row['url'], final_date, final_tags,
                note_title=final_note_title,
                note_body=final_note_body,
            )
            PhotoMetadataService.save()
        except Exception as e:
            logger.warning(f"JSON metadata sync failed (non-fatal): {e}")

        return True

    @staticmethod
    def remove_photo(photo_id: str) -> bool:
        """
        从电子相册中移除引用（不删除原文件）。

        Returns:
            是否移除成功
        """
        return PhotoDAO.delete_by_id(photo_id)

    # ──────────────────────────────────────────
    #  旧接口兼容层（供推荐引擎和旧 API 使用）
    # ──────────────────────────────────────────

    @staticmethod
    def get_photo_index() -> List[Dict[str, Any]]:
        """
        兼容旧 get_photo_index() 接口。

        返回推荐引擎需要的标准格式：
        [{url, date, month, tags, weight, view_count}, ...]

        优先从数据库读取，过滤掉 missing 的照片。
        """
        try:
            rows = PhotoDAO.get_all_v3(include_missing=False)
            return [
                {
                    'id': row.get('id', ''),
                    'url': row['url'],
                    'display_url': row.get('display_url', ''),
                    'source_type': row.get('source_type', 'imported_copy'),
                    'date': row.get('date'),
                    'month': row.get('month'),
                    'tags': row.get('tags', ''),
                    'weight': row.get('weight', 1.0),
                    'view_count': row.get('view_count', 0),
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning(f"get_photo_index() DB fallback failed: {e}")
            return []

    @staticmethod
    def get_count() -> int:
        """获取照片总数（不含缺失）"""
        try:
            return PhotoDAO.get_count()
        except Exception:
            return 0

    @staticmethod
    def calculate_weight(tags: str, tag_weights: Optional[Dict[str, float]] = None) -> float:
        """根据标签计算静态权重"""
        return PhotoService._calculate_weight(tags, tag_weights)

    @staticmethod
    def _calculate_weight(tags: str, tag_weights: Optional[Dict[str, float]] = None) -> float:
        """内部权重计算"""
        weights = tag_weights if tag_weights is not None else config.TAG_WEIGHTS
        weight = 1.0
        if tags:
            for tag_key, w_val in weights.items():
                if tag_key in tags and w_val > weight:
                    weight = w_val
        return weight

    @staticmethod
    def _to_api_dict(row: Dict[str, Any]) -> Dict[str, Any]:
        """将 DB 行转换为 v3.0 API 响应字典"""
        return {
            'id': row.get('id', ''),
            'display_url': row.get('display_url', _make_display_url(row.get('id', ''))),
            'date': row.get('date'),
            'month': row.get('month'),
            'tags': row.get('tags', ''),
            'note_title': row.get('note_title', ''),
            'note_body': row.get('note_body', ''),
            'source_type': row.get('source_type', 'imported_copy'),
            'missing': bool(row.get('missing', 0)),
            'weight': row.get('weight', 1.0),
            'view_count': row.get('view_count', 0),
            'width': row.get('width'),
            'height': row.get('height'),
        }
