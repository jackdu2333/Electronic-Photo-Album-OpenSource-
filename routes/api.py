"""
通用 API 路由模块
照片状态、列表、删除、天气等 API
"""
import os
import json
import logging
import ssl
import urllib.request
from datetime import datetime
from flask import Blueprint, jsonify, request

from auth import EnhancedAuth
from config import config
from services.photo_index import PhotoIndexService, get_photo_index
from services.recommendation import get_force_show_state
from flask import session

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__, url_prefix='/api')

DAILY_QUOTE_CACHE = {
    'date': None,
    'payload': None
}

LOCAL_DAILY_QUOTES = [
    ('风来听风，雨来听雨。', '禅语'),
    ('慢一点，万物自有节律。', '禅语'),
    ('行到水穷处，坐看云起时。', '王维'),
    ('山高月小，水落石出。', '苏轼'),
    ('花开有时，心安即归。', '题签'),
    ('一念放下，万般自在。', '禅语'),
]


def _fetch_json(url, timeout=4, headers=None):
    """通用 JSON 拉取（服务端，避免前端跨域问题）"""
    req = urllib.request.Request(url, headers=headers or {})
    # 使用系统默认证书链，生产环境不禁用 SSL 验证
    ssl_context = ssl.create_default_context() if not os.environ.get('FLASK_DEBUG', '').lower() == 'true' else ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as response:
        return json.loads(response.read().decode('utf-8'))


def _build_quote_payload(text, source, provider, lang='zh'):
    clean_text = str(text or '').strip()
    if not clean_text:
        return None
    return {
        'text': clean_text,
        'source': str(source or '').strip() or '佚名',
        'provider': provider,
        'lang': lang,
        'date': datetime.now().strftime('%Y-%m-%d')
    }


def _quote_from_hitokoto():
    """主源：Hitokoto（一言）"""
    data = _fetch_json('https://v1.hitokoto.cn/?c=i&c=d&c=k&encode=json')
    text = data.get('hitokoto')
    from_who = data.get('from_who')
    from_name = data.get('from')
    if from_who and from_name:
        source = f'{from_who}《{from_name}》'
    elif from_name:
        source = from_name
    else:
        source = '一言'
    return _build_quote_payload(text, source, 'hitokoto', 'zh')


def _quote_from_jinrishici():
    """备用源：古诗词（gushi.ci）"""
    data = _fetch_json('https://v1.jinrishici.com/all.json')
    text = data.get('content')
    author = data.get('author')
    origin = data.get('origin')
    if author and origin:
        source = f'{author}《{origin}》'
    elif origin:
        source = origin
    elif author:
        source = author
    else:
        source = '古诗词'
    return _build_quote_payload(text, source, 'jinrishici', 'zh')


def _quote_from_zenquotes():
    """英文备用源：ZenQuotes"""
    data = _fetch_json('https://zenquotes.io/api/today')
    if isinstance(data, list) and data:
        item = data[0]
        return _build_quote_payload(item.get('q'), item.get('a'), 'zenquotes', 'en')
    return None


def _quote_from_favqs():
    """英文备用源：FavQs QOTD"""
    data = _fetch_json('https://favqs.com/api/qotd')
    quote = data.get('quote', {}) if isinstance(data, dict) else {}
    return _build_quote_payload(quote.get('body'), quote.get('author'), 'favqs', 'en')


def _quote_from_local_fallback():
    """最终兜底：本地静态句库（按日期轮换）"""
    day_of_year = datetime.now().timetuple().tm_yday
    text, source = LOCAL_DAILY_QUOTES[day_of_year % len(LOCAL_DAILY_QUOTES)]
    return _build_quote_payload(text, source, 'local', 'zh')


def _resolve_daily_quote(force_refresh=False):
    """获取每日一言（当天缓存 + 多源回退）"""
    today = datetime.now().strftime('%Y-%m-%d')
    cached = DAILY_QUOTE_CACHE.get('payload')
    if not force_refresh and DAILY_QUOTE_CACHE.get('date') == today and cached:
        return cached, True

    providers = (
        _quote_from_hitokoto,
        _quote_from_jinrishici,
        _quote_from_zenquotes,
        _quote_from_favqs,
    )

    payload = None
    for provider in providers:
        try:
            payload = provider()
            if payload:
                break
        except Exception as exc:
            logger.warning('Daily quote provider failed: %s (%s)', provider.__name__, exc)

    if not payload:
        payload = _quote_from_local_fallback()

    DAILY_QUOTE_CACHE['date'] = today
    DAILY_QUOTE_CACHE['payload'] = payload
    return payload, False


# 元数据 mtime 缓存，避免每次请求都重新加载 JSON 文件
_metadata_mtime = None

def _merge_note_fields(photos):
    """
    将 JSON 元数据里的便签字段合并到照片列表响应中
    使用 mtime 缓存，仅在文件变化时重新加载
    """
    global _metadata_mtime
    from services.metadata import PhotoMetadataService, METADATA_FILE

    current_mtime = None
    if os.path.exists(METADATA_FILE):
        current_mtime = os.path.getmtime(METADATA_FILE)

    if current_mtime != _metadata_mtime:
        PhotoMetadataService.load()
        _metadata_mtime = current_mtime

    metadata = PhotoMetadataService.all()
    merged = []
    for photo in photos:
        item = dict(photo)
        meta = metadata.get(item.get('url', ''), {})
        item['note_title'] = meta.get('note_title', '')
        item['note_body'] = meta.get('note_body', '')
        merged.append(item)
    return merged


@api_bp.route('/status')
def get_status():
    """
    获取强制展示状态

    Returns:
        JSON: {force_url: str 或 null}
    """
    force_img, force_expiry = get_force_show_state()

    force_url = None
    if force_img and datetime.now().timestamp() < force_expiry:
        force_url = force_img

    resp = jsonify({'force_url': force_url})
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@api_bp.route('/all_photos')
def get_all_photos():
    """
    获取所有照片列表（带日期排序）

    Returns:
        JSON: [{url, date, month, tags, weight}, ...]
    """
    photo_index = get_photo_index()

    dated = [p for p in photo_index if p.get('date')]
    undated = [p for p in photo_index if not p.get('date')]

    dated.sort(key=lambda x: x['date'], reverse=True)
    undated.sort(key=lambda x: x['url'], reverse=True)

    resp = jsonify(_merge_note_fields(undated + dated))
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@api_bp.route('/update_photo', methods=['POST'])
def update_photo():
    """
    更新照片元数据

    Request JSON:
        - filename: 照片文件名
        - date: 拍摄日期
        - tags: 标签

    Returns:
        JSON: {message: str}
    """
    from services.metadata import PhotoMetadataService
    from services.photo_index import PhotoIndexService

    data = request.get_json()
    filename = data.get('filename')
    new_date = data.get('date')
    new_tags = data.get('tags', '')
    note_title = data.get('note_title')
    note_body = data.get('note_body')

    if not filename:
        return jsonify({'error': 'Missing filename'}), 400

    # 更新元数据
    PhotoMetadataService.update(
        filename,
        new_date,
        new_tags,
        note_title=note_title,
        note_body=note_body
    )
    PhotoMetadataService.save()

    # 重新计算 month 和 weight，避免人工编辑后推荐数据被写坏
    new_month = None
    if new_date:
        try:
            new_month = datetime.strptime(new_date, '%Y-%m-%d').month
        except ValueError:
            return jsonify({'error': 'Invalid date format, expected YYYY-MM-DD'}), 400

    new_weight = PhotoIndexService.calculate_weight(new_tags, config.TAG_WEIGHTS)

    # 更新索引
    PhotoIndexService.update_photo(filename, new_date, new_month, new_tags, new_weight)

    return jsonify({'message': 'Updated successfully'})


@api_bp.route('/images')
def get_images():
    """
    获取所有照片列表（用于管理后台）

    Returns:
        JSON: [{url, date, month, tags, weight}, ...]
    """
    photo_index = get_photo_index()
    sorted_index = sorted(
        photo_index,
        key=lambda x: (x['date'] or '0000-00-00', x['url']),
        reverse=True
    )
    resp = jsonify(_merge_note_fields(sorted_index))
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@api_bp.route('/images/<path:filename>', methods=['DELETE'])
def delete_image(filename):
    """
    删除照片

    Args:
        filename: 照片文件名（相对路径）

    Returns:
        JSON: {message: str} 或 {error: str}
    """
    from services.photo_index import PhotoIndexService
    from services.image import ImageValidator

    if not ImageValidator.is_allowed(filename):
        return jsonify({'error': 'Invalid filename'}), 400

    file_path = os.path.join(config.UPLOAD_FOLDER, filename)

    # Security check: strict path boundary check
    safe_root = os.path.abspath(config.UPLOAD_FOLDER) + os.sep
    target_path = os.path.abspath(file_path)
    if not target_path.startswith(safe_root):
        return jsonify({'error': 'Invalid path'}), 400

    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            PhotoIndexService.remove_photo(filename)
            return jsonify({'message': 'File deleted successfully'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    else:
        return jsonify({'error': 'File not found'}), 404


@api_bp.route('/weather-config')
def weather_config():
    """
    返回天气配置和当前天气数据

    Returns:
        JSON: {enabled: bool, current?: dict, error?: str}
    """
    if not config.WEATHER_ENABLED:
        return jsonify({'enabled': False})

    try:
        # 调用 Open-Meteo API 获取天气
        url = f'https://api.open-meteo.com/v1/forecast?latitude={config.WEATHER_LAT}&longitude={config.WEATHER_LON}&current=temperature_2m,weather_code&timezone=auto'
        ssl_context = ssl.create_default_context() if not os.environ.get('FLASK_DEBUG', '').lower() == 'true' else ssl._create_unverified_context()
        with urllib.request.urlopen(url, timeout=5, context=ssl_context) as response:
            data = json.loads(response.read().decode())

        result = {
            'enabled': True,
            'current': data.get('current', {})
        }
        resp = jsonify(result)
        resp.headers['Cache-Control'] = 'no-store'
        return resp
    except Exception as e:
        logger.error(f'Weather API error: {e}')
        return jsonify({'enabled': True, 'error': str(e)})


@api_bp.route('/daily-quote')
def get_daily_quote():
    """
    获取每日一言

    Query:
        refresh=1  强制刷新（忽略当天缓存）

    Returns:
        JSON: {text, source, provider, lang, date, cached}
    """
    force_refresh = request.args.get('refresh', '0') == '1'
    payload, cached = _resolve_daily_quote(force_refresh=force_refresh)
    resp = jsonify({**payload, 'cached': cached})
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@api_bp.route('/theme', methods=['POST'])
def set_theme():
    """
    设置用户主题偏好

    Request JSON:
        - theme: 主题名称 (style1...style16|default，style5 已下线会自动转到 style4)

    Returns:
        JSON: {success: bool, theme: str}
    """
    data = request.get_json()
    theme = data.get('theme', 'default')
    if theme == 'style5':
        theme = 'style4'
    
    valid_themes = [
        'style1', 'style2', 'style3', 'style4', 'style6',
        'style7', 'style8', 'style9', 'style10', 'style11', 'style12',
        'style13', 'style14', 'style15', 'style16', 'default'
    ]
    if theme not in valid_themes:
        return jsonify({'error': 'Invalid theme', 'valid_themes': valid_themes}), 400
    
    session['theme'] = theme
    return jsonify({'success': True, 'theme': theme})


@api_bp.route('/theme')
def get_theme():
    """
    获取当前主题偏好

    Returns:
        JSON: {theme: str, available_themes: list}
    """
    current_theme = session.get('theme', 'default')
    if current_theme == 'style5':
        current_theme = 'style4'
        session['theme'] = 'style4'
    available_themes = [
        {'id': 'default', 'name': '经典默认', 'template': 'index.html', 'display_order': 0, 'group': 'system'},
        {'id': 'style1', 'name': '经典分栏', 'template': 'index.html', 'display_order': 1, 'group': 'home'},
        {'id': 'style2', 'name': '沉浸全屏', 'template': 'index.html', 'display_order': 2, 'group': 'home'},
        {'id': 'style3', 'name': '画廊展签', 'template': 'index.html', 'display_order': 3, 'group': 'home'},
        {'id': 'style4', 'name': '悬浮玻璃', 'template': 'index.html', 'display_order': 4, 'group': 'home'},
        {'id': 'style6', 'name': '浅色海报', 'template': 'index.html', 'display_order': 5, 'group': 'home'},
        {'id': 'style7', 'name': '日式禅意', 'template': 'style7-zen.html', 'display_order': 6, 'group': 'immersive'},
        {'id': 'style8', 'name': '赛博朋克', 'template': 'style8-cyberpunk.html', 'display_order': 7, 'group': 'immersive'},
        {'id': 'style9', 'name': '和风木质', 'template': 'style9-japanese.html', 'display_order': 8, 'group': 'immersive'},
        {'id': 'style10', 'name': '北欧极简', 'template': 'style10-nordic.html', 'display_order': 9, 'group': 'immersive'},
        {'id': 'style11', 'name': '复古胶片', 'template': 'style11-vintage.html', 'display_order': 10, 'group': 'immersive'},
        {'id': 'style12', 'name': '悬浮画框', 'template': 'style12-floating.html', 'display_order': 11, 'group': 'immersive'},
        {'id': 'style13', 'name': '瀑布流', 'template': 'style13-waterfall.html', 'display_order': 12, 'group': 'curation'},
        {'id': 'style14', 'name': '全景卷轴', 'template': 'style14-panoramic.html', 'display_order': 13, 'group': 'curation'},
        {'id': 'style15', 'name': '拍立得墙', 'template': 'style15-polaroid.html', 'display_order': 14, 'group': 'curation'},
        {'id': 'style16', 'name': '艺术画廊', 'template': 'style16-gallery.html', 'display_order': 15, 'group': 'curation'},
    ]
    
    return jsonify({
        'theme': current_theme,
        'available_themes': available_themes
    })
