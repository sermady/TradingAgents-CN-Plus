# -*- coding: utf-8 -*-
"""
历史数据加载器
提供A股历史行情数据加载功能
"""

import os
from typing import Optional, Dict, Any

from .base_data_loader import BaseDataLoader, DataSourceError, logger
from ..cache.mongodb_cache_adapter import (
    get_mongodb_cache_adapter,
    get_stock_data_with_fallback,
)


class HistoricalDataLoader(BaseDataLoader):
    """
    历史数据加载器

    负责加载A股历史行情数据，支持多数据源自动降级
    """

    def __init__(self):
        super().__init__()
        self.mongodb_adapter = get_mongodb_cache_adapter()

    def load(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        force_refresh: bool = False,
        **kwargs
    ) -> str:
        """
        加载历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            force_refresh: 是否强制刷新缓存
            **kwargs: 其他参数

        Returns:
            格式化的历史数据字符串
        """
        logger.info(f"📈 获取A股历史数据: {symbol} ({start_date} 到 {end_date})")

        # 1. 优先尝试从MongoDB获取
        if not force_refresh:
            data = self._try_mongodb(symbol, start_date, end_date)
            if data:
                return data

        # 2. 检查文件缓存
        if not force_refresh and not self._check_skip_cache():
            data = self._try_file_cache(symbol, start_date, end_date)
            if data:
                return data

        # 3. 从API获取
        return self._fetch_from_api(symbol, start_date, end_date)

    def _try_mongodb(self, symbol: str, start_date: str, end_date: str) -> Optional[str]:
        """尝试从MongoDB获取数据"""
        if not self.mongodb_adapter.use_app_cache:
            return None

        try:
            df = self.mongodb_adapter.get_historical_data(symbol, start_date, end_date)
            if df is not None and not df.empty:
                logger.info(
                    f"📊 [数据来源: MongoDB] 使用MongoDB历史数据: {symbol} ({len(df)}条记录)"
                )
                return df.to_string()
        except Exception as e:
            logger.debug(f"从MongoDB获取数据失败: {e}")

        return None

    def _try_file_cache(self, symbol: str, start_date: str, end_date: str) -> Optional[str]:
        """尝试从文件缓存获取数据"""
        try:
            cache_key = self.cache.find_cached_stock_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                data_source="unified",
            )

            if cache_key:
                cached_data = self.cache.load_stock_data(cache_key)
                if cached_data:
                    logger.info(f"⚡ [数据来源: 文件缓存] 从缓存加载A股数据: {symbol}")
                    return cached_data
        except Exception as e:
            logger.debug(f"从文件缓存获取数据失败: {e}")

        return None

    def _fetch_from_api(self, symbol: str, start_date: str, end_date: str) -> str:
        """从API获取数据"""
        logger.info(f"🌐 [数据来源: API调用] 从统一数据源接口获取数据: {symbol}")

        try:
            self._wait_for_rate_limit()

            from ..data_source_manager import get_china_stock_data_unified

            # 获取分析日期
            analysis_date = self._get_analysis_date()

            call_kwargs = {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
            }
            if analysis_date:
                call_kwargs["analysis_date"] = analysis_date

            formatted_data = get_china_stock_data_unified(**call_kwargs)

            # 检查是否获取成功
            if "❌" in formatted_data or "错误" in formatted_data:
                logger.error(f"❌ [数据来源: API失败] 数据源API调用失败: {symbol}")
                return self._handle_api_error(symbol, start_date, end_date)

            # 保存到缓存
            self.cache.save_stock_data(
                symbol=symbol,
                data=formatted_data,
                start_date=start_date,
                end_date=end_date,
                data_source="unified",
            )

            logger.info(f"✅ [数据来源: API调用成功] A股数据获取成功: {symbol}")
            return formatted_data

        except Exception as e:
            error_msg = f"历史数据接口调用异常: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return self._handle_api_error(symbol, start_date, end_date, error_msg)

    def _handle_api_error(
        self, symbol: str, start_date: str, end_date: str, error_msg: str = ""
    ) -> str:
        """处理API错误，尝试返回旧缓存或备用数据"""
        # 尝试从旧缓存获取数据
        old_cache = self._try_get_old_cache(symbol, "stock_data")
        if old_cache:
            logger.info(f"📁 [数据来源: 过期缓存] 使用过期缓存数据: {symbol}")
            return old_cache

        # 生成备用数据
        logger.warning(f"⚠️ [数据来源: 备用数据] 生成备用数据: {symbol}")
        return self._generate_fallback_data(symbol, start_date, end_date, error_msg)


# 全局实例
_historical_data_loader: Optional[HistoricalDataLoader] = None


def get_historical_data_loader() -> HistoricalDataLoader:
    """获取全局历史数据加载器实例"""
    global _historical_data_loader
    if _historical_data_loader is None:
        _historical_data_loader = HistoricalDataLoader()
    return _historical_data_loader
