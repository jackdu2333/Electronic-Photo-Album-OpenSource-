"""
留言板路由模块
获取留言、发送留言等 API
"""
import os
import json
import time
import logging
from datetime import datetime
from flask import Blueprint, jsonify, request, session

from auth import EnhancedAuth

logger = logging.getLogger(__name__)

messages_bp = Blueprint('messages', __name__, url_prefix='/api')

# 留言文件路径（从 config 读取）
MESSAGES_FILE = 'messages.json'


def load_messages():
    """加载留言"""
    if not os.path.exists(MESSAGES_FILE):
        return []
    try:
        with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_messages(messages):
    """保存留言"""
    with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
        json.dump(messages, f, ensure_ascii=False, indent=2)


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
    messages = load_messages()
    resp = jsonify(messages[-limit:])
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
        'id': str(int(time.time() * 1000)),
        'content': content,
        'sender': sender,
        'timestamp': datetime.now().strftime('%m-%d %H:%M')
    }

    messages = load_messages()
    messages.append(msg)

    # Keep last 200 Messages to prevent file from growing largely
    if len(messages) > 200:
        messages = messages[-200:]

    save_messages(messages)

    return jsonify(msg)
