# -*- coding: utf-8 -*-
"""
港股数据接口模块

提供港股数据获取功能，支持多数据源自动降级
"""

from typing import Dict
from datetime import datetime

from .base_interface import logger, HK_STOCK_AVAILABLE, AKSHARE_HK_AVAILABLE
from .base_interface import get_hk_stock_data_akshare, get_hk_stock_info_akshare
from .config_reader import _get_enabled_hk_data_sources


def get_hk_stock_data_unified(
    symbol: str, start_date: str = None, end_date: str = None
) -> str:
    """
    获取港股数据的统一接口（根据用户配置选择数据源）

    Args:
        symbol: 港股代码 (如: 0700.HK)
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        str: 格式化的港股数据
    """
    try:
        logger.info(f"🇭🇰 获取港股数据: {symbol}")

        # 🔧 智能日期范围处理：自动扩展到配置的回溯天数，处理周末/节假日
        # 🔧 统一使用交易日管理器，确保所有分析师使用相同的日期基准
        from tradingagents.utils.trading_date_manager import get_trading_date_manager
        from app.core.config import get_settings

        original_start_date = start_date
        original_end_date = end_date

        # 从配置获取市场分析回溯天数（默认60天）
        try:
            settings = get_settings()
            lookback_days = settings.MARKET_ANALYST_LOOKBACK_DAYS
            logger.info(
                f"📅 [港股配置验证] MARKET_ANALYST_LOOKBACK_DAYS: {lookback_days}天"
            )
        except Exception as e:
            lookback_days = 60  # 默认60天
            logger.warning(
                f"⚠️ [港股配置验证] 无法获取配置，使用默认值: {lookback_days}天"
            )
            logger.warning(f"⚠️ [港股配置验证] 错误详情: {e}")

        # 使用 end_date 作为目标日期，向前回溯指定天数
        # 🔧 统一使用交易日管理器，确保所有分析师使用相同的日期基准
        date_mgr = get_trading_date_manager()
        start_date, end_date = date_mgr.get_trading_date_range(
            end_date, lookback_days=lookback_days
        )

        logger.info(
            f"📅 [港股智能日期] 原始输入: {original_start_date} 至 {original_end_date}"
        )
        logger.info(f"📅 [港股智能日期] 回溯天数: {lookback_days}天")
        logger.info(f"📅 [港股智能日期] 计算结果: {start_date} 至 {end_date}")
        logger.info(
            f"📅 [港股智能日期] 实际天数: {(datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days}天"
        )

        # 🔥 从数据库读取用户启用的数据源配置
        enabled_sources = _get_enabled_hk_data_sources()

        # 按优先级尝试各个数据源
        for source in enabled_sources:
            if source == "akshare" and AKSHARE_HK_AVAILABLE:
                try:
                    logger.info(f"🔄 使用AKShare获取港股数据: {symbol}")
                    result = get_hk_stock_data_akshare(symbol, start_date, end_date)
                    if result and "❌" not in result:
                        logger.info(f"✅ AKShare港股数据获取成功: {symbol}")
                        return result
                    else:
                        logger.warning(f"⚠️ AKShare返回错误结果，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ AKShare港股数据获取失败: {e}，尝试下一个数据源")

            elif source == "yfinance" and HK_STOCK_AVAILABLE:
                try:
                    from ..providers.hk.hk_stock import get_hk_stock_data

                    logger.info(f"🔄 使用Yahoo Finance获取港股数据: {symbol}")
                    result = get_hk_stock_data(symbol, start_date, end_date)
                    if result and "❌" not in result:
                        logger.info(f"✅ Yahoo Finance港股数据获取成功: {symbol}")
                        return result
                    else:
                        logger.warning(f"⚠️ Yahoo Finance返回错误结果，尝试下一个数据源")
                except Exception as e:
                    logger.error(
                        f"⚠️ Yahoo Finance港股数据获取失败: {e}，尝试下一个数据源"
                    )

            elif source == "finnhub":
                try:
                    # 导入美股数据提供器（支持新旧路径）
                    try:
                        from ..providers.us import OptimizedUSDataProvider

                        provider = OptimizedUSDataProvider()
                        get_us_stock_data_cached = provider.get_stock_data
                    except ImportError:
                        from tradingagents.dataflows.providers.us.optimized import (
                            get_us_stock_data_cached,
                        )

                    logger.info(f"🔄 使用FINNHUB获取港股数据: {symbol}")
                    result = get_us_stock_data_cached(symbol, start_date, end_date)
                    if result and "❌" not in result:
                        logger.info(f"✅ FINNHUB港股数据获取成功: {symbol}")
                        return result
                    else:
                        logger.warning(f"⚠️ FINNHUB返回错误结果，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ FINNHUB港股数据获取失败: {e}，尝试下一个数据源")

        # 所有数据源都失败
        error_msg = f"❌ 无法获取港股{symbol}数据 - 所有启用的数据源都不可用"
        logger.error(error_msg)
        return error_msg

    except Exception as e:
        logger.error(f"❌ 获取港股数据失败: {e}")
        return f"❌ 获取港股{symbol}数据失败: {e}"


def get_hk_stock_info_unified(symbol: str) -> Dict:
    """
    获取港股信息的统一接口（根据用户配置选择数据源）

    Args:
        symbol: 港股代码

    Returns:
        Dict: 港股信息
    """
    try:
        # 🔥 从数据库读取用户启用的数据源配置
        enabled_sources = _get_enabled_hk_data_sources()

        # 按优先级尝试各个数据源
        for source in enabled_sources:
            if source == "akshare" and AKSHARE_HK_AVAILABLE:
                try:
                    logger.info(f"🔄 使用AKShare获取港股信息: {symbol}")
                    result = get_hk_stock_info_akshare(symbol)
                    if (
                        result
                        and "error" not in result
                        and not result.get("name", "").startswith("港股")
                    ):
                        logger.info(
                            f"✅ AKShare成功获取港股信息: {symbol} -> {result.get('name', 'N/A')}"
                        )
                        return result
                    else:
                        logger.warning(f"⚠️ AKShare返回默认信息，尝试下一个数据源")
                except Exception as e:
                    logger.error(f"⚠️ AKShare港股信息获取失败: {e}，尝试下一个数据源")

            elif source == "yfinance" and HK_STOCK_AVAILABLE:
                try:
                    from ..providers.hk.hk_stock import get_hk_stock_info

                    logger.info(f"🔄 使用Yahoo Finance获取港股信息: {symbol}")
                    result = get_hk_stock_info(symbol)
                    if (
                        result
                        and "error" not in result
                        and not result.get("name", "").startswith("港股")
                    ):
                        logger.info(
                            f"✅ Yahoo Finance成功获取港股信息: {symbol} -> {result.get('name', 'N/A')}"
                        )
                        return result
                    else:
                        logger.warning(f"⚠️ Yahoo Finance返回默认信息，尝试下一个数据源")
                except Exception as e:
                    logger.error(
                        f"⚠️ Yahoo Finance港股信息获取失败: {e}，尝试下一个数据源"
                    )

        # 所有数据源都失败，返回基本信息
        logger.warning(f"⚠️ 所有启用的数据源都失败，使用默认信息: {symbol}")
        return {
            "symbol": symbol,
            "name": f"港股{symbol}",
            "currency": "HKD",
            "exchange": "HKG",
            "source": "fallback",
        }

    except Exception as e:
        logger.error(f"❌ 获取港股信息失败: {e}")
        return {
            "symbol": symbol,
            "name": f"港股{symbol}",
            "currency": "HKD",
            "exchange": "HKG",
            "source": "error",
            "error": str(e),
        }
