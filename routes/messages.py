"""
留言板路由模块
获取留言、发送留言等 API
"""
import os
import json
import time
import logging
import threading
import uuid
from datetime import datetime
from flask import Blueprint, jsonify, request, session

from auth import EnhancedAuth
from config import config
from services.database import MessageDAO

logger = logging.getLogger(__name__)

messages_bp = Blueprint('messages', __name__, url_prefix='/api')

# 留言文件路径（从 config 读取，支持环境变量覆盖）
MESSAGES_FILE = config.MESSAGES_FILE
_migration_lock = threading.Lock()
_messages_migrated = False


def migrate_legacy_messages_if_needed():
    """把旧 JSON 留言迁移到 SQLite，避免并发写丢消息"""
    global _messages_migrated
    if _messages_migrated:
        return

    with _migration_lock:
        if _messages_migrated:
            return

        if MessageDAO.get_count() == 0 and os.path.exists(MESSAGES_FILE):
            try:
                with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                    legacy_messages = json.load(f)
                if isinstance(legacy_messages, list):
                    inserted = MessageDAO.insert_many(legacy_messages)
                    if inserted:
                        logger.info(f"Migrated {inserted} legacy messages from JSON to SQLite")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Skip legacy message migration: {e}")

        _messages_migrated = True


@messages_bp.route('/messages', methods=['GET'])
def get_messages():
    """
    获取留言列表

    Query Params:
        - limit: 最大返回数量（默认 50）

    Returns:
        JSON: [{id, content, sender, timestamp}, ...]
    """
    limit = request.args.get('limit', default=50, type=int)
    migrate_legacy_messages_if_needed()
    messages = MessageDAO.get_recent(limit=limit)
    resp = jsonify(messages)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@messages_bp.route('/send', methods=['POST'])
def send_message():
    """
    发送留言

    Request JSON:
        - content: 留言内容

    Returns:
        JSON: {id, content, sender, timestamp}
    """
    data = request.get_json()
    content = data.get('content') if data else None

    if not content:
        return jsonify({'error': 'No content'}), 400

    # Identify Sender: prefer session username, fall back to Basic Auth header
    sender = session.get('_username') or \
             (request.authorization.username if request.authorization else 'Guest')

    msg = {
        'id': uuid.uuid4().hex,
        'content': content,
        'sender': sender,
        'timestamp': datetime.now().strftime('%m-%d %H:%M')
    }

    migrate_legacy_messages_if_needed()
    MessageDAO.insert_message(msg, keep_last=200)

    return jsonify(msg)
