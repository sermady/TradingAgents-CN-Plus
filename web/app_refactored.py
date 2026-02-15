# -*- coding: utf-8 -*-
"""
TradingAgents-CN Streamlit Web界面 (重构版)
基于Streamlit的股票分析Web应用程序

拆分后的模块化结构：
- core/config.py: Streamlit配置和CSS样式
- core/session.py: 会话状态管理
- pages/analysis.py: 股票分析页面
- pages/config.py: 配置管理页面
- pages/history.py: 历史记录页面
- pages/system.py: 系统状态页面
- utils/helpers.py: 通用工具函数
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入日志模块
try:
    from tradingagents.utils.logging_manager import get_logger
    logger = get_logger('web')
except ImportError:
    # 如果无法导入，使用标准logging
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger('web')

# 加载环境变量
load_dotenv(project_root / ".env", override=True)

# 导入核心模块
from web.core.config import setup_page_config, get_custom_css, get_sidebar_css
from web.core.session import initialize_session_state, check_frontend_auth_cache
from web.utils.auth_manager import auth_manager
from web.utils.helpers import (
    render_sidebar_navigation,
    render_sidebar_controls,
    render_guide_checkbox,
    handle_page_routing
)
from web.utils.user_activity_logger import user_activity_logger
from web.components.header import render_header
from web.components.login import render_login_form, require_permission

# 导入页面模块
from web.pages.analysis import check_api_keys_status, render_api_keys_warning, render_analysis_page


def main():
    """主应用程序"""
    # 1. 设置页面配置
    setup_page_config()

    # 2. 应用自定义CSS样式
    st.markdown(get_custom_css(), unsafe_allow_html=True)

    # 3. 初始化会话状态
    initialize_session_state()

    # 4. 检查前端缓存恢复
    check_frontend_auth_cache()

    # 5. 检查用户认证状态
    if not auth_manager.is_authenticated():
        # 最后一次尝试从session state恢复认证状态
        if (st.session_state.get('authenticated', False) and
            st.session_state.get('user_info') and
            st.session_state.get('login_time')):
            logger.info("🔄 从session state恢复认证状态")
            try:
                auth_manager.login_user(
                    st.session_state.user_info,
                    st.session_state.login_time
                )
                logger.info(f"✅ 成功从session state恢复用户 {st.session_state.user_info.get('username', 'Unknown')} 的认证状态")
            except Exception as e:
                logger.warning(f"⚠️ 从session state恢复认证状态失败: {e}")

        # 如果仍然未认证，显示登录页面
        if not auth_manager.is_authenticated():
            render_login_form()
            return

    # 6. 应用侧边栏CSS样式
    st.markdown(get_sidebar_css(), unsafe_allow_html=True)

    # 7. 渲染页面头部
    render_header()

    # 8. 渲染侧边栏导航
    page = render_sidebar_navigation(user_activity_logger)

    # 9. 处理页面路由
    if not handle_page_routing(page, auth_manager, require_permission):
        return

    # 10. 默认显示股票分析页面
    # 检查分析权限
    if not require_permission("analysis"):
        return

    # 检查API密钥
    api_status = check_api_keys_status()

    if not api_status['all_configured']:
        render_api_keys_warning(api_status)
        return

    # 渲染侧边栏控制组件
    render_sidebar_controls()

    # 渲染使用指南复选框
    show_guide = render_guide_checkbox()

    # 渲染分析页面
    render_analysis_page(show_guide=show_guide)


# 导入streamlit (必须在导入后使用)
import streamlit as st


if __name__ == "__main__":
    main()
