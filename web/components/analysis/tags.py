# -*- coding: utf-8 -*-
"""
分析结果组件 - 标签管理
"""

import json
import logging
from .base import get_tags_file

logger = logging.getLogger(__name__)


def load_tags():
    """加载标签数据"""
    tags_file = get_tags_file()
    if tags_file.exists():
        try:
            with open(tags_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载标签数据失败: {e}")
            return {}
    return {}


def save_tags(tags):
    """保存标签数据"""
    tags_file = get_tags_file()
    try:
        with open(tags_file, "w", encoding="utf-8") as f:
            json.dump(tags, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存标签数据失败: {e}")
        return False


def add_tag_to_analysis(analysis_id, tag):
    """为分析结果添加标签"""
    tags = load_tags()
    if analysis_id not in tags:
        tags[analysis_id] = []
    if tag not in tags[analysis_id]:
        tags[analysis_id].append(tag)
        save_tags(tags)


def remove_tag_from_analysis(analysis_id, tag):
    """从分析结果移除标签"""
    tags = load_tags()
    if analysis_id in tags and tag in tags[analysis_id]:
        tags[analysis_id].remove(tag)
        if not tags[analysis_id]:  # 如果没有标签了，删除该条目
            del tags[analysis_id]
        save_tags(tags)


def get_analysis_tags(analysis_id):
    """获取分析结果的标签"""
    tags = load_tags()
    return tags.get(analysis_id, [])
