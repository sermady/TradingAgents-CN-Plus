# -*- coding: utf-8 -*-
"""
系统状态页面
显示系统运行状态和同步任务状态
"""

import os

import streamlit as st
import requests

from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web')


def render_system_page():
    """渲染系统状态页面"""
    st.header("🔧 系统状态")

    # 展示股票基础信息同步状态
    backend_url = os.getenv('WEBAPI_BASE_URL', 'http://localhost:8000')
    try:
        resp = requests.get(f"{backend_url}/api/sync/stock_basics/status", timeout=5)
        if resp.ok:
            data = resp.json().get('data', {})
            st.subheader("📦 股票基础信息同步状态")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("状态", data.get('status', 'unknown'))
            with col2:
                st.metric("总处理", data.get('total', 0))
            with col3:
                st.metric("错误数", data.get('errors', 0))

            st.write("- 开始时间:", data.get('started_at', ''))
            st.write("- 结束时间:", data.get('finished_at', ''))
            st.write("- 交易日期:", data.get('last_trade_date', ''))

            # 手动触发按钮
            if st.button("🔄 手动运行全量同步"):
                with st.spinner("正在触发后端同步..."):
                    try:
                        run_resp = requests.post(f"{backend_url}/api/sync/stock_basics/run", timeout=10)
                        if run_resp.ok:
                            st.success("已触发同步任务，请稍后刷新查看状态")
                        else:
                            st.error(f"触发失败: {run_resp.status_code} {run_resp.text}")
                    except Exception as e:
                        st.error(f"触发异常: {e}")
        else:
            st.warning(f"无法获取同步状态: {resp.status_code}")
    except Exception as e:
        st.warning(f"同步状态查询失败: {e}")
