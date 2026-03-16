"""
Digital Photo Frame - 主应用入口

模块化架构版本 2.0
从单体结构重构为模块化结构，保持向后兼容
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime

from flask import Flask

from config import config
from auth import auth, hash_password
from extensions import init_extensions
from routes import register_blueprints

# 导入服务层用于初始化
from services.database import init_database, set_db_file
from services.metadata import PhotoMetadataService, set_metadata_file
from services.photo_index import PhotoIndexService, set_photo_index
from services.recommendation import set_recommendation_config, set_force_show, get_force_show_state
from services.image import ImageValidator


def setup_logging(app: Flask):
    """配置日志系统"""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    LOG_DIR = os.path.join(BASE_DIR, 'logs')

    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)
        import stat
        if os.name == 'posix':
            try:
                os.chmod(LOG_DIR, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
            except Exception:
                pass

    try:
        handler = RotatingFileHandler(
            os.path.join(LOG_DIR, 'app.log'),
            maxBytes=config.LOG_MAX_SIZE_MB * 1024 * 1024,
            backupCount=config.LOG_BACKUP_COUNT
        )
        handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)
    except Exception as e:
        app.logger.warning(f"Could not initialize file logger: {e}")
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        app.logger.addHandler(stream_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Digital Photo Frame starting up (v2.0 modular)...')


def create_app(config_obj=None):
    """
    应用工厂函数

    Args:
        config_obj: 配置对象（测试环境可传入自定义配置）

    Returns:
        Flask 应用实例
    """
    app = Flask(__name__)

    # --- 基础配置 ---
    app.config['UPLOAD_FOLDER'] = config.UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = config.max_content_length
    app.secret_key = config.SECRET_KEY

    # CSRF Protection Configuration
    app.config['WTF_CSRF_ENABLED'] = True
    app.config['WTF_CSRF_SECRET_KEY'] = config.SECRET_KEY
    app.config['WTF_CSRF_TIME_LIMIT'] = 3600
    app.config['WTF_CSRF_SSL_STRICT'] = not config.DEBUG

    # --- 日志配置 ---
    setup_logging(app)

    # --- 初始化扩展 ---
    init_extensions(app)

    # --- 初始化认证 ---
    auth.init_app(app)
    auth.set_users(config.ADMIN_USERS, hash_passwords=True)

    # --- 确保上传目录存在 ---
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # --- 配置服务层全局变量 ---
    # 数据库
    set_db_file(config.DATABASE_FILE)

    # 元数据
    set_metadata_file(config.METADATA_FILE)

    # 推荐算法配置
    set_recommendation_config(
        seasonal_weights={
            "current": config.SEASONAL_WEIGHT_CURRENT,
            "adjacent": config.SEASONAL_WEIGHT_ADJACENT,
            "other": config.SEASONAL_WEIGHT_OTHER,
            "none": config.SEASONAL_WEIGHT_NONE
        },
        deep_sea_probability=config.DEEP_SEA_PROBABILITY,
        deep_sea_years_threshold=config.DEEP_SEA_YEARS_THRESHOLD
    )

    # --- 注册蓝图 ---
    register_blueprints(app)

    # --- 启动时初始化 ---
    with app.app_context():
        # 初始化数据库
        init_database()

        # 构建照片索引
        PhotoIndexService.build(
            upload_folder=app.config['UPLOAD_FOLDER'],
            tag_weights=config.TAG_WEIGHTS
        )

        app.logger.info(f"Startup complete. Indexed {PhotoIndexService.get_count()} photos.")

    # --- 错误处理器 ---

    @app.errorhandler(404)
    def not_found(error):
        from flask import request, render_template, jsonify
        if request.path.startswith('/api/'):
            return jsonify({'error': '资源不存在', 'path': request.path}), 404
        # 渲染首页模板（不依赖 url_for）
        from config import config
        return render_template('index.html', error='404 - 资源不存在',
                              username='Guest', baby_name=config.BABY_NAME,
                              baby_birthday=config.BABY_BIRTHDAY), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import request, render_template, jsonify
        app.logger.error(f'Internal server error: {error}')
        if request.path.startswith('/api/'):
            return jsonify({'error': '服务器内部错误'}), 500
        # 渲染首页模板
        from config import config
        return render_template('index.html', error='500 - 服务器内部错误',
                              username='Guest', baby_name=config.BABY_NAME,
                              baby_birthday=config.BABY_BIRTHDAY), 500

    @app.errorhandler(Exception)
    def handle_exception(error):
        from flask import request, render_template, jsonify
        app.logger.error(f'Unhandled exception: {error}')
        if request.path.startswith('/api/'):
            return jsonify({'error': str(error)}), 500
        # 渲染首页模板
        from config import config
        return render_template('index.html', error=f'发生错误：{str(error)}',
                              username='Guest', baby_name=config.BABY_NAME,
                              baby_birthday=config.BABY_BIRTHDAY), 500

    return app


# 为向后兼容（尤其是测试）提供的工具函数
def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return ImageValidator.is_allowed(filename)


def validate_image_mime(file_stream):
    """验证图片的 MIME 类型"""
    return ImageValidator.validate_mime(file_stream)


# 创建应用实例
app = create_app()

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    port = int(os.environ.get('PORT', os.environ.get('FLASK_RUN_PORT', '5001')))
    app.logger.info(f"Starting in {'DEBUG' if debug_mode else 'PRODUCTION'} mode on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
