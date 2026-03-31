(function () {
    if (window.__UNIFIED_STYLE_MENU_INIT__) return;
    window.__UNIFIED_STYLE_MENU_INIT__ = true;

    const STYLE_ITEMS = [
        { id: 'style1', displayOrder: 1, title: '经典分栏', desc: '照片与信息均衡呈现', group: 'home' },
        { id: 'style2', displayOrder: 2, title: '沉浸全屏', desc: '主图更强，适合单图展示', group: 'home' },
        { id: 'style3', displayOrder: 3, title: '画廊展签', desc: '展签式信息布局', group: 'home' },
        { id: 'style4', displayOrder: 4, title: '悬浮玻璃', desc: '透明信息卡与大图同屏', group: 'home' },
        { id: 'style6', displayOrder: 5, title: '浅色海报', desc: '更适合明亮大屏环境', group: 'home' },
        { id: 'style7', displayOrder: 6, title: '日式禅意', desc: '圆形主图与竖签构图', group: 'immersive' },
        { id: 'style8', displayOrder: 7, title: '赛博朋克', desc: '高对比霓虹氛围', group: 'immersive' },
        { id: 'style9', displayOrder: 8, title: '和风木质', desc: '木框舞台与柔和背景', group: 'immersive' },
        { id: 'style10', displayOrder: 9, title: '北欧极简', desc: '留白克制，环境轻动', group: 'immersive' },
        { id: 'style11', displayOrder: 10, title: '复古胶片', desc: '胶片边框与怀旧质感', group: 'immersive' },
        { id: 'style12', displayOrder: 11, title: '悬浮画框', desc: '主图悬浮，层次更轻', group: 'immersive' },
        { id: 'style13', displayOrder: 12, title: '瀑布流', desc: '多图瀑布墙展示', group: 'curation' },
        { id: 'style14', displayOrder: 13, title: '全景卷轴', desc: '横向叙事与长图浏览', group: 'curation' },
        { id: 'style15', displayOrder: 14, title: '拍立得墙', desc: '便签与翻转卡片交互', group: 'curation' },
        { id: 'style16', displayOrder: 15, title: '艺术画廊', desc: '策展式展卡浏览', group: 'curation' }
    ];

    const GROUPS = [
        { id: 'home', title: '主屏系列', desc: '适合首页常亮与基础信息同屏' },
        { id: 'immersive', title: '沉浸系列', desc: '适合单图展示、氛围强化与轻交互' },
        { id: 'curation', title: '策展系列', desc: '适合照片墙、卷轴与画廊式浏览' }
    ];

    function formatDisplayOrder(value) {
        return 'No.' + String(value).padStart(2, '0');
    }

    function detectCurrentStyle() {
        const url = new URL(window.location.href);
        const theme = url.searchParams.get('theme');
        if (theme === 'style5') {
            return 'style4';
        }
        if (/^style([1-9]|1[0-6])$/.test(theme || '')) {
            return theme;
        }

        const homeStyle = document.documentElement.getAttribute('data-home-style') || '';
        const match = homeStyle.match(/^style-(\d+)$/);
        if (match) {
            if (match[1] === '5') {
                return 'style4';
            }
            return 'style' + match[1];
        }
        return 'style2';
    }

    function getStyleItem(themeId) {
        return STYLE_ITEMS.find(function (item) {
            return item.id === themeId;
        }) || STYLE_ITEMS[1];
    }

    function injectStyles() {
        if (document.getElementById('unified-style-menu-css')) return;

        const style = document.createElement('style');
        style.id = 'unified-style-menu-css';
        style.textContent = `
            #unified-style-menu {
                position: fixed;
                top: 14px;
                right: 14px;
                z-index: 999999;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
                opacity: 0;
                transform: translate3d(14px, -8px, 0) scale(0.98);
                transform-origin: top right;
                transition: opacity 0.22s ease, transform 0.22s ease;
                pointer-events: none;
            }

            #unified-style-menu.usm-visible,
            #unified-style-menu.usm-open {
                opacity: 1;
                transform: translate3d(0, 0, 0) scale(1);
            }

            .usm-hotspot {
                position: absolute;
                top: -14px;
                right: -14px;
                width: 210px;
                height: 124px;
                pointer-events: auto;
                background: transparent;
            }

            .usm-toggle {
                display: inline-flex;
                align-items: center;
                gap: 10px;
                max-width: min(72vw, 320px);
                border: 1px solid rgba(255, 255, 255, 0.18);
                background: linear-gradient(135deg, rgba(14, 18, 28, 0.88), rgba(28, 34, 48, 0.94));
                color: #fff;
                border-radius: 999px;
                padding: 9px 14px;
                font-size: 13px;
                font-weight: 600;
                cursor: pointer;
                backdrop-filter: blur(14px);
                box-shadow: 0 10px 24px rgba(0, 0, 0, 0.22);
                pointer-events: auto;
            }

            .usm-toggle-badge {
                flex: 0 0 auto;
                padding: 4px 9px;
                border-radius: 999px;
                border: 1px solid rgba(255, 214, 146, 0.24);
                background: rgba(255, 214, 146, 0.10);
                color: #ffdca0;
                font-size: 11px;
                letter-spacing: 0.10em;
            }

            .usm-toggle-text {
                min-width: 0;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }

            .usm-panel {
                margin-top: 10px;
                width: min(460px, calc(100vw - 28px));
                max-height: min(84vh, 820px);
                overflow-y: auto;
                border-radius: 20px;
                border: 1px solid rgba(255, 255, 255, 0.14);
                background:
                    radial-gradient(circle at top right, rgba(84, 132, 255, 0.16), transparent 28%),
                    linear-gradient(180deg, rgba(7, 10, 18, 0.96), rgba(10, 16, 28, 0.94));
                box-shadow: 0 24px 70px rgba(0, 0, 0, 0.42);
                padding: 14px;
                backdrop-filter: blur(16px);
                pointer-events: auto;
            }

            .usm-panel[hidden] {
                display: none;
            }

            .usm-panel-top {
                display: grid;
                gap: 12px;
                margin-bottom: 14px;
            }

            .usm-hero {
                padding: 14px;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.10);
                background:
                    radial-gradient(circle at top right, rgba(255, 214, 146, 0.12), transparent 32%),
                    linear-gradient(135deg, rgba(255, 255, 255, 0.06), rgba(255, 255, 255, 0.02));
            }

            .usm-hero-kicker {
                font-size: 11px;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                color: rgba(220, 229, 243, 0.68);
            }

            .usm-hero-title {
                margin-top: 6px;
                font-size: 16px;
                font-weight: 700;
                line-height: 1.4;
                color: #f9fbff;
            }

            .usm-hero-meta {
                margin-top: 8px;
                font-size: 12px;
                line-height: 1.55;
                color: rgba(210, 220, 235, 0.74);
            }

            .usm-home-link {
                text-decoration: none;
                color: #e5edff;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 12px;
                border-radius: 999px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                background: rgba(255, 255, 255, 0.04);
            }

            .usm-top-actions {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
            }

            .usm-logout-link {
                text-decoration: none;
                color: #ffd6d6;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 12px;
                border-radius: 999px;
                border: 1px solid rgba(255, 128, 128, 0.22);
                background: rgba(255, 96, 96, 0.08);
            }

            .usm-group {
                margin-top: 14px;
            }

            .usm-group-head {
                margin: 0 2px 10px;
            }

            .usm-group-head h3 {
                font-size: 13px;
                font-weight: 700;
                color: #f1f5ff;
            }

            .usm-group-head p {
                margin-top: 4px;
                font-size: 11px;
                line-height: 1.45;
                color: rgba(202, 213, 231, 0.62);
            }

            .usm-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 10px;
            }

            .usm-item {
                position: relative;
                display: grid;
                gap: 6px;
                min-height: 108px;
                width: 100%;
                padding: 12px 12px 14px;
                text-align: left;
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.08);
                background: linear-gradient(180deg, rgba(255, 255, 255, 0.045), rgba(255, 255, 255, 0.02));
                color: #f7faff;
                cursor: pointer;
                transition: transform 0.16s ease, border-color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease;
            }

            .usm-item:hover {
                transform: translateY(-1px);
                border-color: rgba(255, 255, 255, 0.14);
                background: linear-gradient(180deg, rgba(255, 255, 255, 0.09), rgba(255, 255, 255, 0.04));
                box-shadow: 0 12px 28px rgba(0, 0, 0, 0.2);
            }

            .usm-item.active {
                border-color: rgba(255, 214, 146, 0.38);
                background:
                    radial-gradient(circle at top right, rgba(255, 214, 146, 0.14), transparent 30%),
                    linear-gradient(180deg, rgba(255, 255, 255, 0.09), rgba(255, 255, 255, 0.03));
                box-shadow: inset 0 0 0 1px rgba(255, 214, 146, 0.10), 0 14px 30px rgba(0, 0, 0, 0.24);
            }

            .usm-item-index {
                font-size: 11px;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                color: #ffdca0;
            }

            .usm-item strong {
                font-size: 15px;
                line-height: 1.35;
                font-weight: 700;
            }

            .usm-item small {
                font-size: 12px;
                line-height: 1.5;
                color: rgba(215, 225, 240, 0.72);
            }

            .usm-item-code {
                position: absolute;
                right: 12px;
                bottom: 12px;
                padding: 3px 8px;
                border-radius: 999px;
                background: rgba(255, 255, 255, 0.06);
                color: rgba(215, 225, 240, 0.66);
                font-size: 11px;
                letter-spacing: 0.04em;
            }

            .usm-item-state {
                position: absolute;
                top: 12px;
                right: 12px;
                padding: 3px 7px;
                border-radius: 999px;
                border: 1px solid rgba(255, 214, 146, 0.2);
                background: rgba(255, 214, 146, 0.08);
                color: #ffe3ae;
                font-size: 10px;
                letter-spacing: 0.08em;
            }

            #unified-photo-nav {
                position: fixed;
                right: 16px;
                bottom: 16px;
                z-index: 999980;
                display: flex;
                gap: 10px;
            }

            #unified-photo-nav button {
                width: 46px;
                height: 46px;
                border-radius: 999px;
                border: 1px solid rgba(255, 255, 255, 0.24);
                background: rgba(10, 12, 20, 0.55);
                color: #fff;
                font-size: 22px;
                cursor: pointer;
                backdrop-filter: blur(10px);
            }

            #unified-photo-nav button:hover:not(:disabled) {
                background: rgba(255, 255, 255, 0.24);
            }

            #unified-photo-nav button:disabled {
                opacity: 0.45;
                cursor: not-allowed;
            }

            @media (max-width: 600px) {
                #unified-style-menu {
                    opacity: 1;
                    transform: none;
                    pointer-events: auto;
                }

                .usm-hotspot {
                    display: none;
                }

                .usm-panel {
                    padding: 12px;
                    border-radius: 18px;
                }

                .usm-grid {
                    grid-template-columns: minmax(0, 1fr);
                }

                .usm-item {
                    min-height: 96px;
                }
            }
        `;
        document.head.appendChild(style);
    }

    function parsePhotoUrlFromSrc(rawSrc) {
        if (!rawSrc) return null;
        const marker = '/static/photos/';
        const idx = rawSrc.indexOf(marker);
        if (idx < 0) return null;
        let path = rawSrc.slice(idx + marker.length);
        path = path.split('?')[0].split('#')[0];
        if (!path) return null;
        try {
            return decodeURIComponent(path);
        } catch (_) {
            return path;
        }
    }

    function normalizePhotoEntry(input) {
        if (!input) return null;
        if (typeof input === 'string') {
            return { url: input };
        }

        const url = typeof input.url === 'string' ? input.url.trim() : '';
        if (!url) return null;

        return {
            url: url,
            date: input.date || '',
            tags: input.tags || '',
            note_title: input.note_title || '',
            note_body: input.note_body || '',
            is_salvaged: input.is_salvaged === true
        };
    }

    function formatCaptureMeta(date) {
        return date ? '拍摄于 ' + date : '拍摄日期未记录';
    }

    function applyPhotoMetaToDom(input) {
        const photo = normalizePhotoEntry(input);
        if (!photo) return null;

        window.__currentPhotoMeta = photo;
        document.body.classList.toggle('has-salvaged-photo', photo.is_salvaged === true);

        document.querySelectorAll('[data-photo-date-target]').forEach(function (node) {
            node.textContent = formatCaptureMeta(photo.date);
            node.title = photo.date || '';
        });

        document.querySelectorAll('[data-salvage-target]').forEach(function (node) {
            node.hidden = photo.is_salvaged !== true;
        });

        document.dispatchEvent(new CustomEvent('unified:photo-meta-applied', {
            detail: { photo: photo }
        }));

        return photo;
    }

    window.__applyUnifiedPhotoMeta = applyPhotoMetaToDom;

    function getCurrentPhotoEntryFromDom() {
        const knownMeta = normalizePhotoEntry(window.__currentPhotoMeta);
        if (knownMeta) {
            return knownMeta;
        }

        const mainPhoto = document.getElementById('main-photo');
        if (mainPhoto && mainPhoto.src) {
            const parsed = parsePhotoUrlFromSrc(mainPhoto.src);
            if (parsed) return { url: parsed };
        }

        const framePhoto = document.querySelector('.photo-frame img');
        if (framePhoto && framePhoto.src) {
            const parsed = parsePhotoUrlFromSrc(framePhoto.src);
            if (parsed) return { url: parsed };
        }

        const display = document.getElementById('photo-display');
        if (display) {
            const bg = display.style.backgroundImage || '';
            const match = bg.match(/\/static\/photos\/([^"')?]+)/);
            if (match && match[1]) {
                try {
                    return { url: decodeURIComponent(match[1]) };
                } catch (_) {
                    return { url: match[1] };
                }
            }
        }

        return null;
    }

    function applyPhotoUrlToDom(input) {
        const photo = normalizePhotoEntry(input);
        if (!photo || !photo.url) return;
        const targetUrl = '/static/photos/' + photo.url;

        const display = document.getElementById('photo-display');
        if (display) {
            display.style.backgroundImage = "url('" + targetUrl + "')";
            display.classList.add('loaded');
        }

        const mainPhoto = document.getElementById('main-photo');
        if (mainPhoto) {
            mainPhoto.src = targetUrl;
            mainPhoto.alt = url;
        }

        const mainPhotoBg = document.getElementById('main-photo-bg');
        if (mainPhotoBg) {
            mainPhotoBg.src = targetUrl;
        }

        const framePhoto = document.querySelector('.photo-frame img');
        if (framePhoto && framePhoto !== mainPhoto) {
            framePhoto.src = targetUrl;
            framePhoto.alt = photo.url;
        }

        applyPhotoMetaToDom(photo);
    }

    function initPhotoNavForTheme(themeId) {
        if (!/^style(7|8|9|10|11|12)$/.test(themeId || '')) return;
        if (document.getElementById('unified-photo-nav')) return;

        const wrap = document.createElement('div');
        wrap.id = 'unified-photo-nav';
        wrap.innerHTML = `
            <button type="button" id="unified-prev-btn" aria-label="上一张">&#10094;</button>
            <button type="button" id="unified-next-btn" aria-label="下一张">&#10095;</button>
        `;
        document.body.appendChild(wrap);

        const prevBtn = wrap.querySelector('#unified-prev-btn');
        const nextBtn = wrap.querySelector('#unified-next-btn');
        const history = [];
        let index = -1;

        function syncButtons() {
            prevBtn.disabled = index <= 0;
        }

        function pushHistory(input) {
            const photo = normalizePhotoEntry(input);
            if (!photo || !photo.url) return;
            if (history[index] && history[index].url === photo.url) {
                history[index] = Object.assign({}, history[index], photo);
                return;
            }

            if (index < history.length - 1) {
                history.splice(index + 1);
            }
            history.push(photo);
            index = history.length - 1;
            syncButtons();
        }

        async function fetchAndApplyNext() {
            try {
                const response = await fetch('/api/get_photo', { credentials: 'same-origin' });
                if (!response.ok) return;
                const photo = await response.json();
                if (!photo || !photo.url) return;
                applyPhotoUrlToDom(photo);
                pushHistory(photo);
            } catch (_) {}
        }

        prevBtn.addEventListener('click', function () {
            if (index <= 0) return;
            index -= 1;
            applyPhotoUrlToDom(history[index]);
            syncButtons();
        });

        nextBtn.addEventListener('click', function () {
            fetchAndApplyNext();
        });

        syncButtons();

        setInterval(function () {
            const currentPhoto = getCurrentPhotoEntryFromDom();
            if (currentPhoto) {
                pushHistory(currentPhoto);
            }
        }, 1200);

        setTimeout(function () {
            const currentPhoto = getCurrentPhotoEntryFromDom();
            if (currentPhoto) {
                pushHistory(currentPhoto);
            }
        }, 800);
    }

    function renderMenu() {
        const legacyQuick = document.getElementById('quick-theme-nav');
        if (legacyQuick) legacyQuick.remove();

        const legacyHotspot = document.getElementById('home-style-hotspot');
        if (legacyHotspot) legacyHotspot.style.display = 'none';
        const legacySwitcher = document.getElementById('home-style-switcher');
        if (legacySwitcher) legacySwitcher.style.display = 'none';

        injectStyles();

        const activeTheme = detectCurrentStyle();
        const currentItem = getStyleItem(activeTheme);

        const wrap = document.createElement('div');
        wrap.id = 'unified-style-menu';
        wrap.innerHTML = `
            <div class="usm-hotspot" aria-hidden="true"></div>
            <button type="button" class="usm-toggle" aria-expanded="false">
                <span class="usm-toggle-badge">${formatDisplayOrder(currentItem.displayOrder)}</span>
                <span class="usm-toggle-text">${currentItem.title}</span>
            </button>
            <div class="usm-panel" hidden>
                <div class="usm-panel-top">
                    <div class="usm-hero">
                        <div class="usm-hero-kicker">Style Menu</div>
                        <div class="usm-hero-title">共 ${STYLE_ITEMS.length} 套样式，菜单已按新的连续顺序重排</div>
                        <div class="usm-hero-meta">当前展示使用连续序号 1-${STYLE_ITEMS.length}。为了兼容现有链接和代码，内部主题编号仍保留原来的 style id。</div>
                    </div>
                    <div class="usm-top-actions">
                        <a class="usm-home-link" href="/">返回首页</a>
                        <a class="usm-logout-link" href="/logout">退出登录</a>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(wrap);

        const panel = wrap.querySelector('.usm-panel');
        const toggle = wrap.querySelector('.usm-toggle');
        const hotspot = wrap.querySelector('.usm-hotspot');
        const prefersTouchReveal = window.matchMedia && window.matchMedia('(hover: none)').matches;
        let hideTimer = null;

        function clearHideTimer() {
            if (hideTimer) {
                clearTimeout(hideTimer);
                hideTimer = null;
            }
        }

        function showMenu() {
            clearHideTimer();
            wrap.classList.add('usm-visible');
        }

        function scheduleHide(delay) {
            if (prefersTouchReveal || !panel.hidden) return;
            clearHideTimer();
            hideTimer = setTimeout(function () {
                wrap.classList.remove('usm-visible');
            }, delay || 420);
        }

        GROUPS.forEach(function (group) {
            const section = document.createElement('section');
            section.className = 'usm-group';
            section.innerHTML = `
                <div class="usm-group-head">
                    <h3>${group.title}</h3>
                    <p>${group.desc}</p>
                </div>
                <div class="usm-grid"></div>
            `;

            const grid = section.querySelector('.usm-grid');
            STYLE_ITEMS.filter(function (item) {
                return item.group === group.id;
            }).forEach(function (item) {
                const button = document.createElement('button');
                button.type = 'button';
                button.className = 'usm-item' + (item.id === activeTheme ? ' active' : '');
                button.dataset.theme = item.id;
                button.innerHTML = `
                    <span class="usm-item-index">${formatDisplayOrder(item.displayOrder)}</span>
                    <strong>${item.title}</strong>
                    <small>${item.desc}</small>
                    <span class="usm-item-code">${item.id}</span>
                    ${item.id === activeTheme ? '<span class="usm-item-state">当前</span>' : ''}
                `;
                button.addEventListener('click', function () {
                    const target = '/?theme=' + encodeURIComponent(item.id);
                    if (window.location.pathname + window.location.search === target) {
                        panel.hidden = true;
                        toggle.setAttribute('aria-expanded', 'false');
                        return;
                    }
                    window.location.href = target;
                });
                grid.appendChild(button);
            });

            panel.appendChild(section);
        });

        toggle.addEventListener('click', function (event) {
            event.stopPropagation();
            showMenu();
            panel.hidden = !panel.hidden;
            toggle.setAttribute('aria-expanded', String(!panel.hidden));
            wrap.classList.toggle('usm-open', !panel.hidden);
            if (panel.hidden) {
                scheduleHide(520);
            }
        });

        document.addEventListener('click', function (event) {
            if (!wrap.contains(event.target)) {
                panel.hidden = true;
                toggle.setAttribute('aria-expanded', 'false');
                wrap.classList.remove('usm-open');
                scheduleHide(220);
            }
        });

        document.addEventListener('keydown', function (event) {
            if (event.key === 'Escape') {
                panel.hidden = true;
                toggle.setAttribute('aria-expanded', 'false');
                wrap.classList.remove('usm-open');
                scheduleHide(220);
            }
        });

        if (prefersTouchReveal) {
            wrap.classList.add('usm-visible');
        } else {
            scheduleHide(0);
            hotspot.addEventListener('mouseenter', showMenu);
            hotspot.addEventListener('mousemove', showMenu);
            hotspot.addEventListener('mouseleave', function () {
                scheduleHide(500);
            });
            wrap.addEventListener('mouseenter', showMenu);
            wrap.addEventListener('mouseleave', function () {
                scheduleHide(500);
            });
        }

        initPhotoNavForTheme(activeTheme);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', renderMenu, { once: true });
    } else {
        renderMenu();
    }
})();
