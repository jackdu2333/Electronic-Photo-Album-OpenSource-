"""
主页面路由模块
首页、登录页等基础页面
"""
import time
from flask import Blueprint, render_template, request, make_response, session, redirect, url_for, flash

from config import config
from auth import auth

main_bp = Blueprint('main', __name__, url_prefix='/')


@main_bp.route('/')
def index():
    """
    首页渲染

    认证由 auth.py 的 before_request 统一处理
    支持主题切换：?theme=style1...style16（style5 已下线，自动兼容到 style4）
    """
    # 获取主题偏好（URL 参数 > Session > 默认）
    theme = request.args.get('theme') or session.get('theme', 'default')
    if theme == 'style5':
        theme = 'style4'

    # 首页内置样式（style5 已下线）
    home_style_map = {
        'style1': 'style-1',
        'style2': 'style-2',
        'style3': 'style-3',
        'style4': 'style-4',
        'style6': 'style-6',
    }

    # 独立模板主题（7-16）
    theme_templates = {
        'style7': 'style7-zen.html',
        'style8': 'style8-cyberpunk.html',
        'style9': 'style9-japanese.html',
        'style10': 'style10-nordic.html',
        'style11': 'style11-vintage.html',
        'style12': 'style12-floating.html',
        'style13': 'style13-waterfall.html',
        'style14': 'style14-panoramic.html',
        'style15': 'style15-polaroid.html',
        'style16': 'style16-gallery.html',
    }

    forced_home_style = None

    # 保存主题到 session
    if theme in home_style_map or theme in theme_templates:
        session['theme'] = theme

    # 选择模板
    if theme in home_style_map:
        template_name = 'index.html'
        forced_home_style = home_style_map[theme]
    elif theme in theme_templates:
        template_name = theme_templates[theme]
    else:
        template_name = 'index.html'

    resp = make_response(render_template(
        template_name,
        username=session.get('_username', 'User'),
        baby_name=config.BABY_NAME,
        baby_birthday=config.BABY_BIRTHDAY,
        forced_home_style=forced_home_style
    ))
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@main_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    """
    登录页面

    GET: 显示登录表单
    POST: 处理登录请求
    """
    # 如果已经登录，直接跳转到首页
    if session.get('_auth_ok'):
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('请输入用户名和密码')
            return render_template('login.html')

        # 验证用户凭证
        if auth.check_credentials(username, password):
            # 登录成功，设置 session
            session['_auth_ok'] = True
            session['_username'] = username
            session['_login_time'] = time.time()

            # 返回成功响应（前端会处理跳转）
            return make_response({'success': True, 'username': username}, 200)
        else:
            # 登录失败
            flash('用户名或密码错误')
            return render_template('login.html', error=True)

    # GET 请求，显示登录表单
    return render_template('login.html')


@main_bp.route('/logout')
def logout():
    """登出"""
    session.clear()
    return redirect(url_for('main.login_page'))


@main_bp.route('/admin')
def admin_page():
    """管理后台首页（需要认证，由 auth.py 统一处理）"""
    return render_template('admin.html')


@main_bp.route('/admin/manage')
def manage_page():
    """相册管理页面（需要认证，由 auth.py 统一处理）"""
    return render_template('manage.html')
