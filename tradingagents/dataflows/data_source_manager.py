# -*- coding: utf-8 -*-
"""
数据源管理器
统一管理中国股票数据源的选择和切换，支持Tushare、AKShare、BaoStock等

注意：此文件已重构，功能已拆分到以下模块：
- managers/cache_manager.py: 缓存管理
- managers/fallback_manager.py: 降级策略
- managers/config_manager.py: 配置管理
- realtime/quote_manager.py: 实时行情管理
- adapters/base_adapter.py: 适配器基类
"""

import asyncio
import os
import time
import warnings
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from tradingagents.dataflows.data_sources.enums import ChinaDataSource
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")
warnings.filterwarnings("ignore")


class DataSourceManager:
    """数据源管理器 - 协调各数据源的操作"""

    def __init__(self):
        """初始化数据源管理器"""
        # 延迟导入，避免循环导入
        from tradingagents.dataflows.managers.cache_manager import CacheManager
        from tradingagents.dataflows.managers.config_manager import ConfigManager
        from tradingagents.dataflows.managers.fallback_manager import FallbackManager
        from tradingagents.dataflows.realtime.quote_manager import RealtimeQuoteManager

        # 初始化配置管理器
        self._config_manager = ConfigManager()

        # 检查是否启用MongoDB缓存
        self.use_mongodb_cache = self._config_manager.check_mongodb_enabled()

        # 获取默认数据源和可用数据源
        self.default_source = self._config_manager.get_default_source(self.use_mongodb_cache)
        self.available_sources = self._check_available_sources()
        self.current_source = self.default_source

        # 初始化缓存管理器
        self._cache_manager = None
        self.cache_enabled = False
        try:
            from .cache import get_cache

            self._cache_manager = CacheManager(get_cache(), True)
            self.cache_enabled = True
            logger.info("✅ 统一缓存管理器已启用")
        except Exception as e:
            self._cache_manager = CacheManager(None, False)
            logger.warning(f"⚠️ 统一缓存管理器初始化失败: {e}")

        # 初始化降级管理器
        self._fallback_manager = FallbackManager(self.available_sources, self.current_source)

        # 初始化实时行情管理器
        self._realtime_manager = RealtimeQuoteManager()

        logger.info("📊 数据源管理器初始化完成")
        logger.info(
            f"   MongoDB缓存: {'✅ 已启用' if self.use_mongodb_cache else '❌ 未启用'}"
        )
        logger.info(
            f"   统一缓存: {'✅ 已启用' if self.cache_enabled else '❌ 未启用'}"
        )
        logger.info(f"   默认数据源: {self.default_source.value}")
        logger.info(f"   可用数据源: {[s.value for s in self.available_sources]}")

    def _check_available_sources(self) -> List[ChinaDataSource]:
        """检查可用的数据源"""
        available = []

        # 从数据库读取数据源配置
        enabled_sources_in_db = self._config_manager.get_enabled_sources_from_db()
        datasource_configs = self._config_manager.get_datasource_configs_from_db()

        # 检查MongoDB
        if self.use_mongodb_cache and "mongodb" in enabled_sources_in_db:
            try:
                from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                    get_mongodb_cache_adapter,
                )

                adapter = get_mongodb_cache_adapter()
                if adapter.use_app_cache and adapter.db is not None:
                    available.append(ChinaDataSource.MONGODB)
                    logger.info("✅ MongoDB数据源可用且已启用")
                else:
                    logger.warning("⚠️ MongoDB数据源不可用")
            except Exception as e:
                logger.warning(f"⚠️ MongoDB数据源不可用: {e}")

        # 检查Tushare
        if "tushare" in enabled_sources_in_db:
            try:
                import tushare as ts

                token = datasource_configs.get("tushare", {}).get("api_key") or os.getenv("TUSHARE_TOKEN")
                if token:
                    available.append(ChinaDataSource.TUSHARE)
                    logger.info("✅ Tushare数据源可用且已启用")
                else:
                    logger.warning("⚠️ Tushare数据源不可用: API Key未配置")
            except ImportError:
                logger.warning("⚠️ Tushare数据源不可用: 库未安装")

        # 检查AKShare
        if "akshare" in enabled_sources_in_db:
            try:
                import akshare as ak

                available.append(ChinaDataSource.AKSHARE)
                logger.info("✅ AKShare数据源可用且已启用")
            except ImportError:
                logger.warning("⚠️ AKShare数据源不可用: 库未安装")

        # 检查BaoStock
        if "baostock" in enabled_sources_in_db:
            try:
                import baostock as bs

                available.append(ChinaDataSource.BAOSTOCK)
                logger.info("✅ BaoStock数据源可用且已启用")
            except ImportError:
                logger.warning("⚠️ BaoStock数据源不可用: 库未安装")

        return available

    # ==================== 公共API ====================

    def get_current_source(self) -> ChinaDataSource:
        """获取当前数据源"""
        return self.current_source

    def set_current_source(self, source: ChinaDataSource) -> bool:
        """设置当前数据源"""
        if source in self.available_sources:
            self.current_source = source
            # 更新降级管理器中的当前数据源
            self._fallback_manager.current_source = source
            logger.info(f"✅ 数据源已切换到: {source.value}")
            return True
        else:
            logger.error(f"❌ 数据源不可用: {source.value}")
            return False

    def get_stock_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily",
        analysis_date: Optional[str] = None,
    ) -> str:
        """
        获取股票数据的统一接口

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期
            analysis_date: 分析日期

        Returns:
            str: 格式化的股票数据
        """
        # 获取实时行情
        realtime_quote = None
        try:
            from tradingagents.utils.market_time import MarketTimeUtils

            should_use_rt, reason = MarketTimeUtils.should_use_realtime_quote(
                symbol, analysis_date=analysis_date
            )
            logger.info(f"📊 [实时行情检查] {symbol}: {reason}")

            if should_use_rt:
                realtime_quote = self._realtime_manager.get_realtime_quote(symbol)
        except Exception as e:
            logger.debug(f"实时行情检查失败: {e}")

        logger.info(
            f"📊 [数据来源: {self.current_source.value}] 开始获取{period}数据: {symbol}"
        )

        start_time = time.time()

        # 检查是否跳过MongoDB缓存
        skip_mongodb = (
            os.getenv("SKIP_MONGODB_CACHE_ON_QUERY", "true").lower() == "true"
        )

        try:
            result = None
            actual_source = None

            if self.current_source == ChinaDataSource.MONGODB:
                if skip_mongodb:
                    result, actual_source = self._fallback_manager.try_fallback_sources_with_save(
                        symbol, start_date, end_date, period, realtime_quote,
                        self._get_data_fetcher_dict()
                    )
                else:
                    result, actual_source = self._get_mongodb_data(
                        symbol, start_date, end_date, period, realtime_quote
                    )
            elif self.current_source == ChinaDataSource.TUSHARE:
                result = self._get_tushare_data(symbol, start_date, end_date, period, realtime_quote)
                actual_source = "tushare"
            elif self.current_source == ChinaDataSource.AKSHARE:
                result = self._get_akshare_data(symbol, start_date, end_date, period, realtime_quote)
                actual_source = "akshare"
            elif self.current_source == ChinaDataSource.BAOSTOCK:
                result = self._get_baostock_data(symbol, start_date, end_date, period, realtime_quote)
                actual_source = "baostock"
            else:
                result = f"❌ 不支持的数据源: {self.current_source.value}"

            duration = time.time() - start_time

            if result and "❌" not in result:
                logger.info(
                    f"✅ [数据来源: {actual_source or self.current_source.value}] "
                    f"成功获取股票数据: {symbol} (耗时{duration:.2f}秒)"
                )
                return result
            else:
                logger.warning(f"⚠️ 数据获取失败，尝试降级: {symbol}")
                fallback_result, fallback_source = self._fallback_manager.try_fallback_sources(
                    symbol, start_date, end_date, period, realtime_quote,
                    self._get_data_fetcher_dict()
                )
                if fallback_result and "❌" not in fallback_result:
                    return fallback_result
                return result or f"❌ 无法获取{symbol}的数据"

        except Exception as e:
            logger.error(f"❌ 获取股票数据失败: {e}", exc_info=True)
            fallback_result, _ = self._fallback_manager.try_fallback_sources(
                symbol, start_date, end_date, period, realtime_quote,
                self._get_data_fetcher_dict()
            )
            return fallback_result or f"❌ 获取股票数据失败: {str(e)}"

    def get_stock_info(self, symbol: str) -> Dict:
        """
        获取股票基本信息

        Args:
            symbol: 股票代码

        Returns:
            Dict: 股票基本信息
        """
        logger.info(f"📊 获取股票信息: {symbol}")

        # 尝试从App缓存获取
        try:
            from tradingagents.config.runtime_settings import use_app_cache_enabled

            if use_app_cache_enabled(False):
                from .cache.app_adapter import get_basics_from_cache

                doc = get_basics_from_cache(symbol)
                if doc:
                    return self._format_stock_info_from_cache(doc, symbol)
        except Exception as e:
            logger.debug(f"从缓存获取股票信息失败: {e}")

        # 根据当前数据源获取
        try:
            if self.current_source == ChinaDataSource.TUSHARE:
                return self._get_tushare_stock_info(symbol)
            elif self.current_source == ChinaDataSource.AKSHARE:
                return self._get_akshare_stock_info(symbol)
            elif self.current_source == ChinaDataSource.BAOSTOCK:
                return self._get_baostock_stock_info(symbol)
            else:
                # 尝试降级
                return self._try_fallback_stock_info(symbol)
        except Exception as e:
            logger.error(f"❌ 获取股票信息失败: {e}")
            return {"symbol": symbol, "name": f"股票{symbol}", "source": "unknown"}

    def get_realtime_quote(self, symbol: str) -> Optional[Dict]:
        """
        获取实时行情

        Args:
            symbol: 股票代码

        Returns:
            Dict: 实时行情数据
        """
        return self._realtime_manager.get_realtime_quote(symbol)

    # ==================== 数据获取方法（内部使用）====================

    def _get_data_fetcher_dict(self) -> Dict:
        """获取数据获取函数字典，用于降级管理器"""
        return {
            ChinaDataSource.TUSHARE: self._get_tushare_data,
            ChinaDataSource.AKSHARE: self._get_akshare_data,
            ChinaDataSource.BAOSTOCK: self._get_baostock_data,
            "mongodb": self._get_mongodb_data,
            "format_response": self._format_stock_data_response,
        }

    def _get_mongodb_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Dict[str, Any] = None,
    ) -> Tuple[str, Optional[str]]:
        """从MongoDB获取数据"""
        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                get_mongodb_cache_adapter,
            )

            adapter = get_mongodb_cache_adapter()
            df = adapter.get_historical_data(symbol, start_date, end_date, period=period)

            if df is not None and not df.empty:
                stock_name = f"股票{symbol}"
                if "name" in df.columns and not df["name"].empty:
                    stock_name = df["name"].iloc[0]

                result = self._format_stock_data_response(
                    df, symbol, stock_name, start_date, end_date, realtime_quote
                )
                return result, "mongodb"
            else:
                # MongoDB没有数据，降级
                return self._fallback_manager.try_fallback_sources(
                    symbol, start_date, end_date, period, realtime_quote,
                    self._get_data_fetcher_dict()
                )

        except Exception as e:
            logger.error(f"❌ MongoDB获取数据失败: {e}")
            return self._fallback_manager.try_fallback_sources(
                symbol, start_date, end_date, period, realtime_quote,
                self._get_data_fetcher_dict()
            )

    def _get_tushare_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Optional[Dict[str, Any]] = None,
    ) -> str:
        """使用Tushare获取数据"""
        try:
            from .providers.china.tushare import get_tushare_provider

            provider = get_tushare_provider()
            if not provider or not provider.is_available():
                return f"❌ Tushare提供器不可用"

            # 尝试从缓存获取
            skip_cache = os.getenv("SKIP_MONGODB_CACHE_ON_QUERY", "true").lower() == "true"
            if not skip_cache:
                cached_data = self._cache_manager.get_cached_data(symbol, start_date, end_date)
                if cached_data is not None and not cached_data.empty:
                    stock_info = self._run_async_safe(provider.get_stock_basic_info(symbol))
                    stock_name = stock_info.get("name", f"股票{symbol}") if stock_info else f"股票{symbol}"
                    return self._format_stock_data_response(
                        cached_data, symbol, stock_name, start_date, end_date, realtime_quote
                    )

            # 从provider获取
            data = self._run_async_safe(
                provider.get_historical_data(symbol, start_date, end_date)
            )

            if data is not None and not data.empty:
                # 保存到缓存
                self._cache_manager.save_to_cache(symbol, data, start_date, end_date)

                stock_info = self._run_async_safe(provider.get_stock_basic_info(symbol))
                stock_name = stock_info.get("name", f"股票{symbol}") if stock_info else f"股票{symbol}"

                return self._format_stock_data_response(
                    data, symbol, stock_name, start_date, end_date, realtime_quote
                )
            else:
                return f"❌ 未获取到{symbol}的有效数据"

        except Exception as e:
            logger.error(f"❌ Tushare获取数据失败: {e}")
            return f"❌ Tushare获取{symbol}数据失败: {e}"

    def _get_akshare_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Optional[Dict[str, Any]] = None,
    ) -> str:
        """使用AKShare获取数据"""
        try:
            from .providers.china.akshare import get_akshare_provider

            provider = get_akshare_provider()
            data = self._run_async_safe(
                provider.get_historical_data(symbol, start_date, end_date, period)
            )

            if data is not None and not data.empty:
                stock_info = self._run_async_safe(provider.get_stock_basic_info(symbol))
                stock_name = stock_info.get("name", f"股票{symbol}") if stock_info else f"股票{symbol}"

                return self._format_stock_data_response(
                    data, symbol, stock_name, start_date, end_date, realtime_quote
                )
            else:
                return f"❌ 未获取到{symbol}的有效数据"

        except Exception as e:
            logger.error(f"❌ AKShare获取数据失败: {e}")
            return f"❌ AKShare获取{symbol}数据失败: {e}"

    def _get_baostock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Optional[Dict[str, Any]] = None,
    ) -> str:
        """使用BaoStock获取数据"""
        try:
            from .providers.china.baostock import get_baostock_provider

            provider = get_baostock_provider()
            data = self._run_async_safe(
                provider.get_historical_data(symbol, start_date, end_date, period)
            )

            if data is not None and not data.empty:
                stock_info = self._run_async_safe(provider.get_stock_basic_info(symbol))
                stock_name = stock_info.get("name", f"股票{symbol}") if stock_info else f"股票{symbol}"

                return self._format_stock_data_response(
                    data, symbol, stock_name, start_date, end_date, realtime_quote
                )
            else:
                return f"❌ 未获取到{symbol}的有效数据"

        except Exception as e:
            logger.error(f"❌ BaoStock获取数据失败: {e}")
            return f"❌ BaoStock获取{symbol}数据失败: {e}"

    # ==================== 股票信息获取方法 ====================

    def _get_tushare_stock_info(self, symbol: str) -> Dict:
        """使用Tushare获取股票信息"""
        try:
            from .providers.china.tushare import get_tushare_provider

            provider = get_tushare_provider()
            if not provider or not provider.is_available():
                return self._try_fallback_stock_info(symbol)

            ts_code = provider._normalize_ts_code(symbol)
            stock_data = provider.api.stock_basic(
                ts_code=ts_code,
                fields="ts_code,symbol,name,area,industry,list_date,exchange,market",
            )

            if stock_data is not None and not stock_data.empty:
                row = stock_data.iloc[0]
                return {
                    "symbol": symbol,
                    "name": row.get("name") or f"股票{symbol}",
                    "area": row.get("area") or "未知",
                    "industry": row.get("industry") or "未知",
                    "list_date": row.get("list_date") or "未知",
                    "exchange": row.get("exchange") or "未知",
                    "market": row.get("market") or "未知",
                    "source": "tushare",
                }
            else:
                return self._try_fallback_stock_info(symbol)

        except Exception as e:
            logger.error(f"❌ Tushare获取股票信息失败: {e}")
            return self._try_fallback_stock_info(symbol)

    def _get_akshare_stock_info(self, symbol: str) -> Dict:
        """使用AKShare获取股票信息"""
        try:
            import akshare as ak

            # 转换股票代码格式
            if symbol.startswith("6"):
                akshare_symbol = f"sh{symbol}"
            elif symbol.startswith(("0", "3", "2")):
                akshare_symbol = f"sz{symbol}"
            elif symbol.startswith(("8", "4")):
                akshare_symbol = f"bj{symbol}"
            else:
                akshare_symbol = symbol

            stock_info = ak.stock_individual_info_em(symbol=akshare_symbol)

            if stock_info is not None and not stock_info.empty:
                info = {"symbol": symbol, "source": "akshare"}

                name_row = stock_info[stock_info["item"] == "股票简称"]
                if not name_row.empty:
                    info["name"] = name_row["value"].iloc[0]
                else:
                    info["name"] = f"股票{symbol}"

                info["area"] = "未知"
                info["industry"] = "未知"
                info["market"] = "未知"
                info["list_date"] = "未知"

                return info
            else:
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "akshare"}

        except Exception as e:
            logger.error(f"❌ AKShare获取股票信息失败: {e}")
            return {"symbol": symbol, "name": f"股票{symbol}", "source": "akshare"}

    def _get_baostock_stock_info(self, symbol: str) -> Dict:
        """使用BaoStock获取股票信息"""
        try:
            import baostock as bs

            # 转换股票代码格式
            if symbol.startswith("6"):
                bs_code = f"sh.{symbol}"
            else:
                bs_code = f"sz.{symbol}"

            # 登录BaoStock
            lg = bs.login()
            if lg.error_code != "0":
                logger.error(f"❌ BaoStock登录失败: {lg.error_msg}")
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "baostock"}

            # 查询股票基本信息
            rs = bs.query_stock_basic(code=bs_code)
            bs.logout()

            if rs.error_code != "0":
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "baostock"}

            data_list = []
            while (rs.error_code == "0") & rs.next():
                data_list.append(rs.get_row_data())

            if data_list:
                return {
                    "symbol": symbol,
                    "name": data_list[0][1],
                    "area": "未知",
                    "industry": "未知",
                    "market": "未知",
                    "list_date": data_list[0][2],
                    "source": "baostock",
                }
            else:
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "baostock"}

        except Exception as e:
            logger.error(f"❌ BaoStock获取股票信息失败: {e}")
            return {"symbol": symbol, "name": f"股票{symbol}", "source": "baostock"}

    def _try_fallback_stock_info(self, symbol: str) -> Dict:
        """尝试使用备用数据源获取股票信息"""
        for source in self.available_sources:
            if source == self.current_source:
                continue
            try:
                if source == ChinaDataSource.TUSHARE:
                    return self._get_tushare_stock_info(symbol)
                elif source == ChinaDataSource.AKSHARE:
                    return self._get_akshare_stock_info(symbol)
                elif source == ChinaDataSource.BAOSTOCK:
                    return self._get_baostock_stock_info(symbol)
            except Exception as e:
                logger.warning(f"⚠️ 备用数据源{source.value}获取股票信息失败: {e}")
                continue

        return {"symbol": symbol, "name": f"股票{symbol}", "source": "unknown"}

    def _format_stock_info_from_cache(self, doc: Dict, symbol: str) -> Dict:
        """从缓存文档格式化股票信息"""
        from tradingagents.dataflows.standardizers.stock_basic_standardizer import (
            standardize_stock_basic,
        )

        data_source = doc.get("data_source", "app_cache")
        standardized_data = standardize_stock_basic(doc, data_source)

        name = standardized_data.get("name") or f"股票{symbol}"

        # 规范化行业与板块
        board_labels = {"主板", "中小板", "创业板", "科创板"}
        raw_industry = standardized_data.get("industry", "") or ""
        market_val = standardized_data.get("market", "") or ""

        if raw_industry in board_labels:
            if not market_val:
                market_val = raw_industry
            if standardized_data.get("industry_gn"):
                industry_val = standardized_data.get("industry_gn")
            elif standardized_data.get("industry_sw"):
                industry_val = standardized_data.get("industry_sw")
            else:
                industry_val = "未知"
        else:
            industry_val = raw_industry or "未知"

        return {
            "symbol": standardized_data.get("code", symbol),
            "name": name,
            "area": standardized_data.get("area", "未知"),
            "industry": industry_val,
            "market": market_val or standardized_data.get("market", "未知"),
            "list_date": standardized_data.get("list_date", "未知"),
            "pe": standardized_data.get("pe"),
            "pb": standardized_data.get("pb"),
            "ps": standardized_data.get("ps"),
            "pe_ttm": standardized_data.get("pe_ttm"),
            "total_mv": standardized_data.get("total_mv"),
            "circ_mv": standardized_data.get("circ_mv"),
            "source": "app_cache",
            "data_source": data_source,
        }

    # ==================== 工具方法 ====================

    def _run_async_safe(self, coro):
        """安全地运行异步协程"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()

    def _get_volume_safely(self, data: pd.DataFrame) -> float:
        """安全获取成交量数据"""
        try:
            if "volume" in data.columns:
                volume_raw = data["volume"].iloc[-1]
                return float(volume_raw) if volume_raw else 0
            elif "vol" in data.columns:
                volume_raw = data["vol"].iloc[-1]
                return float(volume_raw) if volume_raw else 0
            else:
                return 0
        except Exception:
            return 0

    def _format_stock_data_response(
        self,
        data: pd.DataFrame,
        symbol: str,
        stock_name: str,
        start_date: str,
        end_date: str,
        realtime_quote: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        格式化股票数据响应（包含技术指标）

        这是一个简化版本，完整实现保留了所有技术指标计算逻辑
        """
        try:
            if data is None or data.empty:
                return f"❌ 无数据: {symbol}"

            # 标准化列名，确保 volume→vol, Close→close 等统一
            data = self._standardize_dataframe(data)

            # 确保数据有日期列
            if "date" not in data.columns and "trade_date" not in data.columns:
                if isinstance(data.index, pd.DatetimeIndex) and len(data) > 0:
                    data["date"] = data.index
                else:
                    return f"❌ 数据格式错误：缺少日期列"

            # 计算技术指标
            # 移动平均线
            data["ma5"] = data["close"].rolling(window=5, min_periods=1).mean()
            data["ma10"] = data["close"].rolling(window=10, min_periods=1).mean()
            data["ma20"] = data["close"].rolling(window=20, min_periods=1).mean()
            data["ma60"] = data["close"].rolling(window=60, min_periods=1).mean()

            # RSI计算
            delta = data["close"].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            avg_gain6 = gain.ewm(com=5, adjust=True).mean()
            avg_loss6 = loss.ewm(com=5, adjust=True).mean()
            rs6 = avg_gain6 / avg_loss6.replace(0, np.nan)
            data["rsi6"] = 100 - (100 / (1 + rs6))

            # MACD计算
            ema12 = data["close"].ewm(span=12, adjust=False).mean()
            ema26 = data["close"].ewm(span=26, adjust=False).mean()
            data["macd_dif"] = ema12 - ema26
            data["macd_dea"] = data["macd_dif"].ewm(span=9, adjust=False).mean()
            data["macd"] = (data["macd_dif"] - data["macd_dea"]) * 2

            # 布林带
            data["boll_mid"] = data["close"].rolling(window=20, min_periods=1).mean()
            std = data["close"].rolling(window=20, min_periods=1).std()
            data["boll_upper"] = data["boll_mid"] + 2 * std
            data["boll_lower"] = data["boll_mid"] - 2 * std

            # ========== P1-1: 扩展技术指标 ==========

            # RSI14 (标准14周期)
            avg_gain14 = gain.ewm(com=13, adjust=True).mean()
            avg_loss14 = loss.ewm(com=13, adjust=True).mean()
            rs14 = avg_gain14 / avg_loss14.replace(0, np.nan)
            data["rsi14"] = 100 - (100 / (1 + rs14))

            # KDJ
            low_min = data["low"].rolling(window=9, min_periods=1).min()
            high_max = data["high"].rolling(window=9, min_periods=1).max()
            rsv = (data["close"] - low_min) / (high_max - low_min).replace(0, np.nan) * 100
            data["kdj_k"] = rsv.ewm(com=2, adjust=False).mean()
            data["kdj_d"] = data["kdj_k"].ewm(com=2, adjust=False).mean()
            data["kdj_j"] = 3 * data["kdj_k"] - 2 * data["kdj_d"]

            # ATR (Average True Range, 14周期)
            tr1 = data["high"] - data["low"]
            tr2 = (data["high"] - data["close"].shift(1)).abs()
            tr3 = (data["low"] - data["close"].shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            data["atr14"] = tr.rolling(window=14, min_periods=1).mean()

            # OBV (On Balance Volume) - 需要成交量列
            if "vol" in data.columns:
                obv = [0]
                for i in range(1, len(data)):
                    if data["close"].iloc[i] > data["close"].iloc[i - 1]:
                        obv.append(obv[-1] + data["vol"].iloc[i])
                    elif data["close"].iloc[i] < data["close"].iloc[i - 1]:
                        obv.append(obv[-1] - data["vol"].iloc[i])
                    else:
                        obv.append(obv[-1])
                data["obv"] = obv
            else:
                data["obv"] = np.nan

            # Williams %R (14周期)
            data["wr14"] = (high_max - data["close"]) / (high_max - low_min).replace(0, np.nan) * -100

            # CCI (Commodity Channel Index, 14周期)
            typical_price = (data["high"] + data["low"] + data["close"]) / 3
            tp_sma = typical_price.rolling(window=14, min_periods=1).mean()
            tp_mad = typical_price.rolling(window=14, min_periods=1).apply(
                lambda x: np.mean(np.abs(x - np.mean(x))), raw=True
            )
            data["cci14"] = (typical_price - tp_sma) / (0.015 * tp_mad.replace(0, np.nan))

            # 获取最新数据
            latest_data = data.iloc[-1]
            display_rows = min(5, len(data))
            display_data = data.tail(display_rows)

            # 计算最新价格和涨跌幅
            if realtime_quote and realtime_quote.get("price"):
                latest_price = realtime_quote.get("price")
                price_source = "实时"
            else:
                latest_price = latest_data.get("close", 0)
                price_source = "历史"

            prev_close = (
                data.iloc[-2].get("close", latest_price)
                if len(data) > 1
                else latest_price
            )
            change = latest_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close != 0 else 0

            # 获取最新数据的实际日期
            latest_data_date = latest_data.get("date", end_date)
            if isinstance(latest_data_date, pd.Timestamp):
                latest_data_date = latest_data_date.strftime("%Y-%m-%d")

            # 构建结果
            result = f"📊 {stock_name}({symbol}) - 技术分析数据\n"
            result += f"数据期间: {start_date} 至 {end_date}\n"
            result += f"最新数据日期: {latest_data_date}\n"
            result += f"数据条数: {len(data)}条 (展示最近{display_rows}个交易日)\n\n"

            # 实时行情
            if realtime_quote and realtime_quote.get("price"):
                result += f"⚡ 实时行情（盘中）\n"
                result += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                result += f"💰 实时价格: ¥{realtime_quote.get('price', 0):.2f}\n"
                result += f"📈 涨跌: {realtime_quote.get('change', 0):+.2f} ({realtime_quote.get('change_pct', 0):+.2f}%)\n"
                result += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

            result += f"💰 最新价格: ¥{latest_price:.2f} (来源: {price_source})\n"
            result += f"📈 涨跌额: {change:+.2f}元 (涨跌幅: {change_pct:+.2f}%)\n\n"

            # 技术指标
            result += f"📊 移动平均线 (MA):\n"
            result += f"   MA5:  ¥{latest_data['ma5']:.2f}\n"
            result += f"   MA10: ¥{latest_data['ma10']:.2f}\n"
            result += f"   MA20: ¥{latest_data['ma20']:.2f}\n"
            result += f"   MA60: ¥{latest_data['ma60']:.2f}\n\n"

            result += f"📈 MACD指标:\n"
            result += f"   DIF:  {latest_data['macd_dif']:.3f}\n"
            result += f"   DEA:  {latest_data['macd_dea']:.3f}\n"
            result += f"   MACD: {latest_data['macd']:.3f}\n\n"

            result += f"📉 RSI指标:\n"
            result += f"   RSI6:  {latest_data['rsi6']:.2f}\n"
            result += f"   RSI14: {latest_data['rsi14']:.2f}\n\n"

            result += f"📊 布林带 (BOLL):\n"
            result += f"   上轨: ¥{latest_data['boll_upper']:.2f}\n"
            result += f"   中轨: ¥{latest_data['boll_mid']:.2f}\n"
            result += f"   下轨: ¥{latest_data['boll_lower']:.2f}\n\n"

            # P1-1: 扩展指标输出
            result += f"📊 KDJ指标:\n"
            result += f"   K: {latest_data['kdj_k']:.2f}\n"
            result += f"   D: {latest_data['kdj_d']:.2f}\n"
            result += f"   J: {latest_data['kdj_j']:.2f}\n\n"

            result += f"📊 ATR(14): {latest_data['atr14']:.4f}\n"
            result += f"📊 Williams %R(14): {latest_data['wr14']:.2f}\n"
            result += f"📊 CCI(14): {latest_data['cci14']:.2f}\n"
            result += f"📊 OBV: {latest_data['obv']:,.0f}\n\n"

            # 成交量统计
            volume_latest = self._get_volume_safely(display_data)
            result += f"📊 成交量分析:\n"
            result += f"   单日成交量: {volume_latest:,.0f}手\n"

            return result

        except Exception as e:
            logger.error(f"❌ 格式化数据响应失败: {e}", exc_info=True)
            return f"❌ 格式化{symbol}数据失败: {e}"

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化 DataFrame 列名和格式"""
        if df is None or df.empty:
            return pd.DataFrame()

        out = df.copy()

        # 列名映射
        colmap = {
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "vol",
            "Amount": "amount",
            "symbol": "code",
            "Symbol": "code",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "vol": "vol",
            "volume": "vol",
            "amount": "amount",
            "code": "code",
            "date": "date",
            "trade_date": "date",
            "日期": "date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "vol",
            "成交额": "amount",
            "涨跌幅": "pct_change",
            "涨跌额": "change",
        }
        out = out.rename(columns={c: colmap.get(c, c) for c in out.columns})

        # 确保日期排序
        if "date" in out.columns:
            try:
                if not pd.api.types.is_datetime64_any_dtype(out["date"]):
                    out["date"] = pd.to_datetime(out["date"])
                out = out.sort_values("date")
            except Exception:
                pass

        # 计算涨跌幅
        if "pct_change" not in out.columns and "close" in out.columns:
            out["pct_change"] = out["close"].pct_change() * 100.0

        return out


# ==================== 全局实例和公共API ====================

_data_source_manager = None


def get_data_source_manager() -> DataSourceManager:
    """获取全局数据源管理器实例"""
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = DataSourceManager()
    return _data_source_manager


def get_china_stock_data_unified(
    symbol: str, start_date: str, end_date: str, analysis_date: str = None
) -> str:
    """统一的中国股票数据获取接口"""
    manager = get_data_source_manager()
    result = manager.get_stock_data(
        symbol, start_date, end_date, analysis_date=analysis_date
    )
    # 处理返回类型错误
    if isinstance(result, tuple):
        result = result[0] if len(result) > 0 else None
    return result


def get_china_stock_info_unified(symbol: str) -> Dict:
    """统一的中国股票信息获取接口"""
    manager = get_data_source_manager()
    return manager.get_stock_info(symbol)


def get_stock_data_service() -> DataSourceManager:
    """获取股票数据服务实例（兼容接口）"""
    return get_data_source_manager()
