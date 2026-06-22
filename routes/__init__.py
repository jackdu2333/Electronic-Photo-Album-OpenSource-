"""
路由模块注册中心
注册所有蓝图到 Flask 应用
"""
from flask import Flask

from extensions import csrf
from .api import api_bp
from .upload import upload_bp
from .messages import messages_bp
from .main import main_bp
from .health import health_bp
from .recommendation import recommendation_bp
from .photos_v3 import photos_v3_bp

__all__ = [
    'api_bp',
    'upload_bp',
    'messages_bp',
    'main_bp',
    'health_bp',
    'recommendation_bp',
    'photos_v3_bp',
]


def register_blueprints(app: Flask):
    """
    注册所有蓝图到 Flask 应用

    Args:
        app: Flask 应用实例
    """
    # 基础页面
    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp)

    # v3.0 统一照片 API（Basic Auth + JSON，不需要 CSRF）
    csrf.exempt(photos_v3_bp)
    app.register_blueprint(photos_v3_bp)

    # 推荐算法
    app.register_blueprint(recommendation_bp)

    # 旧 API（保留兼容）
    app.register_blueprint(api_bp)
    app.register_blueprint(messages_bp)
    app.register_blueprint(upload_bp)
