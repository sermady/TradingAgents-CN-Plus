# -*- coding: utf-8 -*-
"""
并行数据源调用模块
Parallel Data Source Caller Module

实现数据源并行调用，尝试多个数据源并使用第一个成功的结果。
Implements parallel data source calling with first-successful-result strategy.

使用场景 Use Cases:
1. 提高数据获取速度 Try multiple sources simultaneously
2. 提升数据可用性 Improve data availability
3. 自动降级 fallback 机制

作者 Author: Claude
创建日期 Created: 2026-01-18
"""

import asyncio
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

from tradingagents.utils.logging_init import get_logger

logger = get_logger("parallel_data_fetch")


class ParallelDataFetcher:
    """并行数据获取器 - 同时调用多个数据源"""

    def __init__(self, data_source_manager):
        """初始化并行数据获取器 Initialize parallel fetcher"""
        self.data_source = data_source_manager

    async def fetch_with_fallback(
        self, fetch_func_name: str, *args, **kwargs
    ) -> Tuple[bool, Any, str]:
        """
        并行调用数据源，使用第一个成功的结果
        Parallel call data sources, use first successful result

        Args:
            fetch_func_name: 数据源方法名 Data source method name
            *args: 位置参数 Positional arguments
            **kwargs: 关键字参数 Keyword arguments

        Returns:
            (success, result, source_name) tuple
        """
        # 获取可用数据源列表
        available_sources = self._get_available_sources()

        if not available_sources:
            logger.warning("没有可用的数据源 No available data sources")
            return False, None, "none"

        logger.info(f"并行获取数据 Parallel fetching: {fetch_func_name}")
        logger.info(
            f"可用数据源 Available sources: {[s.value for s in available_sources]}"
        )

        # 创建并行任务
        tasks = []
        for source in available_sources:
            task = self._fetch_from_source(source, fetch_func_name, *args, **kwargs)
            tasks.append(task)

        # 并行执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 找到第一个成功的结果
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source_name = available_sources[i].value
                logger.debug(f"数据源失败 Source failed: {source_name} - {str(result)}")
            else:
                source_name = available_sources[i].value
                logger.info(f"数据源成功 Source success: {source_name}")
                # 取消其他任务
                for j, task in enumerate(tasks):
                    if j != i and not task.done():
                        task.cancel()
                return True, result, source_name

        logger.warning("所有数据源均失败 All data sources failed")
        return False, None, "none"

    async def _fetch_from_source(self, source, fetch_func_name: str, *args, **kwargs):
        """
        从指定数据源获取数据 Fetch data from specified source

        Args:
            source: 数据源枚举 Data source enum
            fetch_func_name: 方法名 Method name
            *args: 位置参数 Positional arguments
            **kwargs: 关键字参数 Keyword arguments

        Returns:
            数据获取结果 Fetch result
        """
        try:
            # 根据数据源类型调用不同的方法
            method = getattr(self.data_source, f"_get_{source.value}_data", None)

            if method is None:
                raise AttributeError(
                    f"Data source method not found: _get_{source.value}_data"
                )

            # 执行数据获取（使用事件循环执行同步方法）
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, lambda: method(fetch_func_name, *args, **kwargs)
            )

            return result

        except Exception as e:
            logger.debug(f"数据源异常 Source error [{source.value}]: {str(e)}")
            raise e

    def _get_available_sources(self) -> List:
        """获取可用数据源列表 Get available data sources"""
        # 从 DataSourceManager 获取可用数据源
        if hasattr(self.data_source, "available_sources"):
            return list(self.data_source.available_sources)
        else:
            # 默认数据源优先级
            from tradingagents.dataflows.providers.china import ChinaDataSource

            return [
                ChinaDataSource.TUSHARE,
                ChinaDataSource.AKSHARE,
                ChinaDataSource.BAOSTOCK,
            ]


async def fetch_stock_data_parallel(
    data_source_manager,
    symbol: str,
    start_date: str,
    end_date: str,
    timeout: float = 10.0,
) -> Tuple[bool, Any, str]:
    """
    并行获取股票数据 Parallel fetch stock data

    Args:
        data_source_manager: 数据源管理器 Data source manager
        symbol: 股票代码 Stock symbol
        start_date: 开始日期 Start date
        end_date: 结束日期 End date
        timeout: 超时时间（秒）Timeout in seconds

    Returns:
        (success, data, source_name) tuple
    """
    fetcher = ParallelDataFetcher(data_source_manager)

    try:
        # 设置超时
        result = await asyncio.wait_for(
            fetcher.fetch_with_fallback(
                "get_stock_data",
                symbol,
                start_date=start_date,
                end_date=end_date,
            ),
            timeout=timeout,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"获取股票数据超时 Fetch timeout: {symbol}")
        return False, None, "timeout"


async def fetch_fundamentals_parallel(
    data_source_manager,
    symbol: str,
    timeout: float = 10.0,
) -> Tuple[bool, Any, str]:
    """
    并行获取基本面数据 Parallel fetch fundamentals

    Args:
        data_source_manager: 数据源管理器 Data source manager
        symbol: 股票代码 Stock symbol
        timeout: 超时时间（秒）Timeout in seconds

    Returns:
        (success, data, source_name) tuple
    """
    fetcher = ParallelDataFetcher(data_source_manager)

    try:
        result = await asyncio.wait_for(
            fetcher.fetch_with_fallback(
                "get_fundamentals",
                symbol,
            ),
            timeout=timeout,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"获取基本面数据超时 Fetch timeout: {symbol}")
        return False, None, "timeout"


async def fetch_realtime_quote_parallel(
    data_source_manager,
    symbol: str,
    timeout: float = 5.0,
) -> Tuple[bool, Any, str]:
    """
    并行获取实时行情 Parallel fetch realtime quote

    Args:
        data_source_manager: 数据源管理器 Data source manager
        symbol: 股票代码 Stock symbol
        timeout: 超时时间（秒）Timeout in seconds

    Returns:
        (success, data, source_name) tuple
    """
    fetcher = ParallelDataFetcher(data_source_manager)

    try:
        result = await asyncio.wait_for(
            fetcher.fetch_with_fallback(
                "get_realtime_quote",
                symbol,
            ),
            timeout=timeout,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"获取实时行情超时 Fetch timeout: {symbol}")
        return False, None, "timeout"


# 工具函数
async def parallel_fetch_with_timeout(
    fetcher: ParallelDataFetcher,
    fetch_func_name: str,
    *args,
    timeout: float = 10.0,
    **kwargs,
) -> Tuple[bool, Any, str]:
    """
    带超时的并行数据获取工具函数 Parallel fetch with timeout

    Args:
        fetcher: ParallelDataFetcher instance
        fetch_func_name: 方法名 Method name
        *args: 位置参数 Positional arguments
        timeout: 超时时间 Timeout
        **kwargs: 关键字参数 Keyword arguments

    Returns:
        (success, data, source_name) tuple
    """
    try:
        result = await asyncio.wait_for(
            fetcher.fetch_with_fallback(fetch_func_name, *args, **kwargs),
            timeout=timeout,
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(f"并行获取超时 Parallel fetch timeout: {fetch_func_name}")
        return False, None, "timeout"
