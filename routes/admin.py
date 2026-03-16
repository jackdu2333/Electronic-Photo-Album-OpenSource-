"""
管理后台路由模块
相册管理、用户管理等需要认证的路由
"""
import logging
from flask import Blueprint, render_template, jsonify, request

from auth import EnhancedAuth

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/')


# 注意：认证装饰器在注册蓝图时由 app.py 统一添加
# 这样可以避免在每个路由函数上重复添加 @basic_auth.required
