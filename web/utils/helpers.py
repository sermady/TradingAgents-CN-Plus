# -*- coding: utf-8 -*-
"""
通用工具函数
提供各种辅助功能
"""

import os
import time
from typing import Optional

import streamlit as st

from tradingagents.utils.logging_manager import get_logger
from web.components.login import render_sidebar_user_info, render_sidebar_logout
from web.components.sidebar import render_sidebar

logger = get_logger("web")


def render_sidebar_navigation(user_activity_logger):
    """渲染侧边栏导航

    Args:
        user_activity_logger: 用户活动日志记录器

    Returns:
        str: 选中的页面名称
    """
    # 侧边栏布局 - 标题在最顶部
    st.sidebar.title("🤖 TradingAgents-CN")
    st.sidebar.markdown("---")

    # 页面导航 - 在标题下方显示用户信息
    render_sidebar_user_info()

    # 在用户信息和功能导航之间添加分隔线
    st.sidebar.markdown("---")

    # 添加功能切换标题
    st.sidebar.markdown("**🎯 功能导航**")

    page = st.sidebar.selectbox(
        "切换功能模块",
        [
            "📊 股票分析",
            "⚙️ 配置管理",
            "💾 缓存管理",
            "💰 Token统计",
            "📋 操作日志",
            "📈 分析结果",
            "🔧 系统状态",
        ],
        label_visibility="collapsed",
    )

    # 记录页面访问活动
    try:
        user_activity_logger.log_page_visit(
            page_name=page,
            page_params={
                "page_url": f"/app?page={page.split(' ')[1] if ' ' in page else page}",
                "page_type": "main_navigation",
                "access_method": "sidebar_selectbox",
            },
        )
    except Exception as e:
        logger.warning(f"记录页面访问活动失败: {e}")

    # 在功能选择和AI模型配置之间添加分隔线
    st.sidebar.markdown("---")

    return page


def render_sidebar_controls():
    """渲染侧边栏控制组件"""
    # 添加状态清理按钮
    st.sidebar.markdown("---")
    if st.sidebar.button(
        "🧹 清理分析状态", help="清理僵尸分析状态，解决页面持续刷新问题"
    ):
        _cleanup_analysis_state()

        st.sidebar.success("✅ 分析状态已清理")
        st.rerun()

    # 在侧边栏底部添加退出按钮
    render_sidebar_logout()


def _cleanup_analysis_state():
    """清理分析状态"""
    # 清理session state
    st.session_state.analysis_running = False
    st.session_state.current_analysis_id = None
    st.session_state.analysis_results = None

    # 清理所有自动刷新状态
    keys_to_remove = []
    for key in list(st.session_state.keys()):
        if "auto_refresh" in str(key):
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del st.session_state[key]

    # 清理死亡线程
    from web.utils.thread_tracker import cleanup_dead_analysis_threads

    cleanup_dead_analysis_threads()


def render_guide_checkbox():
    """渲染使用指南复选框

    Returns:
        bool: 是否显示使用指南
    """
    # 添加使用指南显示切换
    # 如果正在分析或有分析结果，默认隐藏使用指南
    default_show_guide = not (
        st.session_state.get("analysis_running", False)
        or st.session_state.get("analysis_results") is not None
    )

    # 如果用户没有手动设置过，使用默认值
    if "user_set_guide_preference" not in st.session_state:
        st.session_state.user_set_guide_preference = False
        st.session_state.show_guide_preference = default_show_guide

    show_guide = st.sidebar.checkbox(
        "📖 显示使用指南",
        value=st.session_state.get("show_guide_preference", default_show_guide),
        help="显示/隐藏右侧使用指南",
        key="guide_checkbox",
    )

    # 记录用户的选择
    if show_guide != st.session_state.get("show_guide_preference", default_show_guide):
        st.session_state.user_set_guide_preference = True
        st.session_state.show_guide_preference = show_guide

    return show_guide


def render_debug_mode():
    """渲染调试模式控件"""
    # 添加调试按钮（仅在调试模式下显示）
    if os.getenv("DEBUG_MODE") == "true":
        if st.button("🔄 清除会话状态"):
            st.session_state.clear()
            st.experimental_rerun()


def render_system_status_indicator():
    """渲染系统状态指示器"""
    if st.session_state.last_analysis_time:
        st.info(
            f"🕒 上次分析时间: {st.session_state.last_analysis_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )


def wait_and_rerun(seconds: int = 2):
    """等待指定秒数后重新运行

    Args:
        seconds: 等待秒数
    """
    time.sleep(seconds)
    st.rerun()


def handle_page_routing(page: str, auth_manager, require_permission):
    """处理页面路由

    Args:
        page: 页面名称
        auth_manager: 认证管理器
        require_permission: 权限检查函数

    Returns:
        bool: 是否应该继续执行后续代码
    """
    if page == "⚙️ 配置管理":
        # 检查配置权限
        if not require_permission("config"):
            return False
        from web.pages.config import render_config_page

        render_config_page()
        return False

    elif page == "💾 缓存管理":
        # 检查管理员权限
        if not require_permission("admin"):
            return False
        from web.pages.config import render_cache_management_page

        render_cache_management_page()
        return False

    elif page == "💰 Token统计":
        # 检查配置权限
        if not require_permission("config"):
            return False
        from web.pages.config import render_token_statistics_page

        render_token_statistics_page()
        return False

    elif page == "📋 操作日志":
        # 检查管理员权限
        if not require_permission("admin"):
            return False
        from web.pages.config import render_operation_logs_page

        render_operation_logs_page()
        return False

    elif page == "📈 分析结果":
        # 检查分析权限
        if not require_permission("analysis"):
            return False
        from web.pages.history import render_history_page

        render_history_page()
        return False

    elif page == "🔧 系统状态":
        # 检查管理员权限
        if not require_permission("admin"):
            return False
        from web.pages.system import render_system_page

        render_system_page()
        return False

    # 默认情况下继续执行（股票分析页面）
    return True
