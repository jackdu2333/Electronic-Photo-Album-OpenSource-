"""
健康检查路由模块
提供 Kubernetes 兼容的健康检查端点
"""
import sqlite3
import os
import logging
from datetime import datetime
from flask import Blueprint, jsonify

from services.database import get_db_connection, DB_FILE
from services.photo_index import get_photo_index

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health_check():
    """
    健康检查端点 - 用于监控和负载均衡

    检查项目：
    - 数据库连接
    - 存储空间
    """
    health = {
        'status': 'healthy',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat(),
        'checks': {
            'database': 'ok',
            'storage': 'ok'
        }
    }

    # 检查数据库连接
    try:
        conn = get_db_connection(timeout=5)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM photos')
        count = c.fetchone()[0]
        conn.close()
        health['checks']['database'] = f'ok ({count} photos)'
    except Exception as e:
        health['status'] = 'unhealthy'
        health['checks']['database'] = f'error: {str(e)}'

    # 检查存储
    try:
        from flask import current_app
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/photos')
        if not os.path.exists(upload_folder):
            health['checks']['storage'] = f'warning: {upload_folder} not found'
        else:
            files = os.listdir(upload_folder)
            health['checks']['storage'] = f'ok ({len(files)} files)'
    except Exception as e:
        health['checks']['storage'] = f'error: {str(e)}'

    status_code = 200 if health['status'] == 'healthy' else 503
    return jsonify(health), status_code


@health_bp.route('/health/live')
def liveness_check():
    """
    存活检查 - Kubernetes 用

    只要应用进程活着就返回 200
    """
    return jsonify({'status': 'alive'}), 200


@health_bp.route('/health/ready')
def readiness_check():
    """
    就绪检查 - Kubernetes 用

    检查数据库是否可用
    """
    try:
        conn = get_db_connection(timeout=5)
        c = conn.cursor()
        c.execute('SELECT 1')
        conn.close()
        return jsonify({'status': 'ready'}), 200
    except Exception as e:
        return jsonify({'status': 'not ready', 'error': str(e)}), 503
