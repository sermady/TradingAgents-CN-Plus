# -*- coding: utf-8 -*-
"""
历史记录页面
显示分析历史记录和操作日志
"""

import streamlit as st

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web')


def render_history_page():
    """渲染历史记录页面"""
    try:
        from web.components.analysis_results import render_analysis_results
        render_analysis_results()
    except ImportError as e:
        st.error(f"分析结果模块加载失败: {e}")
        st.info("请确保已安装所有依赖包")
