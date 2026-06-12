"""
推荐算法服务模块
V3.0 Memory Curator 多频道推荐引擎

频道配比（默认）：
  今日回忆 20% | 好久不见 20% | 小故事 20% | 高光时刻 25% | 随缘漫游 15%

核心改进（Round 1）：
  - v3 字段兼容（id, display_url, source_type）
  - missing=true 过滤
  - 播放冷却池（最近 N 张不重复）
  - recommend_channel / recommend_reason 可解释推荐
  - view_count 按 id 更新
"""
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from .database import AppStateDAO, PhotoDAO

logger = logging.getLogger(__name__)

# ── 全局配置 ──────────────────────────────────────────────
_seasonal_weights: Dict[str, float] = {}
_deep_sea_probability: float = 0.05
_deep_sea_years_threshold: int = 2
_FORCE_SHOW_STATE_KEY = "force_show"

# ── 频道配比（默认） ──────────────────────────────────────
CHANNEL_TODAY_MEMORY = "today_memory"
CHANNEL_LONG_TIME_NO_SEE = "long_time_no_see"
CHANNEL_STORY = "story"
CHANNEL_HIGHLIGHTS = "highlights"
CHANNEL_RANDOM = "random"

_CHANNEL_RATIOS = [
    (CHANNEL_TODAY_MEMORY, 20),
    (CHANNEL_LONG_TIME_NO_SEE, 20),
    (CHANNEL_STORY, 20),
    (CHANNEL_HIGHLIGHTS, 25),
    (CHANNEL_RANDOM, 15),
]

# ── 冷却池与播放控制 ──────────────────────────────────────
COOLDOWN_SIZE = 30
ANNIVERSARY_WINDOW_DAYS = 3
STORY_MAX_LENGTH = 4
PLAY_HISTORY_KEEP_DAYS = 30


def set_recommendation_config(seasonal_weights: Dict[str, float],
                               deep_sea_probability: float,
                               deep_sea_years_threshold: int):
    """
    设置推荐算法配置

    Args:
        seasonal_weights: 季节权重配置 {"current": 2.0, "adjacent": 1.5, "other": 1.0, "none": 0.5}
        deep_sea_probability: 深海打捞概率 (0.0-1.0)
        deep_sea_years_threshold: 深海打捞年份阈值
    """
    global _seasonal_weights, _deep_sea_probability, _deep_sea_years_threshold
    _seasonal_weights = seasonal_weights
    _deep_sea_probability = deep_sea_probability
    _deep_sea_years_threshold = deep_sea_years_threshold


def set_force_show(img_url: str, expiry_timestamp: float):
    """
    设置强制展示照片

    Args:
        img_url: 照片 URL
        expiry_timestamp: 过期时间戳
    """
    AppStateDAO.set_json(
        _FORCE_SHOW_STATE_KEY,
        {"img_url": img_url, "expiry_timestamp": expiry_timestamp}
    )


def clear_force_show():
    """清除强制展示状态"""
    AppStateDAO.delete(_FORCE_SHOW_STATE_KEY)


def get_force_show_state() -> tuple:
    """获取强制展示状态"""
    state = AppStateDAO.get_json(_FORCE_SHOW_STATE_KEY)
    if not state:
        return None, 0

    return state.get("img_url"), float(state.get("expiry_timestamp", 0))


def record_play(photo_id: str, channel: str = '', reason: str = ''):
    """记录播放历史（冷却池 + 故事连续性）"""
    PhotoDAO.record_play(photo_id, channel, reason)


def get_recent_played_ids(limit: int = COOLDOWN_SIZE) -> List[str]:
    """获取最近播放过的照片标识列表"""
    try:
        return PhotoDAO.get_recent_played_ids(limit)
    except Exception:
        return []


class RecommendationService:
    """
    V3.0 Memory Curator 推荐服务

    核心逻辑：
    1. 强制展示优先（管理端上传时触发）
    2. 多频道路由分发（今日回忆 / 好久不见 / 小故事 / 高光时刻 / 随缘漫游）
    3. 冷却池过滤（最近 N 张不重复）
    4. 返回 v3 兼容字段 + 推荐理由
    """

    @staticmethod
    def get_next_photo() -> Optional[Dict[str, Any]]:
        """
        获取下一张推荐照片（V3.0 Memory Curator）

        Returns:
            照片字典（含 v3 字段 + recommend_channel + recommend_reason）
            或 None（无可用照片）
        """
        import time

        # ── 延迟导入避免循环依赖 ────────────────────────
        from services.photo_service import PhotoService

        photo_index = None  # 延迟加载

        # ── 0. 强制展示逻辑（优先级最高）──────────────
        cur_force_img, cur_force_expiry = get_force_show_state()
        if cur_force_img and time.time() < cur_force_expiry:
            photo_index = PhotoService.get_photo_index()
            for p in photo_index:
                if p['url'] == cur_force_img:
                    result = RecommendationService._format_result(
                        p, 'forced', '强制展示'
                    )
                    logger.info(f"[强制展示] 命中：{cur_force_img}")
                    return result
            clear_force_show()
        elif cur_force_img:
            clear_force_show()

        # ── 1. 加载照片索引（已过滤 missing=true）───────
        if photo_index is None:
            photo_index = PhotoService.get_photo_index()
        if not photo_index:
            logger.warning("Photo index is empty")
            return None

        # ── 2. 冷却池：获取最近播放过的照片 ─────────────
        cooled_ids = set(get_recent_played_ids(COOLDOWN_SIZE))

        # 过滤冷却池中的照片
        pool = [p for p in photo_index
                if RecommendationService._photo_key(p) not in cooled_ids]

        # 冷却池过滤后为空则回退到全量（避免卡死）
        if not pool:
            logger.info("[冷却池] 全量冷却，回退到完整照片池")
            pool = photo_index

        # ── 3. 频道路由分发 ─────────────────────────────
        channel = RecommendationService._pick_channel()

        photo, reason = None, ''

        if channel == CHANNEL_TODAY_MEMORY:
            photo, reason = RecommendationService._today_memory(pool)
        elif channel == CHANNEL_LONG_TIME_NO_SEE:
            photo, reason = RecommendationService._long_time_no_see(pool)
        elif channel == CHANNEL_STORY:
            photo, reason = RecommendationService._story_continuity(pool, photo_index)
        elif channel == CHANNEL_HIGHLIGHTS:
            photo, reason = RecommendationService._highlights(pool)
        # CHANNEL_RANDOM 或其他未知频道都走随缘漫游

        # 频道失败或未匹配，降级到随缘漫游
        if not photo:
            photo, reason = RecommendationService._random_roam(pool)

        if photo:
            pid = RecommendationService._photo_key(photo)
            record_play(pid, channel, reason)

            # 按 id 更新 view_count（兼容无 id 的旧数据）
            try:
                if photo.get('id'):
                    PhotoDAO.increment_view_count_by_id(photo['id'])
                else:
                    PhotoDAO.increment_view_count(photo['url'])
            except Exception as e:
                logger.warning(f"view_count 更新失败（非致命）: {e}")

            # 定期清理过期播放历史（每 100 次推荐清理一次）
            if random.randint(1, 100) == 1:
                try:
                    PhotoDAO.cleanup_play_history(PLAY_HISTORY_KEEP_DAYS)
                except Exception:
                    pass

            return RecommendationService._format_result(photo, channel, reason)

        logger.warning("All channels failed to select a photo")
        return None

    # ══════════════════════════════════════════════════════
    #  频道路由
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _pick_channel() -> str:
        """
        按比例随机选择一个推荐频道

        Returns:
            频道标识字符串
        """
        channels = [c for c, _ in _CHANNEL_RATIOS]
        ratios = [r for _, r in _CHANNEL_RATIOS]
        return random.choices(channels, weights=ratios, k=1)[0]

    # ══════════════════════════════════════════════════════
    #  频道实现
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _today_memory(pool: List[Dict]) -> tuple:
        """
        今日回忆频道：往年今天、同月季节照片加权

        Returns:
            (photo, reason) 或 (None, '')
        """
        today = datetime.now()
        current_month = today.month
        current_day = today.day

        # 筛选有日期的照片
        dated = [p for p in pool if p.get('date')]
        if not dated:
            return None, ''

        weights = []
        for p in dated:
            w = p.get('weight', 1.0) * RecommendationService._get_seasonal_weight(
                p.get('month'), current_month
            )

            # 周年加权：日期在今天前后 ANNIVERSARY_WINDOW_DAYS 天内
            try:
                pdate = datetime.strptime(p['date'], '%Y-%m-%d')
                day_diff = abs(pdate.replace(year=today.year) - today).days
                if day_diff <= ANNIVERSARY_WINDOW_DAYS:
                    w *= 3.0  # 往年今天强加权
            except (ValueError, OverflowError):
                pass

            weights.append(max(w, 0.01))

        selected = random.choices(dated, weights=weights, k=1)[0]

        # 生成推荐理由
        reason = '这个季节的回忆'
        if selected.get('date'):
            try:
                pdate = datetime.strptime(selected['date'], '%Y-%m-%d')
                day_diff = abs(pdate.replace(year=today.year) - today).days
                if day_diff <= ANNIVERSARY_WINDOW_DAYS:
                    reason = '往年今天'
            except (ValueError, OverflowError):
                pass

        return selected, reason

    @staticmethod
    def _long_time_no_see(pool: List[Dict]) -> tuple:
        """
        好久不见频道：深海打捞 + 低 view_count 优先

        Returns:
            (photo, reason) 或 (None, '')
        """
        cutoff_date = (
            datetime.now() - timedelta(days=_deep_sea_years_threshold * 365)
        ).strftime('%Y-%m-%d')

        # 优先选老照片（date <= cutoff）中 view_count 最低的
        old_photos = [p for p in pool
                      if p.get('date') and p['date'] <= cutoff_date]

        if old_photos:
            # 按 view_count 升序，从最低的一批中随机选取
            min_vc = min(p.get('view_count', 0) for p in old_photos)
            candidates = [p for p in old_photos if p.get('view_count', 0) <= min_vc + 1]
            selected = random.choice(candidates)
            return selected, '好久不见'

        # 无老照片，从全池选 view_count 较低的
        if pool:
            view_counts = [p.get('view_count', 0) for p in pool]
            median_vc = sorted(view_counts)[len(view_counts) // 2]
            candidates = [p for p in pool if p.get('view_count', 0) <= median_vc]
            if not candidates:
                candidates = pool
            selected = random.choice(candidates)
            return selected, '很久没看到这张了'

        return None, ''

    @staticmethod
    def _story_continuity(pool: List[Dict], full_index: Optional[List[Dict]] = None) -> tuple:
        """
        小故事频道：根据最近播放照片延续同标签 / 同月份故事

        Args:
            pool: 冷却池过滤后的候选照片
            full_index: 完整照片索引（用于查找上一张照片，避免重复查库）

        Returns:
            (photo, reason) 或 (None, '')
        """
        try:
            last_play = PhotoDAO.get_last_played()
        except Exception:
            last_play = None

        if not last_play:
            return None, ''

        last_id = last_play.get('photo_id', '')
        last_photo = None

        # 在完整索引中查找上一张（pool 可能已过滤掉它）
        search_index = full_index
        if search_index is None:
            from services.photo_service import PhotoService
            search_index = PhotoService.get_photo_index()
        for p in search_index:
            if RecommendationService._photo_key(p) == last_id:
                last_photo = p
                break

        if not last_photo:
            return None, ''

        last_tags = last_photo.get('tags', '')
        last_month = last_photo.get('month')

        if not last_tags and last_month is None:
            return None, ''

        # 找出与上一张有共同标签或月份的照片
        candidates = []
        weights = []
        for p in pool:
            if RecommendationService._photo_key(p) == last_id:
                continue  # 跳过自身

            w = p.get('weight', 1.0)
            boosted = False

            if last_tags and p.get('tags'):
                shared = set(last_tags.split('，')) & set(p['tags'].split('，'))
                shared -= {''}
                if shared:
                    w *= 2.0
                    boosted = True

            if last_month and p.get('month') == last_month:
                w *= 1.5
                boosted = True

            if boosted:
                candidates.append(p)
                weights.append(max(w, 0.01))

        if not candidates:
            return None, ''

        selected = random.choices(candidates, weights=weights, k=1)[0]

        reason = '同一组回忆'
        if last_tags and selected.get('tags'):
            shared = set(last_tags.split('，')) & set(selected['tags'].split('，'))
            shared -= {''}
            if shared:
                reason = '同一段旅行'
        elif last_month and selected.get('month') == last_month:
            reason = '同一个季节'

        return selected, reason

    @staticmethod
    def _highlights(pool: List[Dict]) -> tuple:
        """
        高光时刻频道：高权重标签照片优先

        Returns:
            (photo, reason) 或 (None, '')
        """
        if not pool:
            return None, ''

        weights = [
            max(p.get('weight', 1.0) ** 2, 0.01)  # 平方放大权重差异
            for p in pool
        ]

        selected = random.choices(pool, weights=weights, k=1)[0]
        reason = '高光时刻' if selected.get('weight', 1.0) > 1.5 else '温馨瞬间'

        return selected, reason

    @staticmethod
    def _random_roam(pool: List[Dict]) -> tuple:
        """
        随缘漫游频道：随机 + 低曝光轻微补偿

        Returns:
            (photo, reason) 或 (None, '')
        """
        if not pool:
            return None, ''

        # 低曝光补偿：view_count 低于中位数的照片获得加权
        view_counts = [p.get('view_count', 0) for p in pool]
        median_vc = sorted(view_counts)[len(view_counts) // 2] if view_counts else 0

        weights = []
        for p in pool:
            w = p.get('weight', 1.0)
            if p.get('view_count', 0) < median_vc:
                w *= 1.3  # 低曝光轻微补偿
            weights.append(max(w, 0.01))

        selected = random.choices(pool, weights=weights, k=1)[0]

        if selected.get('view_count', 0) < max(median_vc, 3):
            reason = '随机惊喜'
        else:
            reason = '随缘漫游'

        return selected, reason

    # ══════════════════════════════════════════════════════
    #  辅助方法
    # ══════════════════════════════════════════════════════

    @staticmethod
    def _photo_key(photo: Dict) -> str:
        """获取照片唯一标识（优先 id，回退 url）"""
        return photo.get('id') or photo.get('url', '')

    @staticmethod
    def _format_result(photo: Dict, channel: str, reason: str) -> Dict[str, Any]:
        """
        格式化 v3 推荐结果

        Args:
            photo: 照片字典
            channel: 推荐频道标识
            reason: 推荐理由文本

        Returns:
            完整推荐结果字典
        """
        return {
            'id': photo.get('id', ''),
            'url': photo.get('url', ''),
            'display_url': photo.get('display_url', ''),
            'source_type': photo.get('source_type', 'imported_copy'),
            'date': photo.get('date'),
            'month': photo.get('month'),
            'tags': photo.get('tags', ''),
            'weight': photo.get('weight', 1.0),
            'view_count': photo.get('view_count', 0),
            'is_salvaged': channel == CHANNEL_LONG_TIME_NO_SEE,
            'recommend_channel': channel,
            'recommend_reason': reason,
        }

    @staticmethod
    def _get_seasonal_weight(photo_month: Optional[int], current_month: int) -> float:
        """
        计算季节权重

        Args:
            photo_month: 照片拍摄月份
            current_month: 当前月份

        Returns:
            季节权重系数
        """
        if photo_month is None:
            return _seasonal_weights.get('none', 0.5)

        if photo_month == current_month:
            return _seasonal_weights.get('current', 2.0)

        prev_month = 12 if current_month == 1 else current_month - 1
        next_month = 1 if current_month == 12 else current_month + 1

        if photo_month == prev_month or photo_month == next_month:
            return _seasonal_weights.get('adjacent', 1.5)

        return _seasonal_weights.get('other', 1.0)
