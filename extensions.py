"""
Flask 扩展管理模块
集中管理所有 Flask 扩展实例
"""
from flask import Flask
from flask_wtf.csrf import CSRFProtect

# CSRF Protection 实例
csrf = CSRFProtect()


def init_extensions(app: Flask):
    """
    初始化所有 Flask 扩展

    Args:
        app: Flask 应用实例
    """
    # 初始化 CSRF 保护
    csrf.init_app(app)

    # 其他扩展可以在这里添加
    # 例如： flask-cors, flask-caching, flask-compress 等
