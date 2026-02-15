# -*- coding: utf-8 -*-
"""
配置管理页面
提供系统配置功能
"""

import streamlit as st

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web')


def render_config_page():
    """渲染配置管理页面"""
    try:
        from web.modules.config_management import render_config_management
        render_config_management()
    except ImportError as e:
        st.error(f"配置管理模块加载失败: {e}")
        st.info("请确保已安装所有依赖包")


def render_cache_management_page():
    """渲染缓存管理页面"""
    try:
        from web.modules.cache_management import main as cache_main
        cache_main()
    except ImportError as e:
        st.error(f"缓存管理页面加载失败: {e}")


def render_token_statistics_page():
    """渲染Token统计页面"""
    try:
        from web.modules.token_statistics import render_token_statistics
        render_token_statistics()
    except ImportError as e:
        st.error(f"Token统计页面加载失败: {e}")
        st.info("请确保已安装所有依赖包")


def render_operation_logs_page():
    """渲染操作日志页面"""
    try:
        from web.components.operation_logs import render_operation_logs
        render_operation_logs()
    except ImportError as e:
        st.error(f"操作日志模块加载失败: {e}")
        st.info("请确保已安装所有依赖包")
