"""
文件上传路由模块
处理照片上传，支持批量上传和强制展示模式
"""
import os
import time
import logging
from flask import Blueprint, request, jsonify, current_app

from auth import EnhancedAuth
from services.image import ImageValidator, ImageProcessor
from services.photo_index import PhotoIndexService
from services.recommendation import set_force_show

logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__, url_prefix='/')


@upload_bp.route('/upload', methods=['POST'])
def upload_file():
    """
    文件上传接口

    支持：
    - 批量上传
    - 强制展示模式（force=true）

    Returns:
        JSON: {message: str, files: [str]}
    """
    global FORCE_SHOW_IMG, FORCE_SHOW_EXPIRY

    if 'files' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    files = request.files.getlist('files')

    # Check force flag
    is_force = request.args.get('force') == 'true'

    if is_force and len(files) > 1:
        return jsonify({'error': '仅支持单张照片的立即展示'}), 400

    saved_files = []

    for file in files:
        if file and ImageValidator.is_allowed(file.filename):
            # P0: MIME 类型验证（魔数验证 + Pillow 兜底）
            is_valid, mime_result = ImageValidator.validate_mime(file)
            if not is_valid:
                return jsonify({'error': f'无效的文件格式：{mime_result}'}), 400

            ext = file.filename.rsplit('.', 1)[1].lower()

            # Force HEIC to be saved as JPG
            if ext in ('heic', 'heif'):
                ext = 'jpg'

            timestamp = int(time.time() * 1000)
            filename = f"{timestamp}_{files.index(file)}.{ext}"

            # Smart Compress Logic
            try:
                # Process
                compressed_io = ImageProcessor.smart_compress(file)
                # Save
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/photos')
                with open(os.path.join(upload_folder, filename), 'wb') as f_out:
                    f_out.write(compressed_io.read())
            except Exception as e:
                logger.error(f"Save Error {filename}: {e}")
                # Fallback save
                file.seek(0)
                upload_folder = current_app.config.get('UPLOAD_FOLDER', 'static/photos')
                file.save(os.path.join(upload_folder, filename))

            saved_files.append(filename)

            if is_force:
                # 设置强制展示 10 分钟
                set_force_show(filename, time.time() + 600)
                logger.info(f"[强制展示] 设置：{filename}, 过期时间：{time.time() + 600}")

    # Rebuild index after upload
    PhotoIndexService.build(
        upload_folder=current_app.config.get('UPLOAD_FOLDER', 'static/photos'),
        tag_weights={}  # 从 config 读取
    )

    return jsonify({
        'message': f'Successfully uploaded {len(saved_files)} files',
        'files': saved_files
    })
