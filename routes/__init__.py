"""
路由模块注册中心
注册所有蓝图到 Flask 应用
"""
from flask import Flask

from .api import api_bp
from .admin import admin_bp
from .upload import upload_bp
from .messages import messages_bp
from .main import main_bp
from .health import health_bp
from .recommendation import recommendation_bp

__all__ = [
    'api_bp',
    'admin_bp',
    'upload_bp',
    'messages_bp',
    'main_bp',
    'health_bp',
    'recommendation_bp',
]


def register_blueprints(app: Flask):
    """
    注册所有蓝图到 Flask 应用

    Args:
        app: Flask 应用实例
    """
    # 注册主页面路由
    app.register_blueprint(main_bp)

    # 注册健康检查路由（无需认证）
    app.register_blueprint(health_bp)

    # 注册推荐算法路由（需要认证）
    app.register_blueprint(recommendation_bp)

    # 注册通用 API 路由（需要认证）
    app.register_blueprint(api_bp)

    # 注册留言路由（需要认证）
    app.register_blueprint(messages_bp)

    # 注册上传路由（需要认证）
    app.register_blueprint(upload_bp)

    # 注册管理后台路由（需要认证）
    app.register_blueprint(admin_bp)
