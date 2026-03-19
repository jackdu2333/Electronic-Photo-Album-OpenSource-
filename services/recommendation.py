"""
推荐算法服务模块
V2.0 双轨制推荐算法：深海打捞 5% + 常规加权 95%
"""
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from .database import AppStateDAO, PhotoDAO
from .photo_index import get_photo_index

logger = logging.getLogger(__name__)

# 全局配置（由 app.py 设置）
_seasonal_weights: Dict[str, float] = {}
_deep_sea_probability: float = 0.05
_deep_sea_years_threshold: int = 2
_FORCE_SHOW_STATE_KEY = "force_show"


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


class RecommendationService:
    """
    V2.0 双轨制推荐服务

    核心逻辑：
    1. 强制展示优先（管理端上传时触发）
    2. 深海打捞 5%：从冷数据中打捞老照片
    3. 常规加权 95%：标签权重 × 季节权重
    """

    @staticmethod
    def get_next_photo() -> Optional[Dict[str, Any]]:
        """
        获取下一张推荐照片

        Returns:
            照片字典 {url, date, month, tags, weight, view_count, is_salvaged}
            或 None（无可用照片）
        """
        import time

        # ── 0. 强制展示逻辑（优先级最高）──────────────
        cur_force_img, cur_force_expiry = get_force_show_state()
        if cur_force_img and time.time() < cur_force_expiry:
            photo_index = get_photo_index()
            for p in photo_index:
                if p['url'] == cur_force_img:
                    result = p.copy()
                    result['is_salvaged'] = False
                    logger.info(f"[强制展示] 命中：{cur_force_img}")
                    return result
            # 照片已不存在，清理掉失效状态，避免长时间轮询空命中
            clear_force_show()
        elif cur_force_img:
            clear_force_show()

        # ── 保险：若内存索引为空则返回 ───────────────────
        photo_index = get_photo_index()
        if not photo_index:
            logger.warning("Photo index is empty")
            return None

        # ── 全局路由分发器 ─────────────────────────────
        # 深海打捞概率
        deep_sea_threshold = int(_deep_sea_probability * 100)
        rand_num = random.randint(1, 100)

        # ════════════════════════════════════════════════════
        # 轨道 1：深海打捞模式（rand_num <= threshold）
        # ════════════════════════════════════════════════════
        if rand_num <= deep_sea_threshold:
            result = RecommendationService._deep_sea_salvage()
            if result:
                return result
            # 冷数据池为空，降级到常规轨道
            logger.info("[深海打捞] 冷数据池为空，降级至常规加权模式")

        # ════════════════════════════════════════════════════
        # 轨道 2：常规加权模式
        # ════════════════════════════════════════════════════
        return RecommendationService._regular_selection()

    @staticmethod
    def _deep_sea_salvage() -> Optional[Dict[str, Any]]:
        """
        深海打捞：从冷数据中打捞老照片

        冷数据定义：拍摄日期距今超过配置年份（默认 2 年）

        Returns:
            照片字典，包含 is_salvaged=True
        """
        cutoff_date = (datetime.now() - timedelta(days=_deep_sea_years_threshold * 365)).strftime('%Y-%m-%d')

        try:
            row = PhotoDAO.get_deep_sea_candidate(cutoff_date)

            if row:
                row['is_salvaged'] = True
                logger.info(f"[深海打捞] 命中！rand={random.randint(1,100)}, 照片={row['url']}, view_count={row.get('view_count', 'N/A')}")
                return row

        except Exception as e:
            logger.error(f"[深海打捞] SQLite 查询异常，降级至常规模式：{e}")

        return None

    @staticmethod
    def _regular_selection() -> Optional[Dict[str, Any]]:
        """
        常规加权选择：标签权重 × 季节权重

        最终权重 = 静态标签权重 × 动态季节权重

        Returns:
            照片字典，包含 is_salvaged=False
        """
        photo_index = get_photo_index()
        if not photo_index:
            return None

        current_month = datetime.now().month

        # 对全量照片计算最终权重
        weights = [
            p.get('weight', 1.0) * RecommendationService._get_seasonal_weight(
                p.get('month'), current_month
            )
            for p in photo_index
        ]

        # 按权重随机抽取 1 张
        selected_photo = random.choices(photo_index, weights=weights, k=1)[0]

        # 常规轨道也自增 view_count
        try:
            PhotoDAO.increment_view_count(selected_photo['url'])
        except Exception as e:
            logger.warning(f"[常规轨道] view_count 更新失败（非致命）: {e}")

        result = selected_photo.copy()
        result['is_salvaged'] = False
        return result

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
