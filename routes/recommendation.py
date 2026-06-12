"""
推荐算法路由模块
V3.0 Memory Curator 多频道推荐引擎
"""
import logging
from flask import Blueprint, jsonify

from services.recommendation import RecommendationService

logger = logging.getLogger(__name__)

recommendation_bp = Blueprint('recommendation', __name__, url_prefix='/api')


@recommendation_bp.route('/get_photo')
def get_photo():
    """
    V3.0 Memory Curator 推荐路由

    返回下一张推荐照片，包含：
    - v3 字段：id, display_url, source_type
    - 推荐元数据：recommend_channel, recommend_reason
    - 兼容字段：url, date, month, tags, weight, view_count, is_salvaged

    Returns:
        JSON: 推荐照片或 404
    """
    photo = RecommendationService.get_next_photo()

    if not photo:
        return jsonify({'error': 'No photos available'}), 404

    resp = jsonify(photo)
    resp.headers['Cache-Control'] = 'no-store'
    return resp
