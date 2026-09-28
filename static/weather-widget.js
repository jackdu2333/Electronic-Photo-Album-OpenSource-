/* ============================================================
   WeatherWidget — uiteam 风格评审 P0-1 / 系统性建议 1
   style17(黑胶) / style18(折光) / style19(折纸) 共用天气模块
   修复：三款天气 UI 此前永远显示占位符（无更新逻辑）

   数据源：/api/weather-config
     → { enabled: bool, current?: { temperature_2m, weather_code } }

   挂载约定（元素存在才更新，缺失自动跳过）：
     #weather-icon  → 天气 emoji
     #weather-temp  → "21°C"（若同页无 #weather-desc/#weather-icon，
                        则输出 "21°C ☀️" 组合式，适配 style17 徽标）
     #weather-desc  → 同页有 #weather-icon 时填纯描述（style19），
                        否则填 "多云 • 21°C" 组合式（style18）
   ============================================================ */
(function () {
    'use strict';

    function iconFromCode(code) {
        if (code <= 1) return '☀️';
        if (code <= 3) return '⛅';
        if (code <= 48) return '🌫️';
        if (code <= 57) return '🌦️';
        if (code <= 67) return '🌧️';
        if (code <= 77) return '❄️';
        if (code <= 86) return '🌨️';
        return '⛈️';
    }

    function descFromCode(code) {
        if (code <= 1) return '晴';
        if (code <= 3) return '多云';
        if (code <= 48) return '雾';
        if (code <= 57) return '毛毛雨';
        if (code <= 67) return '雨';
        if (code <= 77) return '雪';
        if (code <= 86) return '阵雨';
        return '雷雨';
    }

    function apply(data) {
        const tempEl = document.getElementById('weather-temp');
        const descEl = document.getElementById('weather-desc');
        const iconEl = document.getElementById('weather-icon');
        if (!tempEl && !descEl && !iconEl) return;

        const showPlaceholder = function (closed) {
            if (tempEl && descEl && iconEl) {
                tempEl.textContent = '--°C';
                iconEl.textContent = '🌤️';
                descEl.textContent = closed ? '天气已关闭' : '暂无数据';
            } else if (descEl) {
                descEl.textContent = closed ? '天气已关闭' : '--°C';
            } else if (tempEl) {
                tempEl.textContent = closed ? '--°C 🌤️' : '--°C';
            }
        };

        if (!data || !data.enabled || !data.current) {
            showPlaceholder(true);
            return;
        }

        const temp = Math.round(Number(data.current.temperature_2m));
        const code = Number(data.current.weather_code ?? 0);
        if (Number.isNaN(temp)) {
            showPlaceholder(false);
            return;
        }

        const icon = iconFromCode(code);
        const desc = descFromCode(code);

        if (tempEl && descEl && iconEl) {
            // style19：三元素分体布局
            tempEl.textContent = temp + '°C';
            iconEl.textContent = icon;
            descEl.textContent = desc;
        } else if (descEl) {
            // style18：单元素组合式
            descEl.textContent = desc + ' • ' + temp + '°C';
        } else if (tempEl) {
            // style17：单徽标组合式
            tempEl.textContent = temp + '°C ' + icon;
        }
    }

    async function refresh() {
        try {
            const res = await fetch('/api/weather-config', { credentials: 'same-origin' });
            if (!res.ok) throw new Error('weather failed');
            apply(await res.json());
        } catch (e) {
            console.log('天气获取失败，保持占位');
        }
    }

    function init() {
        const has = document.getElementById('weather-temp') ||
                    document.getElementById('weather-desc') ||
                    document.getElementById('weather-icon');
        if (has) refresh();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // 暴露手动刷新入口，便于后续统一菜单联动
    window.WeatherWidget = { refresh: refresh };
})();
