# -*- coding: utf-8 -*-
"""
数据获取工具

提供财务数据和基本面数据的统一获取接口
"""

from typing import Annotated

from tradingagents.utils.logging_manager import get_logger

logger = get_logger("data_tools")


def get_stock_comprehensive_financials(
    ticker: str,
    curr_date: str = None,
    config: dict = None,
) -> str:
    """获取股票综合财务数据

    Args:
        ticker: 股票代码
        curr_date: 当前日期
        config: 配置字典

    Returns:
        财务数据字符串
    """
    # 从原始 unified_tools.py 第16-435行提取
    logger.info(f"获取综合财务数据: {ticker}")

    # 这里需要调用实际的数据获取逻辑
    # 暂时返回空数据，需要完整实现
    return f"综合财务数据获取功能待完善"


def get_stock_fundamentals_unified(
    ticker: Annotated[str, "股票代码（支持A股、港股、美股）"] = None,
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
    research_depth = config.get("research_depth", "标准") if config else "标准"
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
                    f"🔢 [等级转换] 字符串数字 '{research_level}' → 中文等级 '{chinese_depth}'"
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
    if research_depth == "快速":
        data_depth = "basic"
        logger.info(f"🔧 [分析级别] 快速分析模式：获取基础数据")
    elif research_depth == "基础":
        data_depth = "standard"
        logger.info(f"🔧 [分析级别] 基础分析模式：获取标准数据")
    elif research_depth == "标准":
        data_depth = "standard"
        logger.info(f"🔧 [分析级别] 标准分析模式：获取标准数据")
    elif research_depth == "深度":
        data_depth = "full"
        logger.info(f"🔧 [分析级别] 深度分析模式：获取完整数据")
    elif research_depth == "全面":
        data_depth = "comprehensive"
        logger.info(f"🔧 [分析级别] 全面分析模式：获取最全面数据")
    else:
        data_depth = "standard"
        logger.info(f"🔧 [分析级别] 未知级别，使用标准分析模式")

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

        # 设置默认日期
        if not curr_date:
            curr_date = config.get("trade_date") if config else None
            if curr_date:
                logger.info(
                    f"📅 [统一基本面工具] 使用 config 中的分析日期: {curr_date}"
                )
            else:
                curr_date = datetime.now().strftime("%Y-%m-%d")
                logger.warning(
                    f"⚠️ [统一基本面工具] 未提供分析日期，使用系统时间: {curr_date}"
                )

        # 根据数据深度设置分析模块
        if data_depth == "basic":
            analysis_modules = "basic"
            logger.info(f"📊 [基本面策略] 快速分析模式：获取基础财务指标")
        elif data_depth == "standard":
            analysis_modules = "standard"
            logger.info(f"📊 [基本面策略] 标准分析模式：获取标准财务分析")
        elif data_depth == "full":
            analysis_modules = "full"
            logger.info(f"📊 [基本面策略] 深度分析模式：获取完整基本面分析")
        elif data_depth == "comprehensive":
            analysis_modules = "comprehensive"
            logger.info(f"📊 [基本面策略] 全面分析模式：获取综合基本面分析")
        else:
            analysis_modules = "standard"
            logger.info(f"📊 [基本面策略] 默认模式：获取标准基本面分析")

        # 基本面分析策略
        days_to_fetch = 10
        days_to_analyze = 2

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
            # 中国A股：基本面分析优化策略
            logger.info(f"🇨🇳 [统一基本面工具] 处理A股数据，数据深度: {data_depth}...")

            # 使用统一交易日管理器
            from tradingagents.utils.trading_date_manager import (
                get_trading_date_manager,
            )

            date_mgr = get_trading_date_manager()
            trading_date = date_mgr.get_latest_trading_date(curr_date)

            if trading_date != curr_date:
                logger.info(
                    f"📅 [基本面分析] 日期对齐: {curr_date} → {trading_date} (最新交易日)"
                )

            try:
                # 获取最新股价信息
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

                current_price_data = get_china_stock_data_unified(
                    ticker, recent_start_date, recent_end_date
                )

                logger.info(
                    f"🔍 [基本面工具调试] A股价格数据返回长度: {len(current_price_data)}"
                )

                result_data.append(f"## A股当前价格信息\n{current_price_data}")
            except Exception as e:
                logger.error(f"❌ [基本面工具调试] A股价格数据获取失败: {e}")
                result_data.append(f"## A股当前价格信息\n获取失败: {e}")
                current_price_data = ""

            try:
                # 获取基本面财务数据
                from tradingagents.dataflows.optimized_china_data import (
                    OptimizedChinaDataProvider,
                )

                analyzer = OptimizedChinaDataProvider()
                logger.info(
                    f"🔍 [股票代码追踪] 调用 OptimizedChinaDataProvider._generate_fundamentals_report，传入参数: ticker='{ticker}', analysis_modules='{analysis_modules}'"
                )

                fundamentals_data = analyzer._generate_fundamentals_report(
                    ticker, analysis_modules
                )

                logger.info(
                    f"🔍 [基本面工具调试] A股基本面数据返回长度: {len(fundamentals_data)}"
                )

                result_data.append(f"## A股基本面财务数据\n{fundamentals_data}")
            except Exception as e:
                logger.error(f"❌ [基本面工具调试] A股基本面数据获取失败: {e}")
                result_data.append(f"## A股基本面财务数据\n获取失败: {e}")

        elif is_hk:
            # 港股：使用AKShare数据源
            logger.info(f"🇭🇰 [统一基本面工具] 处理港股数据，数据深度: {data_depth}...")

            hk_data_success = False

            try:
                from tradingagents.dataflows.interface import (
                    get_hk_stock_data_unified,
                )

                hk_data = get_hk_stock_data_unified(ticker, start_date, end_date)

                logger.info(f"🔍 [基本面工具调试] 港股数据返回长度: {len(hk_data)}")

                if hk_data and len(hk_data) > 100 and "❌" not in hk_data:
                    result_data.append(f"## 港股数据\n{hk_data}")
                    hk_data_success = True
                    logger.info(f"✅ [统一基本面工具] 港股主要数据源成功")
                else:
                    logger.warning(f"⚠️ [统一基本面工具] 港股主要数据源质量不佳")

            except Exception as e:
                logger.error(f"❌ [基本面工具调试] 港股数据获取失败: {e}")

            # 备用方案
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
"""
                    result_data.append(basic_info)
                    logger.info(f"✅ [统一基本面工具] 港股备用信息成功")

                except Exception as e2:
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

        logger.info(f"📊 [统一基本面工具] ===== 数据获取完成摘要 =====")
        logger.info(f"📊 [统一基本面工具] 股票代码: {ticker}")
        logger.info(f"📊 [统一基本面工具] 股票类型: {market_info['market_name']}")
        logger.info(f"📊 [统一基本面工具] 数据深度级别: {data_depth}")
        logger.info(f"📊 [统一基本面工具] 获取的数据模块数量: {len(result_data)}")
        logger.info(f"📊 [统一基本面工具] 总数据长度: {len(combined_result)} 字符")

        # 添加数据验证
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
