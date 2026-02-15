# -*- coding: utf-8 -*-
"""
分析结果组件 - 收藏管理
"""

import json
import logging
from .base import get_favorites_file

logger = logging.getLogger(__name__)


def load_favorites():
    """加载收藏列表"""
    favorites_file = get_favorites_file()
    if favorites_file.exists():
        try:
            with open(favorites_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载收藏列表失败: {e}")
            return []
    return []


def save_favorites(favorites):
    """保存收藏列表"""
    favorites_file = get_favorites_file()
    try:
        with open(favorites_file, "w", encoding="utf-8") as f:
            json.dump(favorites, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存收藏列表失败: {e}")
        return False


def toggle_favorite(analysis_id):
    """切换收藏状态"""
    favorites = load_favorites()
    if analysis_id in favorites:
        favorites.remove(analysis_id)
    else:
        favorites.append(analysis_id)
    save_favorites(favorites)
