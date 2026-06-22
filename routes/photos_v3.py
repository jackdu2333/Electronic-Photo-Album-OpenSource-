"""
v3.0 照片 API 路由

新增统一照片接口，前端只消费 display_url，不关心照片来自哪里。

接口：
- GET  /api/photos                 照片列表
- GET  /api/photos/<id>/image      获取图片文件
- POST /api/photos/<id>/metadata   更新元数据
- DELETE /api/photos/<id>          移除引用（不删原图）
- POST /api/photo-sources/rescan   重新扫描照片源
- GET  /api/photo-sources          获取照片源状态
- POST /api/photo-sources/folders  添加桌面端文件夹
- DELETE /api/photo-sources/folders 移除桌面端文件夹
"""
import os
import logging
from flask import Blueprint, jsonify, request, send_file, abort

from auth import auth
from services.photo_service import PhotoService

logger = logging.getLogger(__name__)

photos_v3_bp = Blueprint('photos_v3', __name__, url_prefix='/api')


@photos_v3_bp.before_request
def require_auth():
    """显式认证检查，确保 v3 API 即使全局认证配置变更也受保护。"""
    if not auth.authenticate():
        return auth.challenge()


# ─────────────────────────────────────────────
#  照片列表与详情
# ─────────────────────────────────────────────

@photos_v3_bp.route('/photos')
def list_photos():
    """
    GET /api/photos

    照片列表（v3.0 统一格式）。

    Query params:
        source_type: 可选，按源类型过滤 (desktop_folder / imported_copy)
        include_missing: 可选，是否包含缺失照片 (0/1)
        limit: 可选，分页大小（整数，默认不限制）
        offset: 可选，分页偏移量（整数，默认 0）

    Returns:
        JSON: [{id, display_url, date, month, tags, note_title, note_body,
                source_type, missing}, ...]
    """
    source_type = request.args.get('source_type')
    include_missing = request.args.get('include_missing', '0') == '1'

    # 分页参数
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', 0, type=int)
    if limit is not None and limit <= 0:
        limit = None
    if offset < 0:
        offset = 0

    photos = PhotoService.list_photos(
        source_type=source_type,
        include_missing=include_missing,
        limit=limit,
        offset=offset,
    )

    resp = jsonify(photos)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@photos_v3_bp.route('/photos/<photo_id>')
def get_photo(photo_id):
    """
    GET /api/photos/<photo_id>

    获取单张照片详情。

    Returns:
        JSON: {id, display_url, date, ...} 或 404
    """
    photo = PhotoService.get_photo(photo_id)
    if not photo:
        return jsonify({'error': '照片不存在'}), 404

    resp = jsonify(photo)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


# ─────────────────────────────────────────────
#  图片文件读取（安全受控）
# ─────────────────────────────────────────────

@photos_v3_bp.route('/photos/<photo_id>/image')
def get_photo_image(photo_id):
    """
    GET /api/photos/<photo_id>/image

    获取图片文件。

    安全机制：
    - photo id 不暴露真实路径
    - 后端根据 id 查询 source_type + source_ref
    - PhotoSource 做路径边界校验
    - 只返回授权目录内的文件
    """
    file_path = PhotoService.get_image_path(photo_id)

    if not file_path:
        logger.warning(f"Image not found or unauthorized: photo_id={photo_id}")
        abort(404)

    if not os.path.isfile(file_path):
        logger.warning(f"Image file missing: {file_path}")
        abort(404)

    # 根据扩展名推断 MIME 类型
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
        '.png': 'image/png', '.gif': 'image/gif',
        '.webp': 'image/webp', '.heic': 'image/heic',
    }
    mimetype = mime_map.get(ext, 'image/jpeg')

    return send_file(
        file_path,
        mimetype=mimetype,
        max_age=3600,  # 浏览器缓存 1 小时
    )


# ─────────────────────────────────────────────
#  元数据更新
# ─────────────────────────────────────────────

@photos_v3_bp.route('/photos/<photo_id>/metadata', methods=['POST'])
def update_photo_metadata(photo_id):
    """
    POST /api/photos/<photo_id>/metadata

    更新照片元数据（不修改原图 EXIF）。

    Request JSON:
        date: 拍摄日期 (YYYY-MM-DD，可选)
        tags: 标签字符串 (可选)
        note_title: 便签标题 (可选)
        note_body: 便签正文 (可选)

    Returns:
        JSON: {message: str} 或 {error: str}
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400

    date = data.get('date')
    tags = data.get('tags')
    note_title = data.get('note_title')
    note_body = data.get('note_body')

    # 输入长度限制
    if tags is not None and len(str(tags)) > 500:
        return jsonify({'error': '标签长度不能超过 500 个字符'}), 400
    if note_title is not None and len(str(note_title)) > 200:
        return jsonify({'error': '便签标题长度不能超过 200 个字符'}), 400
    if note_body is not None and len(str(note_body)) > 2000:
        return jsonify({'error': '便签正文长度不能超过 2000 个字符'}), 400

    # 日期格式校验
    if date:
        from datetime import datetime as dt
        try:
            dt.strptime(date, '%Y-%m-%d')
        except ValueError:
            return jsonify({'error': '日期格式无效，应为 YYYY-MM-DD'}), 400

    success = PhotoService.update_metadata(
        photo_id,
        date=date,
        tags=tags,
        note_title=note_title,
        note_body=note_body,
    )

    if not success:
        return jsonify({'error': '照片不存在'}), 404

    return jsonify({'message': '更新成功'})


# ─────────────────────────────────────────────
#  移除照片引用（不删原图）
# ─────────────────────────────────────────────

@photos_v3_bp.route('/photos/<photo_id>', methods=['DELETE'])
def delete_photo(photo_id):
    """
    DELETE /api/photos/<photo_id>

    从电子相册中移除引用，不删除原文件。

    Returns:
        JSON: {message: str} 或 {error: str}
    """
    success = PhotoService.remove_photo(photo_id)

    if not success:
        return jsonify({'error': '照片不存在'}), 404

    return jsonify({'message': '已从电子相册中移除（原文件未删除）'})


# ─────────────────────────────────────────────
#  照片源管理
# ─────────────────────────────────────────────

@photos_v3_bp.route('/photo-sources/rescan', methods=['POST'])
def rescan_sources():
    """
    POST /api/photo-sources/rescan

    重新扫描所有照片源。

    行为：
    - 扫描授权文件夹
    - 新增照片入库
    - 标记不存在的照片为 missing=true
    - 不主动删除数据库记录

    Returns:
        JSON: {total: N, inserted: N, missing_marked: N}
    """
    from config import config as app_config
    stats = PhotoService.rescan(tag_weights=app_config.TAG_WEIGHTS)
    return jsonify(stats)


@photos_v3_bp.route('/photo-sources')
def get_photo_sources():
    """
    GET /api/photo-sources

    获取当前照片源状态。

    Returns:
        JSON: {sources: [{name, type, authorized, folders?}], photo_count: N}
    """
    from services.photo_source import get_photo_source_registry

    registry = get_photo_source_registry()
    sources_info = []

    for name, source in registry.all_sources().items():
        info = {
            'name': name,
            'type': source.source_type,
            'authorized': source.is_authorized(),
        }

        # 桌面端额外返回文件夹列表
        from services.photo_source import DesktopFolderPhotoSource
        if isinstance(source, DesktopFolderPhotoSource):
            info['folders'] = source.get_folders()

        sources_info.append(info)

    return jsonify({
        'sources': sources_info,
        'photo_count': PhotoService.get_count(),
    })


@photos_v3_bp.route('/photo-sources/folders', methods=['POST'])
def add_folder():
    """
    POST /api/photo-sources/folders

    添加桌面端本地文件夹。

    Request JSON:
        folder: 文件夹绝对路径

    Returns:
        JSON: {message: str} 或 {error: str}
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400
    folder = data.get('folder', '').strip()

    if not folder:
        return jsonify({'error': '文件夹路径不能为空'}), 400

    # 路径安全：仅允许用户主目录及常见媒体目录下的文件夹
    resolved = os.path.realpath(folder)
    allowed_prefixes = [
        os.path.realpath(os.path.expanduser('~')),
        '/media', '/mnt', '/Volumes',
    ]
    if not any(resolved.startswith(p) for p in allowed_prefixes):
        return jsonify({'error': f'不允许添加该路径，仅允许用户目录及外部存储目录'}), 403

    if not os.path.isdir(folder):
        return jsonify({'error': f'文件夹不存在: {folder}'}), 400

    success = PhotoService.add_desktop_folder(folder)
    if not success:
        return jsonify({'error': '添加文件夹失败'}), 500

    return jsonify({'message': f'已添加文件夹: {folder}'})


@photos_v3_bp.route('/photo-sources/folders', methods=['DELETE'])
def remove_folder():
    """
    DELETE /api/photo-sources/folders

    移除桌面端本地文件夹。

    Request JSON:
        folder: 文件夹绝对路径
    """
    data = request.get_json()
    folder = data.get('folder', '').strip()

    if not folder:
        return jsonify({'error': '文件夹路径不能为空'}), 400

    success = PhotoService.remove_desktop_folder(folder)
    if not success:
        return jsonify({'error': '文件夹未在授权列表中'}), 404

    return jsonify({'message': f'已移除文件夹: {folder}'})
