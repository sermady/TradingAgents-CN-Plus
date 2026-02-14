# -*- coding: utf-8 -*-
"""
分析结果管理组件 - Facade模式
提供股票分析历史结果的查看和管理功能

此文件作为facade，将所有实现委托给子模块
"""

# 导入所有公共API并重新导出
from web.components.analysis import (
    # 基础函数和常量
    safe_timestamp_to_datetime,
    get_analysis_results_dir,
    get_favorites_file,
    get_tags_file,
    # 收藏管理
    load_favorites,
    save_favorites,
    toggle_favorite,
    # 标签管理
    load_tags,
    save_tags,
    add_tag_to_analysis,
    remove_tag_from_analysis,
    get_analysis_tags,
    # 数据加载
    load_analysis_results,
    # 显示函数
    render_analysis_results,
    render_results_list,
    render_results_table,
    render_results_cards,
    render_results_charts,
    render_detailed_analysis,
    render_detailed_analysis_content,
    save_analysis_result,
    show_expanded_detail,
)

# 为了保持向后兼容，也导出所有公共API
__all__ = [
    # 基础
    "safe_timestamp_to_datetime",
    "get_analysis_results_dir",
    "get_favorites_file",
    "get_tags_file",
    # 收藏
    "load_favorites",
    "save_favorites",
    "toggle_favorite",
    # 标签
    "load_tags",
    "save_tags",
    "add_tag_to_analysis",
    "remove_tag_from_analysis",
    "get_analysis_tags",
    # 加载
    "load_analysis_results",
    # 显示
    "render_analysis_results",
    "render_results_list",
    "render_results_table",
    "render_results_cards",
    "render_results_charts",
    "render_detailed_analysis",
    "render_detailed_analysis_content",
    "save_analysis_result",
    "show_expanded_detail",
]
