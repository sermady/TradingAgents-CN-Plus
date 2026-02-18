# -*- coding: utf-8 -*-
"""
基本面数据接口模块

提供美股基本面数据获取功能，支持多数据源自动降级
"""

import os
from openai import OpenAI

from .base_interface import logger, get_config


def get_fundamentals_finnhub(ticker, curr_date):
    """
    使用Finnhub API获取股票基本面数据作为OpenAI的备选方案
    Args:
        ticker (str): 股票代码
        curr_date (str): 当前日期，格式为yyyy-mm-dd
    Returns:
        str: 格式化的基本面数据报告
    """
    try:
        import finnhub

        # 导入缓存管理器（统一入口）
        from ..cache import get_cache

        cache = get_cache()
        cached_key = cache.find_cached_fundamentals_data(ticker, data_source="finnhub")
        if cached_key:
            cached_data = cache.load_fundamentals_data(cached_key)
            if cached_data:
                logger.debug(f"💾 [DEBUG] 从缓存加载Finnhub基本面数据: {ticker}")
                return cached_data

        # 获取Finnhub API密钥
        api_key = os.getenv("FINNHUB_API_KEY")
        if not api_key:
            return "错误：未配置FINNHUB_API_KEY环境变量"

        # 初始化Finnhub客户端
        finnhub_client = finnhub.Client(api_key=api_key)

        logger.debug(f"📊 [DEBUG] 使用Finnhub API获取 {ticker} 的基本面数据...")

        # 获取基本财务数据
        try:
            basic_financials = finnhub_client.company_basic_financials(ticker, "all")
        except Exception as e:
            logger.error(f"❌ [DEBUG] Finnhub基本财务数据获取失败: {str(e)}")
            basic_financials = None

        # 获取公司概况
        try:
            company_profile = finnhub_client.company_profile2(symbol=ticker)
        except Exception as e:
            logger.error(f"❌ [DEBUG] Finnhub公司概况获取失败: {str(e)}")
            company_profile = None

        # 获取收益数据
        try:
            earnings = finnhub_client.company_earnings(ticker, limit=4)
        except Exception as e:
            logger.error(f"❌ [DEBUG] Finnhub收益数据获取失败: {str(e)}")
            earnings = None

        # 格式化报告
        report = f"# {ticker} 基本面分析报告（Finnhub数据源）\n\n"
        report += f"**数据获取时间**: {curr_date}\n"
        report += f"**数据来源**: Finnhub API\n\n"

        # 公司概况部分
        if company_profile:
            report += "## 公司概况\n"
            report += f"- **公司名称**: {company_profile.get('name', 'N/A')}\n"
            report += f"- **行业**: {company_profile.get('finnhubIndustry', 'N/A')}\n"
            report += f"- **国家**: {company_profile.get('country', 'N/A')}\n"
            report += f"- **货币**: {company_profile.get('currency', 'N/A')}\n"
            report += f"- **市值**: {company_profile.get('marketCapitalization', 'N/A')} 百万美元\n"
            report += f"- **流通股数**: {company_profile.get('shareOutstanding', 'N/A')} 百万股\n\n"

        # 基本财务指标
        if basic_financials and "metric" in basic_financials:
            metrics = basic_financials["metric"]
            report += "## 关键财务指标\n"
            report += "| 指标 | 数值 |\n"
            report += "|------|------|\n"

            # 估值指标
            if "peBasicExclExtraTTM" in metrics:
                report += f"| 市盈率 (PE) | {metrics['peBasicExclExtraTTM']:.2f} |\n"
            if "psAnnual" in metrics:
                report += f"| 市销率 (PS) | {metrics['psAnnual']:.2f} |\n"
            if "pbAnnual" in metrics:
                report += f"| 市净率 (PB) | {metrics['pbAnnual']:.2f} |\n"

            # 盈利能力指标
            if "roeTTM" in metrics:
                report += f"| 净资产收益率 (ROE) | {metrics['roeTTM']:.2f}% |\n"
            if "roaTTM" in metrics:
                report += f"| 总资产收益率 (ROA) | {metrics['roaTTM']:.2f}% |\n"
            if "netProfitMarginTTM" in metrics:
                report += f"| 净利润率 | {metrics['netProfitMarginTTM']:.2f}% |\n"

            # 财务健康指标
            if "currentRatioAnnual" in metrics:
                report += f"| 流动比率 | {metrics['currentRatioAnnual']:.2f} |\n"
            if "totalDebt/totalEquityAnnual" in metrics:
                report += (
                    f"| 负债权益比 | {metrics['totalDebt/totalEquityAnnual']:.2f} |\n"
                )

            report += "\n"

        # 收益历史
        if earnings:
            report += "## 收益历史\n"
            report += "| 季度 | 实际EPS | 预期EPS | 差异 |\n"
            report += "|------|---------|---------|------|\n"
            for earning in earnings[:4]:  # 显示最近4个季度
                actual = earning.get("actual", "N/A")
                estimate = earning.get("estimate", "N/A")
                period = earning.get("period", "N/A")
                surprise = earning.get("surprise", "N/A")
                report += f"| {period} | {actual} | {estimate} | {surprise} |\n"
            report += "\n"

        # 数据可用性说明
        report += "## 数据说明\n"
        report += "- 本报告使用Finnhub API提供的官方财务数据\n"
        report += "- 数据来源于公司财报和SEC文件\n"
        report += "- TTM表示过去12个月数据\n"
        report += "- Annual表示年度数据\n\n"

        if not basic_financials and not company_profile and not earnings:
            report += "⚠️ **警告**: 无法获取该股票的基本面数据，可能原因：\n"
            report += "- 股票代码不正确\n"
            report += "- Finnhub API限制\n"
            report += "- 该股票暂无基本面数据\n"

        # 保存到缓存
        if report and len(report) > 100:  # 只有当报告有实际内容时才缓存
            cache.save_fundamentals_data(ticker, report, data_source="finnhub")

        logger.debug(f"📊 [DEBUG] Finnhub基本面数据获取完成，报告长度: {len(report)}")
        return report

    except ImportError:
        return "错误：未安装finnhub-python库，请运行: pip install finnhub-python"
    except Exception as e:
        logger.error(f"❌ [DEBUG] Finnhub基本面数据获取失败: {str(e)}")
        return f"Finnhub基本面数据获取失败: {str(e)}"


def get_fundamentals_openai(ticker, curr_date):
    """
    获取美股基本面数据，使用数据源管理器自动选择和降级

    支持的数据源（按数据库配置的优先级）：
    - Alpha Vantage: 基本面和新闻数据（准确度高）
    - yfinance: 股票价格和基本信息（免费）
    - Finnhub: 备用数据源
    - OpenAI: 使用 AI 搜索基本面信息（需要配置）

    优先级从数据库 datasource_groupings 集合读取（market_category_id='us_stocks'）

    Args:
        ticker (str): 股票代码
        curr_date (str): 当前日期，格式为yyyy-mm-dd
    Returns:
        str: 基本面数据报告
    """
    try:
        # 导入缓存管理器和数据源管理器
        from ..cache import get_cache
        from ..data_source_manager import get_us_data_source_manager, USDataSource

        cache = get_cache()
        us_manager = get_us_data_source_manager()

        # 检查缓存 - 按数据源优先级检查
        data_source_cache_names = {
            USDataSource.ALPHA_VANTAGE: "alpha_vantage",
            USDataSource.YFINANCE: "yfinance",
            USDataSource.FINNHUB: "finnhub",
        }

        for source in us_manager.available_sources:
            if source == USDataSource.MONGODB:
                continue  # MongoDB 缓存单独处理

            cache_name = data_source_cache_names.get(source)
            if cache_name:
                cached_key = cache.find_cached_fundamentals_data(
                    ticker, data_source=cache_name
                )
                if cached_key:
                    cached_data = cache.load_fundamentals_data(cached_key)
                    if cached_data:
                        logger.info(
                            f"💾 [缓存] 从 {cache_name} 缓存加载基本面数据: {ticker}"
                        )
                        return cached_data

        # 🔥 从数据库获取数据源优先级顺序
        priority_order = us_manager._get_data_source_priority_order(ticker)
        logger.info(
            f"📊 [美股基本面] 数据源优先级: {[s.value for s in priority_order]}"
        )

        # 按优先级尝试每个数据源
        for source in priority_order:
            try:
                if source == USDataSource.ALPHA_VANTAGE:
                    result = _get_fundamentals_alpha_vantage(ticker, curr_date, cache)
                    if result:
                        return result

                elif source == USDataSource.YFINANCE:
                    result = _get_fundamentals_yfinance(ticker, curr_date, cache)
                    if result:
                        return result

                elif source == USDataSource.FINNHUB:
                    result = get_fundamentals_finnhub(ticker, curr_date)
                    if result and "❌" not in result:
                        cache.save_fundamentals_data(
                            ticker, result, data_source="finnhub"
                        )
                        return result

            except Exception as e:
                logger.warning(f"⚠️ [{source.value}] 获取失败: {e}，尝试下一个数据源")
                continue

        # 🔥 特殊处理：OpenAI（如果配置了）
        config = get_config()
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if (
            openai_api_key
            and config.get("backend_url")
            and config.get("quick_think_llm")
        ):
            backend_url = config.get("backend_url", "")
            if "openai.com" in backend_url:
                try:
                    logger.info(f"📊 [OpenAI] 尝试使用 OpenAI 获取基本面数据...")
                    return _get_fundamentals_openai_impl(
                        ticker, curr_date, config, cache
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [OpenAI] 获取失败: {e}")

        # 所有数据源都失败
        logger.error(f"❌ [美股基本面] 所有数据源都失败: {ticker}")
        return f"❌ 获取 {ticker} 基本面数据失败：所有数据源都不可用"

    except Exception as e:
        logger.error(f"❌ [美股基本面] 获取失败: {str(e)}")
        return f"❌ 获取 {ticker} 基本面数据失败: {str(e)}"


def _get_fundamentals_alpha_vantage(ticker, curr_date, cache):
    """
    从 Alpha Vantage 获取基本面数据

    Args:
        ticker: 股票代码
        curr_date: 当前日期
        cache: 缓存对象

    Returns:
        str: 基本面数据报告，失败返回 None
    """
    try:
        logger.info(f"📊 [Alpha Vantage] 获取 {ticker} 的基本面数据...")
        from ..providers.us.alpha_vantage_fundamentals import (
            get_fundamentals as get_av_fundamentals,
        )

        result = get_av_fundamentals(ticker, curr_date)

        if result and "Error" not in result and len(result) > 100:
            # 保存到缓存
            cache.save_fundamentals_data(ticker, result, data_source="alpha_vantage")
            logger.info(f"✅ [Alpha Vantage] 基本面数据获取成功: {ticker}")
            return result
        else:
            logger.warning(f"⚠️ [Alpha Vantage] 数据质量不佳")
            return None
    except Exception as e:
        logger.warning(f"⚠️ [Alpha Vantage] 获取失败: {e}")
        return None


def _get_fundamentals_yfinance(ticker, curr_date, cache):
    """
    从 yfinance 获取基本面数据

    Args:
        ticker: 股票代码
        curr_date: 当前日期
        cache: 缓存对象

    Returns:
        str: 基本面数据报告，失败返回 None
    """
    try:
        logger.info(f"📊 [yfinance] 获取 {ticker} 的基本面数据...")
        import yfinance as yf

        ticker_obj = yf.Ticker(ticker.upper())
        info = ticker_obj.info

        if info and len(info) > 5:  # 确保有实际数据
            # 格式化 yfinance 数据
            result = f"""# {ticker} 基本面数据 (来源: Yahoo Finance)

## 公司信息
- 公司名称: {info.get("longName", "N/A")}
- 行业: {info.get("industry", "N/A")}
- 板块: {info.get("sector", "N/A")}
- 网站: {info.get("website", "N/A")}

## 估值指标
- 市值: ${info.get("marketCap", "N/A"):,}
- PE比率: {info.get("trailingPE", "N/A")}
- 前瞻PE: {info.get("forwardPE", "N/A")}
- PB比率: {info.get("priceToBook", "N/A")}
- PS比率: {info.get("priceToSalesTrailing12Months", "N/A")}

## 财务指标
- 总收入: ${info.get("totalRevenue", "N/A"):,}
- 毛利润: ${info.get("grossProfits", "N/A"):,}
- EBITDA: ${info.get("ebitda", "N/A"):,}
- 每股收益(EPS): ${info.get("trailingEps", "N/A")}
- 股息率: {info.get("dividendYield", "N/A")}

## 盈利能力
- 利润率: {info.get("profitMargins", "N/A")}
- 营业利润率: {info.get("operatingMargins", "N/A")}
- ROE: {info.get("returnOnEquity", "N/A")}
- ROA: {info.get("returnOnAssets", "N/A")}

## 股价信息
- 当前价格: ${info.get("currentPrice", "N/A")}
- 52周最高: ${info.get("fiftyTwoWeekHigh", "N/A")}
- 52周最低: ${info.get("fiftyTwoWeekLow", "N/A")}
- 50日均线: ${info.get("fiftyDayAverage", "N/A")}
- 200日均线: ${info.get("twoHundredDayAverage", "N/A")}

## 分析师评级
- 目标价: ${info.get("targetMeanPrice", "N/A")}
- 推荐评级: {info.get("recommendationKey", "N/A")}

数据获取时间: {curr_date}
"""
            # 保存到缓存
            cache.save_fundamentals_data(ticker, result, data_source="yfinance")
            logger.info(f"✅ [yfinance] 基本面数据获取成功: {ticker}")
            return result
        else:
            logger.warning(f"⚠️ [yfinance] 数据不完整")
            return None
    except Exception as e:
        logger.warning(f"⚠️ [yfinance] 获取失败: {e}")
        return None


def _get_fundamentals_openai_impl(ticker, curr_date, config, cache):
    """
    OpenAI 基本面数据获取实现（内部函数）

    Args:
        ticker: 股票代码
        curr_date: 当前日期
        config: 配置对象
        cache: 缓存对象

    Returns:
        str: 基本面数据报告
    """
    try:
        logger.debug(f"📊 [OpenAI] 尝试使用OpenAI获取 {ticker} 的基本面数据...")

        client = OpenAI(base_url=config["backend_url"])

        response = client.responses.create(
            model=config["quick_think_llm"],
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": f"Can you search Fundamental for discussions on {ticker} during of the month before {curr_date} to the month of {curr_date}. Make sure you only get the data posted during that period. List as a table, with PE/PS/Cash flow/ etc",
                        }
                    ],
                }
            ],
            text={"format": {"type": "text"}},
            reasoning={},
            tools=[
                {
                    "type": "web_search_preview",
                    "user_location": {"type": "approximate"},
                    "search_context_size": "low",
                }
            ],
            temperature=1,
            max_output_tokens=4096,
            top_p=1,
            store=True,
        )

        # 提取响应文本，处理 Union 类型
        result = ""
        try:
            output_item = response.output[1]
            content = getattr(output_item, "content", None)
            if content and len(content) > 0:
                text = getattr(content[0], "text", None)
                if text:
                    result = text
        except (IndexError, AttributeError):
            pass

        # 保存到缓存
        if result and len(result) > 100:  # 只有当结果有实际内容时才缓存
            cache.save_fundamentals_data(ticker, result, data_source="openai")

        logger.info(f"✅ [OpenAI] 基本面数据获取成功: {ticker}")
        return result

    except Exception as e:
        logger.error(f"❌ [OpenAI] 基本面数据获取失败: {str(e)}")
        raise  # 抛出异常，让外层函数继续尝试其他数据源
