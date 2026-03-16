"""
推荐算法路由模块
V2.0 双轨制推荐算法：深海打捞 5% + 常规加权 95%
"""
import logging
from flask import Blueprint, jsonify, make_response

from services.recommendation import RecommendationService
from auth import EnhancedAuth

logger = logging.getLogger(__name__)

recommendation_bp = Blueprint('recommendation', __name__, url_prefix='/api')


@recommendation_bp.route('/get_photo')
def get_photo():
    """
    V2.0 双轨制路由分发器

    返回下一张推荐照片，可能来自：
    1. 强制展示（管理端上传时触发）
    2. 深海打捞（5% 概率，冷数据）
    3. 常规加权（95% 概率，标签×季节权重）

    Returns:
        JSON: {url, date, month, tags, weight, view_count, is_salvaged}
    """
    photo = RecommendationService.get_next_photo()

    if not photo:
        return jsonify({'error': 'No photos available'}), 404

    resp = jsonify(photo)
    resp.headers['Cache-Control'] = 'no-store'
    return resp
