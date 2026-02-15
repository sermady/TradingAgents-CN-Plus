# -*- coding: utf-8 -*-
"""
分析结果组件 - 显示函数
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from .base import safe_timestamp_to_datetime
from .favorites import toggle_favorite
from .tags import load_tags, add_tag_to_analysis, remove_tag_from_analysis

logger = logging.getLogger(__name__)

# MongoDB相关导入
try:
    from web.utils.mongodb_report_manager import MongoDBReportManager

    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False


def render_analysis_results():
    """渲染分析结果管理界面"""
    # 检查权限
    try:
        import sys
        import os

        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from utils.auth_manager import auth_manager

        if not auth_manager or not auth_manager.check_permission("analysis"):
            st.error("❌ 您没有权限访问分析结果")
            st.info("💡 提示：分析结果功能需要 'analysis' 权限")
            return
    except Exception as e:
        st.error(f"❌ 权限检查失败: {e}")
        return

    st.title("📊 分析结果历史记录")

    # 侧边栏过滤选项
    with st.sidebar:
        st.header("🔍 搜索与过滤")

        # 文本搜索
        search_text = st.text_input(
            "🔍 关键词搜索", placeholder="搜索股票代码、摘要内容..."
        )

        # 收藏过滤
        favorites_only = st.checkbox("⭐ 仅显示收藏")

        # 日期范围选择
        date_range = st.selectbox(
            "📅 时间范围",
            ["最近1天", "最近3天", "最近7天", "最近30天", "自定义"],
            index=2,
        )

        if date_range == "自定义":
            start_date = st.date_input("开始日期", datetime.now() - timedelta(days=7))
            end_date = st.date_input("结束日期", datetime.now())
        else:
            days_map = {"最近1天": 1, "最近3天": 3, "最近7天": 7, "最近30天": 30}
            days = days_map[date_range]
            end_date = datetime.now().date()
            start_date = (datetime.now() - timedelta(days=days)).date()

        # 股票代码过滤
        stock_filter = st.text_input("📈 股票代码", placeholder="如: 000001, AAPL")

        # 分析师类型过滤
        analyst_filter = st.selectbox(
            "👥 分析师类型",
            [
                "全部",
                "market_analyst",
                "social_media_analyst",
                "news_analyst",
                "fundamental_analyst",
            ],
            help="注意：社交媒体分析师仅适用于美股和港股，A股分析中不包含此类型",
        )

        if analyst_filter == "全部":
            analyst_filter = None

        # 标签过滤
        from .tags import load_tags

        all_tags = set()
        tags_data = load_tags()
        for tag_list in tags_data.values():
            all_tags.update(tag_list)

        if all_tags:
            selected_tags = st.multiselect("🏷️ 标签过滤", sorted(all_tags))
        else:
            selected_tags = []

    # 导入load_analysis_results
    from .loader import load_analysis_results

    # 加载分析结果
    results = load_analysis_results(
        start_date=start_date,
        end_date=end_date,
        stock_symbol=stock_filter if stock_filter else None,
        analyst_type=analyst_filter,
        limit=200,
        search_text=search_text if search_text else None,
        tags_filter=selected_tags if selected_tags else None,
        favorites_only=favorites_only,
    )

    if not results:
        st.warning("📭 未找到符合条件的分析结果")
        return

    # 显示统计概览
    _render_statistics(results)

    # 标签页
    tab1, tab2, tab3 = st.tabs(["📋 结果列表", "📈 统计图表", "📊 详细分析"])

    with tab1:
        render_results_list(results)

    with tab2:
        render_results_charts(results)

    with tab3:
        render_detailed_analysis(results)


def _render_statistics(results: List[Dict[str, Any]]) -> None:
    """渲染统计概览"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📊 总分析数", len(results))

    with col2:
        unique_stocks = len(
            set(result.get("stock_symbol", "unknown") for result in results)
        )
        st.metric("📈 分析股票", unique_stocks)

    with col3:
        successful_analyses = sum(
            1 for result in results if result.get("status") == "completed"
        )
        success_rate = (successful_analyses / len(results) * 100) if results else 0
        st.metric("✅ 成功率", f"{success_rate:.1f}%")

    with col4:
        favorites_count = sum(
            1 for result in results if result.get("is_favorite", False)
        )
        st.metric("⭐ 收藏数", favorites_count)


def render_results_list(results: List[Dict[str, Any]]) -> None:
    """渲染分析结果列表"""
    st.subheader("📋 分析结果列表")

    # 排序选项
    col1, col2 = st.columns([2, 1])
    with col1:
        sort_by = st.selectbox(
            "排序方式", ["时间倒序", "时间正序", "股票代码", "成功率"]
        )
    with col2:
        view_mode = st.selectbox("显示模式", ["卡片视图", "表格视图"])

    # 排序结果
    if sort_by == "时间正序":
        results.sort(key=lambda x: safe_timestamp_to_datetime(x.get("timestamp", 0)))
    elif sort_by == "股票代码":
        results.sort(key=lambda x: x.get("stock_symbol", ""))
    elif sort_by == "成功率":
        results.sort(
            key=lambda x: 1 if x.get("status") == "completed" else 0, reverse=True
        )

    if view_mode == "表格视图":
        render_results_table(results)
    else:
        render_results_cards(results)


def render_results_table(results: List[Dict[str, Any]]) -> None:
    """渲染表格视图"""
    # 准备表格数据
    table_data = []
    for result in results:
        table_data.append(
            {
                "时间": safe_timestamp_to_datetime(result.get("timestamp", 0)).strftime(
                    "%m-%d %H:%M"
                ),
                "股票": result.get("stock_symbol", "unknown"),
                "分析师": ", ".join(result.get("analysts", [])[:2])
                + ("..." if len(result.get("analysts", [])) > 2 else ""),
                "状态": "✅" if result.get("status") == "completed" else "❌",
                "收藏": "⭐" if result.get("is_favorite", False) else "",
                "标签": ", ".join(result.get("tags", [])[:2])
                + ("..." if len(result.get("tags", [])) > 2 else ""),
                "摘要": (result.get("summary", "")[:50] + "...")
                if len(result.get("summary", "")) > 50
                else result.get("summary", ""),
            }
        )

    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True)


def render_results_cards(results: List[Dict[str, Any]]) -> None:
    """渲染卡片视图"""
    # 分页设置
    page_size = st.selectbox("每页显示", [5, 10, 20, 50], index=1)
    total_pages = (len(results) + page_size - 1) // page_size

    if total_pages > 1:
        page = st.number_input("页码", min_value=1, max_value=total_pages, value=1) - 1
    else:
        page = 0

    # 获取当前页数据
    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(results))
    page_results = results[start_idx:end_idx]

    # 显示结果卡片
    for i, result in enumerate(page_results):
        _render_result_card(result, start_idx + i)
        st.divider()

    # 显示分页信息
    if total_pages > 1:
        st.info(f"第 {page + 1} 页，共 {total_pages} 页，总计 {len(results)} 条记录")


def _render_result_card(result: Dict[str, Any], index: int) -> None:
    """渲染单个结果卡片"""
    analysis_id = result.get("analysis_id", "")

    with st.container():
        # 卡片头部
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])

        with col1:
            st.markdown(f"### 📊 {result.get('stock_symbol', 'unknown')}")
            st.caption(
                f"🕐 {safe_timestamp_to_datetime(result.get('timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')}"
            )

        with col2:
            # 收藏按钮
            is_favorite = result.get("is_favorite", False)
            if st.button("⭐" if is_favorite else "☆", key=f"fav_{index}"):
                toggle_favorite(analysis_id)
                st.rerun()

        with col3:
            # 查看详情按钮
            result_id = (
                result.get("_id") or result.get("analysis_id") or f"result_{index}"
            )
            current_expanded = st.session_state.get("expanded_result_id") == result_id
            button_text = "🔼 收起" if current_expanded else "👁️ 详情"

            if st.button(button_text, key=f"view_{index}"):
                if current_expanded:
                    # 如果当前已展开，则收起
                    st.session_state["expanded_result_id"] = None
                else:
                    # 展开当前结果的详情
                    st.session_state["expanded_result_id"] = result_id
                    st.session_state["selected_result_for_detail"] = result
                st.rerun()

        with col4:
            # 状态显示
            status_icon = "✅" if result.get("status") == "completed" else "❌"
            st.markdown(f"**状态**: {status_icon}")

        # 卡片内容
        col1, col2 = st.columns([2, 1])

        with col1:
            st.write(f"**分析师**: {', '.join(result.get('analysts', []))}")
            st.write(f"**研究深度**: {result.get('research_depth', 'unknown')}")

            # 显示分析摘要
            if result.get("summary"):
                summary = (
                    result["summary"][:150] + "..."
                    if len(result["summary"]) > 150
                    else result["summary"]
                )
                st.write(f"**摘要**: {summary}")

        with col2:
            # 显示标签
            tags = result.get("tags", [])
            if tags:
                st.write("**标签**:")
                for tag in tags[:3]:  # 最多显示3个标签
                    st.markdown(f"`{tag}`")
                if len(tags) > 3:
                    st.caption(f"还有 {len(tags) - 3} 个标签...")

        # 显示折叠详情
        result_id = result.get("_id") or result.get("analysis_id") or f"result_{index}"
        if st.session_state.get("expanded_result_id") == result_id:
            show_expanded_detail(result)


def show_expanded_detail(result: Dict[str, Any]) -> None:
    """显示展开的详情内容"""
    # 创建详情容器
    with st.container():
        st.markdown("---")
        st.markdown("### 📊 详细分析报告")

        # 检查是否有报告数据
        if "reports" not in result or not result["reports"]:
            _show_fallback_detail(result)
            return

        # 获取报告数据
        reports = result["reports"]

        # 为报告名称添加中文标题和图标
        report_display_names = {
            "final_trade_decision": "🎯 最终交易决策",
            "fundamentals_report": "💰 基本面分析",
            "technical_report": "📈 技术面分析",
            "market_sentiment_report": "💭 市场情绪分析",
            "risk_assessment_report": "⚠️ 风险评估",
            "price_target_report": "🎯 目标价格分析",
            "summary_report": "📋 分析摘要",
            "news_analysis_report": "📰 新闻分析",
            "news_report": "📰 新闻分析",
            "market_report": "📈 市场分析",
            "social_media_report": "📱 社交媒体分析",
            "bull_state": "🐂 多头观点",
            "bear_state": "🐻 空头观点",
            "trader_state": "💼 交易员分析",
            "invest_judge_state": "⚖️ 投资判断",
            "research_team_state": "🔬 研究团队观点",
            "risk_debate_state": "⚠️ 风险管理讨论",
            "research_team_decision": "🔬 研究团队决策",
            "risk_management_decision": "🛡️ 风险管理决策",
            "investment_plan": "📋 投资计划",
            "trader_investment_plan": "💼 交易员投资计划",
            "investment_debate_state": "💬 投资讨论状态",
        }

        # 创建标签页显示不同的报告
        report_tabs = list(reports.keys())
        tab_names = [
            report_display_names.get(
                report_key, f"📄 {report_key.replace('_', ' ').title()}"
            )
            for report_key in report_tabs
        ]

        if len(tab_names) == 1:
            # 只有一个报告，直接显示内容
            report_content = reports[report_tabs[0]]
            if not report_content.strip().startswith("#"):
                st.markdown(f"### {tab_names[0]}")
                st.markdown("---")
            st.markdown(report_content)
        else:
            # 多个报告，使用标签页
            tabs = st.tabs(tab_names)

            for tab, report_key in zip(tabs, report_tabs):
                with tab:
                    st.markdown(reports[report_key])

        st.markdown("---")


def _show_fallback_detail(result: Dict[str, Any]) -> None:
    """显示备用详情（当没有reports字段时）"""
    # 如果没有reports字段，检查是否有其他分析数据
    if result.get("summary"):
        st.subheader("📝 分析摘要")
        st.markdown(result["summary"])

    # 检查是否有full_data中的报告
    if "full_data" in result and result["full_data"]:
        full_data = result["full_data"]
        if isinstance(full_data, dict):
            # 显示full_data中的分析内容
            analysis_fields = [
                ("market_report", "📈 市场分析"),
                ("fundamentals_report", "💰 基本面分析"),
                ("sentiment_report", "💭 情感分析"),
                ("news_report", "📰 新闻分析"),
                ("risk_assessment", "⚠️ 风险评估"),
                ("investment_plan", "📋 投资建议"),
                ("final_trade_decision", "🎯 最终决策"),
            ]

            available_reports = []
            for field_key, field_name in analysis_fields:
                if field_key in full_data and full_data[field_key]:
                    available_reports.append(
                        (field_key, field_name, full_data[field_key])
                    )

            if available_reports:
                # 创建标签页显示分析内容
                tab_names = [name for _, name, _ in available_reports]
                tabs = st.tabs(tab_names)

                for tab, (field_key, field_name, content) in zip(
                    tabs, available_reports
                ):
                    with tab:
                        if isinstance(content, str):
                            st.markdown(content)
                        elif isinstance(content, dict):
                            for key, value in content.items():
                                if value:
                                    st.subheader(key.replace("_", " ").title())
                                    st.markdown(str(value))
                        else:
                            st.write(content)
            else:
                st.info("暂无详细分析报告")
        else:
            st.info("暂无详细分析报告")
    else:
        st.info("暂无详细分析报告")


def render_results_charts(results: List[Dict[str, Any]]) -> None:
    """渲染分析结果统计图表"""
    st.subheader("📈 统计图表")

    # 按股票统计
    _render_stock_chart(results)

    # 按时间统计
    _render_daily_trend(results)

    # 按分析师类型统计
    _render_analyst_distribution(results)

    # 成功率统计
    _render_success_rate(results)

    # 标签使用统计
    _render_tag_statistics(results)


def _render_stock_chart(results: List[Dict[str, Any]]) -> None:
    """渲染股票统计图表"""
    st.subheader("📊 按股票统计")
    stock_counts = {}
    for result in results:
        stock = result.get("stock_symbol", "unknown")
        stock_counts[stock] = stock_counts.get(stock, 0) + 1

    if stock_counts:
        # 只显示前10个最常分析的股票
        top_stocks = sorted(stock_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        stocks = [item[0] for item in top_stocks]
        counts = [item[1] for item in top_stocks]

        fig_bar = px.bar(
            x=stocks,
            y=counts,
            title="最常分析的股票 (前10名)",
            labels={"x": "股票代码", "y": "分析次数"},
            color=counts,
            color_continuous_scale="viridis",
        )
        st.plotly_chart(fig_bar, use_container_width=True)


def _render_daily_trend(results: List[Dict[str, Any]]) -> None:
    """渲染每日分析趋势"""
    st.subheader("📅 每日分析趋势")
    daily_results = {}
    for result in results:
        date_str = safe_timestamp_to_datetime(result.get("timestamp", 0)).strftime(
            "%Y-%m-%d"
        )
        daily_results[date_str] = daily_results.get(date_str, 0) + 1

    if daily_results:
        dates = sorted(daily_results.keys())
        counts = [daily_results[date] for date in dates]

        fig_line = go.Figure()
        fig_line.add_trace(
            go.Scatter(
                x=dates,
                y=counts,
                mode="lines+markers",
                name="每日分析数",
                line=dict(color="#2E8B57", width=3),
                marker=dict(size=8, color="#FF6B6B"),
                fill="tonexty",
            )
        )
        fig_line.update_layout(
            title="每日分析趋势",
            xaxis_title="日期",
            yaxis_title="分析数量",
            hovermode="x unified",
        )
        st.plotly_chart(fig_line, use_container_width=True)


def _render_analyst_distribution(results: List[Dict[str, Any]]) -> None:
    """渲染分析师使用分布"""
    st.subheader("👥 分析师使用分布")
    analyst_counts = {}
    for result in results:
        analysts = result.get("analysts", [])
        for analyst in analysts:
            analyst_counts[analyst] = analyst_counts.get(analyst, 0) + 1

    if analyst_counts:
        fig_pie = px.pie(
            values=list(analyst_counts.values()),
            names=list(analyst_counts.keys()),
            title="分析师使用分布",
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        st.plotly_chart(fig_pie, use_container_width=True)


def _render_success_rate(results: List[Dict[str, Any]]) -> None:
    """渲染成功率统计"""
    st.subheader("✅ 分析成功率统计")
    success_data = {"成功": 0, "失败": 0}
    for result in results:
        if result.get("status") == "completed":
            success_data["成功"] += 1
        else:
            success_data["失败"] += 1

    if success_data["成功"] + success_data["失败"] > 0:
        fig_success = px.pie(
            values=list(success_data.values()),
            names=list(success_data.keys()),
            title="分析成功率",
            color_discrete_map={"成功": "#4CAF50", "失败": "#F44336"},
        )
        st.plotly_chart(fig_success, use_container_width=True)


def _render_tag_statistics(results: List[Dict[str, Any]]) -> None:
    """渲染标签使用统计"""
    tags_data = load_tags()
    if tags_data:
        st.subheader("🏷️ 标签使用统计")
        tag_counts = {}
        for tag_list in tags_data.values():
            for tag in tag_list:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        if tag_counts:
            # 只显示前10个最常用的标签
            top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            tags = [item[0] for item in top_tags]
            counts = [item[1] for item in top_tags]

            fig_tags = px.bar(
                x=tags,
                y=counts,
                title="最常用标签 (前10名)",
                labels={"x": "标签", "y": "使用次数"},
                color=counts,
                color_continuous_scale="plasma",
            )
            fig_tags.update_layout(xaxis_tickangle=-45)
            st.plotly_chart(fig_tags, use_container_width=True)


def render_detailed_analysis(results: List[Dict[str, Any]]) -> None:
    """渲染详细分析"""
    st.subheader("📊 详细分析")

    if not results:
        st.info("没有可分析的数据")
        return

    # 选择要查看的分析结果
    result_options = []
    for i, result in enumerate(results[:50]):  # 显示前50个
        option = f"{result.get('stock_symbol', 'unknown')} - {safe_timestamp_to_datetime(result.get('timestamp', 0)).strftime('%m-%d %H:%M')}"
        result_options.append((option, i))

    if result_options:
        selected_option = st.selectbox(
            "选择分析结果", result_options, format_func=lambda x: x[0]
        )
        if selected_option and selected_option[1] is not None:
            selected_result = results[selected_option[1]]
        else:
            selected_result = None

        if not selected_result:
            st.warning("无法获取选中的分析结果")
            return

        # 显示基本信息
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("股票代码", selected_result.get("stock_symbol", "unknown"))
            st.metric("分析师数量", len(selected_result.get("analysts", [])))

        with col2:
            analysis_time = safe_timestamp_to_datetime(
                selected_result.get("timestamp", 0)
            )
            st.metric("分析时间", analysis_time.strftime("%m-%d %H:%M"))
            status = (
                "✅ 完成" if selected_result.get("status") == "completed" else "❌ 失败"
            )
            st.metric("状态", status)

        with col3:
            st.metric("研究深度", selected_result.get("research_depth", "unknown"))
            tags = selected_result.get("tags", [])
            st.metric("标签数量", len(tags))

        # 显示标签
        if tags:
            st.write("**标签**:")
            tag_cols = st.columns(min(len(tags), 5))
            for i, tag in enumerate(tags):
                with tag_cols[i % 5]:
                    st.markdown(f"`{tag}`")

        # 显示分析摘要
        if selected_result.get("summary"):
            st.subheader("📝 分析摘要")
            st.markdown(selected_result["summary"])

        # 显示性能指标
        performance = selected_result.get("performance", {})
        if performance:
            st.subheader("⚡ 性能指标")
            perf_cols = st.columns(len(performance))
            for i, (key, value) in enumerate(performance.items()):
                with perf_cols[i]:
                    st.metric(
                        key.replace("_", " ").title(),
                        f"{value:.2f}"
                        if isinstance(value, (int, float))
                        else str(value),
                    )

        # 显示完整分析结果
        if st.checkbox("显示完整分析结果"):
            render_detailed_analysis_content(selected_result)


def render_detailed_analysis_content(selected_result: Dict[str, Any]) -> None:
    """渲染详细分析结果内容"""
    st.subheader("📊 完整分析数据")

    # 检查是否有报告数据（支持文件系统和MongoDB）
    if "reports" in selected_result and selected_result["reports"]:
        # 显示文件系统中的报告
        reports = selected_result["reports"]

        if not reports:
            st.warning("该分析结果没有可用的报告内容")
            return

        # 调试信息：显示所有可用的报告
        print(f"🔍 [弹窗调试] 数据来源: {selected_result.get('source', '未知')}")
        print(f"🔍 [弹窗调试] 可用报告数量: {len(reports)}")
        print(f"🔍 [弹窗调试] 报告类型: {list(reports.keys())}")

        # 创建标签页显示不同的报告
        report_tabs = list(reports.keys())

        # 为报告名称添加中文标题和图标
        report_display_names = {
            "final_trade_decision": "🎯 最终交易决策",
            "fundamentals_report": "💰 基本面分析",
            "technical_report": "📈 技术面分析",
            "market_sentiment_report": "💭 市场情绪分析",
            "risk_assessment_report": "⚠️ 风险评估",
            "price_target_report": "🎯 目标价格分析",
            "summary_report": "📋 分析摘要",
            "news_analysis_report": "📰 新闻分析",
            "social_media_report": "📱 社交媒体分析",
        }

        # 创建显示名称列表
        tab_names = []
        for report_key in report_tabs:
            display_name = report_display_names.get(
                report_key, f"📄 {report_key.replace('_', ' ').title()}"
            )
            tab_names.append(display_name)
            print(f"🔍 [弹窗调试] 添加标签: {display_name}")

        print(f"🔍 [弹窗调试] 总标签数: {len(tab_names)}")

        if len(tab_names) == 1:
            # 只有一个报告，直接显示
            st.markdown(f"### {tab_names[0]}")
            st.markdown("---")
            st.markdown(reports[report_tabs[0]])
        else:
            # 多个报告，使用标签页
            tabs = st.tabs(tab_names)

            for tab, report_key in zip(tabs, report_tabs):
                with tab:
                    st.markdown(reports[report_key])

        return

    # 添加自定义CSS样式美化标签页
    st.markdown(
        """
    <style>
    /* 标签页容器样式 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8f9fa;
        padding: 8px;
        border-radius: 10px;
        margin-bottom: 20px;
    }

    /* 单个标签页样式 */
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding: 8px 16px;
        background-color: #ffffff;
        border-radius: 8px;
        border: 1px solid #e1e5e9;
        color: #495057;
        font-weight: 500;
        transition: all 0.3s ease;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }

    /* 标签页悬停效果 */
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #e3f2fd;
        border-color: #2196f3;
        transform: translateY(-1px);
        box-shadow: 0 2px 8px rgba(33,150,243,0.2);
    }

    /* 选中的标签页样式 */
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        border-color: #667eea !important;
        box-shadow: 0 4px 12px rgba(102,126,234,0.3) !important;
        transform: translateY(-2px);
    }

    /* 标签页内容区域 */
    .stTabs [data-baseweb="tab-panel"] {
        padding: 20px;
        background-color: #ffffff;
        border-radius: 10px;
        border: 1px solid #e1e5e9;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    /* 标签页文字样式 */
    .stTabs [data-baseweb="tab"] p {
        margin: 0;
        font-size: 14px;
        font-weight: 600;
    }

    /* 选中标签页的文字样式 */
    .stTabs [aria-selected="true"] p {
        color: white !important;
        text-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # 定义分析模块
    analysis_modules = [
        {
            "key": "market_report",
            "title": "📈 市场技术分析",
            "icon": "📈",
            "description": "技术指标、价格趋势、支撑阻力位分析",
        },
        {
            "key": "fundamentals_report",
            "title": "💰 基本面分析",
            "icon": "💰",
            "description": "财务数据、估值水平、盈利能力分析",
        },
        {
            "key": "sentiment_report",
            "title": "💭 市场情绪分析",
            "icon": "💭",
            "description": "投资者情绪、社交媒体情绪指标",
        },
        {
            "key": "news_report",
            "title": "📰 新闻事件分析",
            "icon": "📰",
            "description": "相关新闻事件、市场动态影响分析",
        },
        {
            "key": "risk_assessment",
            "title": "⚠️ 风险评估",
            "icon": "⚠️",
            "description": "风险因素识别、风险等级评估",
        },
        {
            "key": "investment_plan",
            "title": "📋 投资建议",
            "icon": "📋",
            "description": "具体投资策略、仓位管理建议",
        },
        {
            "key": "investment_debate_state",
            "title": "🔬 研究团队决策",
            "icon": "🔬",
            "description": "多头/空头研究员辩论分析，研究经理综合决策",
        },
        {
            "key": "trader_investment_plan",
            "title": "💼 交易团队计划",
            "icon": "💼",
            "description": "专业交易员制定的具体交易执行计划",
        },
        {
            "key": "risk_debate_state",
            "title": "⚖️ 风险管理团队",
            "icon": "⚖️",
            "description": "激进/保守/中性分析师风险评估，投资组合经理最终决策",
        },
        {
            "key": "final_trade_decision",
            "title": "🎯 最终交易决策",
            "icon": "🎯",
            "description": "综合所有团队分析后的最终投资决策",
        },
    ]

    # 过滤出有数据的模块
    available_modules = []
    for module in analysis_modules:
        if module["key"] in selected_result and selected_result[module["key"]]:
            # 检查字典类型的数据是否有实际内容
            if isinstance(selected_result[module["key"]], dict):
                # 对于字典，检查是否有非空的值
                has_content = any(
                    v for v in selected_result[module["key"]].values() if v
                )
                if has_content:
                    available_modules.append(module)
            else:
                # 对于字符串或其他类型，直接添加
                available_modules.append(module)

    if not available_modules:
        # 如果没有预定义模块的数据，显示所有可用的分析数据
        st.info("📊 显示完整分析报告数据")

        # 排除一些基础字段，只显示分析相关的数据
        excluded_keys = {
            "analysis_id",
            "timestamp",
            "stock_symbol",
            "analysts",
            "research_depth",
            "status",
            "summary",
            "performance",
            "is_favorite",
            "tags",
            "full_data",
        }

        # 获取所有分析相关的数据
        analysis_data = {}
        for key, value in selected_result.items():
            if key not in excluded_keys and value:
                analysis_data[key] = value

        # 如果有full_data字段，优先使用它
        if "full_data" in selected_result and selected_result["full_data"]:
            full_data = selected_result["full_data"]
            if isinstance(full_data, dict):
                for key, value in full_data.items():
                    if key not in excluded_keys and value:
                        analysis_data[key] = value

        if analysis_data:
            # 创建动态标签页显示所有分析数据
            tab_names = []
            tab_data = []

            for key, value in analysis_data.items():
                # 格式化标签页名称
                tab_name = key.replace("_", " ").title()
                if "report" in key.lower():
                    tab_name = f"📊 {tab_name}"
                elif "analysis" in key.lower():
                    tab_name = f"🔍 {tab_name}"
                elif "decision" in key.lower():
                    tab_name = f"🎯 {tab_name}"
                elif "plan" in key.lower():
                    tab_name = f"📋 {tab_name}"
                else:
                    tab_name = f"📄 {tab_name}"

                tab_names.append(tab_name)
                tab_data.append((key, value))

            # 创建标签页
            tabs = st.tabs(tab_names)

            for tab, (key, value) in zip(tabs, tab_data):
                with tab:
                    st.markdown(f"## {tab_name}")
                    st.markdown("---")

                    # 根据数据类型显示内容
                    if isinstance(value, str):
                        # 如果是长文本，使用markdown显示
                        if len(value) > 100:
                            st.markdown(value)
                        else:
                            st.write(value)
                    elif isinstance(value, dict):
                        # 字典类型，递归显示
                        for sub_key, sub_value in value.items():
                            if sub_value:
                                st.subheader(sub_key.replace("_", " ").title())
                                if isinstance(sub_value, str):
                                    st.markdown(sub_value)
                                else:
                                    st.write(sub_value)
                    elif isinstance(value, list):
                        # 列表类型
                        for idx, item in enumerate(value):
                            st.subheader(f"项目 {idx + 1}")
                            if isinstance(item, str):
                                st.markdown(item)
                            else:
                                st.write(item)
                    else:
                        # 其他类型直接显示
                        st.write(value)
        else:
            # 如果真的没有任何分析数据，显示原始JSON
            st.warning("📊 该分析结果暂无详细报告数据")
            with st.expander("查看原始数据"):
                st.json(selected_result)
        return

    # 只为有数据的模块创建标签页
    tabs = st.tabs([module["title"] for module in available_modules])

    for tab, module in zip(tabs, available_modules):
        with tab:
            # 在内容区域显示图标和描述
            st.markdown(f"## {module['icon']} {module['title']}")
            st.markdown(f"*{module['description']}*")
            st.markdown("---")

            # 格式化显示内容
            content = selected_result[module["key"]]
            if isinstance(content, str):
                st.markdown(content)
            elif isinstance(content, dict):
                # 特殊处理团队决策报告的字典结构
                if module["key"] == "investment_debate_state":
                    _render_investment_debate_content(content)
                elif module["key"] == "risk_debate_state":
                    _render_risk_debate_content(content)
                else:
                    # 普通字典格式化显示
                    for key, value in content.items():
                        if value:  # 只显示非空值
                            st.subheader(key.replace("_", " ").title())
                            if isinstance(value, str):
                                st.markdown(value)
                            else:
                                st.write(value)
            else:
                st.write(content)


def _render_investment_debate_content(content: Dict[str, Any]) -> None:
    """渲染投资辩论内容"""
    if "bull_analyst_report" in content and content["bull_analyst_report"]:
        st.subheader("🐂 多头分析师观点")
        st.markdown(content["bull_analyst_report"])

    if "bear_analyst_report" in content and content["bear_analyst_report"]:
        st.subheader("🐻 空头分析师观点")
        st.markdown(content["bear_analyst_report"])

    if "research_manager_decision" in content and content["research_manager_decision"]:
        st.subheader("👨‍💼 研究经理决策")
        st.markdown(content["research_manager_decision"])


def _render_risk_debate_content(content: Dict[str, Any]) -> None:
    """渲染风险辩论内容"""
    if "aggressive_analyst_report" in content and content["aggressive_analyst_report"]:
        st.subheader("🔥 激进分析师观点")
        st.markdown(content["aggressive_analyst_report"])

    if (
        "conservative_analyst_report" in content
        and content["conservative_analyst_report"]
    ):
        st.subheader("🛡️ 保守分析师观点")
        st.markdown(content["conservative_analyst_report"])

    if "neutral_analyst_report" in content and content["neutral_analyst_report"]:
        st.subheader("⚖️ 中性分析师观点")
        st.markdown(content["neutral_analyst_report"])

    if (
        "portfolio_manager_decision" in content
        and content["portfolio_manager_decision"]
    ):
        st.subheader("👨‍💼 投资组合经理决策")
        st.markdown(content["portfolio_manager_decision"])


def save_analysis_result(
    analysis_id: str,
    stock_symbol: str,
    analysts: List[str],
    research_depth: int,
    result_data: Dict,
    status: str = "completed",
) -> bool:
    """保存分析结果"""
    try:
        from web.utils.async_progress_tracker import safe_serialize
        from .base import get_analysis_results_dir

        # 创建结果条目，使用安全序列化
        result_entry = {
            "analysis_id": analysis_id,
            "timestamp": datetime.now().timestamp(),
            "stock_symbol": stock_symbol,
            "analysts": analysts,
            "research_depth": research_depth,
            "status": status,
            "summary": safe_serialize(result_data.get("summary", "")),
            "performance": safe_serialize(result_data.get("performance", {})),
            "full_data": safe_serialize(result_data),
        }

        # 1. 保存到文件系统（保持兼容性）
        results_dir = get_analysis_results_dir()
        result_file = results_dir / f"analysis_{analysis_id}.json"

        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result_entry, f, ensure_ascii=False, indent=2)

        # 2. 保存到MongoDB（如果可用）
        if MONGODB_AVAILABLE:
            _save_to_mongodb(result_entry, stock_symbol, analysis_id)

        return True

    except Exception as e:
        print(f"❌ [保存分析结果] 保存失败: {e}")
        logger.error(f"保存分析结果异常: {e}")
        return False


def _save_to_mongodb(
    result_entry: Dict[str, Any], stock_symbol: str, analysis_id: str
) -> None:
    """保存到MongoDB"""
    try:
        print(f"💾 [MongoDB保存] 开始保存分析结果: {analysis_id}")
        mongodb_manager = MongoDBReportManager()

        # 使用标准的save_analysis_report方法，确保数据结构一致
        analysis_results = {
            "stock_symbol": result_entry.get("stock_symbol", ""),
            "analysts": result_entry.get("analysts", []),
            "research_depth": result_entry.get("research_depth", 1),
            "summary": result_entry.get("summary", ""),
            "model_info": result_entry.get("model_info", "Unknown"),
        }

        # 尝试从文件系统读取报告内容
        reports = _read_reports_from_filesystem(stock_symbol)

        # 使用标准保存方法，确保字段结构一致
        success = mongodb_manager.save_analysis_report(
            stock_symbol=result_entry.get("stock_symbol", ""),
            analysis_results=analysis_results,
            reports=reports,
        )

        if success:
            print(
                f"✅ [MongoDB保存] 分析结果已保存到MongoDB: {analysis_id} (包含 {len(reports)} 个报告)"
            )
        else:
            print(f"❌ [MongoDB保存] 保存失败: {analysis_id}")

    except Exception as e:
        print(f"❌ [MongoDB保存] 保存异常: {e}")
        logger.error(f"MongoDB保存异常: {e}")


def _read_reports_from_filesystem(stock_symbol: str) -> Dict[str, str]:
    """从文件系统读取报告"""
    from pathlib import Path
    import os

    reports = {}
    try:
        # 获取当前日期
        current_date = datetime.now().strftime("%Y-%m-%d")

        # 构建报告路径
        project_root = Path(__file__).parent.parent.parent.parent
        reports_dir = (
            project_root
            / "data"
            / "analysis_results"
            / stock_symbol
            / current_date
            / "reports"
        )

        # 确保路径在Windows上正确显示（避免双反斜杠）
        reports_dir_str = os.path.normpath(str(reports_dir))
        print(f"🔍 [MongoDB保存] 查找报告目录: {reports_dir_str}")

        if reports_dir.exists():
            # 读取所有报告文件
            for report_file in reports_dir.glob("*.md"):
                try:
                    with open(report_file, "r", encoding="utf-8") as f:
                        content = f.read()
                        report_name = report_file.stem
                        reports[report_name] = content
                        print(
                            f"✅ [MongoDB保存] 读取报告: {report_name} ({len(content)} 字符)"
                        )
                except Exception as e:
                    print(f"⚠️ [MongoDB保存] 读取报告文件失败 {report_file}: {e}")

            print(f"📊 [MongoDB保存] 共读取 {len(reports)} 个报告文件")
        else:
            print(f"⚠️ [MongoDB保存] 报告目录不存在: {reports_dir_str}")

    except Exception as e:
        print(f"⚠️ [MongoDB保存] 读取报告文件异常: {e}")

    return reports
