# -*- coding: utf-8 -*-
"""统一接口工具模块 - 提供股票分析的统一入口"""

from typing import Annotated
from datetime import datetime, timedelta

import pandas as pd
from langchain_core.tools import tool

from tradingagents.utils.logging_manager import get_logger
from tradingagents.utils.tool_logging import log_tool_call

logger = get_logger("agents")


def get_stock_comprehensive_financials(
    ticker: Annotated[str, "股票代码（支持A股6位代码，如：000001、600000）"],
    curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None,
    config: dict = None,
) -> str:
    """
    获取股票完整标准化财务数据（供分析师使用）

    使用 Tushare 5120积分权限，一次性获取所有财务指标：
    - 估值指标：PE、PE_TTM、PB、PS、股息率
    - 盈利能力：EPS、ROE、ROA、毛利率、净利率
    - 财务数据：营业收入、净利润、经营现金流净额
    - 分红数据：每股分红、股息率、分红历史
    - 资产负债：总资产、总负债、资产负债率

    数据来源：
    - daily_basic: 每日估值指标（PE、PB、PS等）
    - income: 利润表（营收、净利润）
    - cashflow: 现金流量表（经营现金流）
    - fina_indicator: 财务指标（EPS、ROE等）
    - dividend: 分红送股数据

    Args:
        ticker: 股票代码（如：000001、600000）
        curr_date: 当前日期（可选，格式：YYYY-MM-DD）
        config: 配置字典

    Returns:
        str: 标准化的完整财务数据报告
    """
    import asyncio

    logger.info(f"📊 [完整财务数据] 开始获取 {ticker} 的完整财务数据")

    # 设置默认日期
    if not curr_date:
        curr_date = config.get("trade_date") or datetime.now().strftime("%Y-%m-%d")
        logger.info(f"📅 [完整财务数据] 使用分析日期: {curr_date}")

    try:
        from tradingagents.dataflows.providers.china.tushare import TushareProvider
        from tradingagents.utils.stock_utils import StockUtils

        # 验证股票类型
        market_info = StockUtils.get_market_info(ticker)
        if not market_info["is_china"]:
            return f"❌ 该工具仅支持中国A股，当前股票: {ticker} ({market_info['market_name']})"

        # 初始化 TushareProvider
        provider = TushareProvider()

        # 异步获取完整财务数据
        async def fetch_all_financials():
            await provider.connect()

            # 1. 获取完整财务数据包（包含 income、cashflow、fina_indicator、dividend）
            financial_data = await provider.get_financial_data(ticker, limit=8)

            # 2. 获取每日估值指标（PE、PB、PS等）
            trade_date = curr_date.replace("-", "")
            daily_basic_df = await provider.get_daily_basic(trade_date)

            return financial_data, daily_basic_df

        # 🔥 修复：安全地运行异步任务（避免事件循环冲突）
        def run_async_in_thread(coro):
            """在新线程中创建新的事件循环来运行协程（避免与主事件循环冲突）"""
            import threading
            import concurrent.futures

            def run_coro():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(coro)
                finally:
                    loop.close()

            # 使用线程池执行，避免阻塞当前线程
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(run_coro)
                return future.result(timeout=120)  # 120秒超时

        try:
            # 检查是否已经在事件循环中
            try:
                loop = asyncio.get_running_loop()
                # 如果在事件循环中，在新线程中运行以避免冲突
                logger.debug("🔧 在已有事件循环中运行，使用线程隔离模式")
                financial_data, daily_basic_df = run_async_in_thread(
                    fetch_all_financials()
                )
            except RuntimeError:
                # 没有事件循环，可以直接使用 asyncio.run
                logger.debug("🔧 无事件循环，直接运行")
                financial_data, daily_basic_df = asyncio.run(fetch_all_financials())
        except Exception as e:
            logger.error(f"❌ [完整财务数据] 异步执行失败: {e}")
            return f"❌ 获取财务数据失败: {str(e)}"

        if not financial_data:
            return f"❌ 未能获取 {ticker} 的财务数据"

        # 构建标准化输出
        report_lines = [
            f"# {ticker} 完整财务数据报告",
            f"数据日期: {curr_date}",
            "=" * 60,
            "",
            "## 📊 估值指标",
            "-" * 40,
        ]

        # 从 daily_basic 获取估值指标
        if daily_basic_df is not None and not daily_basic_df.empty:
            # 转换股票代码格式
            ts_code = f"{ticker}.{'SH' if ticker.startswith('6') else 'SZ'}"
            stock_data = daily_basic_df[daily_basic_df["ts_code"] == ts_code]

            if not stock_data.empty:
                row = stock_data.iloc[0]

                # 获取PS和PS_TTM值
                ps_value = row.get("ps", "N/A")
                ps_ttm_value = row.get("ps_ttm", "N/A")

                # 检查PS_TTM是否可用
                ps_ttm_available = pd.notna(ps_ttm_value) and ps_ttm_value != "N/A"

                report_lines.extend(
                    [
                        f"市盈率 (PE): {row.get('pe', 'N/A')}",
                        f"滚动市盈率 (PE_TTM): {row.get('pe_ttm', 'N/A')}",
                        f"市净率 (PB): {row.get('pb', 'N/A')}",
                        "",
                        "## 📊 市销率（PS）指标说明",
                        f"市销率 (PS静态): {ps_value}",
                        f"滚动市销率 (PS_TTM): {ps_ttm_value}",
                    ]
                )

                # 添加PS指标使用建议
                if ps_ttm_available:
                    report_lines.append(
                        "✅ **建议**：PS_TTM数据可用，估值分析时优先使用PS_TTM（更能反映最近12个月营收水平）"
                    )
                else:
                    report_lines.append(
                        "⚠️ **注意**：PS_TTM数据不可用，估值分析时将使用PS静态指标，请明确说明使用的是单期营收数据"
                    )

                # 股息率显示（2026-02-12 增强）
                dv_ratio = row.get("dv_ratio")
                dv_ttm = row.get("dv_ttm")
                if pd.notna(dv_ratio) or pd.notna(dv_ttm):
                    report_lines.append("")
                    report_lines.append("## 💰 股息率指标")
                    if pd.notna(dv_ttm):
                        report_lines.append(
                            f"股息率TTM (%): {dv_ttm:.2f} [近12个月股息率，优先参考]"
                        )
                    if pd.notna(dv_ratio):
                        report_lines.append(f"股息率 (%): {dv_ratio:.2f}")
                    # 股息率评估
                    if pd.notna(dv_ttm) and dv_ttm > 3:
                        report_lines.append(
                            f"✅ **股息率评估**：{dv_ttm:.2f}% 属于较高水平，具备较好的分红收益"
                        )
                    elif pd.notna(dv_ttm) and dv_ttm > 1:
                        report_lines.append(
                            f"📊 **股息率评估**：{dv_ttm:.2f}% 处于中等水平，有一定分红收益"
                        )
                    elif pd.notna(dv_ttm):
                        report_lines.append(
                            f"⚠️ **股息率评估**：{dv_ttm:.2f}% 较低，分红收益有限"
                        )
                else:
                    report_lines.extend(["", "股息率 (%): N/A (数据不可用)"])

                # 市值和股本信息
                report_lines.append("")
                report_lines.append("## 📊 市值与股本信息")
                if pd.notna(row.get("total_mv")):
                    report_lines.append(f"总市值 (万元): {row.get('total_mv'):,.0f}")
                else:
                    report_lines.append("总市值 (万元): N/A")
                if pd.notna(row.get("circ_mv")):
                    report_lines.append(f"流通市值 (万元): {row.get('circ_mv'):,.0f}")
                else:
                    report_lines.append("流通市值 (万元): N/A")
                # 股本数据（2026-02-12 新增）
                total_share = row.get("total_share")
                float_share = row.get("float_share")
                if pd.notna(total_share):
                    report_lines.append(f"总股本 (万股): {total_share:,.0f}")
                if pd.notna(float_share):
                    report_lines.append(f"流通股本 (万股): {float_share:,.0f}")
                report_lines.append("")

        # 从 fina_indicator 获取盈利指标
        report_lines.extend(
            [
                "## 💰 盈利能力指标",
                "-" * 40,
            ]
        )

        if "indicators" in financial_data and financial_data["indicators"]:
            latest = (
                financial_data["indicators"][0]
                if isinstance(financial_data["indicators"], list)
                else financial_data["indicators"]
            )
            report_lines.extend(
                [
                    f"每股收益 (EPS): {latest.get('eps', 'N/A')}",
                    f"净资产收益率 (ROE): {latest.get('roe', 'N/A')}%"
                    if latest.get("roe")
                    else "净资产收益率 (ROE): N/A",
                    f"总资产报酬率 (ROA): {latest.get('roa', 'N/A')}%"
                    if latest.get("roa")
                    else "总资产报酬率 (ROA): N/A",
                    f"销售毛利率: {latest.get('grossprofit_margin', 'N/A')}%"
                    if latest.get("grossprofit_margin")
                    else "销售毛利率: N/A",
                    f"销售净利率: {latest.get('netprofit_margin', 'N/A')}%"
                    if latest.get("netprofit_margin")
                    else "销售净利率: N/A",
                    "",
                ]
            )

        # 从 income 获取营收和利润
        report_lines.extend(
            [
                "## 📈 营业收入与利润",
                "-" * 40,
            ]
        )

        if "income" in financial_data and financial_data["income"]:
            latest_income = (
                financial_data["income"][0]
                if isinstance(financial_data["income"], list)
                else financial_data["income"]
            )
            report_lines.extend(
                [
                    f"营业收入: {latest_income.get('revenue', 'N/A'):,.0f} 万元"
                    if latest_income.get("revenue")
                    else "营业收入: N/A",
                    f"营业总收入: {latest_income.get('total_revenue', 'N/A'):,.0f} 万元"
                    if latest_income.get("total_revenue")
                    else "营业总收入: N/A",
                    f"净利润: {latest_income.get('n_income', 'N/A'):,.0f} 万元"
                    if latest_income.get("n_income")
                    else "净利润: N/A",
                    f"归母净利润: {latest_income.get('n_income_attr_p', 'N/A'):,.0f} 万元"
                    if latest_income.get("n_income_attr_p")
                    else "归母净利润: N/A",
                    "",
                ]
            )

        # 从 cashflow 获取现金流
        report_lines.extend(
            [
                "## 💸 现金流量",
                "-" * 40,
            ]
        )

        if "cashflow" in financial_data and financial_data["cashflow"]:
            latest_cf = (
                financial_data["cashflow"][0]
                if isinstance(financial_data["cashflow"], list)
                else financial_data["cashflow"]
            )
            report_lines.extend(
                [
                    f"经营现金流净额: {latest_cf.get('n_cashflow_act', 'N/A'):,.0f} 万元"
                    if latest_cf.get("n_cashflow_act")
                    else "经营现金流净额: N/A",
                    f"投资现金流净额: {latest_cf.get('n_cashflow_inv_act', 'N/A'):,.0f} 万元"
                    if latest_cf.get("n_cashflow_inv_act")
                    else "投资现金流净额: N/A",
                    f"筹资现金流净额: {latest_cf.get('n_cashflow_fin_act', 'N/A'):,.0f} 万元"
                    if latest_cf.get("n_cashflow_fin_act")
                    else "筹资现金流净额: N/A",
                    "",
                ]
            )

        # 从 balancesheet 获取资产负债
        report_lines.extend(
            [
                "## 🏦 资产负债情况",
                "-" * 40,
            ]
        )

        if "balancesheet" in financial_data and financial_data["balancesheet"]:
            latest_bs = (
                financial_data["balancesheet"][0]
                if isinstance(financial_data["balancesheet"], list)
                else financial_data["balancesheet"]
            )
            report_lines.extend(
                [
                    f"总资产: {latest_bs.get('total_assets', 'N/A'):,.0f} 万元"
                    if latest_bs.get("total_assets")
                    else "总资产: N/A",
                    f"总负债: {latest_bs.get('total_liab', 'N/A'):,.0f} 万元"
                    if latest_bs.get("total_liab")
                    else "总负债: N/A",
                    f"股东权益: {latest_bs.get('total_hldr_eqy_exc_min_int', 'N/A'):,.0f} 万元"
                    if latest_bs.get("total_hldr_eqy_exc_min_int")
                    else "股东权益: N/A",
                    "",
                ]
            )

        # 从 dividend 获取分红数据
        report_lines.extend(
            [
                "## 💝 分红送股",
                "-" * 40,
            ]
        )

        if "dividend" in financial_data and financial_data["dividend"]:
            dividends = (
                financial_data["dividend"]
                if isinstance(financial_data["dividend"], list)
                else [financial_data["dividend"]]
            )
            report_lines.append(f"最近 {len(dividends)} 次分红记录:")
            for i, div in enumerate(dividends[:3]):  # 只显示最近3次
                report_lines.extend(
                    [
                        f"  {i + 1}. 除权除息日: {div.get('ex_date', 'N/A')}",
                        f"     每股现金分红: {div.get('cash_div', 'N/A')} 元"
                        if div.get("cash_div")
                        else "     每股现金分红: N/A",
                        f"     实施进度: {div.get('div_proc', 'N/A')}",
                    ]
                )
            report_lines.append("")

        # 添加最新股息率
        if "latest_dividend_yield" in financial_data:
            report_lines.extend(
                [
                    f"最新股息率: {financial_data['latest_dividend_yield']}%",
                    f"最新每股分红: {financial_data.get('latest_cash_div', 'N/A')} 元"
                    if financial_data.get("latest_cash_div")
                    else "最新每股分红: N/A",
                    "",
                ]
            )

        # 添加财务摘要总结
        report_lines.extend(
            [
                "=" * 60,
                "## 📝 财务健康度摘要",
                "-" * 40,
            ]
        )

        # 根据数据生成简要分析
        health_indicators = []

        if "indicators" in financial_data and financial_data["indicators"]:
            latest = (
                financial_data["indicators"][0]
                if isinstance(financial_data["indicators"], list)
                else financial_data["indicators"]
            )
            roe = latest.get("roe")
            if roe and roe > 15:
                health_indicators.append(f"✅ ROE {roe}% > 15%，盈利能力优秀")
            elif roe and roe > 10:
                health_indicators.append(f"✅ ROE {roe}% > 10%，盈利能力良好")
            elif roe:
                health_indicators.append(f"⚠️ ROE {roe}% < 10%，盈利能力一般")

            debt_ratio = latest.get("debt_to_assets")
            if debt_ratio and debt_ratio < 40:
                health_indicators.append(
                    f"✅ 资产负债率 {debt_ratio}% < 40%，财务风险较低"
                )
            elif debt_ratio and debt_ratio < 60:
                health_indicators.append(f"⚠️ 资产负债率 {debt_ratio}% 适中")
            elif debt_ratio:
                health_indicators.append(
                    f"❌ 资产负债率 {debt_ratio}% > 60%，财务风险较高"
                )

        if health_indicators:
            report_lines.extend(health_indicators)
        else:
            report_lines.append("暂无足够数据生成财务健康度分析")

        report_lines.append("")
        report_lines.append(
            f"数据来源: Tushare Pro | 积分要求: 5120 | 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        return "\n".join(report_lines)

    except Exception as e:
        import traceback

        error_details = traceback.format_exc()
        logger.error(f"❌ [完整财务数据] 获取失败: {e}")
        logger.error(f"详细错误: {error_details}")
        return f"❌ 获取 {ticker} 完整财务数据失败: {str(e)}"


def get_stock_fundamentals_unified(
    ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
    start_date: Annotated[str, "开始日期，格式：YYYY-MM-DD"] = None,
    end_date: Annotated[str, "结束日期，格式：YYYY-MM-DD"] = None,
    curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"] = None,
    config: dict = None,
) -> str:
    """
    统一的股票基本面分析工具
    自动识别股票类型（A股、港股、美股）并调用相应的数据源
    支持基于分析级别的数据获取策略

    Args:
        ticker: 股票代码（如：000001、0700.HK、AAPL）
        start_date: 开始日期（可选，格式：YYYY-MM-DD）
        end_date: 结束日期（可选，格式：YYYY-MM-DD）
        curr_date: 当前日期（可选，格式：YYYY-MM-DD）
        config: 配置字典

    Returns:
        str: 基本面分析数据和报告
    """
    logger.info(f"📊 [统一基本面工具] 分析股票: {ticker}")

    # 🔧 获取分析级别配置，支持基于级别的数据获取策略
    research_depth = config.get("research_depth", "标准")
    logger.info(f"🔧 [分析级别] 当前分析级别: {research_depth}")

    # 数字等级到中文等级的映射
    numeric_to_chinese = {1: "快速", 2: "基础", 3: "标准", 4: "深度", 5: "全面"}

    # 标准化研究深度：支持数字输入
    if isinstance(research_depth, (int, float)):
        research_depth = int(research_depth)
        if research_depth in numeric_to_chinese:
            chinese_depth = numeric_to_chinese[research_depth]
            logger.info(
                f"🔢 [等级转换] 数字等级 {research_depth} → 中文等级 '{chinese_depth}'"
            )
            research_depth = chinese_depth
        else:
            logger.warning(f"⚠️ 无效的数字等级: {research_depth}，使用默认标准分析")
            research_depth = "标准"
    elif isinstance(research_depth, str):
        # 如果是字符串形式的数字，转换为整数
        if research_depth.isdigit():
            numeric_level = int(research_depth)
            if numeric_level in numeric_to_chinese:
                chinese_depth = numeric_to_chinese[numeric_level]
                logger.info(
                    f"🔢 [等级转换] 字符串数字 '{research_depth}' → 中文等级 '{chinese_depth}'"
                )
                research_depth = chinese_depth
            else:
                logger.warning(
                    f"⚠️ 无效的字符串数字等级: {research_depth}，使用默认标准分析"
                )
                research_depth = "标准"
        # 如果已经是中文等级，直接使用
        elif research_depth in ["快速", "基础", "标准", "深度", "全面"]:
            logger.info(f"📝 [等级确认] 使用中文等级: '{research_depth}'")
        else:
            logger.warning(f"⚠️ 未知的研究深度: {research_depth}，使用默认标准分析")
            research_depth = "标准"
    else:
        logger.warning(
            f"⚠️ 无效的研究深度类型: {type(research_depth)}，使用默认标准分析"
        )
        research_depth = "标准"

    # 根据分析级别调整数据获取策略
    # 🔧 修正映射关系：data_depth 应该与 research_depth 保持一致
    if research_depth == "快速":
        # 快速分析：获取基础数据，减少数据源调用
        data_depth = "basic"
        logger.info(f"🔧 [分析级别] 快速分析模式：获取基础数据")
    elif research_depth == "基础":
        # 基础分析：获取标准数据
        data_depth = "standard"
        logger.info(f"🔧 [分析级别] 基础分析模式：获取标准数据")
    elif research_depth == "标准":
        # 标准分析：获取标准数据（不是full！）
        data_depth = "standard"
        logger.info(f"🔧 [分析级别] 标准分析模式：获取标准数据")
    elif research_depth == "深度":
        # 深度分析：获取完整数据
        data_depth = "full"
        logger.info(f"🔧 [分析级别] 深度分析模式：获取完整数据")
    elif research_depth == "全面":
        # 全面分析：获取最全面的数据，包含所有可用数据源
        data_depth = "comprehensive"
        logger.info(f"🔧 [分析级别] 全面分析模式：获取最全面数据")
    else:
        # 默认使用标准分析
        data_depth = "standard"
        logger.info(f"🔧 [分析级别] 未知级别，使用标准分析模式")

    # 添加详细的股票代码追踪日志
    logger.info(
        f"🔍 [股票代码追踪] 统一基本面工具接收到的原始股票代码: '{ticker}' (类型: {type(ticker)})"
    )
    logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(ticker))}")
    logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(ticker))}")

    # 保存原始ticker用于对比
    original_ticker = ticker

    try:
        from tradingagents.utils.stock_utils import StockUtils
        from datetime import datetime, timedelta

        # 自动识别股票类型
        market_info = StockUtils.get_market_info(ticker)
        is_china = market_info["is_china"]
        is_hk = market_info["is_hk"]
        is_us = market_info["is_us"]

        logger.info(
            f"🔍 [股票代码追踪] StockUtils.get_market_info 返回的市场信息: {market_info}"
        )
        logger.info(f"📊 [统一基本面工具] 股票类型: {market_info['market_name']}")
        logger.info(
            f"📊 [统一基本面工具] 货币: {market_info['currency_name']} ({market_info['currency_symbol']})"
        )

        # 检查ticker是否在处理过程中发生了变化
        if str(ticker) != str(original_ticker):
            logger.warning(
                f"🔍 [股票代码追踪] 警告：股票代码发生了变化！原始: '{original_ticker}' -> 当前: '{ticker}'"
            )

        # 设置默认日期 - 优先使用 config 中的 trade_date
        if not curr_date:
            # 尝试从 Toolkit 配置获取分析日期
            curr_date = config.get("trade_date")
            if curr_date:
                logger.info(
                    f"📅 [统一基本面工具] 使用 config 中的分析日期: {curr_date}"
                )
            else:
                curr_date = datetime.now().strftime("%Y-%m-%d")
                logger.warning(
                    f"⚠️ [统一基本面工具] 未提供分析日期，使用系统时间: {curr_date}"
                )

        # 基本面分析优化：不需要大量历史数据，只需要当前价格和财务数据
        # 根据数据深度级别设置不同的分析模块数量，而非历史数据范围
        # 🔧 修正映射关系：analysis_modules 应该与 data_depth 保持一致
        if data_depth == "basic":  # 快速分析：基础模块
            analysis_modules = "basic"
            logger.info(f"📊 [基本面策略] 快速分析模式：获取基础财务指标")
        elif data_depth == "standard":  # 基础/标准分析：标准模块
            analysis_modules = "standard"
            logger.info(f"📊 [基本面策略] 标准分析模式：获取标准财务分析")
        elif data_depth == "full":  # 深度分析：完整模块
            analysis_modules = "full"
            logger.info(f"📊 [基本面策略] 深度分析模式：获取完整基本面分析")
        elif data_depth == "comprehensive":  # 全面分析：综合模块
            analysis_modules = "comprehensive"
            logger.info(f"📊 [基本面策略] 全面分析模式：获取综合基本面分析")
        else:
            analysis_modules = "standard"  # 默认标准分析
            logger.info(f"📊 [基本面策略] 默认模式：获取标准基本面分析")

        # 基本面分析策略：
        # 1. 获取10天数据（保证能拿到数据，处理周末/节假日）
        # 2. 只使用最近2天数据参与分析（仅需当前价格）
        days_to_fetch = 10  # 固定获取10天数据
        days_to_analyze = 2  # 只分析最近2天

        logger.info(
            f"📅 [基本面策略] 获取{days_to_fetch}天数据，分析最近{days_to_analyze}天"
        )

        if not start_date:
            start_date = (datetime.now() - timedelta(days=days_to_fetch)).strftime(
                "%Y-%m-%d"
            )

        if not end_date:
            end_date = curr_date

        result_data = []

        if is_china:
            # 中国A股：基本面分析优化策略 - 只获取必要的当前价格和基本面数据
            logger.info(f"🇨🇳 [统一基本面工具] 处理A股数据，数据深度: {data_depth}...")
            logger.info(f"🔍 [股票代码追踪] 进入A股处理分支，ticker: '{ticker}'")
            logger.info(
                f"💡 [优化策略] 基本面分析只获取当前价格和财务数据，不获取历史日线数据"
            )

            # 🔧 FIX: 使用统一交易日管理器，确保与技术分析使用相同的数据日期
            from tradingagents.utils.trading_date_manager import (
                get_trading_date_manager,
            )
            from tradingagents.utils.price_cache import get_price_cache

            date_mgr = get_trading_date_manager()
            trading_date = date_mgr.get_latest_trading_date(curr_date)

            # 如果对齐后的日期不同，记录日志
            if trading_date != curr_date:
                logger.info(
                    f"📅 [基本面分析] 日期对齐: {curr_date} → {trading_date} (最新交易日)"
                )

            # 优化策略：基本面分析不需要大量历史日线数据
            # 只获取当前股价信息（最近5天数据以确保包含交易日）和基本面财务数据
            try:
                # 获取最新股价信息
                from datetime import datetime, timedelta

                recent_end_date = trading_date
                recent_start_date = (
                    datetime.strptime(trading_date, "%Y-%m-%d") - timedelta(days=5)
                ).strftime("%Y-%m-%d")

                logger.info(
                    f"📅 [基本面分析] 使用统一交易日: {trading_date}, 查询范围: {recent_start_date} 至 {recent_end_date}"
                )

                from tradingagents.dataflows.interface import (
                    get_china_stock_data_unified,
                )

                logger.info(
                    f"🔍 [股票代码追踪] 调用 get_china_stock_data_unified（仅获取最新价格），传入参数: ticker='{ticker}', start_date='{recent_start_date}', end_date='{recent_end_date}'"
                )
                current_price_data = get_china_stock_data_unified(
                    ticker, recent_start_date, recent_end_date
                )

                # 🔍 调试：打印返回数据的前500字符
                logger.info(
                    f"🔍 [基本面工具调试] A股价格数据返回长度: {len(current_price_data)}"
                )
                logger.info(
                    f"🔍 [基本面工具调试] A股价格数据前500字符:\n{current_price_data[:500]}"
                )

                result_data.append(f"## A股当前价格信息\n{current_price_data}")
            except Exception as e:
                logger.error(f"❌ [基本面工具调试] A股价格数据获取失败: {e}")
                result_data.append(f"## A股当前价格信息\n获取失败: {e}")
                current_price_data = ""

            try:
                # 获取基本面财务数据（这是基本面分析的核心）
                from tradingagents.dataflows.optimized_china_data import (
                    OptimizedChinaDataProvider,
                )

                analyzer = OptimizedChinaDataProvider()
                logger.info(
                    f"🔍 [股票代码追踪] 调用 OptimizedChinaDataProvider._generate_fundamentals_report，传入参数: ticker='{ticker}', analysis_modules='{analysis_modules}'"
                )

                # 传递分析模块参数到基本面分析方法
                fundamentals_data = analyzer._generate_fundamentals_report(
                    ticker, analysis_modules
                )

                # 🔍 调试：打印返回数据的前500字符
                logger.info(
                    f"🔍 [基本面工具调试] A股基本面数据返回长度: {len(fundamentals_data)}"
                )
                logger.info(
                    f"🔍 [基本面工具调试] A股基本面数据前500字符:\n{fundamentals_data[:500]}"
                )

                result_data.append(f"## A股基本面财务数据\n{fundamentals_data}")
            except Exception as e:
                logger.error(f"❌ [基本面工具调试] A股基本面数据获取失败: {e}")
                result_data.append(f"## A股基本面财务数据\n获取失败: {e}")

        elif is_hk:
            # 港股：使用AKShare数据源，支持多重备用方案
            logger.info(f"🇭🇰 [统一基本面工具] 处理港股数据，数据深度: {data_depth}...")

            hk_data_success = False

            # 🔥 统一策略：所有级别都获取完整数据
            # 原因：提示词是统一的，如果数据不完整会导致LLM基于不存在的数据进行分析（幻觉）
            logger.info(
                f"🔍 [港股基本面] 统一策略：获取完整数据（忽略 data_depth 参数）"
            )

            # 主要数据源：AKShare
            try:
                from tradingagents.dataflows.interface import (
                    get_hk_stock_data_unified,
                )

                hk_data = get_hk_stock_data_unified(ticker, start_date, end_date)

                # 🔍 调试：打印返回数据的前500字符
                logger.info(f"🔍 [基本面工具调试] 港股数据返回长度: {len(hk_data)}")
                logger.info(f"🔍 [基本面工具调试] 港股数据前500字符:\n{hk_data[:500]}")

                # 检查数据质量
                if hk_data and len(hk_data) > 100 and "❌" not in hk_data:
                    result_data.append(f"## 港股数据\n{hk_data}")
                    hk_data_success = True
                    logger.info(f"✅ [统一基本面工具] 港股主要数据源成功")
                else:
                    logger.warning(f"⚠️ [统一基本面工具] 港股主要数据源质量不佳")

            except Exception as e:
                logger.error(f"❌ [基本面工具调试] 港股数据获取失败: {e}")

            # 备用方案：基础港股信息
            if not hk_data_success:
                try:
                    from tradingagents.dataflows.interface import (
                        get_hk_stock_info_unified,
                    )

                    hk_info = get_hk_stock_info_unified(ticker)

                    basic_info = f"""## 港股基础信息

**股票代码**: {ticker}
**股票名称**: {hk_info.get("name", f"港股{ticker}")}
**交易货币**: 港币 (HK$)
**交易所**: 香港交易所 (HKG)
**数据源**: {hk_info.get("source", "基础信息")}

⚠️ 注意：详细的价格和财务数据暂时无法获取，建议稍后重试或使用其他数据源。

**基本面分析建议**：
- 建议查看公司最新财报
- 关注港股市场整体走势
- 考虑汇率因素对投资的影响
"""
                    result_data.append(basic_info)
                    logger.info(f"✅ [统一基本面工具] 港股备用信息成功")

                except Exception as e2:
                    # 最终备用方案
                    fallback_info = f"""## 港股信息（备用）

**股票代码**: {ticker}
**股票类型**: 港股
**交易货币**: 港币 (HK$)
**交易所**: 香港交易所 (HKG)

❌ 数据获取遇到问题: {str(e2)}

**建议**：
- 请稍后重试
- 或使用其他数据源
- 检查股票代码格式是否正确
"""
                    result_data.append(fallback_info)
                    logger.error(f"❌ [统一基本面工具] 港股所有数据源都失败: {e2}")

        else:
            # 美股：使用OpenAI/Finnhub数据源
            logger.info(f"🇺🇸 [统一基本面工具] 处理美股数据...")

            # 🔥 统一策略：所有级别都获取完整数据
            # 原因：提示词是统一的，如果数据不完整会导致LLM基于不存在的数据进行分析（幻觉）
            logger.info(
                f"🔍 [美股基本面] 统一策略：获取完整数据（忽略 data_depth 参数）"
            )

            try:
                from tradingagents.dataflows.interface import (
                    get_fundamentals_openai,
                )

                us_data = get_fundamentals_openai(ticker, curr_date)
                result_data.append(f"## 美股基本面数据\n{us_data}")
                logger.info(f"✅ [统一基本面工具] 美股数据获取成功")
            except Exception as e:
                result_data.append(f"## 美股基本面数据\n获取失败: {e}")
                logger.error(f"❌ [统一基本面工具] 美股数据获取失败: {e}")

        # 组合所有数据
        combined_result = f"""# {ticker} 基本面分析数据

**股票类型**: {market_info["market_name"]}
**货币**: {market_info["currency_name"]} ({market_info["currency_symbol"]})
**分析日期**: {curr_date}
**数据深度级别**: {data_depth}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的数据源*
"""

        # 添加详细的数据获取日志
        logger.info(f"📊 [统一基本面工具] ===== 数据获取完成摘要 =====")
        logger.info(f"📊 [统一基本面工具] 股票代码: {ticker}")
        logger.info(f"📊 [统一基本面工具] 股票类型: {market_info['market_name']}")
        logger.info(f"📊 [统一基本面工具] 数据深度级别: {data_depth}")
        logger.info(f"📊 [统一基本面工具] 获取的数据模块数量: {len(result_data)}")
        logger.info(f"📊 [统一基本面工具] 总数据长度: {len(combined_result)} 字符")

        # 记录每个数据模块的详细信息
        for i, data_section in enumerate(result_data, 1):
            section_lines = data_section.split("\n")
            section_title = section_lines[0] if section_lines else "未知模块"
            section_length = len(data_section)
            logger.info(
                f"📊 [统一基本面工具] 数据模块 {i}: {section_title} ({section_length} 字符)"
            )

            # 如果数据包含错误信息，特别标记
            if "获取失败" in data_section or "❌" in data_section:
                logger.warning(f"⚠️ [统一基本面工具] 数据模块 {i} 包含错误信息")
            else:
                logger.info(f"✅ [统一基本面工具] 数据模块 {i} 获取成功")

        # 根据数据深度级别记录具体的获取策略
        if data_depth in ["basic", "standard"]:
            logger.info(
                f"📊 [统一基本面工具] 基础/标准级别策略: 仅获取核心价格数据和基础信息"
            )
        elif data_depth in ["full", "detailed", "comprehensive"]:
            logger.info(
                f"📊 [统一基本面工具] 完整/详细/全面级别策略: 获取价格数据 + 基本面数据"
            )
        else:
            logger.info(f"📊 [统一基本面工具] 默认策略: 获取完整数据")

        logger.info(f"📊 [统一基本面工具] ===== 数据获取摘要结束 =====")

        # 🔍 添加数据验证信息
        try:
            from tradingagents.agents.utils.data_validation_integration import (
                add_data_validation_to_fundamentals_report,
            )

            combined_result = add_data_validation_to_fundamentals_report(
                ticker, combined_result
            )
            logger.info(f"✅ [统一基本面工具] {ticker} 数据验证已完成")
        except Exception as e:
            logger.warning(f"⚠️ [统一基本面工具] 数据验证失败: {e}")

        return combined_result

    except Exception as e:
        error_msg = f"统一基本面分析工具执行失败: {str(e)}"
        logger.error(f"❌ [统一基本面工具] {error_msg}")
        return error_msg


def get_stock_market_data_unified(
    ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
    start_date: Annotated[
        str,
        "开始日期，格式：YYYY-MM-DD。注意：系统会自动扩展到配置的回溯天数（通常为365天），你只需要传递分析日期即可",
    ],
    end_date: Annotated[
        str,
        "结束日期，格式：YYYY-MM-DD。通常与start_date相同，传递当前分析日期即可",
    ],
) -> str:
    """
    统一的股票市场数据工具
    自动识别股票类型（A股、港股、美股）并调用相应的数据源获取价格和技术指标数据

    ⚠️ 重要：系统会自动扩展日期范围到配置的回溯天数（通常为365天），以确保技术指标计算有足够的历史数据。
    你只需要传递当前分析日期作为 start_date 和 end_date 即可，无需手动计算历史日期范围。

    Args:
        ticker: 股票代码（如：000001、0700.HK、AAPL）
        start_date: 开始日期（格式：YYYY-MM-DD）。传递当前分析日期即可，系统会自动扩展
        end_date: 结束日期（格式：YYYY-MM-DD）。传递当前分析日期即可

    Returns:
        str: 市场数据和技术分析报告

    示例：
        如果分析日期是 2025-11-09，传递：
        - ticker: "00700.HK"
        - start_date: "2025-11-09"
        - end_date: "2025-11-09"
        系统会自动获取 2024-11-09 到 2025-11-09 的365天历史数据
    """
    logger.info(f"📈 [统一市场工具] 分析股票: {ticker}")

    try:
        from tradingagents.utils.stock_utils import StockUtils

        # 自动识别股票类型
        market_info = StockUtils.get_market_info(ticker)
        is_china = market_info["is_china"]
        is_hk = market_info["is_hk"]
        is_us = market_info["is_us"]

        logger.info(f"📈 [统一市场工具] 股票类型: {market_info['market_name']}")
        logger.info(
            f"📈 [统一市场工具] 货币: {market_info['currency_name']} ({market_info['currency_symbol']}"
        )

        result_data = []

        if is_china:
            # 中国A股：使用中国股票数据源
            logger.info(f"🇨🇳 [统一市场工具] 处理A股市场数据...")

            # 🔧 FIX: 使用统一交易日管理器，确保与基本面分析使用相同的数据日期
            from tradingagents.utils.trading_date_manager import (
                get_trading_date_manager,
            )

            date_mgr = get_trading_date_manager()
            aligned_end_date = date_mgr.get_latest_trading_date(end_date)

            # 如果对齐后的日期不同，记录日志
            if aligned_end_date != end_date:
                logger.info(
                    f"📅 [技术分析] 日期对齐: {end_date} → {aligned_end_date} (最新交易日)"
                )

            try:
                from tradingagents.dataflows.interface import (
                    get_china_stock_data_unified,
                )

                stock_data = get_china_stock_data_unified(
                    ticker, start_date, aligned_end_date
                )

                # 🔍 调试：打印返回数据的前500字符
                logger.info(f"🔍 [市场工具调试] A股数据返回长度: {len(stock_data)}")
                logger.info(f"🔍 [市场工具调试] A股数据前500字符:\n{stock_data[:500]}")

                result_data.append(f"## A股市场数据\n{stock_data}")
            except Exception as e:
                logger.error(f"❌ [市场工具调试] A股数据获取失败: {e}")
                result_data.append(f"## A股市场数据\n获取失败: {e}")

        elif is_hk:
            # 港股：使用AKShare数据源
            logger.info(f"🇭🇰 [统一市场工具] 处理港股市场数据...")

            try:
                from tradingagents.dataflows.interface import (
                    get_hk_stock_data_unified,
                )

                hk_data = get_hk_stock_data_unified(ticker, start_date, end_date)

                # 🔍 调试：打印返回数据的前500字符
                logger.info(f"🔍 [市场工具调试] 港股数据返回长度: {len(hk_data)}")
                logger.info(f"🔍 [市场工具调试] 港股数据前500字符:\n{hk_data[:500]}")

                result_data.append(f"## 港股市场数据\n{hk_data}")
            except Exception as e:
                logger.error(f"❌ [市场工具调试] 港股数据获取失败: {e}")
                result_data.append(f"## 港股市场数据\n获取失败: {e}")

        else:
            # 美股：优先使用FINNHUB API数据源
            logger.info(f"🇺🇸 [统一市场工具] 处理美股市场数据...")

            try:
                from tradingagents.dataflows.providers.us.optimized import (
                    get_us_stock_data_cached,
                )

                us_data = get_us_stock_data_cached(ticker, start_date, end_date)
                result_data.append(f"## 美股市场数据\n{us_data}")
            except Exception as e:
                result_data.append(f"## 美股市场数据\n获取失败: {e}")

        # 组合所有数据
        combined_result = f"""# {ticker} 市场数据分析

**股票类型**: {market_info["market_name"]}
**货币**: {market_info["currency_name"]} ({market_info["currency_symbol"]})
**分析期间**: {start_date} 至 {end_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的数据源*
"""

        # 🔍 添加数据验证信息
        try:
            from tradingagents.agents.utils.data_validation_integration import (
                add_data_validation_to_market_report,
            )

            combined_result = add_data_validation_to_market_report(
                ticker, combined_result
            )
            logger.info(f"✅ [统一市场工具] {ticker} 数据验证已完成")
        except Exception as e:
            logger.warning(f"⚠️ [统一市场工具] 数据验证失败: {e}")

        logger.info(f"📈 [统一市场工具] 数据获取完成，总长度: {len(combined_result)}")
        return combined_result

    except Exception as e:
        error_msg = f"统一市场数据工具执行失败: {str(e)}"
        logger.error(f"❌ [统一市场工具] {error_msg}")
        return error_msg


def get_stock_news_unified(
    ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
    curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"],
) -> str:
    """
    统一的股票新闻工具
    自动识别股票类型（A股、港股、美股）并调用相应的新闻数据源

    数据源策略:
    - A股/港股: 使用东方财富新闻（AKShare）
    - 美股: 使用 Finnhub 新闻
    - 注: 已移除 Google 新闻（国内访问不稳定）

    Args:
        ticker: 股票代码（如：000001、0700.HK、AAPL）
        curr_date: 当前日期（格式：YYYY-MM-DD）

    Returns:
        str: 新闻分析报告
    """
    logger.info(f"📰 [统一新闻工具] 分析股票: {ticker}")

    try:
        from tradingagents.utils.stock_utils import StockUtils
        from datetime import datetime, timedelta

        # 自动识别股票类型
        market_info = StockUtils.get_market_info(ticker)
        is_china = market_info["is_china"]
        is_hk = market_info["is_hk"]
        is_us = market_info["is_us"]

        logger.info(f"📰 [统一新闻工具] 股票类型: {market_info['market_name']}")

        # 计算新闻查询的日期范围
        end_date = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date = end_date - timedelta(days=7)
        start_date_str = start_date.strftime("%Y-%m-%d")

        result_data = []

        if is_china or is_hk:
            # 中国A股和港股：使用AKShare东方财富新闻和Google新闻（中文搜索）
            logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 处理中文新闻...")

            # 1. 尝试获取AKShare东方财富新闻
            try:
                # 处理股票代码
                clean_ticker = (
                    ticker.replace(".SH", "")
                    .replace(".SZ", "")
                    .replace(".SS", "")
                    .replace(".HK", "")
                    .replace(".XSHE", "")
                    .replace(".XSHG", "")
                )

                logger.info(f"🇨🇳🇭🇰 [统一新闻工具] 尝试获取东方财富新闻: {clean_ticker}")

                # 通过 AKShare Provider 获取新闻
                from tradingagents.dataflows.providers.china.akshare import (
                    AKShareProvider,
                )

                provider = AKShareProvider()

                # 获取东方财富新闻
                news_df = provider.get_stock_news_sync(symbol=clean_ticker)

                if news_df is not None and not news_df.empty:
                    # 格式化东方财富新闻
                    em_news_items = []
                    for _, row in news_df.iterrows():
                        # AKShare 返回的字段名
                        news_title = row.get("新闻标题", "") or row.get("标题", "")
                        news_time = row.get("发布时间", "") or row.get("时间", "")
                        news_url = row.get("新闻链接", "") or row.get("链接", "")

                        news_item = f"- **{news_title}** [{news_time}]({news_url})"
                        em_news_items.append(news_item)

                    # 添加到结果中
                    if em_news_items:
                        em_news_text = "\n".join(em_news_items)
                        result_data.append(f"## 东方财富新闻\n{em_news_text}")
                        logger.info(
                            f"🇨🇳🇭🇰 [统一新闻工具] 成功获取{len(em_news_items)}条东方财富新闻"
                        )
            except Exception as em_e:
                logger.error(f"❌ [统一新闻工具] 东方财富新闻获取失败: {em_e}")
                result_data.append(f"## 东方财富新闻\n获取失败: {em_e}")

        else:
            # 美股：使用Finnhub新闻
            logger.info(f"🇺🇸 [统一新闻工具] 处理美股新闻...")

            try:
                from tradingagents.dataflows.interface import get_finnhub_news

                news_data = get_finnhub_news(ticker, start_date_str, curr_date)
                result_data.append(f"## 美股新闻\n{news_data}")
            except Exception as e:
                result_data.append(f"## 美股新闻\n获取失败: {e}")

        # 组合所有数据
        combined_result = f"""# {ticker} 新闻分析

**股票类型**: {market_info["market_name"]}
**分析日期**: {curr_date}
**新闻时间范围**: {start_date_str} 至 {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的新闻源*
"""

        logger.info(f"📰 [统一新闻工具] 数据获取完成，总长度: {len(combined_result)}")
        return combined_result

    except Exception as e:
        error_msg = f"统一新闻工具执行失败: {str(e)}"
        logger.error(f"❌ [统一新闻工具] {error_msg}")
        return error_msg


def get_stock_sentiment_unified(
    ticker: Annotated[str, "股票代码（支持A股、港股、美股）"],
    curr_date: Annotated[str, "当前日期，格式：YYYY-MM-DD"],
) -> str:
    """
    统一的股票情绪分析工具
    自动识别股票类型（A股、港股、美股）并调用相应的情绪数据源

    Args:
        ticker: 股票代码（如：000001、0700.HK、AAPL）
        curr_date: 当前日期（格式：YYYY-MM-DD）

    Returns:
        str: 情绪分析报告
    """
    logger.info(f"😊 [统一情绪工具] 分析股票: {ticker}")

    try:
        from tradingagents.utils.stock_utils import StockUtils

        # 自动识别股票类型
        market_info = StockUtils.get_market_info(ticker)
        is_china = market_info["is_china"]
        is_hk = market_info["is_hk"]
        is_us = market_info["is_us"]

        logger.info(f"😊 [统一情绪工具] 股票类型: {market_info['market_name']}")

        result_data = []

        if is_china or is_hk:
            # 中国A股和港股：使用社交媒体情绪分析
            logger.info(f"🇨🇳🇭🇰 [统一情绪工具] 处理中文市场情绪...")

            try:
                # 可以集成微博、雪球、东方财富等中文社交媒体情绪
                # 目前使用基础的情绪分析
                sentiment_summary = f"""
## 中文市场情绪分析

**股票**: {ticker} ({market_info["market_name"]})
**分析日期**: {curr_date}

### 市场情绪概况
- 由于中文社交媒体情绪数据源暂未完全集成，当前提供基础分析
- 建议关注雪球、东方财富、同花顺等平台的讨论热度
- 港股市场还需关注香港本地财经媒体情绪

### 情绪指标
- 整体情绪: 中性
- 讨论热度: 待分析
- 投资者信心: 待评估

*注：完整的中文社交媒体情绪分析功能正在开发中*
"""
                result_data.append(sentiment_summary)
            except Exception as e:
                result_data.append(f"## 中文市场情绪\n获取失败: {e}")

        else:
            # 美股：使用Reddit情绪分析
            logger.info(f"🇺🇸 [统一情绪工具] 处理美股情绪...")

            try:
                from tradingagents.dataflows.interface import get_reddit_sentiment

                sentiment_data = get_reddit_sentiment(ticker, curr_date)
                result_data.append(f"## 美股Reddit情绪\n{sentiment_data}")
            except Exception as e:
                result_data.append(f"## 美股Reddit情绪\n获取失败: {e}")

        # 组合所有数据
        combined_result = f"""# {ticker} 情绪分析

**股票类型**: {market_info["market_name"]}
**分析日期**: {curr_date}

{chr(10).join(result_data)}

---
*数据来源: 根据股票类型自动选择最适合的情绪数据源*
"""

        logger.info(f"😊 [统一情绪工具] 数据获取完成，总长度: {len(combined_result)}")
        return combined_result

    except Exception as e:
        error_msg = f"统一情绪分析工具执行失败: {str(e)}"
        logger.error(f"❌ [统一情绪工具] {error_msg}")
        return error_msg
