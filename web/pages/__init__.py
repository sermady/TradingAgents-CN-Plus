# -*- coding: utf-8 -*-
"""
Web页面模块
提供各种功能页面的渲染函数
"""

from .analysis import render_analysis_page
from .config import render_config_page
from .history import render_history_page
from .system import render_system_page

__all__ = [
    'render_analysis_page',
    'render_config_page',
    'render_history_page',
    'render_system_page',
]
