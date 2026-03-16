"""
通用 API 路由模块
照片状态、列表、删除、天气等 API
"""
import os
import ssl
import json
import logging
import urllib.request
from datetime import datetime
from flask import Blueprint, jsonify, request

from auth import EnhancedAuth
from config import config
from services.photo_index import PhotoIndexService, get_photo_index
from services.recommendation import get_force_show_state

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/status')
def get_status():
    """
    获取强制展示状态

    Returns:
        JSON: {force_url: str 或 null}
    """
    force_img, force_expiry = get_force_show_state()

    force_url = None
    if force_img and datetime.now().timestamp() < force_expiry:
        force_url = force_img

    resp = jsonify({'force_url': force_url})
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@api_bp.route('/all_photos')
def get_all_photos():
    """
    获取所有照片列表（带日期排序）

    Returns:
        JSON: [{url, date, month, tags, weight}, ...]
    """
    photo_index = get_photo_index()

    dated = [p for p in photo_index if p.get('date')]
    undated = [p for p in photo_index if not p.get('date')]

    dated.sort(key=lambda x: x['date'], reverse=True)
    undated.sort(key=lambda x: x['url'], reverse=True)

    resp = jsonify(undated + dated)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@api_bp.route('/update_photo', methods=['POST'])
def update_photo():
    """
    更新照片元数据

    Request JSON:
        - filename: 照片文件名
        - date: 拍摄日期
        - tags: 标签

    Returns:
        JSON: {message: str}
    """
    from services.metadata import PhotoMetadataService
    from services.photo_index import PhotoIndexService

    data = request.get_json()
    filename = data.get('filename')
    new_date = data.get('date')
    new_tags = data.get('tags')

    if not filename:
        return jsonify({'error': 'Missing filename'}), 400

    # 更新元数据
    PhotoMetadataService.update(filename, new_date, new_tags)
    PhotoMetadataService.save()

    # 更新索引
    PhotoIndexService.update_photo(filename, new_date, None, new_tags, 1.0)

    return jsonify({'message': 'Updated successfully'})


@api_bp.route('/images')
def get_images():
    """
    获取所有照片列表（用于管理后台）

    Returns:
        JSON: [{url, date, month, tags, weight}, ...]
    """
    photo_index = get_photo_index()
    sorted_index = sorted(
        photo_index,
        key=lambda x: x['date'] or x['url'],
        reverse=True
    )
    resp = jsonify(sorted_index)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@api_bp.route('/images/<path:filename>', methods=['DELETE'])
def delete_image(filename):
    """
    删除照片

    Args:
        filename: 照片文件名（相对路径）

    Returns:
        JSON: {message: str} 或 {error: str}
    """
    from services.photo_index import PhotoIndexService
    from services.image import ImageValidator

    if not ImageValidator.is_allowed(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    file_path = os.path.join(config.UPLOAD_FOLDER, filename)

    # Security check: strict path boundary check
    safe_root = os.path.abspath(config.UPLOAD_FOLDER) + os.sep
    target_path = os.path.abspath(file_path)
    if not target_path.startswith(safe_root):
        return jsonify({'error': 'Invalid path'}), 400

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            PhotoIndexService.remove_photo(filename)
            return jsonify({'message': 'File deleted successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'File not found'}), 404


@api_bp.route('/weather-config')
def weather_config():
    """
    返回天气配置和当前天气数据

    Returns:
        JSON: {enabled: bool, current?: dict, error?: str}
    """
    if not config.WEATHER_ENABLED:
        return jsonify({'enabled': False})

    try:
        # 调用 Open-Meteo API 获取天气 (跳过 SSL 校验以解决本地环境证书缺失问题)
        context = ssl._create_unverified_context()
        url = f'https://api.open-meteo.com/v1/forecast?latitude={config.WEATHER_LAT}&longitude={config.WEATHER_LON}&current=temperature_2m,weather_code&timezone=auto'
        with urllib.request.urlopen(url, timeout=5, context=context) as response:
            data = json.loads(response.read().decode())

        result = {
            'enabled': True,
            'current': data.get('current', {})
        }
        resp = jsonify(result)
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    except Exception as e:
        logger.error(f'Weather API error: {e}')
        return jsonify({'enabled': True, 'error': str(e)})
