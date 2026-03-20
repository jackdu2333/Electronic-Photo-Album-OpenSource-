"""
健康检查路由模块
提供 Kubernetes 兼容的健康检查端点
"""
import os
import shutil
import logging
from datetime import datetime
from flask import Blueprint, jsonify, current_app

from services.database import get_db_connection, DB_FILE
from services.photo_index import get_photo_index, PhotoIndexService

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health_check():
    """
    健康检查端点 - 用于监控和负载均衡

    检查项目：
    - 数据库连接（实际执行查询）
    - 存储空间（目录存在 + 磁盘剩余）
    - 照片索引（内存中照片数量）
    """
    health = {
        'status': 'healthy',
        'version': '2.0.0',
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }

    # ── 1. 数据库连接 ──────────────────────────────────────────
    try:
        conn = get_db_connection(timeout=5)
        try:
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM photos')
            count = c.fetchone()[0]
            health['checks']['database'] = f'ok ({count} photos)'
        finally:
            conn.close()
    except Exception as e:
        health['status'] = 'unhealthy'
        health['checks']['database'] = f'error: {str(e)}'
        logger.error(f'Health check DB error: {e}')

    # ── 2. 存储目录 + 磁盘剩余空间 ─────────────────────────────
    try:
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/photos')
        if not os.path.exists(upload_folder):
            health['status'] = 'unhealthy'
            health['checks']['storage'] = f'error: {upload_folder} not found'
        else:
            files = [f for f in os.listdir(upload_folder)
                     if os.path.isfile(os.path.join(upload_folder, f))]
            disk = shutil.disk_usage(upload_folder)
            free_gb = disk.free / (1024 ** 3)
            storage_status = f'ok ({len(files)} files, {free_gb:.1f} GB free)'
            # 磁盘剩余不足 500 MB 时降级为 warning
            if free_gb < 0.5:
                health['status'] = 'degraded'
                storage_status = f'warning: low disk ({free_gb:.2f} GB free)'
            health['checks']['storage'] = storage_status
    except Exception as e:
        health['checks']['storage'] = f'error: {str(e)}'
        logger.error(f'Health check storage error: {e}')

    # ── 3. 内存照片索引 ─────────────────────────────────────────
    try:
        index_count = PhotoIndexService.get_count()
        health['checks']['photo_index'] = f'ok ({index_count} photos in memory)'
    except Exception as e:
        health['checks']['photo_index'] = f'error: {str(e)}'
        logger.error(f'Health check index error: {e}')

    status_code = 503 if health['status'] == 'unhealthy' else 200
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
        try:
            c = conn.cursor()
            c.execute('SELECT 1')
        finally:
            conn.close()
        return jsonify({'status': 'ready'}), 200
    except Exception as e:
        return jsonify({'status': 'not ready', 'error': str(e)}), 503
