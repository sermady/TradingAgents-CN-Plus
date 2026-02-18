# -*- coding: utf-8 -*-
"""
分析结果显示组件
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime

# 导入导出功能
from ..utils.report_exporter import render_export_buttons

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('web')

def render_results(results):
    """渲染分析结果"""

    if not results:
        st.warning("暂无分析结果")
        return

    # 添加CSS确保结果内容不被右侧遮挡
    st.markdown("""
    <style>
    /* 确保分析结果内容有足够的右边距 */
    .element-container, .stMarkdown, .stExpander {
        margin-right: 1.5rem !important;
        padding-right: 0.5rem !important;
    }

    /* 特别处理展开组件 */
    .streamlit-expanderHeader {
        margin-right: 1rem !important;
    }

    /* 确保文本内容不被截断 */
    .stMarkdown p, .stMarkdown div {
        word-wrap: break-word !important;
        overflow-wrap: break-word !important;
    }
    </style>
    """, unsafe_allow_html=True)

    stock_symbol = results.get('stock_symbol', 'N/A')
    decision = results.get('decision', {})
    state = results.get('state', {})
    success = results.get('success', False)
    error = results.get('error')

    st.markdown("---")
    st.header(f"📊 {stock_symbol} 分析结果")

    # 如果分析失败，显示错误信息
    if not success and error:
        st.error(f"❌ **分析失败**: {error}")
        st.info("💡 **解决方案**: 请检查API密钥配置，确保网络连接正常，然后重新运行分析。")
        return

    # 投资决策摘要
    render_decision_summary(decision, stock_symbol)

    # 分析配置信息
    render_analysis_info(results)

    # 详细分析报告
    render_detailed_analysis(state)

    # 风险提示
    render_risk_warning()
    
    # 导出报告功能
    render_export_buttons(results)

def render_analysis_info(results):
    """渲染分析配置信息"""

    with st.expander("📋 分析配置信息", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            llm_provider = results.get('llm_provider', 'dashscope')
            provider_name = {
                'dashscope': '阿里百炼',
                'google': 'Google AI',
                'qianfan': '文心一言（千帆）'
            }.get(llm_provider, llm_provider)

            st.metric(
                label="LLM提供商",
                value=provider_name,
                help="使用的AI模型提供商"
            )

        with col2:
            llm_model = results.get('llm_model', 'N/A')
            logger.debug(f"🔍 [DEBUG] llm_model from results: {llm_model}")
            model_display = {
                'qwen-turbo': 'Qwen Turbo',
                'qwen-plus': 'Qwen Plus',
                'qwen-max': 'Qwen Max',
                'gemini-2.0-flash': 'Gemini 2.0 Flash',
                'gemini-1.5-pro': 'Gemini 1.5 Pro',
                'gemini-1.5-flash': 'Gemini 1.5 Flash',
                'ERNIE-Speed-8K': 'ERNIE Speed 8K',
                'ERNIE-Lite-8K': 'ERNIE Lite 8K'
            }.get(llm_model, llm_model)

            st.metric(
                label="AI模型",
                value=model_display,
                help="使用的具体AI模型"
            )

        with col3:
            analysts = results.get('analysts', [])
            logger.debug(f"🔍 [DEBUG] analysts from results: {analysts}")
            analysts_count = len(analysts) if analysts else 0

            st.metric(
                label="分析师数量",
                value=f"{analysts_count}个",
                help="参与分析的AI分析师数量"
            )

        # 显示分析师列表
        if analysts:
            st.write("**参与的分析师:**")
            analyst_names = {
                'market': '📈 市场技术分析师',
                'fundamentals': '💰 基本面分析师',
                'news': '📰 新闻分析师',
                'social_media': '💭 社交媒体分析师',
                'risk': '⚠️ 风险评估师'
            }

            analyst_list = [analyst_names.get(analyst, analyst) for analyst in analysts]
            st.write(" • ".join(analyst_list))

def render_decision_summary(decision, stock_symbol=None):
    """渲染投资决策摘要"""

    st.subheader("🎯 投资决策摘要")

    # 如果没有决策数据，显示占位符
    if not decision:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                    padding: 30px; border-radius: 15px; text-align: center;
                    border: 2px dashed #dee2e6; margin: 20px 0;">
            <h4 style="color: #6c757d; margin-bottom: 15px;">📊 等待投资决策</h4>
            <p style="color: #6c757d; font-size: 16px; margin-bottom: 20px;">
                分析完成后，投资决策将在此处显示
            </p>
            <div style="display: flex; justify-content: center; gap: 15px; flex-wrap: wrap;">
                <span style="background: white; padding: 8px 16px; border-radius: 20px;
                           color: #6c757d; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    📊 投资建议
                </span>
                <span style="background: white; padding: 8px 16px; border-radius: 20px;
                           color: #6c757d; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    💰 目标价位
                </span>
                <span style="background: white; padding: 8px 16px; border-radius: 20px;
                           color: #6c757d; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    ⚖️ 风险评级
                </span>
                <span style="background: white; padding: 8px 16px; border-radius: 20px;
                           color: #6c757d; font-size: 14px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    🎯 置信度
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        return

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        action = decision.get('action', 'N/A')

        # 将英文投资建议转换为中文
        action_translation = {
            'BUY': '买入',
            'SELL': '卖出',
            'HOLD': '持有',
            '买入': '买入',
            '卖出': '卖出',
            '持有': '持有'
        }

        # 获取中文投资建议
        chinese_action = action_translation.get(action.upper(), action)

        action_color = {
            'BUY': 'normal',
            'SELL': 'inverse',
            'HOLD': 'off',
            '买入': 'normal',
            '卖出': 'inverse',
            '持有': 'off'
        }.get(action.upper(), 'normal')

        st.metric(
            label="投资建议",
            value=chinese_action,
            help="基于AI分析的投资建议"
        )

    with col2:
        confidence = decision.get('confidence', 0)
        if isinstance(confidence, (int, float)):
            confidence_str = f"{confidence:.1%}"
            confidence_delta = f"{confidence-0.5:.1%}" if confidence != 0 else None
        else:
            confidence_str = str(confidence)
            confidence_delta = None

        st.metric(
            label="置信度",
            value=confidence_str,
            delta=confidence_delta,
            help="AI对分析结果的置信度"
        )

    with col3:
        risk_score = decision.get('risk_score', 0)
        if isinstance(risk_score, (int, float)):
            risk_str = f"{risk_score:.1%}"
            risk_delta = f"{risk_score-0.3:.1%}" if risk_score != 0 else None
        else:
            risk_str = str(risk_score)
            risk_delta = None

        st.metric(
            label="风险评分",
            value=risk_str,
            delta=risk_delta,
            delta_color="inverse",
            help="投资风险评估分数"
        )

    with col4:
        target_price = decision.get('target_price')
        logger.debug(f"🔍 [DEBUG] target_price from decision: {target_price}, type: {type(target_price)}")
        logger.debug(f"🔍 [DEBUG] decision keys: {list(decision.keys()) if isinstance(decision, dict) else 'Not a dict'}")

        # 根据股票代码确定货币符号
        def is_china_stock(ticker_code):
            import re

            return re.match(r'^\d{6}$', str(ticker_code)) if ticker_code else False

        is_china = is_china_stock(stock_symbol)
        currency_symbol = "¥" if is_china else "$"

        # 处理目标价格显示
        if target_price is not None and isinstance(target_price, (int, float)) and target_price > 0:
            price_display = f"{currency_symbol}{target_price:.2f}"
            help_text = "AI预测的目标价位"
        else:
            price_display = "待分析"
            help_text = "目标价位需要更详细的分析才能确定"

        st.metric(
            label="目标价位",
            value=price_display,
            help=help_text
        )
    
    # 分析推理
    if 'reasoning' in decision and decision['reasoning']:
        with st.expander("🧠 AI分析推理", expanded=True):
            st.markdown(decision['reasoning'])

def render_detailed_analysis(state):
    """渲染详细分析报告"""

    st.subheader("📋 详细分析报告")

    # 添加自定义CSS样式美化标签页
    st.markdown("""
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
    """, unsafe_allow_html=True)

    # 调试信息：显示实际的状态键
    if st.checkbox("🔍 显示调试信息", key="debug_state_keys"):
        st.write("**实际状态中的键：**")
        st.write(list(state.keys()))
        st.write("**各键的数据类型和内容预览：**")
        for key, value in state.items():
            if isinstance(value, str):
                preview = value[:100] + "..." if len(value) > 100 else value
                st.write(f"- `{key}`: {type(value).__name__} ({len(value)} 字符) - {preview}")
            elif isinstance(value, dict):
                st.write(f"- `{key}`: {type(value).__name__} - 包含键: {list(value.keys())}")
            else:
                st.write(f"- `{key}`: {type(value).__name__} - {str(value)[:100]}")
        st.markdown("---")
    
    # 定义分析模块 - 包含完整的团队决策报告，与CLI端保持一致
    analysis_modules = [
        {
            'key': 'market_report',
            'title': '📈 市场技术分析',
            'icon': '📈',
            'description': '技术指标、价格趋势、支撑阻力位分析'
        },
        {
            'key': 'fundamentals_report',
            'title': '💰 基本面分析',
            'icon': '💰',
            'description': '财务数据、估值水平、盈利能力分析'
        },
        {
            'key': 'sentiment_report',
            'title': '💭 市场情绪分析',
            'icon': '💭',
            'description': '投资者情绪、社交媒体情绪指标'
        },
        {
            'key': 'news_report',
            'title': '📰 新闻事件分析',
            'icon': '📰',
            'description': '相关新闻事件、市场动态影响分析'
        },
        {
            'key': 'risk_assessment',
            'title': '⚠️ 风险评估',
            'icon': '⚠️',
            'description': '风险因素识别、风险等级评估'
        },
        {
            'key': 'investment_plan',
            'title': '📋 投资建议',
            'icon': '📋',
            'description': '具体投资策略、仓位管理建议'
        },
        # 添加团队决策报告模块
        {
            'key': 'investment_debate_state',
            'title': '🔬 研究团队决策',
            'icon': '🔬',
            'description': '多头/空头研究员辩论分析，研究经理综合决策'
        },
        {
            'key': 'trader_investment_plan',
            'title': '💼 交易团队计划',
            'icon': '💼',
            'description': '专业交易员制定的具体交易执行计划'
        },
        {
            'key': 'risk_debate_state',
            'title': '⚖️ 风险管理团队',
            'icon': '⚖️',
            'description': '激进/保守/中性分析师风险评估，投资组合经理最终决策'
        },
        {
            'key': 'final_trade_decision',
            'title': '🎯 最终交易决策',
            'icon': '🎯',
            'description': '综合所有团队分析后的最终投资决策'
        }
    ]
    
    # 过滤出有数据的模块
    available_modules = []
    for module in analysis_modules:
        if module['key'] in state and state[module['key']]:
            # 检查字典类型的数据是否有实际内容
            if isinstance(state[module['key']], dict):
                # 对于字典，检查是否有非空的值
                has_content = any(v for v in state[module['key']].values() if v)
                if has_content:
                    available_modules.append(module)
            else:
                # 对于字符串或其他类型，直接添加
                available_modules.append(module)

    if not available_modules:
        # 显示占位符而不是演示数据
        render_analysis_placeholder()
        return

    # 只为有数据的模块创建标签页 - 移除重复图标
    tabs = st.tabs([module['title'] for module in available_modules])

    for i, (tab, module) in enumerate(zip(tabs, available_modules)):
        with tab:
            # 在内容区域显示图标和描述
            st.markdown(f"## {module['icon']} {module['title']}")
            st.markdown(f"*{module['description']}*")
            st.markdown("---")

            # 格式化显示内容
            content = state[module['key']]
            if isinstance(content, str):
                st.markdown(content)
            elif isinstance(content, dict):
                # 特殊处理团队决策报告的字典结构
                if module['key'] == 'investment_debate_state':
                    render_investment_debate_content(content)
                elif module['key'] == 'risk_debate_state':
                    render_risk_debate_content(content)
                else:
                    # 普通字典格式化显示
                    for key, value in content.items():
                        st.subheader(key.replace('_', ' ').title())
                        st.write(value)
            else:
                st.write(content)

def render_investment_debate_content(content):
    """渲染研究团队决策内容"""
    if content.get('bull_history'):
        st.subheader("📈 多头研究员分析")
        st.markdown(content['bull_history'])
        st.markdown("---")

    if content.get('bear_history'):
        st.subheader("📉 空头研究员分析")
        st.markdown(content['bear_history'])
        st.markdown("---")

    if content.get('judge_decision'):
        st.subheader("🎯 研究经理综合决策")
        st.markdown(content['judge_decision'])

def render_risk_debate_content(content):
    """渲染风险管理团队决策内容"""
    if content.get('risky_history'):
        st.subheader("🚀 激进分析师评估")
        st.markdown(content['risky_history'])
        st.markdown("---")

    if content.get('safe_history'):
        st.subheader("🛡️ 保守分析师评估")
        st.markdown(content['safe_history'])
        st.markdown("---")

    if content.get('neutral_history'):
        st.subheader("⚖️ 中性分析师评估")
        st.markdown(content['neutral_history'])
        st.markdown("---")

    if content.get('judge_decision'):
        st.subheader("🎯 投资组合经理最终决策")
        st.markdown(content['judge_decision'])

def render_analysis_placeholder():
    """渲染分析占位符"""

    st.markdown("""
    <div style="text-align: center; padding: 40px; background-color: #f8f9fa; border-radius: 10px; border: 2px dashed #dee2e6;">
        <h3 style="color: #6c757d; margin-bottom: 20px;">📊 等待分析数据</h3>
        <p style="color: #6c757d; font-size: 16px; margin-bottom: 30px;">
            请先配置API密钥并运行股票分析，分析完成后详细报告将在此处显示
        </p>

        <div style="display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; margin-bottom: 30px;">
            <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); min-width: 150px;">
                <div style="font-size: 24px; margin-bottom: 8px;">📈</div>
                <div style="font-weight: bold; color: #495057;">技术分析</div>
                <div style="font-size: 12px; color: #6c757d;">价格趋势、支撑阻力</div>
            </div>

            <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); min-width: 150px;">
                <div style="font-size: 24px; margin-bottom: 8px;">💰</div>
                <div style="font-weight: bold; color: #495057;">基本面分析</div>
                <div style="font-size: 12px; color: #6c757d;">财务数据、估值分析</div>
            </div>

            <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); min-width: 150px;">
                <div style="font-size: 24px; margin-bottom: 8px;">📰</div>
                <div style="font-weight: bold; color: #495057;">新闻分析</div>
                <div style="font-size: 12px; color: #6c757d;">市场情绪、事件影响</div>
            </div>

            <div style="background: white; padding: 15px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); min-width: 150px;">
                <div style="font-size: 24px; margin-bottom: 8px;">⚖️</div>
                <div style="font-weight: bold; color: #495057;">风险评估</div>
                <div style="font-size: 12px; color: #6c757d;">风险控制、投资建议</div>
            </div>
        </div>

        <div style="background: #e3f2fd; padding: 15px; border-radius: 8px; margin-top: 20px;">
            <p style="color: #1976d2; margin: 0; font-size: 14px;">
                💡 <strong>提示</strong>: 配置API密钥后，系统将生成包含多个智能体团队分析的详细投资报告
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def render_risk_warning():
    """渲染风险提示"""

    st.markdown("---")
    st.subheader("⚠️ 重要风险提示")

    # 移除演示数据相关的提示，因为我们不再显示演示数据
    st.error("""
    **投资风险提示**:
    - **仅供参考**: 本分析结果仅供参考，不构成投资建议
    - **投资风险**: 股票投资有风险，可能导致本金损失
    - **理性决策**: 请结合多方信息进行理性投资决策
    - **专业咨询**: 重大投资决策建议咨询专业财务顾问
    - **自担风险**: 投资决策及其后果由投资者自行承担
    """)

    # 添加时间戳
    st.caption(f"分析生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def create_price_chart(price_data):
    """创建价格走势图"""
    
    if not price_data:
        return None
    
    fig = go.Figure()
    
    # 添加价格线
    fig.add_trace(go.Scatter(
        x=price_data['date'],
        y=price_data['price'],
        mode='lines',
        name='股价',
        line=dict(color='#1f77b4', width=2)
    ))
    
    # 设置图表样式
    fig.update_layout(
        title="股价走势图",
        xaxis_title="日期",
        yaxis_title="价格 ($)",
        hovermode='x unified',
        showlegend=True
    )
    
    return fig

def create_sentiment_gauge(sentiment_score):
    """创建情绪指标仪表盘"""
    
    if sentiment_score is None:
        return None
    
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = sentiment_score,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "市场情绪指数"},
        delta = {'reference': 50},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 25], 'color': "lightgray"},
                {'range': [25, 50], 'color': "gray"},
                {'range': [50, 75], 'color': "lightgreen"},
                {'range': [75, 100], 'color': "green"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    
    return fig
