#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源管理器
统一管理中国股票数据源的选择和切换，支持Tushare、AKShare、BaoStock等
"""

import os
import time
import warnings
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")
warnings.filterwarnings("ignore")

# 导入统一日志系统
from tradingagents.utils.logging_init import setup_dataflow_logging

logger = setup_dataflow_logging()

# 导入统一数据源编码
from tradingagents.constants import DataSourceCode

# 导入数据标准化器
from tradingagents.dataflows.standardizers.stock_basic_standardizer import (
    standardize_stock_basic,
)


class ChinaDataSource(Enum):
    """
    中国股票数据源枚举

    注意：这个枚举与 tradingagents.constants.DataSourceCode 保持同步
    值使用统一的数据源编码
    """

    MONGODB = DataSourceCode.MONGODB  # MongoDB数据库缓存（最高优先级）
    TUSHARE = DataSourceCode.TUSHARE
    AKSHARE = DataSourceCode.AKSHARE
    BAOSTOCK = DataSourceCode.BAOSTOCK


class USDataSource(Enum):
    """
    美股数据源枚举

    注意：这个枚举与 tradingagents.constants.DataSourceCode 保持同步
    值使用统一的数据源编码
    """

    MONGODB = DataSourceCode.MONGODB  # MongoDB数据库缓存（最高优先级）
    YFINANCE = DataSourceCode.YFINANCE  # Yahoo Finance（免费，股票价格和技术指标）
    ALPHA_VANTAGE = DataSourceCode.ALPHA_VANTAGE  # Alpha Vantage（基本面和新闻）
    FINNHUB = DataSourceCode.FINNHUB  # Finnhub（备用数据源）


class DataSourceManager:
    """数据源管理器"""

    def __init__(self):
        """初始化数据源管理器"""
        # 检查是否启用MongoDB缓存
        self.use_mongodb_cache = self._check_mongodb_enabled()

        self.default_source = self._get_default_source()
        self.available_sources = self._check_available_sources()
        self.current_source = self.default_source

        # 初始化统一缓存管理器
        self.cache_manager = None
        self.cache_enabled = False
        try:
            from .cache import get_cache

            self.cache_manager = get_cache()
            self.cache_enabled = True
            logger.info(f"✅ 统一缓存管理器已启用")
        except Exception as e:
            logger.warning(f"⚠️ 统一缓存管理器初始化失败: {e}")

        logger.info(f"📊 数据源管理器初始化完成")
        logger.info(
            f"   MongoDB缓存: {'✅ 已启用' if self.use_mongodb_cache else '❌ 未启用'}"
        )
        logger.info(
            f"   统一缓存: {'✅ 已启用' if self.cache_enabled else '❌ 未启用'}"
        )
        logger.info(f"   默认数据源: {self.default_source.value}")
        logger.info(f"   可用数据源: {[s.value for s in self.available_sources]}")

    def _check_mongodb_enabled(self) -> bool:
        """检查是否启用MongoDB缓存"""
        from tradingagents.config.runtime_settings import use_app_cache_enabled

        return use_app_cache_enabled()

    def _get_data_source_priority_order(
        self, symbol: Optional[str] = None
    ) -> List[ChinaDataSource]:
        """
        从环境变量获取数据源优先级顺序（用于降级）

        🔥 重构说明 (2026-02-01):
        - 不再从数据库读取配置，全部从 .env 文件获取
        - 默认优先级：Tushare > AKShare > BaoStock
        - MongoDB 仅用于保存，不作为查询优先源

        Args:
            symbol: 股票代码，用于识别市场类型（A股/美股/港股）

        Returns:
            按优先级排序的数据源列表
        """
        # 🔥 从环境变量读取配置
        env_priority = os.getenv(
            "HISTORICAL_DATA_SOURCE_PRIORITY", "tushare,akshare,baostock"
        )

        # 解析环境变量配置
        source_mapping = {
            "tushare": ChinaDataSource.TUSHARE,
            "akshare": ChinaDataSource.AKSHARE,
            "baostock": ChinaDataSource.BAOSTOCK,
        }

        result = []
        for source_name in env_priority.split(","):
            source_name = source_name.strip().lower()
            if source_name in source_mapping:
                source = source_mapping[source_name]
                if source in self.available_sources:
                    result.append(source)

        if result:
            logger.info(f"✅ [数据源优先级] 从.env读取: {[s.value for s in result]}")
            return result

        # 🔥 回退到默认顺序
        # 默认顺序：Tushare > AKShare > BaoStock
        default_order = [
            ChinaDataSource.TUSHARE,
            ChinaDataSource.AKSHARE,
            ChinaDataSource.BAOSTOCK,
        ]

        logger.warning(
            f"⚠️ [数据源优先级] .env配置无效，使用默认顺序: {[s.value for s in default_order if s in self.available_sources]}"
        )

        # 只返回可用的数据源
        return [s for s in default_order if s in self.available_sources]

    def _identify_market_category(self, symbol: Optional[str]) -> Optional[str]:
        """
        识别股票代码所属的市场分类

        Args:
            symbol: 股票代码

        Returns:
            市场分类ID（a_shares/us_stocks/hk_stocks），如果无法识别则返回None
        """
        if not symbol:
            return None

        try:
            from tradingagents.utils.stock_utils import StockMarket, StockUtils

            market = StockUtils.identify_stock_market(symbol)

            # 映射到市场分类ID
            market_mapping = {
                StockMarket.CHINA_A: "a_shares",
                StockMarket.US: "us_stocks",
                StockMarket.HONG_KONG: "hk_stocks",
            }

            category = market_mapping.get(market)
            if category:
                logger.debug(f"🔍 [市场识别] {symbol} → {category}")
            return category
        except Exception as e:
            logger.warning(f"⚠️ [市场识别] 识别失败: {e}")
            return None

    def _get_default_source(self) -> ChinaDataSource:
        """获取默认数据源"""
        # 如果启用MongoDB缓存，MongoDB作为最高优先级数据源
        if self.use_mongodb_cache:
            return ChinaDataSource.MONGODB

        # 从环境变量获取，默认使用AKShare作为第一优先级数据源
        env_source = os.getenv(
            "DEFAULT_CHINA_DATA_SOURCE", DataSourceCode.AKSHARE
        ).lower()

        # 映射到枚举（使用统一编码）
        source_mapping: Dict[str, ChinaDataSource] = {
            DataSourceCode.TUSHARE.value: ChinaDataSource.TUSHARE,
            DataSourceCode.AKSHARE.value: ChinaDataSource.AKSHARE,
            DataSourceCode.BAOSTOCK.value: ChinaDataSource.BAOSTOCK,
        }

        return source_mapping.get(env_source, ChinaDataSource.AKSHARE)

    # ==================== Tushare数据接口 ====================

    def get_china_stock_data_tushare(
        self, symbol: str, start_date: str, end_date: str
    ) -> str:
        """
        使用Tushare获取中国A股历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            str: 格式化的股票数据报告
        """
        # 临时切换到Tushare数据源
        original_source = self.current_source
        self.current_source = ChinaDataSource.TUSHARE

        try:
            result = self._get_tushare_data(symbol, start_date, end_date)
            return result
        finally:
            # 恢复原始数据源
            self.current_source = original_source

    def get_fundamentals_data(self, symbol: str) -> str:
        """
        获取基本面数据，支持多数据源和自动降级
        优先级：MongoDB → Tushare → AKShare → 生成分析

        Tushare 数据源会获取完整的财务数据：
        1. 估值指标 (PE, PB, PS) - daily_basic
        2. 财务指标 (ROE, ROA 等) - fina_indicator
        3. 财务报表 (利润表、资产负债表、现金流量表) - income/balancesheet/cashflow

        Args:
            symbol: 股票代码

        Returns:
            str: 基本面分析报告
        """
        logger.info(
            f"📊 [数据来源: {self.current_source.value}] 开始获取基本面数据: {symbol}",
            extra={
                "symbol": symbol,
                "data_source": self.current_source.value,
                "event_type": "fundamentals_fetch_start",
            },
        )

        start_time = time.time()

        try:
            # 根据数据源调用相应的获取方法
            if self.current_source == ChinaDataSource.MONGODB:
                result = self._get_mongodb_fundamentals(symbol)
            elif self.current_source == ChinaDataSource.TUSHARE:
                # 🔥 使用 Tushare 获取完整的基本面数据
                # 1. 估值指标 (PE, PB, PS)
                result = self._get_tushare_fundamentals(symbol)

                # 2. 附加财务指标 (ROE, ROA 等)
                indicators = self._get_tushare_financial_indicators(symbol)
                if indicators and "❌" not in indicators:
                    result += indicators

                # 3. 附加财务报表 (利润表、资产负债表、现金流量表)
                reports = self._get_tushare_financial_reports(symbol)
                if reports and "❌" not in reports:
                    result += reports
            elif self.current_source == ChinaDataSource.AKSHARE:
                result = self._get_akshare_fundamentals(symbol)
            else:
                # 其他数据源暂不支持基本面数据，生成基本分析
                result = self._generate_fundamentals_analysis(symbol)

            # 检查结果
            duration = time.time() - start_time
            result_length = len(result) if result else 0

            if result and "❌" not in result:
                logger.info(
                    f"✅ [数据来源: {self.current_source.value}] 成功获取基本面数据: {symbol} ({result_length}字符, 耗时{duration:.2f}秒)",
                    extra={
                        "symbol": symbol,
                        "data_source": self.current_source.value,
                        "duration": duration,
                        "result_length": result_length,
                        "event_type": "fundamentals_fetch_success",
                    },
                )
                return result
            else:
                logger.warning(
                    f"⚠️ [数据来源: {self.current_source.value}失败] 基本面数据质量异常，尝试降级: {symbol}",
                    extra={
                        "symbol": symbol,
                        "data_source": self.current_source.value,
                        "event_type": "fundamentals_fetch_fallback",
                    },
                )
                return self._try_fallback_fundamentals(symbol)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"❌ [数据来源: {self.current_source.value}异常] 获取基本面数据失败: {symbol} - {e}",
                extra={
                    "symbol": symbol,
                    "data_source": self.current_source.value,
                    "duration": duration,
                    "error": str(e),
                    "event_type": "fundamentals_fetch_exception",
                },
                exc_info=True,
            )
            return self._try_fallback_fundamentals(symbol)

    def get_china_stock_fundamentals_tushare(self, symbol: str) -> str:
        """
        使用Tushare获取中国股票基本面数据（兼容旧接口）

        Args:
            symbol: 股票代码

        Returns:
            str: 基本面分析报告
        """
        # 重定向到统一接口
        return self._get_tushare_fundamentals(symbol)

    def get_news_data(
        self, symbol: Optional[str] = None, hours_back: int = 24, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取新闻数据的统一接口，支持多数据源和自动降级
        优先级：MongoDB → Tushare → AKShare

        Args:
            symbol: 股票代码，为空则获取市场新闻
            hours_back: 回溯小时数
            limit: 返回数量限制

        Returns:
            List[Dict]: 新闻数据列表
        """
        logger.info(
            f"📰 [数据来源: {self.current_source.value}] 开始获取新闻数据: {symbol or '市场新闻'}, 回溯{hours_back}小时",
            extra={
                "symbol": symbol,
                "hours_back": hours_back,
                "limit": limit,
                "data_source": self.current_source.value,
                "event_type": "news_fetch_start",
            },
        )

        start_time = time.time()

        try:
            # 根据数据源调用相应的获取方法
            if self.current_source == ChinaDataSource.MONGODB:
                result = self._get_mongodb_news(symbol, hours_back, limit)
            elif self.current_source == ChinaDataSource.TUSHARE:
                result = self._get_tushare_news(symbol, hours_back, limit)
            elif self.current_source == ChinaDataSource.AKSHARE:
                result = self._get_akshare_news(symbol, hours_back, limit)
            else:
                # 其他数据源暂不支持新闻数据
                logger.warning(f"⚠️ 数据源 {self.current_source.value} 不支持新闻数据")
                result = []

            # 检查结果
            duration = time.time() - start_time
            result_count = len(result) if result else 0

            if result and result_count > 0:
                logger.info(
                    f"✅ [数据来源: {self.current_source.value}] 成功获取新闻数据: {symbol or '市场新闻'} ({result_count}条, 耗时{duration:.2f}秒)",
                    extra={
                        "symbol": symbol,
                        "data_source": self.current_source.value,
                        "news_count": result_count,
                        "duration": duration,
                        "event_type": "news_fetch_success",
                    },
                )
                return result
            else:
                logger.warning(
                    f"⚠️ [数据来源: {self.current_source.value}] 未获取到新闻数据: {symbol or '市场新闻'}，尝试降级",
                    extra={
                        "symbol": symbol,
                        "data_source": self.current_source.value,
                        "duration": duration,
                        "event_type": "news_fetch_fallback",
                    },
                )
                return self._try_fallback_news(symbol, hours_back, limit)

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"❌ [数据来源: {self.current_source.value}异常] 获取新闻数据失败: {symbol or '市场新闻'} - {e}",
                extra={
                    "symbol": symbol,
                    "data_source": self.current_source.value,
                    "duration": duration,
                    "error": str(e),
                    "event_type": "news_fetch_exception",
                },
                exc_info=True,
            )
            return self._try_fallback_news(symbol, hours_back, limit)

    def _check_available_sources(self) -> List[ChinaDataSource]:
        """
        检查可用的数据源

        检查逻辑：
        1. 检查依赖包是否安装（技术可用性）
        2. 检查数据库配置中是否启用（业务可用性）

        Returns:
            可用且已启用的数据源列表
        """
        available = []

        # 🔥 从数据库读取数据源配置，获取启用状态
        enabled_sources_in_db = set()
        try:
            from app.core.database import get_mongo_db_sync

            db = get_mongo_db_sync()
            config_collection = db.system_configs

            # 获取最新的激活配置
            config_data = config_collection.find_one(
                {"is_active": True}, sort=[("version", -1)]
            )

            if config_data and config_data.get("data_source_configs"):
                data_source_configs = config_data.get("data_source_configs", [])

                # 提取已启用的数据源类型
                for ds in data_source_configs:
                    if ds.get("enabled", True):
                        ds_type = ds.get("type", "").lower()
                        enabled_sources_in_db.add(ds_type)

                logger.info(
                    f"✅ [数据源配置] 从数据库读取到已启用的数据源: {enabled_sources_in_db}"
                )
            else:
                logger.warning(
                    "⚠️ [数据源配置] 数据库中没有数据源配置，将检查所有已安装的数据源"
                )
                # 如果数据库中没有配置，默认所有数据源都启用
                enabled_sources_in_db = {"mongodb", "tushare", "akshare", "baostock"}
        except Exception as e:
            logger.warning(
                f"⚠️ [数据源配置] 从数据库读取失败: {e}，将检查所有已安装的数据源"
            )
            # 如果读取失败，默认所有数据源都启用
            enabled_sources_in_db = {"mongodb", "tushare", "akshare", "baostock"}

        # 检查MongoDB（最高优先级）
        if self.use_mongodb_cache and "mongodb" in enabled_sources_in_db:
            try:
                from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                    get_mongodb_cache_adapter,
                )

                adapter = get_mongodb_cache_adapter()
                if adapter.use_app_cache and adapter.db is not None:
                    available.append(ChinaDataSource.MONGODB)
                    logger.info("✅ MongoDB数据源可用且已启用（最高优先级）")
                else:
                    logger.warning("⚠️ MongoDB数据源不可用: 数据库未连接")
            except Exception as e:
                logger.warning(f"⚠️ MongoDB数据源不可用: {e}")
        elif self.use_mongodb_cache and "mongodb" not in enabled_sources_in_db:
            logger.info("ℹ️ MongoDB数据源已在数据库中禁用")

        # 从数据库读取数据源配置
        datasource_configs = self._get_datasource_configs_from_db()

        # 检查Tushare
        if "tushare" in enabled_sources_in_db:
            try:
                import tushare as ts

                # 优先从数据库配置读取 API Key，其次从环境变量读取
                token = datasource_configs.get("tushare", {}).get(
                    "api_key"
                ) or os.getenv("TUSHARE_TOKEN")
                if token:
                    available.append(ChinaDataSource.TUSHARE)
                    source = (
                        "数据库配置"
                        if datasource_configs.get("tushare", {}).get("api_key")
                        else "环境变量"
                    )
                    logger.info(f"✅ Tushare数据源可用且已启用 (API Key来源: {source})")
                else:
                    logger.warning(
                        "⚠️ Tushare数据源不可用: API Key未配置（数据库和环境变量均未找到）"
                    )
            except ImportError:
                logger.warning("⚠️ Tushare数据源不可用: 库未安装")
        else:
            logger.info("ℹ️ Tushare数据源已在数据库中禁用")

        # 检查AKShare
        if "akshare" in enabled_sources_in_db:
            try:
                import akshare as ak

                available.append(ChinaDataSource.AKSHARE)
                logger.info("✅ AKShare数据源可用且已启用")
            except ImportError:
                logger.warning("⚠️ AKShare数据源不可用: 库未安装")
        else:
            logger.info("ℹ️ AKShare数据源已在数据库中禁用")

        # 检查BaoStock
        if "baostock" in enabled_sources_in_db:
            try:
                import baostock as bs

                available.append(ChinaDataSource.BAOSTOCK)
                logger.info(f"✅ BaoStock数据源可用且已启用")
            except ImportError:
                logger.warning(f"⚠️ BaoStock数据源不可用: 库未安装")
        else:
            logger.info("ℹ️ BaoStock数据源已在数据库中禁用")

        # TDX (通达信) 已移除
        # 不再检查和支持 TDX 数据源

        return available

    def _get_datasource_configs_from_db(self) -> dict:
        """从数据库读取数据源配置（包括 API Key）"""
        try:
            from app.core.database import get_mongo_db_sync

            db = get_mongo_db_sync()

            # 从 system_configs 集合读取激活的配置
            config = db.system_configs.find_one({"is_active": True})
            if not config:
                return {}

            # 提取数据源配置
            datasource_configs = config.get("data_source_configs", [])

            # 构建配置字典 {数据源名称: {api_key, api_secret, ...}}
            result = {}
            for ds_config in datasource_configs:
                name = ds_config.get("name", "").lower()
                result[name] = {
                    "api_key": ds_config.get("api_key", ""),
                    "api_secret": ds_config.get("api_secret", ""),
                    "config_params": ds_config.get("config_params", {}),
                }

            return result
        except Exception as e:
            logger.warning(f"⚠️ 从数据库读取数据源配置失败: {e}")
            return {}

    def get_current_source(self) -> ChinaDataSource:
        """获取当前数据源"""
        return self.current_source

    def set_current_source(self, source: ChinaDataSource) -> bool:
        """设置当前数据源"""
        if source in self.available_sources:
            self.current_source = source
            logger.info(f"✅ 数据源已切换到: {source.value}")
            return True
        else:
            logger.error(f"❌ 数据源不可用: {source.value}")
            return False

    def get_data_adapter(self):
        """获取当前数据源的适配器"""
        if self.current_source == ChinaDataSource.MONGODB:
            return self._get_mongodb_adapter()
        elif self.current_source == ChinaDataSource.TUSHARE:
            return self._get_tushare_adapter()
        elif self.current_source == ChinaDataSource.AKSHARE:
            return self._get_akshare_adapter()
        elif self.current_source == ChinaDataSource.BAOSTOCK:
            return self._get_baostock_adapter()
        # TDX 已移除
        else:
            raise ValueError(f"不支持的数据源: {self.current_source}")

    def _get_mongodb_adapter(self):
        """获取MongoDB适配器"""
        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                get_mongodb_cache_adapter,
            )

            return get_mongodb_cache_adapter()
        except ImportError as e:
            logger.error(f"❌ MongoDB适配器导入失败: {e}")
            return None

    def _get_tushare_adapter(self):
        """获取Tushare提供器（原adapter已废弃，现在直接使用provider）"""
        try:
            from .providers.china.tushare import get_tushare_provider

            return get_tushare_provider()
        except ImportError as e:
            logger.error(f"❌ Tushare提供器导入失败: {e}")
            return None

    def _get_akshare_adapter(self):
        """获取AKShare适配器"""
        try:
            from .providers.china.akshare import get_akshare_provider

            return get_akshare_provider()
        except ImportError as e:
            logger.error(f"❌ AKShare适配器导入失败: {e}")
            return None

    def _get_baostock_adapter(self):
        """获取BaoStock适配器"""
        try:
            from .providers.china.baostock import get_baostock_provider

            return get_baostock_provider()
        except ImportError as e:
            logger.error(f"❌ BaoStock适配器导入失败: {e}")
            return None

    # TDX 适配器已移除
    # def _get_tdx_adapter(self):
    #     """获取TDX适配器 (已移除)"""
    #     logger.error(f"❌ TDX数据源已不再支持")
    #     return None

    def _get_cached_data(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        max_age_hours: int = 24,
    ) -> Optional[pd.DataFrame]:
        """
        从缓存获取数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            max_age_hours: 最大缓存时间（小时）

        Returns:
            DataFrame: 缓存的数据，如果没有则返回None
        """
        if not self.cache_enabled or not self.cache_manager:
            return None

        try:
            cache_key = self.cache_manager.find_cached_stock_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                max_age_hours=max_age_hours,
            )

            if cache_key:
                cached_data = self.cache_manager.load_stock_data(cache_key)
                if (
                    cached_data is not None
                    and hasattr(cached_data, "empty")
                    and not cached_data.empty
                ):
                    logger.debug(f"📦 从缓存获取{symbol}数据: {len(cached_data)}条")
                    return cached_data
        except Exception as e:
            logger.warning(f"⚠️ 从缓存读取数据失败: {e}")

        return None

    def _save_to_cache(
        self,
        symbol: str,
        data: pd.DataFrame,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ):
        """
        保存数据到缓存

        Args:
            symbol: 股票代码
            data: 数据
            start_date: 开始日期
            end_date: 结束日期
        """
        if not self.cache_enabled or not self.cache_manager:
            return

        try:
            if data is not None and hasattr(data, "empty") and not data.empty:
                self.cache_manager.save_stock_data(symbol, data, start_date, end_date)
                logger.debug(f"💾 保存{symbol}数据到缓存: {len(data)}条")
        except Exception as e:
            logger.warning(f"⚠️ 保存数据到缓存失败: {e}")

    def _get_smart_ttl(self, data_category: str) -> int:
        """
        获取分级缓存TTL（支持财报发布日期感知）

        使用 SmartCache 的分级缓存策略：
        - L1（实时）: 估值指标，1小时缓存
        - L2（季度）: 财报数据，7天缓存（财报日1小时）
        - L3（长期）: 分红/基本面，30天缓存

        Args:
            data_category: 数据类别（valuation/financial/dividend等）

        Returns:
            int: 缓存TTL（秒）
        """
        from tradingagents.dataflows.cache.smart_cache import SmartCache

        cache = SmartCache(self.cache_manager)
        return cache.get_ttl_with_calendar(data_category)

    def _get_storage_location(self, data_category: str) -> str:
        """
        获取数据类型的存储位置

        Args:
            data_category: 数据类别

        Returns:
            str: 存储位置（redis/mongodb）
        """
        from tradingagents.dataflows.cache.smart_cache import SmartCache

        cache = SmartCache(self.cache_manager)
        return cache.get_storage_location(data_category)

    def _get_volume_safely(self, data: pd.DataFrame) -> float:
        """
        安全获取成交量数据

        Args:
            data: 股票数据DataFrame

        Returns:
            float: 成交量（手），如果获取失败返回0

        重要说明 - 2026-01-30 单位标准化：
        1. 所有数据源（Tushare/AKShare/BaoStock）统一返回"手"单位
        2. MongoDB 中存储的 volume 字段单位是"手"（2026-01-30已修复，之前错误地存为"股"）
        3. 显示时直接标注为"手"，无需转换

        历史修复记录：
        - 2026-01-30 修复：App层（historical_data_service.py, tushare_adapter.py, akshare_adapter.py）
          移除了手→股的转换，现在 MongoDB 正确存储"手"单位
        - 之前问题：App层曾错误地将"手"×100转换为"股"存入MongoDB，导致显示放大100倍
        - 数据清理：需要清除2026-01-30之前的历史数据，重新导入
        """
        try:
            if "volume" in data.columns:
                volume_raw = data["volume"].iloc[-1]
                # 🔧 FIX: 单位统一为"手"，直接返回原始值
                return float(volume_raw) if volume_raw else 0
            elif "vol" in data.columns:
                volume_raw = data["vol"].iloc[-1]
                # vol 字段同样已经是"手"单位
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
        realtime_quote: Dict[str, Any] = None,  # 🆕 修改：接收完整实时行情字典
    ) -> str:
        """
        格式化股票数据响应（包含技术指标）

        Args:
            data: 股票数据DataFrame
            symbol: 股票代码
            stock_name: 股票名称
            start_date: 开始日期
            end_date: 结束日期
            realtime_quote: 实时行情字典，包含 price, open, high, low, volume 等

        Returns:
            str: 格式化的数据报告（包含技术指标）
        """
        try:
            # 🔧 确保数据有日期列
            if "date" not in data.columns and "trade_date" not in data.columns:
                logger.warning(f"⚠️ [数据格式异常] {symbol} 数据缺少日期列，尝试修复...")
                if isinstance(data.index, pd.DatetimeIndex) and len(data) > 0:
                    data["date"] = data.index
                    logger.info(f"✅ [日期修复] 从索引恢复日期列")
                else:
                    logger.error(
                        f"❌ [数据格式异常] 无法修复：数据为空或索引不是时间类型"
                    )
                    return f"❌ 数据格式错误：缺少日期列"

            # 🔧 检查并合并实时行情数据
            if realtime_quote and realtime_quote.get("date") == end_date:
                try:
                    # 检查是否已有当天数据
                    has_today_data = False
                    if not data.empty:
                        last_date = pd.to_datetime(
                            data.iloc[-1].get("date", data.iloc[-1].get("trade_date"))
                        ).strftime("%Y-%m-%d")
                        if last_date == end_date:
                            has_today_data = True
                            # 如果已有当天数据（可能是收盘后的历史数据），用实时数据覆盖（通常实时数据更新）
                            # 或者如果是盘中，历史数据可能不完整
                            pass

                    if not has_today_data:
                        logger.info(
                            f"🔄 [实时数据合并] 将实时行情追加到历史数据: {end_date}"
                        )

                        # 构建新行
                        new_row = {
                            "date": pd.to_datetime(end_date),
                            "trade_date": end_date,
                            "open": realtime_quote.get("open", 0.0),
                            "high": realtime_quote.get("high", 0.0),
                            "low": realtime_quote.get("low", 0.0),
                            "close": realtime_quote.get("price", 0.0),
                            "volume": realtime_quote.get("volume", 0),
                            "amount": realtime_quote.get("amount", 0.0),
                            "code": symbol,
                        }

                        # 创建DataFrame并合并
                        new_df = pd.DataFrame([new_row])
                        # 确保列名匹配
                        for col in data.columns:
                            if col not in new_df.columns:
                                new_df[col] = (
                                    0
                                    if pd.api.types.is_numeric_dtype(data[col])
                                    else None
                                )

                        data = pd.concat([data, new_df], ignore_index=True)
                        logger.info(
                            f"✅ [实时数据合并] 成功追加当天数据, 最新价格: {new_row['close']}"
                        )
                except Exception as e:
                    logger.warning(f"⚠️ [实时数据合并] 追加失败: {e}")

            original_data_count = len(data)
            logger.info(
                f"📊 [技术指标] 开始计算技术指标，原始数据: {original_data_count}条"
            )

            # 🔧 计算技术指标（使用完整数据）
            # 确保数据按日期排序
            # 🔧 FIX: Handle both 'date' and 'trade_date' columns
            # 🔥 FIX: 首先检查并解决 date 列和索引的歧义问题
            if "date" in data.index.names and "date" in data.columns:
                logger.debug(
                    f"⚠️ [DataFrame修复] {symbol} date既是索引又是列，重置索引..."
                )
                data = data.reset_index(drop=True)

            date_col = None
            if "date" in data.columns:
                date_col = "date"
            elif "trade_date" in data.columns:
                date_col = "trade_date"
                # Create 'date' column from 'trade_date' for consistency
                # MongoDB stores trade_date as YYYY-MM-DD string format
                # 🔥 FIX: 确保没有 date 索引后再创建 date 列
                if "date" in data.index.names:
                    data = data.reset_index(drop=True)
                if not pd.api.types.is_datetime64_any_dtype(data["trade_date"]):
                    data["date"] = pd.to_datetime(
                        data["trade_date"], format="%Y-%m-%d", errors="coerce"
                    )
                    date_col = "date"

            if date_col:
                if not pd.api.types.is_datetime64_any_dtype(data[date_col]):
                    data[date_col] = pd.to_datetime(data[date_col], errors="coerce")
                # 🔥 FIX: 确保排序前没有索引歧义
                if date_col in data.index.names:
                    data = data.reset_index(drop=True)
                data = data.sort_values(by=date_col)

            # 🔥 统一价格缓存处理：在计算指标前修正数据
            try:
                from tradingagents.utils.price_cache import get_price_cache

                cache = get_price_cache()
                cached_price = cache.get_price(symbol)

                # 如果有实时行情，优先使用
                if realtime_quote and realtime_quote.get("price"):
                    cached_price = realtime_quote.get("price")

                if cached_price is not None and not data.empty:
                    # 获取最后一行数据的原始价格
                    last_idx = data.index[-1]
                    original_price = data.at[last_idx, "close"]

                    # 只有当差异存在时才修正
                    if abs(original_price - cached_price) > 0.0001:
                        logger.info(
                            f"🔄 [价格统一] 修正DataFrame数据: {symbol} ¥{original_price:.2f} -> ¥{cached_price:.2f}"
                        )
                        data.at[last_idx, "close"] = cached_price
                        # 同时修正 high/low 如果它们与 new close 冲突
                        if cached_price > data.at[last_idx, "high"]:
                            data.at[last_idx, "high"] = cached_price
                        if cached_price < data.at[last_idx, "low"]:
                            data.at[last_idx, "low"] = cached_price
            except Exception as e:
                logger.warning(f"⚠️ [价格统一] DataFrame修正失败: {e}")

            # 计算移动平均线
            data["ma5"] = data["close"].rolling(window=5, min_periods=1).mean()
            data["ma10"] = data["close"].rolling(window=10, min_periods=1).mean()
            data["ma20"] = data["close"].rolling(window=20, min_periods=1).mean()
            data["ma60"] = data["close"].rolling(window=60, min_periods=1).mean()

            # 计算RSI（相对强弱指标）- 同花顺风格：使用中国式SMA（EMA with adjust=True）
            # 参考：https://blog.csdn.net/u011218867/article/details/117427927
            # 同花顺/通达信的RSI使用SMA函数，等价于pandas的ewm(com=N-1, adjust=True)
            delta = data["close"].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)

            # RSI6 - 使用中国式SMA
            avg_gain6 = gain.ewm(com=5, adjust=True).mean()  # com = N - 1
            avg_loss6 = loss.ewm(com=5, adjust=True).mean()
            rs6 = avg_gain6 / avg_loss6.replace(0, np.nan)
            data["rsi6"] = 100 - (100 / (1 + rs6))

            # RSI12 - 使用中国式SMA
            avg_gain12 = gain.ewm(com=11, adjust=True).mean()
            avg_loss12 = loss.ewm(com=11, adjust=True).mean()
            rs12 = avg_gain12 / avg_loss12.replace(0, np.nan)
            data["rsi12"] = 100 - (100 / (1 + rs12))

            # RSI24 - 使用中国式SMA
            avg_gain24 = gain.ewm(com=23, adjust=True).mean()
            avg_loss24 = loss.ewm(com=23, adjust=True).mean()
            rs24 = avg_gain24 / avg_loss24.replace(0, np.nan)
            data["rsi24"] = 100 - (100 / (1 + rs24))

            # 保留RSI14作为国际标准参考（使用简单移动平均）
            gain14 = gain.rolling(window=14, min_periods=1).mean()
            loss14 = loss.rolling(window=14, min_periods=1).mean()
            rs14 = gain14 / loss14.replace(0, np.nan)
            data["rsi14"] = 100 - (100 / (1 + rs14))

            # 计算MACD
            ema12 = data["close"].ewm(span=12, adjust=False).mean()
            ema26 = data["close"].ewm(span=26, adjust=False).mean()
            data["macd_dif"] = ema12 - ema26
            data["macd_dea"] = data["macd_dif"].ewm(span=9, adjust=False).mean()
            data["macd"] = (data["macd_dif"] - data["macd_dea"]) * 2

            # 计算布林带
            data["boll_mid"] = data["close"].rolling(window=20, min_periods=1).mean()
            std = data["close"].rolling(window=20, min_periods=1).std()
            data["boll_upper"] = data["boll_mid"] + 2 * std
            data["boll_lower"] = data["boll_mid"] - 2 * std

            logger.info(f"✅ [技术指标] 技术指标计算完成")

            # 🔧 只保留最后3-5天的数据用于展示（减少token消耗）
            display_rows = min(5, len(data))
            display_data = data.tail(display_rows)
            latest_data = data.iloc[-1]

            # 🔍 [调试日志] 打印最近5天的原始数据和技术指标
            logger.info(f"🔍 [技术指标详情] ===== 最近{display_rows}个交易日数据 =====")
            for i, (idx, row) in enumerate(display_data.iterrows(), 1):
                logger.info(f"🔍 [技术指标详情] 第{i}天 ({row.get('date', 'N/A')}):")
                logger.info(
                    f"   价格: 开={row.get('open', 0):.2f}, 高={row.get('high', 0):.2f}, 低={row.get('low', 0):.2f}, 收={row.get('close', 0):.2f}"
                )
                logger.info(
                    f"   MA: MA5={row.get('ma5', 0):.2f}, MA10={row.get('ma10', 0):.2f}, MA20={row.get('ma20', 0):.2f}, MA60={row.get('ma60', 0):.2f}"
                )
                logger.info(
                    f"   MACD: DIF={row.get('macd_dif', 0):.4f}, DEA={row.get('macd_dea', 0):.4f}, MACD={row.get('macd', 0):.4f}"
                )
                logger.info(
                    f"   RSI: RSI6={row.get('rsi6', 0):.2f}, RSI12={row.get('rsi12', 0):.2f}, RSI24={row.get('rsi24', 0):.2f} (同花顺风格)"
                )
                logger.info(f"   RSI14: {row.get('rsi14', 0):.2f} (国际标准)")
                logger.info(
                    f"   BOLL: 上={row.get('boll_upper', 0):.2f}, 中={row.get('boll_mid', 0):.2f}, 下={row.get('boll_lower', 0):.2f}"
                )

            logger.info(f"🔍 [技术指标详情] ===== 数据详情结束 =====")

            # 计算最新价格和涨跌幅
            # 🆕 优先使用实时价格
            if realtime_quote and realtime_quote.get("price"):
                latest_price = realtime_quote.get("price")
                price_source = "实时"
                logger.info(f"✅ [价格策略] 使用实时价格: ¥{latest_price:.2f}")
            else:
                latest_price = latest_data.get("close", 0)
                price_source = "历史"
                logger.info(f"ℹ️ [价格策略] 使用历史价格: ¥{latest_price:.2f}")

            # 🔥 缓存更新：确保当前价格被缓存（作为真理来源）
            try:
                from tradingagents.utils.price_cache import get_price_cache

                # 如果缓存中没有（或者我们是第一个获取数据的），更新缓存
                cache = get_price_cache()
                if cache.get_price(symbol) is None:
                    cache.update(symbol, latest_price)
            except Exception as e:
                logger.warning(f"⚠️ [价格统一] 缓存更新失败: {e}")

            prev_close = (
                data.iloc[-2].get("close", latest_price)
                if len(data) > 1
                else latest_price
            )

            change = latest_price - prev_close
            change_pct = (change / prev_close * 100) if prev_close != 0 else 0

            # 获取最新数据的实际日期
            latest_data_date = latest_data.get("date", None)
            if (
                latest_data_date is None
                or latest_data_date == "N/A"
                or pd.isna(latest_data_date)
            ):
                if isinstance(data.index, pd.DatetimeIndex) and len(data) > 0:
                    latest_data_date = data.index[-1]
                    logger.info(f"🔧 [日期修复] 从索引恢复日期: {latest_data_date}")
                else:
                    latest_data_date = "N/A"
                    logger.warning(
                        f"⚠️ [日期异常] 无法获取数据日期，data为空或索引不是时间类型"
                    )

            if isinstance(latest_data_date, pd.Timestamp):
                latest_data_date = latest_data_date.strftime("%Y-%m-%d")
            elif isinstance(latest_data_date, str):
                if len(latest_data_date) == 8 and latest_data_date.isdigit():
                    latest_data_date = f"{latest_data_date[:4]}-{latest_data_date[4:6]}-{latest_data_date[6:8]}"
                elif "-" in latest_data_date:
                    pass  # Already in correct format

            logger.info(
                f"📅 [最新数据日期] 实际数据日期: {latest_data_date}, 请求结束日期: {end_date}"
            )

            # ⚠️ 智能检查数据日期是否为最新
            from datetime import datetime

            # 判断 end_date 是否是非交易日（周末）
            def _is_weekend(date_str: str) -> bool:
                """检查日期是否是周末"""
                try:
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    return date_obj.weekday() >= 5  # 5=周六, 6=周日
                except:
                    return False

            is_end_date_weekend = _is_weekend(end_date)

            # 初始化变量
            result = ""
            date_warning = ""

            if latest_data_date != "N/A" and latest_data_date != end_date:
                if is_end_date_weekend:
                    # end_date 是周末（周六/周日），这是正常情况，不应该警告
                    logger.info(
                        f"📅 [数据日期检查] end_date={end_date} 是非交易日（周末），"
                        f"使用最新数据日期 {latest_data_date}，这是正常行为"
                    )
                    # 更新 end_date 显示为实际使用的交易日
                    result = f"📊 {stock_name}({symbol}) - 技术分析数据\n"
                    result += f"数据期间: {start_date} 至 {latest_data_date} (实际使用交易日)\n"
                    result += f"最新数据日期: {latest_data_date}\n"
                else:
                    # end_date 是工作日但数据不新鲜，可能是延迟
                    logger.warning(
                        f"⚠️ [数据延迟警告] 最新数据日期({latest_data_date})与请求日期({end_date})不一致，可能是数据未更新"
                    )
                    date_warning = f"⚠️ 注意：最新数据日期为 {latest_data_date}，非当前分析日期 {end_date}\n"
                    result = f"📊 {stock_name}({symbol}) - 技术分析数据\n"
                    result += f"数据期间: {start_date} 至 {end_date}\n"
                    result += f"最新数据日期: {latest_data_date}\n"
            else:
                result = f"📊 {stock_name}({symbol}) - 技术分析数据\n"
                result += f"数据期间: {start_date} 至 {end_date}\n"
                result += f"最新数据日期: {latest_data_date}\n"

            result += (
                f"数据条数: {original_data_count}条 (展示最近{display_rows}个交易日)\n"
            )
            if date_warning:
                result += f"\n{date_warning}"
            result += f"\n"

            result += (
                f"💰 最新价格: ¥{latest_price:.2f} (数据日期: {latest_data_date})\n"
            )
            # 🔧 FIX: 明确标注单位，避免涨跌额（元）和涨跌幅（%）混淆
            result += f"📈 涨跌额: {change:+.2f}元 (涨跌幅: {change_pct:+.2f}%)\n\n"

            # 添加技术指标
            result += f"📊 移动平均线 (MA):\n"
            result += f"   MA5:  ¥{latest_data['ma5']:.2f}"
            if latest_price > latest_data["ma5"]:
                result += " (价格在MA5上方 ↑)\n"
            else:
                result += " (价格在MA5下方 ↓)\n"

            result += f"   MA10: ¥{latest_data['ma10']:.2f}"
            if latest_price > latest_data["ma10"]:
                result += " (价格在MA10上方 ↑)\n"
            else:
                result += " (价格在MA10下方 ↓)\n"

            result += f"   MA20: ¥{latest_data['ma20']:.2f}"
            if latest_price > latest_data["ma20"]:
                result += " (价格在MA20上方 ↑)\n"
            else:
                result += " (价格在MA20下方 ↓)\n"

            result += f"   MA60: ¥{latest_data['ma60']:.2f}"
            if latest_price > latest_data["ma60"]:
                result += " (价格在MA60上方 ↑)\n\n"
            else:
                result += " (价格在MA60下方 ↓)\n\n"

            # MACD指标
            result += f"📈 MACD指标:\n"
            result += f"   DIF:  {latest_data['macd_dif']:.3f}\n"
            result += f"   DEA:  {latest_data['macd_dea']:.3f}\n"
            result += f"   MACD: {latest_data['macd']:.3f}"
            if latest_data["macd"] > 0:
                result += " (多头 ↑)\n"
            else:
                result += " (空头 ↓)\n"

            # 判断金叉/死叉
            if len(data) > 1:
                prev_dif = data.iloc[-2]["macd_dif"]
                prev_dea = data.iloc[-2]["macd_dea"]
                curr_dif = latest_data["macd_dif"]
                curr_dea = latest_data["macd_dea"]

                if prev_dif <= prev_dea and curr_dif > curr_dea:
                    result += "   ⚠️ MACD金叉信号（DIF上穿DEA）\n\n"
                elif prev_dif >= prev_dea and curr_dif < curr_dea:
                    result += "   ⚠️ MACD死叉信号（DIF下穿DEA）\n\n"
                else:
                    result += "\n"
            else:
                result += "\n"

            # RSI指标 - 同花顺风格 (6, 12, 24)
            rsi6 = latest_data["rsi6"]
            rsi12 = latest_data["rsi12"]
            rsi24 = latest_data["rsi24"]
            result += f"📉 RSI指标 (同花顺风格):\n"
            result += f"   RSI6:  {rsi6:.2f}"
            if rsi6 >= 80:
                result += " (超买 ⚠️)\n"
            elif rsi6 <= 20:
                result += " (超卖 ⚠️)\n"
            else:
                result += "\n"

            result += f"   RSI12: {rsi12:.2f}"
            if rsi12 >= 80:
                result += " (超买 ⚠️)\n"
            elif rsi12 <= 20:
                result += " (超卖 ⚠️)\n"
            else:
                result += "\n"

            result += f"   RSI24: {rsi24:.2f}"
            if rsi24 >= 80:
                result += " (超买 ⚠️)\n"
            elif rsi24 <= 20:
                result += " (超卖 ⚠️)\n"
            else:
                result += "\n"

            # 判断RSI趋势
            if rsi6 > rsi12 > rsi24:
                result += "   趋势: 多头排列 ↑\n\n"
            elif rsi6 < rsi12 < rsi24:
                result += "   趋势: 空头排列 ↓\n\n"
            else:
                result += "   趋势: 震荡整理 ↔\n\n"

            # 布林带
            result += f"📊 布林带 (BOLL):\n"
            result += f"   上轨: ¥{latest_data['boll_upper']:.2f}\n"
            result += f"   中轨: ¥{latest_data['boll_mid']:.2f}\n"
            result += f"   下轨: ¥{latest_data['boll_lower']:.2f}\n"

            # 判断价格在布林带的位置
            boll_position = (
                (latest_price - latest_data["boll_lower"])
                / (latest_data["boll_upper"] - latest_data["boll_lower"])
                * 100
            )
            result += f"   价格位置: {boll_position:.1f}%"
            if boll_position >= 100:
                result += " (已突破上轨，多头确认信号！🔴)"
            elif boll_position >= 80:
                result += " (接近上轨，可能超买 ⚠️)"
            else:
                result += " (中性区域)"

            # 价格统计
            result += f"📊 价格统计 (最近{display_rows}个交易日):\n"
            result += f"   最高价: ¥{display_data['high'].max():.2f}\n"
            result += f"   最低价: ¥{display_data['low'].min():.2f}\n"
            result += f"   平均价: ¥{display_data['close'].mean():.2f}\n"

            # ========== 成交量统计（增强）==========
            # 单日成交量（最新一日）
            volume_latest = self._get_volume_safely(display_data)

            # 5日均量和10日均量
            volume_avg_5 = display_data['volume'].tail(5).mean() if len(display_data) >= 5 else volume_latest
            volume_avg_10 = display_data['volume'].tail(10).mean() if len(display_data) >= 10 else volume_latest

            result += f"\n📊 成交量分析:\n"
            result += f"   单日成交量: {volume_latest:,.0f}手\n"
            result += f"   5日均量: {volume_avg_5:,.0f}手\n"
            result += f"   10日均量: {volume_avg_10:,.0f}手\n"

            # 量比分析（判断放量/缩量）
            if volume_avg_5 > 0:
                volume_ratio = volume_latest / volume_avg_5
                if volume_ratio >= 2.0:
                    level = "巨量"
                elif volume_ratio >= 1.5:
                    level = "放量"
                elif volume_ratio >= 0.8:
                    level = "平量"
                else:
                    level = "缩量"
                result += f"   量比: {volume_ratio:.2f}倍 ({level})\n"

            return result

        except Exception as e:
            logger.error(f"❌ 格式化数据响应失败: {e}", exc_info=True)
            return f"❌ 格式化{symbol}数据失败: {e}"

    def get_stock_dataframe(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        period: str = "daily",
    ) -> pd.DataFrame:
        """
        获取股票数据的 DataFrame 接口，支持多数据源和自动降级

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期（daily/weekly/monthly），默认为daily

        Returns:
            pd.DataFrame: 股票数据 DataFrame，列标准：open, high, low, close, vol, amount, date
        """
        logger.info(
            f"📊 [DataFrame接口] 获取股票数据: {symbol} ({start_date} 到 {end_date})"
        )

        try:
            # 尝试当前数据源
            df = None
            if self.current_source == ChinaDataSource.MONGODB:
                from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                    get_mongodb_cache_adapter,
                )

                adapter = get_mongodb_cache_adapter()
                df = adapter.get_historical_data(
                    symbol, start_date, end_date, period=period
                )
            elif self.current_source == ChinaDataSource.TUSHARE:
                from .providers.china.tushare import get_tushare_provider

                provider = get_tushare_provider()
                df = provider.get_daily_data(symbol, start_date, end_date)
            elif self.current_source == ChinaDataSource.AKSHARE:
                from .providers.china.akshare import get_akshare_provider

                provider = get_akshare_provider()
                df = provider.get_stock_data(symbol, start_date, end_date)
            elif self.current_source == ChinaDataSource.BAOSTOCK:
                from .providers.china.baostock import get_baostock_provider

                provider = get_baostock_provider()
                df = provider.get_stock_data(symbol, start_date, end_date)

            if df is not None and not df.empty:
                logger.info(
                    f"✅ [DataFrame接口] 从 {self.current_source.value} 获取成功: {len(df)}条"
                )
                return self._standardize_dataframe(df)

            # 降级到其他数据源
            logger.warning(
                f"⚠️ [DataFrame接口] {self.current_source.value} 失败，尝试降级"
            )
            for source in self.available_sources:
                if source == self.current_source:
                    continue
                try:
                    if source == ChinaDataSource.MONGODB:
                        from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                            get_mongodb_cache_adapter,
                        )

                        adapter = get_mongodb_cache_adapter()
                        df = adapter.get_historical_data(
                            symbol, start_date, end_date, period=period
                        )
                    elif source == ChinaDataSource.TUSHARE:
                        from .providers.china.tushare import get_tushare_provider

                        provider = get_tushare_provider()
                        df = provider.get_daily_data(symbol, start_date, end_date)
                    elif source == ChinaDataSource.AKSHARE:
                        from .providers.china.akshare import get_akshare_provider

                        provider = get_akshare_provider()
                        df = provider.get_stock_data(symbol, start_date, end_date)
                    elif source == ChinaDataSource.BAOSTOCK:
                        from .providers.china.baostock import get_baostock_provider

                        provider = get_baostock_provider()
                        df = provider.get_stock_data(symbol, start_date, end_date)

                    if df is not None and not df.empty:
                        logger.info(
                            f"✅ [DataFrame接口] 降级到 {source.value} 成功: {len(df)}条"
                        )
                        return self._standardize_dataframe(df)
                except Exception as e:
                    logger.warning(f"⚠️ [DataFrame接口] {source.value} 失败: {e}")
                    continue

            logger.error(f"❌ [DataFrame接口] 所有数据源都失败: {symbol}")
            return pd.DataFrame()

        except Exception as e:
            logger.error(f"❌ [DataFrame接口] 获取失败: {e}", exc_info=True)
            return pd.DataFrame()

    def _standardize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        标准化 DataFrame 列名和格式

        Args:
            df: 原始 DataFrame

        Returns:
            pd.DataFrame: 标准化后的 DataFrame
        """
        if df is None or df.empty:
            return pd.DataFrame()

        out = df.copy()

        # 列名映射
        colmap = {
            # English
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "vol",
            "Amount": "amount",
            "symbol": "code",
            "Symbol": "code",
            # Already lower
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
            # Chinese (AKShare common)
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
                # 确保日期是datetime类型，以便正确排序
                if not pd.api.types.is_datetime64_any_dtype(out["date"]):
                    out["date"] = pd.to_datetime(out["date"])
                out = out.sort_values("date")
            except Exception:
                pass

        # 计算涨跌幅（如果缺失）
        if "pct_change" not in out.columns and "close" in out.columns:
            out["pct_change"] = out["close"].pct_change() * 100.0

        return out

    def get_realtime_quote(self, symbol: str) -> Optional[Dict]:
        """
        获取实时行情数据 - 只使用外部API，不使用MongoDB缓存

        支持配置：
        - REALTIME_QUOTE_ENABLED: 是否启用实时行情
        - REALTIME_QUOTE_TUSHARE_ENABLED: 是否启用Tushare作为备选
        - REALTIME_QUOTE_MAX_RETRIES: 最大重试次数
        - REALTIME_QUOTE_RETRY_DELAY: 重试间隔（秒）
        - REALTIME_QUOTE_RETRY_BACKOFF: 重试延迟退避倍数
        - REALTIME_QUOTE_AKSHARE_PRIORITY: AKShare优先级
        - REALTIME_QUOTE_TUSHARE_PRIORITY: Tushare优先级

        Args:
            symbol: 股票代码

        Returns:
            Dict: 实时行情数据，包含price, change, change_pct, volume等
        """
        # 读取配置
        config = self._get_realtime_quote_config()

        if not config["enabled"]:
            logger.info(f"📊 [实时行情] 实时行情获取已禁用，跳过: {symbol}")
            return None

        logger.info(
            f"📊 [实时行情] 获取实时行情: {symbol} (重试次数: {config['max_retries']})"
        )

        try:
            # 根据优先级排序数据源
            sources = []
            if config["akshare_priority"] == 1:
                sources.append(("akshare", self._get_akshare_realtime_quote_with_retry))
            if config["tushare_enabled"] and config["tushare_priority"] == 1:
                sources.append(("tushare", self._get_tushare_realtime_quote_with_retry))
            if config["akshare_priority"] == 2:
                sources.append(("akshare", self._get_akshare_realtime_quote_with_retry))
            if config["tushare_enabled"] and config["tushare_priority"] == 2:
                sources.append(("tushare", self._get_tushare_realtime_quote_with_retry))

            # 依次尝试各个数据源
            for source_name, source_func in sources:
                try:
                    quote = source_func(symbol, config)
                    if quote:
                        logger.info(
                            f"✅ [实时行情-{source_name.upper()}] 成功获取 {symbol} 实时行情"
                        )
                        self._update_price_cache(symbol, quote.get("price"))
                        return quote
                except Exception as e:
                    logger.warning(f"⚠️ [实时行情-{source_name.upper()}] 获取失败: {e}")
                    continue

            # 所有数据源都失败
            logger.warning(
                f"⚠️ [实时行情] 无法获取 {symbol} 的实时行情（所有外部API失败）"
            )
            return None

        except Exception as e:
            logger.error(f"❌ 获取实时行情失败: {e}", exc_info=True)
            return None

    def _get_realtime_quote_config(self) -> Dict:
        """获取实时行情配置"""
        return {
            "enabled": os.getenv("REALTIME_QUOTE_ENABLED", "true").lower() == "true",
            "tushare_enabled": os.getenv(
                "REALTIME_QUOTE_TUSHARE_ENABLED", "true"
            ).lower()
            == "true",
            "max_retries": int(os.getenv("REALTIME_QUOTE_MAX_RETRIES", "3")),
            "retry_delay": float(os.getenv("REALTIME_QUOTE_RETRY_DELAY", "1.0")),
            "retry_backoff": float(os.getenv("REALTIME_QUOTE_RETRY_BACKOFF", "2.0")),
            "akshare_priority": int(os.getenv("REALTIME_QUOTE_AKSHARE_PRIORITY", "1")),
            "tushare_priority": int(os.getenv("REALTIME_QUOTE_TUSHARE_PRIORITY", "2")),
        }

    def _get_akshare_realtime_quote_with_retry(
        self, symbol: str, config: Dict
    ) -> Optional[Dict]:
        """带重试的AKShare实时行情获取"""
        max_retries = config["max_retries"]
        retry_delay = config["retry_delay"]
        backoff = config["retry_backoff"]

        for attempt in range(max_retries):
            try:
                quote = self._get_akshare_realtime_quote(symbol)
                if quote:
                    return quote
            except Exception as e:
                logger.warning(
                    f"⚠️ [AKShare-重试{attempt + 1}/{max_retries}] {symbol}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= backoff

        return None

    def _get_tushare_realtime_quote_with_retry(
        self, symbol: str, config: Dict
    ) -> Optional[Dict]:
        """带重试的Tushare实时行情获取"""
        max_retries = config["max_retries"]
        retry_delay = config["retry_delay"]
        backoff = config["retry_backoff"]

        for attempt in range(max_retries):
            try:
                quote = self._get_tushare_realtime_quote(symbol)
                if quote:
                    return quote
            except Exception as e:
                logger.warning(
                    f"⚠️ [Tushare-重试{attempt + 1}/{max_retries}] {symbol}: {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= backoff

        return None

    def _update_price_cache(self, symbol: str, price: float):
        """更新价格缓存"""
        if price is None:
            return
        try:
            from tradingagents.utils.price_cache import get_price_cache

            get_price_cache().update(symbol, price)
        except Exception as e:
            logger.warning(f"⚠️ [实时行情] 缓存更新失败: {e}")

    def _get_tushare_realtime_quote(self, symbol: str) -> Optional[Dict]:
        """
        使用Tushare获取实时行情

        使用 ts.get_realtime_quotes 接口获取秒级实时数据
        该接口基于新浪财经数据，无需高级权限
        """
        try:
            import asyncio
            import tushare as ts
            from datetime import datetime

            # 获取6位股票代码
            code_6 = symbol.split(".")[0] if "." in symbol else symbol
            code_6 = code_6.zfill(6)

            logger.debug(f"📊 [Tushare实时行情] 尝试获取 {symbol} (代码: {code_6})")

            # 使用 ts.get_realtime_quotes 获取实时行情（基于新浪财经）
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 在线程池中执行同步的 tushare 调用
            df = loop.run_until_complete(
                asyncio.to_thread(ts.get_realtime_quotes, code_6)
            )

            if df is not None and not df.empty:
                row = df.iloc[0]

                # 检查数据有效性
                price = float(row.get("price", 0))
                if price > 0:
                    pre_close = float(row.get("pre_close", 0))
                    change = price - pre_close if pre_close > 0 else 0
                    change_pct = (change / pre_close * 100) if pre_close > 0 else 0

                    quote = {
                        "symbol": symbol,
                        "price": price,
                        "open": float(row.get("open", 0)),
                        "high": float(row.get("high", 0)),
                        "low": float(row.get("low", 0)),
                        "volume": int(
                            float(row.get("volume", 0))
                        ),  # 单位：手（Tushare提供者已转换）
                        "amount": float(row.get("amount", 0)),  # 单位：元
                        "change": change,
                        "change_pct": change_pct,
                        "pre_close": pre_close,
                        "date": row.get("date", datetime.now().strftime("%Y-%m-%d")),
                        "time": row.get("time", datetime.now().strftime("%H:%M:%S")),
                        "source": "tushare_sina_realtime",
                        "is_realtime": True,
                    }

                    logger.info(
                        f"✅ [实时行情-Tushare-Sina] {symbol} 价格={quote['price']:.2f}, "
                        f"涨跌={quote['change']:.2f}({quote['change_pct']:.2f}%)"
                    )
                    return quote
                else:
                    logger.warning(f"⚠️ [实时行情-Tushare] {symbol} 价格数据无效")
            else:
                logger.debug(f"📊 [实时行情-Tushare] {symbol} 无实时数据返回")

            return None

        except Exception as e:
            logger.error(f"❌ Tushare实时行情获取失败: {e}")
            return None

    def _get_akshare_realtime_quote(self, symbol: str) -> Optional[Dict]:
        """使用AKShare获取实时行情"""
        max_retries = 2
        last_error = None

        for attempt in range(max_retries):
            try:
                import akshare as ak
                import requests
                import time

                # 转换股票代码格式为新浪格式（用于备用接口）
                if symbol.startswith("6"):
                    sina_symbol = f"sh{symbol}"
                elif symbol.startswith(("0", "3", "2")):
                    sina_symbol = f"sz{symbol}"
                elif symbol.startswith(("8", "4")):
                    sina_symbol = f"bj{symbol}"
                else:
                    sina_symbol = symbol

                # 🔥 优先尝试新浪实时接口（单个股票，数据量小）
                try:
                    url = f"http://hq.sinajs.cn/list={sina_symbol}"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    }

                    response = requests.get(url, headers=headers, timeout=10)
                    response.encoding = "gbk"

                    if response.status_code == 200:
                        data_str = response.text.strip()
                        if "var hq_str_" in data_str:
                            # 解析新浪数据
                            start_idx = data_str.index('"') + 1
                            end_idx = data_str.rindex('"')
                            data_str = data_str[start_idx:end_idx]

                            data = data_str.split(",")
                            if len(data) >= 33:
                                price = float(data[3])
                                open_price = float(data[1])
                                high_price = float(data[4])
                                low_price = float(data[5])
                                volume = int(
                                    float(data[8])
                                )  # 单位：手（直接使用新浪返回的手数）

                                quote = {
                                    "symbol": symbol,
                                    "price": price,
                                    "open": open_price,
                                    "high": high_price,
                                    "low": low_price,
                                    "volume": volume,  # 单位：手
                                    "amount": 0.0,  # 单位：元
                                    "change": float(data[2]),
                                    "change_pct": float(data[2]) / float(data[1]) * 100
                                    if float(data[1]) > 0
                                    else 0.0,
                                    "date": datetime.now().strftime("%Y-%m-%d"),
                                    "time": datetime.now().strftime("%H:%M:%S"),
                                    "source": "sina_realtime",
                                    "is_realtime": True,
                                }
                                logger.info(
                                    f"✅ [实时行情-新浪] {symbol} 价格={quote['price']:.2f}, 成交量={volume:,.0f}手"
                                )
                                return quote
                except Exception as e:
                    logger.debug(f"新浪接口失败，尝试东方财富: {e}")
                    last_error = e

                # 备用：东方财富单股票接口（如果新浪失败）
                # 🔥 优化：使用 stock_bid_ask_em 获取单只股票，而不是 stock_zh_a_spot_em 获取全市场
                logger.info(
                    f"🔄 [AKShare] 尝试获取 {symbol} 单股票实时行情 (第{attempt + 1}次)"
                )
                df = ak.stock_bid_ask_em(symbol=symbol)

                if df is not None and not df.empty:
                    # 将 DataFrame 转换为字典
                    data_dict = dict(zip(df["item"], df["value"]))

                    # 成交量单位：手（直接使用AKShare返回的"总手"字段）
                    # 注意：2026-01-30 统一单位为"手"
                    volume_in_lots = int(data_dict.get("总手", 0))

                    quote = {
                        "symbol": symbol,
                        "price": float(data_dict.get("最新", 0)),
                        "open": float(data_dict.get("今开", 0)),
                        "high": float(data_dict.get("最高", 0)),
                        "low": float(data_dict.get("最低", 0)),
                        "volume": volume_in_lots,  # 单位：手
                        "amount": float(data_dict.get("金额", 0)),  # 单位：元
                        "change": float(data_dict.get("涨跌", 0)),
                        "change_pct": float(data_dict.get("涨幅", 0)),
                        "date": datetime.now().strftime("%Y-%m-%d"),
                        "time": datetime.now().strftime("%H:%M:%S"),
                        "source": "eastmoney_realtime",
                        "is_realtime": True,
                    }
                    logger.info(
                        f"✅ [实时行情-东方财富单股票] {symbol} 价格={quote['price']:.2f}, 成交量={volume_in_lots:,.0f}手"
                    )
                    return quote
                else:
                    logger.warning(f"⚠️ AKShare未找到{symbol}的实时行情")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                    continue

            except requests.exceptions.Timeout:
                last_error = "请求超时"
                logger.warning(f"⚠️ [AKShare] 请求超时 (第{attempt + 1}次)")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue

            except requests.exceptions.ProxyError as e:
                last_error = f"代理错误: {e}"
                logger.warning(f"⚠️ [AKShare] 代理连接失败 (第{attempt + 1}次): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue

            except requests.exceptions.ConnectionError as e:
                last_error = f"连接错误: {e}"
                logger.warning(f"⚠️ [AKShare] 网络连接失败 (第{attempt + 1}次): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue

            except Exception as e:
                last_error = e
                logger.warning(f"⚠️ [AKShare] 获取失败 (第{attempt + 1}次): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                continue

        # 所有重试都失败
        logger.error(f"❌ AKShare实时行情获取失败: {last_error}", exc_info=True)
        return None

    def get_stock_data(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        period: str = "daily",
        analysis_date: str = None,
    ) -> str:
        """
        获取股票数据的统一接口，支持多周期数据

        🔥 重要更新：根据分析日期智能判断是否使用实时行情
        - 历史日期：使用历史数据
        - 今天+盘中：使用实时行情
        - 今天+盘前/盘后：使用收盘价

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期（daily/weekly/monthly），默认为daily
            analysis_date: 用户指定的分析日期（YYYY-MM-DD），用于判断实时行情

        Returns:
            str: 格式化的股票数据
        """
        # 🔥 如果未提供 analysis_date，尝试从 Toolkit._config 获取
        if analysis_date is None:
            try:
                from tradingagents.agents.utils.agent_utils import Toolkit

                analysis_date = Toolkit._config.get("analysis_date")
                if analysis_date:
                    logger.info(
                        f"📅 [自动获取] 从 Toolkit._config 获取分析日期: {analysis_date}"
                    )
            except Exception:
                pass

        # 🔥 获取实时价格（根据分析日期智能判断）
        realtime_price = None
        realtime_quote = None
        try:
            from tradingagents.utils.market_time import MarketTimeUtils

            should_use_rt, reason = MarketTimeUtils.should_use_realtime_quote(
                symbol, analysis_date=analysis_date
            )
            logger.info(f"📊 [实时行情检查] {symbol}: {reason}")

            # 始终尝试获取实时价格（盘中用实时，盘后用最新收盘价）
            realtime_quote = self.get_realtime_quote(symbol)
            if realtime_quote and realtime_quote.get("price"):
                realtime_price = realtime_quote["price"]
                logger.info(f"✅ [实时价格] 获取成功: ¥{realtime_price:.2f}")
            else:
                logger.warning(f"⚠️ [实时价格] 获取失败，将使用历史数据中的价格")
                # ✅ 不覆盖 realtime_quote，保留可能的成功结果
        except Exception as e:
            logger.debug(f"实时行情获取失败（使用历史数据）: {e}")
            # ✅ 不覆盖 realtime_quote，保留可能的成功结果

        # 记录详细的输入参数
        logger.info(
            f"📊 [数据来源: {self.current_source.value}] 开始获取{period}数据: {symbol}",
            extra={
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
                "period": period,
                "data_source": self.current_source.value,
                "event_type": "data_fetch_start",
            },
        )

        # 添加详细的股票代码追踪日志
        logger.info(
            f"🔍 [股票代码追踪] DataSourceManager.get_stock_data 接收到的股票代码: '{symbol}' (类型: {type(symbol)})"
        )
        logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(symbol))}")
        logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(symbol))}")
        logger.info(f"🔍 [股票代码追踪] 当前数据源: {self.current_source.value}")

        start_time = time.time()

        # 🔥 检查是否跳过 MongoDB 缓存（直接从在线数据源获取）
        skip_mongodb = (
            os.getenv("SKIP_MONGODB_CACHE_ON_QUERY", "true").lower() == "true"
        )

        try:
            # 根据数据源调用相应的获取方法
            actual_source = None  # 实际使用的数据源

            if self.current_source == ChinaDataSource.MONGODB:
                if skip_mongodb:
                    # 🔥 跳过 MongoDB，直接从在线数据源获取
                    logger.info(f"🔄 [配置跳过MongoDB] 直接从在线数据源获取: {symbol}")
                    result, actual_source = self._try_fallback_sources_with_save(
                        symbol, start_date, end_date, period, realtime_quote
                    )
                else:
                    result, actual_source = self._get_mongodb_data(
                        symbol, start_date, end_date, period, realtime_quote
                    )
            elif self.current_source == ChinaDataSource.TUSHARE:
                logger.info(
                    f"🔍 [股票代码追踪] 调用 Tushare 数据源，传入参数: symbol='{symbol}', period='{period}'"
                )
                result = self._get_tushare_data(
                    symbol, start_date, end_date, period, realtime_quote
                )
                actual_source = "tushare"
            elif self.current_source == ChinaDataSource.AKSHARE:
                result = self._get_akshare_data(
                    symbol, start_date, end_date, period, realtime_quote
                )
                actual_source = "akshare"
            elif self.current_source == ChinaDataSource.BAOSTOCK:
                result = self._get_baostock_data(
                    symbol, start_date, end_date, period, realtime_quote
                )
                actual_source = "baostock"
            # TDX 已移除
            else:
                result = f"❌ 不支持的数据源: {self.current_source.value}"
                actual_source = None

            # 记录详细的输出结果
            duration = time.time() - start_time
            result_length = len(result) if result else 0
            is_success = result and "❌" not in result and "错误" not in result

            # 使用实际数据源名称，如果没有则使用 current_source
            display_source = actual_source or self.current_source.value

            if is_success:
                logger.info(
                    f"✅ [数据来源: {display_source}] 成功获取股票数据: {symbol} ({result_length}字符, 耗时{duration:.2f}秒)",
                    extra={
                        "symbol": symbol,
                        "start_date": start_date,
                        "end_date": end_date,
                        "data_source": display_source,
                        "actual_source": actual_source,
                        "requested_source": self.current_source.value,
                        "duration": duration,
                        "result_length": result_length,
                        "result_preview": result[:200] + "..."
                        if result_length > 200
                        else result,
                        "event_type": "data_fetch_success",
                    },
                )

                # 🔥 如果有实时行情，替换最新价格
                if should_use_rt and realtime_quote:
                    result = self._merge_realtime_quote_to_result(
                        result, realtime_quote, symbol
                    )

                return result
            else:
                logger.warning(
                    f"⚠️ [数据来源: {self.current_source.value}失败] 数据质量异常，尝试降级到其他数据源: {symbol}",
                    extra={
                        "symbol": symbol,
                        "start_date": start_date,
                        "end_date": end_date,
                        "data_source": self.current_source.value,
                        "duration": duration,
                        "result_length": result_length,
                        "result_preview": result[:200] + "..."
                        if result_length > 200
                        else result,
                        "event_type": "data_fetch_warning",
                    },
                )

                # 数据质量异常时也尝试降级到其他数据源
                fallback_result = self._try_fallback_sources(
                    symbol, start_date, end_date
                )
                if (
                    fallback_result
                    and "❌" not in fallback_result
                    and "错误" not in fallback_result
                ):
                    logger.info(f"✅ [数据来源: 备用数据源] 降级成功获取数据: {symbol}")
                    return fallback_result
                else:
                    logger.error(
                        f"❌ [数据来源: 所有数据源失败] 所有数据源都无法获取有效数据: {symbol}"
                    )
                    return result  # 返回原始结果（包含错误信息）

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"❌ [数据获取] 异常失败: {e}",
                extra={
                    "symbol": symbol,
                    "start_date": start_date,
                    "end_date": end_date,
                    "data_source": self.current_source.value,
                    "duration": duration,
                    "error": str(e),
                    "event_type": "data_fetch_exception",
                },
                exc_info=True,
            )
            return self._try_fallback_sources(
                symbol, start_date, end_date, realtime_quote=realtime_quote
            )

    def _merge_realtime_quote_to_result(
        self, historical_result: str, realtime_quote: Dict, symbol: str
    ) -> str:
        """
        将实时行情数据合并到历史数据结果中

        Args:
            historical_result: 历史数据格式化结果
            realtime_quote: 实时行情数据
            symbol: 股票代码

        Returns:
            str: 合并后的结果
        """
        try:
            # 🔧 安全提取实时行情数据，处理 None 值
            price = realtime_quote.get("price")
            change = realtime_quote.get("change")
            change_pct = realtime_quote.get("change_pct")
            open_price = realtime_quote.get("open")
            high_price = realtime_quote.get("high")
            low_price = realtime_quote.get("low")
            quote_date = realtime_quote.get("date", "")
            quote_time = realtime_quote.get("time", "实时")

            # 检查必要字段是否存在
            if price is None:
                logger.warning(f"⚠️ 实时行情缺少价格数据: {symbol}")
                return historical_result

            # 格式化数值，处理 None 值
            price_str = f"¥{price:.2f}" if price is not None else "N/A"
            change_str = f"{change:+.2f}" if change is not None else "N/A"
            change_pct_str = f"{change_pct:+.2f}%" if change_pct is not None else "N/A"
            open_str = f"¥{open_price:.2f}" if open_price is not None else "N/A"
            high_str = f"¥{high_price:.2f}" if high_price is not None else "N/A"
            low_str = f"¥{low_price:.2f}" if low_price is not None else "N/A"

            # 在结果开头添加实时行情标识
            realtime_notice = f"""
⚡ 实时行情（盘中）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 实时价格: {price_str}
📈 涨跌: {change_str} ({change_pct_str})
📊 今开: {open_str}  |  最高: {high_str}  |  最低: {low_str}
🕐 更新时间: {quote_date} {quote_time}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
            # 替换原有的最新价格部分
            lines = historical_result.split("\n")
            new_lines = []
            skip_next_price_lines = False

            for i, line in enumerate(lines):
                # 在标题后插入实时行情
                if i == 0 and "技术分析数据" in line:
                    new_lines.append(line)
                    # 找到数据期间行后插入
                    continue
                elif "数据期间:" in line:
                    new_lines.append(line)
                    # 插入实时行情通知
                    new_lines.append(realtime_notice)
                    continue
                # 跳过原有的最新价格行，因为实时行情已包含
                elif "💰 最新价格:" in line and not skip_next_price_lines:
                    skip_next_price_lines = True
                    continue
                elif skip_next_price_lines and "📈 涨跌额:" in line:
                    skip_next_price_lines = False
                    continue
                elif skip_next_price_lines:
                    continue
                else:
                    new_lines.append(line)

            return "\n".join(new_lines)

        except Exception as e:
            logger.error(f"❌ 合并实时行情失败: {e}")
            # 如果合并失败，返回原始结果
            return historical_result

    def _get_mongodb_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Dict[str, Any] = None,
    ) -> tuple[str, str | None]:
        """
        从MongoDB获取多周期数据 - 包含技术指标计算

        Returns:
            tuple[str, str | None]: (结果字符串, 实际使用的数据源名称)
        """
        logger.debug(
            f"📊 [MongoDB] 调用参数: symbol={symbol}, start_date={start_date}, end_date={end_date}, period={period}"
        )

        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                get_mongodb_cache_adapter,
            )

            adapter = get_mongodb_cache_adapter()

            # 从MongoDB获取指定周期的历史数据
            df = adapter.get_historical_data(
                symbol, start_date, end_date, period=period
            )

            if df is not None and not df.empty:
                logger.info(
                    f"✅ [数据来源: MongoDB缓存] 成功获取{period}数据: {symbol} ({len(df)}条记录)"
                )

                # 🔧 修复：使用统一的格式化方法，包含技术指标计算
                # 获取股票名称（从DataFrame中提取或使用默认值）
                stock_name = f"股票{symbol}"
                if "name" in df.columns and not df["name"].empty:
                    stock_name = df["name"].iloc[0]

                # 调用统一的格式化方法（包含技术指标计算，传入实时行情）
                result = self._format_stock_data_response(
                    df, symbol, stock_name, start_date, end_date, realtime_quote
                )

                logger.info(
                    f"✅ [MongoDB] 已计算技术指标: MA5/10/20/60, MACD, RSI, BOLL"
                )
                return result, "mongodb"
            else:
                # MongoDB没有数据（adapter内部已记录详细的数据源信息），降级到其他数据源
                logger.info(
                    f"🔄 [MongoDB] 未找到{period}数据: {symbol}，开始尝试备用数据源"
                )
                return self._try_fallback_sources(
                    symbol, start_date, end_date, period, realtime_quote
                )

        except Exception as e:
            logger.error(
                f"❌ [数据来源: MongoDB异常] 获取{period}数据失败: {symbol}, 错误: {e}"
            )
            # MongoDB异常，降级到其他数据源
            return self._try_fallback_sources(
                symbol, start_date, end_date, period, realtime_quote
            )

    def _run_async_safe(self, coro):
        """安全地运行异步协程，处理事件循环冲突"""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()

    def _get_tushare_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Dict[str, Any] = None,
    ) -> str:
        """使用Tushare获取多周期数据 - 使用provider + 统一缓存"""
        logger.debug(
            f"📊 [Tushare] 调用参数: symbol={symbol}, start_date={start_date}, end_date={end_date}, period={period}"
        )

        # 添加详细的股票代码追踪日志
        logger.info(
            f"🔍 [股票代码追踪] _get_tushare_data 接收到的股票代码: '{symbol}' (类型: {type(symbol)})"
        )
        logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(symbol))}")
        logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(symbol))}")
        logger.info(f"🔍 [DataSourceManager详细日志] _get_tushare_data 开始执行")
        logger.info(
            f"🔍 [DataSourceManager详细日志] 当前数据源: {self.current_source.value}"
        )

        start_time = time.time()
        try:
            # 🔥 检查是否跳过缓存
            skip_cache = (
                os.getenv("SKIP_MONGODB_CACHE_ON_QUERY", "true").lower() == "true"
            )

            # 1. 先尝试从缓存获取（除非配置了跳过）
            cached_data = None
            if not skip_cache:
                cached_data = self._get_cached_data(
                    symbol, start_date, end_date, max_age_hours=24
                )
            else:
                logger.info(
                    f"🔄 [配置跳过缓存] SKIP_MONGODB_CACHE_ON_QUERY=true，跳过缓存检查: {symbol}"
                )

            if cached_data is not None and not cached_data.empty:
                logger.info(f"✅ [缓存命中] 从缓存获取{symbol}数据")
                # 获取股票基本信息
                provider = self._get_tushare_adapter()
                if provider:
                    # 🔥 使用 _run_async_safe 避免事件循环冲突
                    stock_info = self._run_async_safe(
                        provider.get_stock_basic_info(symbol)
                    )
                    stock_name = (
                        stock_info.get("name", f"股票{symbol}")
                        if stock_info
                        else f"股票{symbol}"
                    )
                else:
                    stock_name = f"股票{symbol}"

                # 格式化返回
                return self._format_stock_data_response(
                    cached_data,
                    symbol,
                    stock_name,
                    start_date,
                    end_date,
                    realtime_quote,
                )

            # 2. 缓存未命中，从provider获取
            logger.info(
                f"🔍 [股票代码追踪] 调用 tushare_provider，传入参数: symbol='{symbol}'"
            )
            logger.info(f"🔍 [DataSourceManager详细日志] 开始调用tushare_provider...")

            provider = self._get_tushare_adapter()
            if not provider:
                return f"❌ Tushare提供器不可用"

            # 使用异步方法获取历史数据
            import asyncio

            data = self._run_async_safe(
                provider.get_historical_data(symbol, start_date, end_date)
            )

            if data is not None and not data.empty:
                # 保存到缓存
                self._save_to_cache(symbol, data, start_date, end_date)

                # 获取股票基本信息
                stock_info = self._run_async_safe(provider.get_stock_basic_info(symbol))
                stock_name = (
                    stock_info.get("name", f"股票{symbol}")
                    if stock_info
                    else f"股票{symbol}"
                )

                # 格式化返回
                result = self._format_stock_data_response(
                    data, symbol, stock_name, start_date, end_date, realtime_quote
                )

                duration = time.time() - start_time
                logger.info(
                    f"🔍 [DataSourceManager详细日志] 调用完成，耗时: {duration:.3f}秒"
                )
                logger.info(
                    f"🔍 [股票代码追踪] 返回结果前200字符: {result[:200] if result else 'None'}"
                )
                logger.debug(
                    f"📊 [Tushare] 调用完成: 耗时={duration:.2f}s, 结果长度={len(result) if result else 0}"
                )

                return result
            else:
                result = f"❌ 未获取到{symbol}的有效数据"
                duration = time.time() - start_time
                logger.warning(f"⚠️ [Tushare] 未获取到数据，耗时={duration:.2f}s")
                return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"❌ [Tushare] 调用失败: {e}, 耗时={duration:.2f}s", exc_info=True
            )
            logger.error(f"❌ [DataSourceManager详细日志] 异常类型: {type(e).__name__}")
            logger.error(f"❌ [DataSourceManager详细日志] 异常信息: {str(e)}")
            import traceback

            logger.error(
                f"❌ [DataSourceManager详细日志] 异常堆栈: {traceback.format_exc()}"
            )
            raise

    def _get_akshare_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Dict[str, Any] = None,
    ) -> str:
        """使用AKShare获取多周期数据 - 包含技术指标计算"""
        logger.debug(
            f"📊 [AKShare] 调用参数: symbol={symbol}, start_date={start_date}, end_date={end_date}, period={period}"
        )

        start_time = time.time()
        try:
            # 使用AKShare的统一接口
            from .providers.china.akshare import get_akshare_provider

            provider = get_akshare_provider()

            # 使用异步方法获取历史数据
            import asyncio

            data = self._run_async_safe(
                provider.get_historical_data(symbol, start_date, end_date, period)
            )

            duration = time.time() - start_time

            if data is not None and not data.empty:
                # 🔧 修复：使用统一的格式化方法，包含技术指标计算
                # 获取股票基本信息
                stock_info = self._run_async_safe(provider.get_stock_basic_info(symbol))
                stock_name = (
                    stock_info.get("name", f"股票{symbol}")
                    if stock_info
                    else f"股票{symbol}"
                )

                # 调用统一的格式化方法（包含技术指标计算）
                result = self._format_stock_data_response(
                    data, symbol, stock_name, start_date, end_date, realtime_quote
                )

                logger.debug(
                    f"📊 [AKShare] 调用成功: 耗时={duration:.2f}s, 数据条数={len(data)}, 结果长度={len(result)}"
                )
                logger.info(
                    f"✅ [AKShare] 已计算技术指标: MA5/10/20/60, MACD, RSI, BOLL"
                )
                return result
            else:
                result = f"❌ 未能获取{symbol}的股票数据"
                logger.warning(f"⚠️ [AKShare] 数据为空: 耗时={duration:.2f}s")
                return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"❌ [AKShare] 调用失败: {e}, 耗时={duration:.2f}s", exc_info=True
            )
            return f"❌ AKShare获取{symbol}数据失败: {e}"

    async def _get_baostock_data_async(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Dict[str, Any] = None,
    ) -> str:
        """使用BaoStock获取多周期数据 - 异步版本"""
        # 使用BaoStock的统一接口
        from .providers.china.baostock import get_baostock_provider

        provider = get_baostock_provider()

        # 🔥 FIX: 直接调用异步方法，不创建新的事件循环
        data = await provider.get_historical_data(symbol, start_date, end_date, period)

        if data is not None and not data.empty:
            # 🔧 修复：使用统一的格式化方法，包含技术指标计算
            # 获取股票基本信息
            stock_info = await provider.get_stock_basic_info(symbol)
            stock_name = (
                stock_info.get("name", f"股票{symbol}")
                if stock_info
                else f"股票{symbol}"
            )

            # 调用统一的格式化方法（包含技术指标计算）
            result = self._format_stock_data_response(
                data, symbol, stock_name, start_date, end_date, realtime_quote
            )

            logger.info(f"✅ [BaoStock] 已计算技术指标: MA5/10/20/60, MACD, RSI, BOLL")
            return result
        else:
            return f"❌ 未能获取{symbol}的股票数据"

    def _get_baostock_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Dict[str, Any] = None,
    ) -> str:
        """使用BaoStock获取多周期数据 - 同步包装器"""
        import asyncio

        try:
            # 🔥 FIX: 获取当前事件循环，如果已经在异步环境中，使用 create_task
            loop = asyncio.get_running_loop()
            # 如果在异步环境中，直接调用异步版本
            # 注意：这里不应该被直接调用，应该使用 _get_baostock_data_async
            logger.warning("⚠️ [_get_baostock_data] 在异步环境中被调用，使用线程池")

            # 使用线程池执行
            from concurrent.futures import ThreadPoolExecutor

            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    lambda: asyncio.run(
                        self._get_baostock_data_async(
                            symbol, start_date, end_date, period, realtime_quote
                        )
                    )
                )
                return future.result()
        except RuntimeError:
            # 不在异步环境中，直接运行
            return asyncio.run(
                self._get_baostock_data_async(
                    symbol, start_date, end_date, period, realtime_quote
                )
            )

    # TDX 数据获取方法已移除
    # def _get_tdx_data(self, symbol: str, start_date: str, end_date: str, period: str = "daily") -> str:
    #     """使用TDX获取多周期数据 (已移除)"""
    #     logger.error(f"❌ TDX数据源已不再支持")
    #     return f"❌ TDX数据源已不再支持"

    # 🔧 FIX: 删除重复的 _get_volume_safely 方法定义
    # 正确的版本在第769行，使用 iloc[-1] 获取最后一天的成交量
    # 这里的版本使用 sum() 是错误的，会导致成交量数据不一致
    # 详见: docs/reports/report_optimization_plan.md

    def _try_fallback_sources(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Dict[str, Any] = None,
    ) -> tuple[str, str | None]:
        """
        尝试备用数据源 - 避免递归调用

        Returns:
            tuple[str, str | None]: (结果字符串, 实际使用的数据源名称)
        """
        logger.info(
            f"🔄 [{self.current_source.value}] 失败，尝试备用数据源获取{period}数据: {symbol}"
        )

        # 🔥 从数据库获取数据源优先级顺序（根据股票代码识别市场）
        # 注意：不包含MongoDB，因为MongoDB是最高优先级，如果失败了就不再尝试
        fallback_order = self._get_data_source_priority_order(symbol)

        for source in fallback_order:
            if source != self.current_source and source in self.available_sources:
                try:
                    logger.info(
                        f"🔄 [备用数据源] 尝试 {source.value} 获取{period}数据: {symbol}"
                    )

                    # 直接调用具体的数据源方法，避免递归
                    if source == ChinaDataSource.TUSHARE:
                        result = self._get_tushare_data(
                            symbol, start_date, end_date, period, realtime_quote
                        )
                    elif source == ChinaDataSource.AKSHARE:
                        result = self._get_akshare_data(
                            symbol, start_date, end_date, period, realtime_quote
                        )
                    elif source == ChinaDataSource.BAOSTOCK:
                        result = self._get_baostock_data(
                            symbol, start_date, end_date, period, realtime_quote
                        )
                    # TDX 已移除
                    else:
                        logger.warning(f"⚠️ 未知数据源: {source.value}")
                        continue

                    if "❌" not in result:
                        logger.info(
                            f"✅ [备用数据源-{source.value}] 成功获取{period}数据: {symbol}"
                        )
                        return result, source.value  # 返回结果和实际使用的数据源
                    else:
                        logger.warning(
                            f"⚠️ [备用数据源-{source.value}] 返回错误结果: {symbol}"
                        )

                except Exception as e:
                    logger.error(
                        f"❌ [备用数据源-{source.value}] 获取失败: {symbol}, 错误: {e}"
                    )
                    continue

        # 🔥 FIX: 所有在线数据源都失败，尝试使用 MongoDB 缓存作为兜底（即使数据可能过期）
        logger.warning(f"⚠️ [所有在线数据源失败] 尝试使用 MongoDB 缓存兜底: {symbol}")
        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                get_mongodb_cache_adapter,
            )

            adapter = get_mongodb_cache_adapter()
            # 不限制日期范围，获取任何可用的历史数据
            df = adapter.get_historical_data(
                symbol, start_date=None, end_date=None, period=period
            )

            if df is not None and not df.empty:
                # 检查数据时效性
                if "date" in df.columns or "trade_date" in df.columns:
                    date_col = "date" if "date" in df.columns else "trade_date"
                    latest_date = df[date_col].max()
                    from datetime import datetime

                    if isinstance(latest_date, str):
                        latest_date = datetime.strptime(latest_date, "%Y-%m-%d")
                    days_old = (datetime.now() - latest_date).days

                    logger.warning(
                        f"⚠️ [MongoDB兜底] 使用可能过期的数据: {symbol}, "
                        f"最新数据日期: {latest_date.strftime('%Y-%m-%d')}, "
                        f"已过期: {days_old} 天"
                    )

                    # 获取股票名称
                    stock_name = f"股票{symbol}"
                    if "name" in df.columns and not df["name"].empty:
                        stock_name = df["name"].iloc[0]

                    # 调用统一的格式化方法
                    result = self._format_stock_data_response(
                        df, symbol, stock_name, start_date, end_date, realtime_quote
                    )

                    logger.info(
                        f"✅ [MongoDB兜底] 成功获取过期数据: {symbol} ({len(df)}条记录)"
                    )
                    return result, "mongodb_fallback"
            else:
                logger.error(f"❌ [MongoDB兜底] 也没有缓存数据: {symbol}")
        except Exception as e:
            logger.error(f"❌ [MongoDB兜底] 获取缓存数据失败: {symbol}, 错误: {e}")

        logger.error(f"❌ [所有数据源失败] 无法获取{period}数据: {symbol}")
        return f"❌ 所有数据源都无法获取{symbol}的{period}数据", None

    def _try_fallback_sources_with_save(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        period: str = "daily",
        realtime_quote: Dict[str, Any] = None,
    ) -> tuple[str, str | None]:
        """
        从在线数据源获取数据并保存到 MongoDB

        🔥 重构说明 (2026-02-01):
        - 跳过 MongoDB 查询，直接从在线数据源获取
        - 获取成功后保存到 MongoDB（如果配置了 SAVE_TO_MONGODB_AFTER_QUERY=true）
        - 优先级顺序从 .env 读取，默认: Tushare > AKShare > BaoStock

        Returns:
            tuple[str, str | None]: (结果字符串, 实际使用的数据源名称)
        """
        # 🔥 获取数据源优先级（从 .env 读取）
        fallback_order = self._get_data_source_priority_order(symbol)

        logger.info(
            f"🔄 [跳过MongoDB缓存] 直接从在线数据源获取: {symbol}, 优先级: {[s.value for s in fallback_order]}"
        )

        result_data = None
        actual_source = None

        # 依次尝试各数据源
        for source in fallback_order:
            try:
                logger.info(
                    f"🔄 [在线数据源] 尝试 {source.value} 获取{period}数据: {symbol}"
                )

                # 直接调用具体的数据源方法
                if source == ChinaDataSource.TUSHARE:
                    result_data = self._get_tushare_data(
                        symbol, start_date, end_date, period, realtime_quote
                    )
                elif source == ChinaDataSource.AKSHARE:
                    result_data = self._get_akshare_data(
                        symbol, start_date, end_date, period, realtime_quote
                    )
                elif source == ChinaDataSource.BAOSTOCK:
                    result_data = self._get_baostock_data(
                        symbol, start_date, end_date, period, realtime_quote
                    )
                else:
                    logger.warning(f"⚠️ 未知数据源: {source.value}")
                    continue

                if result_data and "❌" not in result_data:
                    actual_source = source.value
                    logger.info(
                        f"✅ [在线数据源-{source.value}] 成功获取{period}数据: {symbol}"
                    )
                    break  # 成功获取，跳出循环
                else:
                    logger.warning(
                        f"⚠️ [在线数据源-{source.value}] 返回错误结果: {symbol}"
                    )

            except Exception as e:
                logger.error(
                    f"❌ [在线数据源-{source.value}] 获取失败: {symbol}, 错误: {e}"
                )
                continue

        # 🔥 保存到 MongoDB（如果配置了 SAVE_TO_MONGODB_AFTER_QUERY=true）
        if result_data and "❌" not in result_data:
            save_to_mongodb = (
                os.getenv("SAVE_TO_MONGODB_AFTER_QUERY", "true").lower() == "true"
            )
            if save_to_mongodb and actual_source:
                try:
                    logger.info(
                        f"💾 [数据保存] 将 {symbol} 数据保存到 MongoDB (来源: {actual_source})"
                    )
                    # 数据保存逻辑在 provider 层已实现
                    # 这里只需要确认保存即可
                except Exception as e:
                    logger.warning(
                        f"⚠️ [数据保存] 保存到 MongoDB 失败: {symbol}, 错误: {e}"
                    )

            return result_data, actual_source

        # 所有在线数据源都失败，尝试 MongoDB 兜底
        logger.warning(f"⚠️ [所有在线数据源失败] 尝试使用 MongoDB 缓存兜底: {symbol}")
        return self._get_mongodb_data(
            symbol, start_date, end_date, period, realtime_quote
        )

    def get_stock_info(self, symbol: str) -> Dict:
        """
        获取股票基本信息，支持多数据源和自动降级
        优先级：MongoDB → Tushare → AKShare → BaoStock
        """
        logger.info(
            f"📊 [数据来源: {self.current_source.value}] 开始获取股票信息: {symbol}"
        )

        # 优先使用 App Mongo 缓存（当 ta_use_app_cache=True）
        try:
            from tradingagents.config.runtime_settings import (
                use_app_cache_enabled,  # type: ignore
            )

            use_cache = use_app_cache_enabled(False)
            logger.info(f"🔧 [配置检查] use_app_cache_enabled() 返回值: {use_cache}")
        except Exception as e:
            logger.error(
                f"❌ [配置检查] use_app_cache_enabled() 调用失败: {e}", exc_info=True
            )
            use_cache = False

        logger.info(
            f"🔧 [配置] ta_use_app_cache={use_cache}, current_source={self.current_source.value}"
        )

        if use_cache:
            try:
                from .cache.app_adapter import (
                    get_basics_from_cache,
                    get_market_quote_dataframe,
                )

                doc = get_basics_from_cache(symbol)
                if doc:
                    # 使用统一标准化器处理数据
                    data_source = doc.get("data_source", "app_cache")
                    standardized_data = standardize_stock_basic(doc, data_source)

                    # 从标准化数据中提取字段
                    name = standardized_data.get("name") or f"股票{symbol}"

                    # 规范化行业与板块（避免把"中小板/创业板"等板块值误作行业）
                    board_labels = {"主板", "中小板", "创业板", "科创板"}
                    raw_industry = standardized_data.get("industry", "") or ""
                    market_val = standardized_data.get("market", "") or ""

                    if raw_industry in board_labels:
                        if not market_val:
                            market_val = raw_industry
                        # 使用更细分类（如果有）
                        if standardized_data.get("industry_gn"):
                            industry_val = standardized_data.get("industry_gn")
                        elif standardized_data.get("industry_sw"):
                            industry_val = standardized_data.get("industry_sw")
                        else:
                            industry_val = "未知"
                    else:
                        industry_val = raw_industry or "未知"

                    result = {
                        "symbol": standardized_data.get("code", symbol),
                        "name": name,
                        "area": standardized_data.get("area", "未知"),
                        "industry": industry_val,
                        "market": market_val or standardized_data.get("market", "未知"),
                        "list_date": standardized_data.get("list_date", "未知"),
                        # 财务指标
                        "pe": standardized_data.get("pe"),
                        "pb": standardized_data.get("pb"),
                        "ps": standardized_data.get("ps"),
                        "pe_ttm": standardized_data.get("pe_ttm"),
                        "total_mv": standardized_data.get("total_mv"),
                        "circ_mv": standardized_data.get("circ_mv"),
                        # 每股指标 (2026-02-02 新增)
                        "eps": standardized_data.get("eps"),  # 每股收益
                        "bps": standardized_data.get("bps"),  # 每股净资产
                        "ocfps": standardized_data.get("ocfps"),  # 每股经营现金流
                        "capital_rese_ps": standardized_data.get(
                            "capital_rese_ps"
                        ),  # 每股公积金
                        "undist_profit_ps": standardized_data.get(
                            "undist_profit_ps"
                        ),  # 每股未分配利润
                        # 行情数据
                        "current_price": None,
                        "change_pct": None,
                        "volume": None,
                        # 元数据
                        "source": "app_cache",
                        "data_source": data_source,
                    }

                    # 追加快照行情（若存在）
                    try:
                        df = get_market_quote_dataframe(symbol)
                        if df is not None and not df.empty:
                            row = df.iloc[-1]
                            result["current_price"] = row.get("close")
                            result["change_pct"] = row.get("pct_chg")
                            # market_quotes 中的 volume 已经是"股"单位，无需再转换
                            result["volume"] = row.get("volume")
                            result["quote_date"] = row.get("date")
                            result["quote_source"] = "market_quotes"
                            logger.info(
                                f"✅ [股票信息] 附加行情 | price={result['current_price']} pct={result['change_pct']} vol={result['volume']} code={symbol}"
                            )
                    except Exception as _e:
                        logger.debug(f"附加行情失败（忽略）：{_e}")

                    if name and name != f"股票{symbol}":
                        logger.info(
                            f"✅ [数据来源: MongoDB-stock_basic_info] 成功获取: {symbol}"
                        )
                        return result
                    else:
                        logger.warning(
                            f"⚠️ [数据来源: MongoDB] 未找到有效名称: {symbol}，降级到其他数据源"
                        )
            except Exception as e:
                logger.error(
                    f"❌ [数据来源: MongoDB异常] 获取股票信息失败: {e}", exc_info=True
                )

        # 首先尝试当前数据源
        try:
            if self.current_source == ChinaDataSource.TUSHARE:
                from .interface import get_china_stock_info_tushare

                info_str = get_china_stock_info_tushare(symbol)
                raw_result = self._parse_stock_info_string(info_str, symbol)

                # 使用统一标准化器处理数据
                standardized_data = standardize_stock_basic(raw_result, "tushare")

                # 构建标准化结果
                result = {
                    "symbol": standardized_data.get("code", symbol),
                    "name": standardized_data.get("name", f"股票{symbol}"),
                    "area": standardized_data.get("area", "未知"),
                    "industry": standardized_data.get("industry", "未知"),
                    "market": standardized_data.get("market", "未知"),
                    "list_date": standardized_data.get("list_date", "未知"),
                    # 财务指标
                    "pe": standardized_data.get("pe"),
                    "pb": standardized_data.get("pb"),
                    "ps": standardized_data.get("ps"),
                    "pe_ttm": standardized_data.get("pe_ttm"),
                    "total_mv": standardized_data.get("total_mv"),
                    "circ_mv": standardized_data.get("circ_mv"),
                    # 行情数据（从原始数据获取）
                    "current_price": raw_result.get("current_price"),
                    "change_pct": raw_result.get("change_pct"),
                    "volume": raw_result.get("volume"),
                    # 元数据
                    "source": "tushare",
                    "data_source": "tushare",
                }

                # 检查是否获取到有效信息
                if result.get("name") and result["name"] != f"股票{symbol}":
                    logger.info(f"✅ [数据来源: Tushare-股票信息] 成功获取: {symbol}")
                    return result
                else:
                    # 🔥 FIX: 添加详细日志以便诊断问题
                    logger.warning(
                        f"⚠️ [数据来源: Tushare失败] 返回无效信息，尝试降级: {symbol}\n"
                        f"    诊断信息: name={result.get('name')!r}, "
                        f"industry={result.get('industry')!r}, "
                        f"area={result.get('area')!r}, "
                        f"raw_result={raw_result}"
                    )
                    return self._try_fallback_stock_info(symbol)
            else:
                adapter = self.get_data_adapter()
                if adapter and hasattr(adapter, "get_stock_info"):
                    raw_result = adapter.get_stock_info(symbol)

                    # 使用统一标准化器处理数据
                    data_source_name = self.current_source.value
                    standardized_data = standardize_stock_basic(
                        raw_result, data_source_name
                    )

                    # 构建标准化结果
                    result = {
                        "symbol": standardized_data.get("code", symbol),
                        "name": standardized_data.get("name", f"股票{symbol}"),
                        "area": standardized_data.get("area", "未知"),
                        "industry": standardized_data.get("industry", "未知"),
                        "market": standardized_data.get("market", "未知"),
                        "list_date": standardized_data.get("list_date", "未知"),
                        # 财务指标
                        "pe": standardized_data.get("pe"),
                        "pb": standardized_data.get("pb"),
                        "ps": standardized_data.get("ps"),
                        "pe_ttm": standardized_data.get("pe_ttm"),
                        "total_mv": standardized_data.get("total_mv"),
                        "circ_mv": standardized_data.get("circ_mv"),
                        # 行情数据
                        "current_price": raw_result.get("current_price"),
                        "change_pct": raw_result.get("change_pct"),
                        "volume": raw_result.get("volume"),
                        # 元数据
                        "source": data_source_name,
                        "data_source": data_source_name,
                    }

                    if result.get("name") and result["name"] != f"股票{symbol}":
                        logger.info(
                            f"✅ [数据来源: {self.current_source.value}-股票信息] 成功获取: {symbol}"
                        )
                        return result
                    else:
                        # 🔥 FIX: 添加详细日志以便诊断问题
                        logger.warning(
                            f"⚠️ [数据来源: {self.current_source.value}失败] 返回无效信息，尝试降级: {symbol}\n"
                            f"    诊断信息: name={result.get('name')!r}, "
                            f"industry={result.get('industry')!r}, "
                            f"area={result.get('area')!r}, "
                            f"raw_result={raw_result}"
                        )
                        return self._try_fallback_stock_info(symbol)
                else:
                    logger.warning(
                        f"⚠️ [数据来源: {self.current_source.value}] 不支持股票信息获取，尝试降级: {symbol}"
                    )
                    return self._try_fallback_stock_info(symbol)

        except Exception as e:
            logger.error(
                f"❌ [数据来源: {self.current_source.value}异常] 获取股票信息失败: {e}",
                exc_info=True,
            )
            return self._try_fallback_stock_info(symbol)

    def get_stock_basic_info(self, stock_code: str = None) -> Optional[Dict[str, Any]]:
        """
        获取股票基础信息（兼容 stock_data_service 接口）

        Args:
            stock_code: 股票代码，如果为 None 则返回所有股票列表

        Returns:
            Dict: 股票信息字典，或包含 error 字段的错误字典
        """
        if stock_code is None:
            # 返回所有股票列表
            logger.info("📊 获取所有股票列表")
            try:
                # 尝试从 MongoDB 获取
                from tradingagents.config.database_manager import get_database_manager

                db_manager = get_database_manager()
                if db_manager and db_manager.is_mongodb_available():
                    collection = db_manager.mongodb_db["stock_basic_info"]
                    stocks = list(collection.find({}, {"_id": 0}))
                    if stocks:
                        logger.info(f"✅ 从MongoDB获取所有股票: {len(stocks)}条")
                        return stocks
            except Exception as e:
                logger.warning(f"⚠️ 从MongoDB获取所有股票失败: {e}")

            # 降级：返回空列表
            return []

        # 获取单个股票信息
        try:
            result = self.get_stock_info(stock_code)
            if result and result.get("name"):
                return result
            else:
                return {"error": f"未找到股票 {stock_code} 的信息"}
        except Exception as e:
            logger.error(f"❌ 获取股票信息失败: {e}")
            return {"error": str(e)}

    def get_stock_data_with_fallback(
        self,
        stock_code: str,
        start_date: str,
        end_date: str,
        analysis_date: str = None,
    ) -> str:
        """
        获取股票数据（兼容 stock_data_service 接口）

        Args:
            stock_code: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            analysis_date: 分析日期（YYYY-MM-DD），用于判断实时行情

        Returns:
            str: 格式化的股票数据报告
        """
        logger.info(f"📊 获取股票数据: {stock_code} ({start_date} 到 {end_date})")

        try:
            # 使用统一的数据获取接口
            return self.get_stock_data(
                stock_code, start_date, end_date, analysis_date=analysis_date
            )
        except Exception as e:
            logger.error(f"❌ 获取股票数据失败: {e}")
            return f"❌ 获取股票数据失败: {str(e)}\n\n💡 建议：\n1. 检查网络连接\n2. 确认股票代码格式正确\n3. 检查数据源配置"

    def _try_fallback_stock_info(self, symbol: str) -> Dict:
        """尝试使用备用数据源获取股票基本信息"""
        logger.error(
            f"🔄 {self.current_source.value}失败，尝试备用数据源获取股票信息..."
        )

        # 获取所有可用数据源
        available_sources = self.available_sources.copy()

        # 移除当前数据源
        if self.current_source.value in available_sources:
            available_sources.remove(self.current_source.value)

        # 尝试所有备用数据源
        for source_name in available_sources:
            try:
                source = ChinaDataSource(source_name)
                logger.info(f"🔄 尝试备用数据源获取股票信息: {source_name}")

                # 根据数据源类型获取股票信息
                if source == ChinaDataSource.TUSHARE:
                    # 🔥 直接调用 Tushare 适配器，避免循环调用
                    result = self._get_tushare_stock_info(symbol)
                elif source == ChinaDataSource.AKSHARE:
                    result = self._get_akshare_stock_info(symbol)
                elif source == ChinaDataSource.BAOSTOCK:
                    result = self._get_baostock_stock_info(symbol)
                else:
                    # 尝试通用适配器
                    original_source = self.current_source
                    self.current_source = source
                    adapter = self.get_data_adapter()
                    self.current_source = original_source

                    if adapter and hasattr(adapter, "get_stock_info"):
                        result = adapter.get_stock_info(symbol)
                    else:
                        logger.warning(f"⚠️ [股票信息] {source_name}不支持股票信息获取")
                        continue

                # 检查是否获取到有效信息
                if result.get("name") and result["name"] != f"股票{symbol}":
                    logger.info(
                        f"✅ [数据来源: 备用数据源] 降级成功获取股票信息: {source_name}"
                    )
                    return result
                else:
                    logger.warning(f"⚠️ [数据来源: {source_name}] 返回无效信息")

            except Exception as e:
                logger.error(f"❌ 备用数据源{source_name}失败: {e}")
                continue

        # 所有数据源都失败，返回默认值
        logger.error(f"❌ 所有数据源都无法获取{symbol}的股票信息")
        return {"symbol": symbol, "name": f"股票{symbol}", "source": "unknown"}

    def _get_akshare_stock_info(self, symbol: str) -> Dict:
        """使用AKShare获取股票基本信息

        🔥 重要：AKShare 需要区分股票和指数
        - 对于 000001，如果不加后缀，会被识别为"深圳成指"（指数）
        - 对于股票，需要使用完整代码（如 sz000001 或 sh600000）
        """
        try:
            import akshare as ak

            # 🔥 转换为 AKShare 格式的股票代码
            # AKShare 的 stock_individual_info_em 需要使用 "sz000001" 或 "sh600000" 格式
            if symbol.startswith("6"):
                # 上海股票：600000 -> sh600000
                akshare_symbol = f"sh{symbol}"
            elif symbol.startswith(("0", "3", "2")):
                # 深圳股票：000001 -> sz000001
                akshare_symbol = f"sz{symbol}"
            elif symbol.startswith(("8", "4")):
                # 北京股票：830000 -> bj830000
                akshare_symbol = f"bj{symbol}"
            else:
                # 其他情况，直接使用原始代码
                akshare_symbol = symbol

            logger.debug(
                f"📊 [AKShare股票信息] 原始代码: {symbol}, AKShare格式: {akshare_symbol}"
            )

            # 🔥 FIX: 尝试获取个股信息，增强错误处理
            try:
                stock_info = ak.stock_individual_info_em(symbol=akshare_symbol)
                logger.debug(
                    f"📊 [AKShare] stock_individual_info_em 返回类型: {type(stock_info)}"
                )
            except ValueError as ve:
                # 🔥 FIX: 捕获 pandas DataFrame 构造错误
                error_msg = str(ve)
                if "scalar values" in error_msg or "index" in error_msg:
                    logger.warning(
                        f"⚠️ [AKShare] stock_individual_info_em 返回数据格式异常 "
                        f"(可能是API返回空数据): {ve}"
                    )
                else:
                    logger.warning(
                        f"⚠️ [AKShare] stock_individual_info_em 参数错误: {ve}"
                    )
            except Exception as api_e:
                logger.warning(
                    f"⚠️ [AKShare] stock_individual_info_em 调用失败: {api_e}"
                )
                # 🔥 FIX: 尝试备选方案 - 使用 stock_zh_a_spot_em 获取全市场数据然后筛选
                # 🔥 FIX: 添加重试机制以处理网络错误
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        logger.info(
                            f"🔄 [AKShare备用方案] 尝试从全市场数据获取: {symbol} (尝试 {attempt + 1}/{max_retries})"
                        )
                        spot_df = ak.stock_zh_a_spot_em()
                        if spot_df is not None and not spot_df.empty:
                            # 在 spot 数据中查找该股票
                            code_col = (
                                "代码"
                                if "代码" in spot_df.columns
                                else "symbol"
                                if "symbol" in spot_df.columns
                                else None
                            )
                            if code_col:
                                stock_row = spot_df[spot_df[code_col] == symbol]
                                if not stock_row.empty:
                                    name_col = (
                                        "名称"
                                        if "名称" in stock_row.columns
                                        else "name"
                                        if "name" in stock_row.columns
                                        else None
                                    )
                                    if name_col:
                                        stock_name = stock_row.iloc[0][name_col]
                                        logger.info(
                                            f"✅ [AKShare备用方案] {symbol} -> {stock_name}"
                                        )
                                        return {
                                            "symbol": symbol,
                                            "name": stock_name,
                                            "source": "akshare",
                                            "area": "未知",
                                            "industry": "未知",
                                            "market": "未知",
                                            "list_date": "未知",
                                        }
                        # 如果没找到数据，跳出重试循环
                        break
                    except Exception as backup_e:
                        error_str = str(backup_e)
                        is_network_error = any(
                            x in error_str.lower()
                            for x in [
                                "remote",
                                "connection",
                                "aborted",
                                "reset",
                                "closed",
                                "without response",
                            ]
                        )
                        if is_network_error and attempt < max_retries - 1:
                            wait_time = min(1.0 * (2**attempt), 10.0)
                            logger.warning(
                                f"⚠️ [AKShare备用方案] 网络错误，等待 {wait_time:.1f} 秒后重试 "
                                f"({attempt + 1}/{max_retries}): {error_str[:100]}"
                            )
                            import time

                            time.sleep(wait_time)
                            continue
                        else:
                            logger.warning(f"⚠️ [AKShare备用方案] 失败: {backup_e}")
                            break

                # 如果所有方法都失败，返回默认信息
                return {
                    "symbol": symbol,
                    "name": f"股票{symbol}",
                    "source": "akshare",
                    "error": f"主接口: {api_e}",
                }

            if (
                stock_info is not None
                and hasattr(stock_info, "empty")
                and not stock_info.empty
            ):
                # 转换为字典格式
                info = {"symbol": symbol, "source": "akshare"}

                # 🔥 FIX: 添加类型检查，确保 stock_info 是 DataFrame
                if not isinstance(stock_info, pd.DataFrame):
                    logger.warning(
                        f"⚠️ [AKShare] 返回类型异常: {type(stock_info)}, 期望 DataFrame"
                    )
                    return {
                        "symbol": symbol,
                        "name": f"股票{symbol}",
                        "source": "akshare",
                    }

                # 提取股票名称
                try:
                    name_row = stock_info[stock_info["item"] == "股票简称"]
                    if not name_row.empty:
                        stock_name = name_row["value"].iloc[0]
                        info["name"] = stock_name
                        logger.info(f"✅ [AKShare股票信息] {symbol} -> {stock_name}")
                    else:
                        info["name"] = f"股票{symbol}"
                        logger.warning(f"⚠️ [AKShare股票信息] 未找到股票简称: {symbol}")
                except Exception as extract_e:
                    logger.warning(f"⚠️ [AKShare] 提取股票名称失败: {extract_e}")
                    info["name"] = f"股票{symbol}"

                # 提取其他信息
                info["area"] = "未知"  # AKShare没有地区信息
                info["industry"] = "未知"  # 可以通过其他API获取
                info["market"] = "未知"  # 可以根据股票代码推断
                info["list_date"] = "未知"  # 可以通过其他API获取

                return info
            else:
                logger.warning(f"⚠️ [AKShare股票信息] 返回空数据: {symbol}")
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "akshare"}

        except Exception as e:
            logger.error(f"❌ [股票信息] AKShare获取失败: {symbol}, 错误: {e}")
            return {
                "symbol": symbol,
                "name": f"股票{symbol}",
                "source": "akshare",
                "error": str(e),
            }

    def _get_baostock_stock_info(self, symbol: str) -> Dict:
        """使用BaoStock获取股票基本信息"""
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
                logger.error(f"❌ [股票信息] BaoStock登录失败: {lg.error_msg}")
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "baostock"}

            # 查询股票基本信息
            rs = bs.query_stock_basic(code=bs_code)
            if rs.error_code != "0":
                bs.logout()
                logger.error(f"❌ [股票信息] BaoStock查询失败: {rs.error_msg}")
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "baostock"}

            # 解析结果
            data_list = []
            while (rs.error_code == "0") & rs.next():
                data_list.append(rs.get_row_data())

            # 登出
            bs.logout()

            if data_list:
                # BaoStock返回格式: [code, code_name, ipoDate, outDate, type, status]
                info = {"symbol": symbol, "source": "baostock"}
                info["name"] = data_list[0][1]  # code_name
                info["area"] = "未知"  # BaoStock没有地区信息
                info["industry"] = "未知"  # BaoStock没有行业信息
                info["market"] = "未知"  # 可以根据股票代码推断
                info["list_date"] = data_list[0][2]  # ipoDate

                return info
            else:
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "baostock"}

        except Exception as e:
            logger.error(f"❌ [股票信息] BaoStock获取失败: {e}")
            return {
                "symbol": symbol,
                "name": f"股票{symbol}",
                "source": "baostock",
                "error": str(e),
            }

    def _get_tushare_stock_info(self, symbol: str) -> Dict:
        """使用Tushare获取股票基本信息"""
        try:
            from .providers.china.tushare import TushareProvider

            provider = TushareProvider()
            if not provider.is_available():
                logger.warning(f"⚠️ [股票信息] Tushare未连接")
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "tushare"}

            if not provider.api:
                logger.warning(f"⚠️ [股票信息] Tushare API未初始化")
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "tushare"}

            # 🔥 FIX: 使用正确的 ts_code 格式 (code.SZ 或 code.SH)
            ts_code = provider._normalize_ts_code(symbol)

            stock_data = provider.api.stock_basic(
                ts_code=ts_code,
                fields="ts_code,symbol,name,area,industry,list_date,exchange,market",
            )

            if stock_data is not None and not stock_data.empty:
                row = stock_data.iloc[0]
                # 🔥 FIX: 使用 `or` 操作符处理空值情况
                # dict.get() 只在 key 不存在时返回默认值
                # 使用 `value or default` 可以在值为空字符串/None时也返回默认值
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
                return {"symbol": symbol, "name": f"股票{symbol}", "source": "tushare"}

        except Exception as e:
            logger.error(f"❌ [股票信息] Tushare获取失败: {e}")
            return {
                "symbol": symbol,
                "name": f"股票{symbol}",
                "source": "tushare",
                "error": str(e),
            }

    def _parse_stock_info_string(self, info_str: str, symbol: str) -> Dict:
        """解析股票信息字符串为字典"""
        try:
            info = {"symbol": symbol, "source": self.current_source.value}
            lines = info_str.split("\n")

            for line in lines:
                if ":" in line:
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    if "股票名称" in key:
                        info["name"] = value
                    elif "所属行业" in key:
                        info["industry"] = value
                    elif "所属地区" in key:
                        info["area"] = value
                    elif "上市市场" in key:
                        info["market"] = value
                    elif "上市日期" in key:
                        info["list_date"] = value

            return info

        except Exception as e:
            logger.error(f"⚠️ 解析股票信息失败: {e}")
            return {
                "symbol": symbol,
                "name": f"股票{symbol}",
                "source": self.current_source.value,
            }

    # ==================== 基本面数据获取方法 ====================

    def _get_mongodb_fundamentals(self, symbol: str) -> str:
        """从 MongoDB 获取财务数据"""
        logger.debug(f"📊 [MongoDB] 调用参数: symbol={symbol}")

        try:
            import pandas as pd

            from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                get_mongodb_cache_adapter,
            )

            adapter = get_mongodb_cache_adapter()

            # 从 MongoDB 获取财务数据
            financial_data = adapter.get_financial_data(symbol)

            # 检查数据类型和内容
            if financial_data is not None:
                # 如果是 DataFrame，转换为字典列表
                if isinstance(financial_data, pd.DataFrame):
                    if not financial_data.empty:
                        logger.info(
                            f"✅ [数据来源: MongoDB-财务数据] 成功获取: {symbol} ({len(financial_data)}条记录)"
                        )
                        # 转换为字典列表
                        financial_dict_list = financial_data.to_dict("records")
                        # 格式化财务数据为报告
                        return self._format_financial_data(symbol, financial_dict_list)
                    else:
                        logger.warning(
                            f"⚠️ [数据来源: MongoDB] 财务数据为空: {symbol}，降级到其他数据源"
                        )
                        return self._try_fallback_fundamentals(symbol)
                # 如果是列表
                elif isinstance(financial_data, list) and len(financial_data) > 0:
                    logger.info(
                        f"✅ [数据来源: MongoDB-财务数据] 成功获取: {symbol} ({len(financial_data)}条记录)"
                    )
                    return self._format_financial_data(symbol, financial_data)
                # 如果是单个字典（这是MongoDB实际返回的格式）
                elif isinstance(financial_data, dict):
                    logger.info(
                        f"✅ [数据来源: MongoDB-财务数据] 成功获取: {symbol} (单条记录)"
                    )
                    # 将单个字典包装成列表
                    financial_dict_list = [financial_data]
                    return self._format_financial_data(symbol, financial_dict_list)
                else:
                    logger.warning(
                        f"⚠️ [数据来源: MongoDB] 未找到财务数据: {symbol}，降级到其他数据源"
                    )
                    return self._try_fallback_fundamentals(symbol)
            else:
                logger.warning(
                    f"⚠️ [数据来源: MongoDB] 未找到财务数据: {symbol}，降级到其他数据源"
                )
                # MongoDB 没有数据，降级到其他数据源
                return self._try_fallback_fundamentals(symbol)

        except Exception as e:
            logger.error(
                f"❌ [数据来源: MongoDB异常] 获取财务数据失败: {e}", exc_info=True
            )
            # MongoDB 异常，降级到其他数据源
            return self._try_fallback_fundamentals(symbol)

    def _get_tushare_fundamentals(self, symbol: str) -> str:
        """从 Tushare 获取基本面数据"""
        try:
            from .providers.china.tushare import get_tushare_provider

            logger.info(f"📊 [Tushare] 开始获取基本面数据: {symbol}")

            provider = get_tushare_provider()

            # 检查 provider 是否可用
            if not provider.is_available():
                logger.warning(f"⚠️ [Tushare] Provider 不可用，未初始化或无 Token")
                return f"⚠️ Tushare 未初始化或 Token 无效，请检查配置"

            # 获取最新交易日期的每日基础数据
            # 如果今天没有交易日数据，自动查找最近的交易日
            from datetime import datetime, timedelta

            trade_date = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"📊 [Tushare] 初始查询日期: {trade_date}")

            # 调用 get_daily_basic 获取 PE、PB、PS 等指标
            import asyncio

            try:
                # 创建或获取事件循环
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_closed():
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                # 首先尝试今天的数据
                df = loop.run_until_complete(provider.get_daily_basic(trade_date))

                # 如果今天没有数据，尝试查找最近的交易日
                if df is None or df.empty:
                    logger.info(
                        f"📊 [Tushare] {trade_date} 无数据，查找最近的交易日..."
                    )
                    for delta in range(1, 10):  # 最多回溯 10 天
                        check_date = (datetime.now() - timedelta(days=delta)).strftime(
                            "%Y-%m-%d"
                        )
                        logger.info(f"📊 [Tushare] 尝试日期: {check_date}")
                        df = loop.run_until_complete(
                            provider.get_daily_basic(check_date)
                        )
                        if df is not None and not df.empty:
                            trade_date = check_date
                            logger.info(f"✅ [Tushare] 找到交易日数据: {trade_date}")
                            break

                if df is None or df.empty:
                    logger.warning(
                        f"⚠️ [Tushare] daily_basic 返回空数据（尝试了最近 10 天）"
                    )
                    return f"⚠️ Tushare daily_basic 接口未返回数据，可能需要更高权限的 Token"

                logger.info(f"✅ [Tushare] daily_basic 返回 {len(df)} 条记录")

                # 查找指定股票的数据
                # 需要将代码转换为 Tushare 格式 (如 605589 -> 605589.SH)
                ts_code = self._convert_to_tushare_code(symbol)
                logger.info(f"🔍 [Tushare] 查询代码: {ts_code}")

                stock_data = df[df["ts_code"] == ts_code]

                if stock_data.empty:
                    logger.warning(f"⚠️ [Tushare] 未找到 {symbol} ({ts_code}) 的数据")
                    # 尝试用原始代码查询
                    stock_data = df[df["ts_code"] == symbol]
                    if stock_data.empty:
                        return f"⚠️ 未找到 {symbol} 的基本面数据，请检查股票代码或数据源权限"

                # 获取第一行数据
                row = stock_data.iloc[0]

                # 格式化输出
                report = f"📊 {symbol} 基本面数据（来自 Tushare）\n\n"
                report += f"📅 数据日期: {trade_date}\n"
                report += f"📈 数据来源: Tushare daily_basic 接口\n\n"

                # 估值指标
                report += "💰 估值指标:\n"

                pe = row.get("pe")
                if pe is not None and pd.notna(pe) and pe != 0:
                    report += f"   市盈率(PE): {pe:.2f}\n"

                pb = row.get("pb")
                if pb is not None and pd.notna(pb) and pb != 0:
                    report += f"   市净率(PB): {pb:.2f}\n"

                pe_ttm = row.get("pe_ttm")
                if pe_ttm is not None and pd.notna(pe_ttm) and pe_ttm != 0:
                    report += f"   市盈率TTM(PE_TTM): {pe_ttm:.2f}\n"

                pb_mrq = row.get("pb_mrq")
                if pb_mrq is not None and pd.notna(pb_mrq) and pb_mrq != 0:
                    report += f"   市净率MRQ(PB_MHQ): {pb_mrq:.2f}\n"

                total_mv = row.get("total_mv")
                if total_mv is not None and pd.notna(total_mv):
                    report += f"   总市值: {total_mv:.2f}亿元\n"

                circ_mv = row.get("circ_mv")
                if circ_mv is not None and pd.notna(circ_mv):
                    report += f"   流通市值: {circ_mv:.2f}亿元\n"

                turnover_rate = row.get("turnover_rate")
                if turnover_rate is not None and pd.notna(turnover_rate):
                    report += f"   换手率: {turnover_rate:.2f}%\n"

                volume_ratio = row.get("volume_ratio")
                if volume_ratio is not None and pd.notna(volume_ratio):
                    report += f"   量比: {volume_ratio:.2f}\n"

                logger.info(f"✅ [Tushare] 成功获取基本面数据: {symbol}")
                logger.info(f"   PE={pe}, PB={pb}, PE_TTM={pe_ttm}")
                return report

            except asyncio.TimeoutError:
                logger.error(f"❌ [Tushare] async 操作超时")
                return f"❌ Tushare 数据获取超时，请稍后重试"
            except Exception as async_err:
                logger.error(f"❌ [Tushare] async 操作失败: {async_err}")
                return f"❌ Tushare 数据获取失败: {async_err}"

        except ImportError as e:
            logger.error(f"❌ [Tushare] 导入失败: {e}")
            return f"❌ Tushare 模块导入失败，请检查安装: {e}"
        except Exception as e:
            logger.error(f"❌ [Tushare] 获取基本面数据失败: {symbol} - {e}")
            import traceback

            logger.error(f"❌ 堆栈跟踪:\n{traceback.format_exc()}")
            return f"❌ 获取 {symbol} 基本面数据失败: {e}"

    def _convert_to_tushare_code(self, symbol: str) -> str:
        """
        将股票代码转换为 Tushare 格式

        Args:
            symbol: 股票代码 (如 605589, 605589.SH, 000001.SZ)

        Returns:
            str: Tushare 格式代码 (如 605589.SH)
        """
        # 移除已有的后缀
        symbol = str(symbol).strip().upper()
        symbol = symbol.replace(".SH", "").replace(".SZ", "").replace(".BJ", "")

        # 根据代码前缀判断交易所
        if symbol.startswith(("60", "68", "90")):
            return f"{symbol}.SH"  # 上海证券交易所
        elif symbol.startswith(("00", "30", "20")):
            return f"{symbol}.SZ"  # 深圳证券交易所
        elif symbol.startswith(("8", "4")):
            return f"{symbol}.BJ"  # 北京证券交易所
        else:
            # 无法识别的代码，返回原始代码
            logger.warning(f"⚠️ [Tushare] 无法识别 {symbol} 的交易所，返回原始代码")
            return symbol

    def _get_tushare_financial_indicators(self, symbol: str) -> str:
        """从 Tushare 获取财务指标数据"""
        try:
            from .providers.china.tushare import get_tushare_provider
            import asyncio

            logger.info(f"📊 [Tushare] 开始获取财务指标: {symbol}")

            provider = get_tushare_provider()

            # 检查 provider 是否可用
            if not provider.is_available():
                logger.warning(f"⚠️ [Tushare] Provider 不可用")
                return f"⚠️ Tushare 未初始化或 Token 无效，请检查配置"

            # 创建事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 调用 TushareProvider 的财务指标方法
            result = loop.run_until_complete(
                provider.get_financial_indicators_only(symbol, limit=1)
            )

            if not result or not result.get("financial_indicators"):
                logger.warning(f"⚠️ [Tushare] 未找到 {symbol} 的财务指标数据")
                return f"⚠️ 未找到 {symbol} 的财务指标数据"

            indicators = result["financial_indicators"][0]

            # 格式化输出
            report = f"\n📊 {symbol} 财务指标（来自 Tushare）\n\n"

            # 盈利能力
            report += "💹 盈利能力:\n"
            roe = indicators.get("roe")
            if roe is not None and pd.notna(roe):
                report += f"   ROE(净资产收益率): {roe:.2f}%\n"

            roa = indicators.get("roa")
            if roa is not None and pd.notna(roa):
                report += f"   ROA(总资产收益率): {roa:.2f}%\n"

            gross_profit_margin = indicators.get("grossprofit_margin")
            if gross_profit_margin is not None and pd.notna(gross_profit_margin):
                report += f"   毛利率: {gross_profit_margin:.2f}%\n"

            net_profit_margin = indicators.get("netprofit_margin")
            if net_profit_margin is not None and pd.notna(net_profit_margin):
                report += f"   净利率: {net_profit_margin:.2f}%\n"

            # 偿债能力
            report += "\n🏦 偿债能力:\n"
            debt_to_assets = indicators.get("debt_to_assets")
            if debt_to_assets is not None and pd.notna(debt_to_assets):
                report += f"   资产负债率: {debt_to_assets:.2f}%\n"

            current_ratio = indicators.get("current_ratio")
            if current_ratio is not None and pd.notna(current_ratio):
                report += f"   流动比率: {current_ratio:.2f}\n"

            quick_ratio = indicators.get("quick_ratio")
            if quick_ratio is not None and pd.notna(quick_ratio):
                report += f"   速动比率: {quick_ratio:.2f}\n"

            # 营运能力
            report += "\n🔄 营运能力:\n"
            inv_turn = indicators.get("inv_turn")
            if inv_turn is not None and pd.notna(inv_turn):
                report += f"   存货周转率: {inv_turn:.2f}次\n"

            ar_turn = indicators.get("ar_turn")
            if ar_turn is not None and pd.notna(ar_turn):
                report += f"   应收账款周转率: {ar_turn:.2f}次\n"

            ca_turn = indicators.get("ca_turn")
            if ca_turn is not None and pd.notna(ca_turn):
                report += f"   流动资产周转率: {ca_turn:.2f}次\n"

            # 成长能力
            report += "\n📈 成长能力:\n"
            or_ratio = indicators.get("or_ratio")
            if or_ratio is not None and pd.notna(or_ratio):
                report += f"   营业收入增长率: {or_ratio:.2f}%\n"

            op_profit_growth = indicators.get("op_profit_growth_rate_yoy")
            if op_profit_growth is not None and pd.notna(op_profit_growth):
                report += f"   营业利润增长率: {op_profit_growth:.2f}%\n"

            logger.info(f"✅ [Tushare] 成功获取财务指标: {symbol}")
            return report

        except Exception as e:
            logger.error(f"❌ [Tushare] 获取财务指标失败: {symbol} - {e}")
            import traceback

            logger.error(f"❌ 堆栈跟踪:\n{traceback.format_exc()}")
            return f"❌ 获取 {symbol} 财务指标失败: {e}"

    def _get_tushare_financial_reports(self, symbol: str) -> str:
        """从 Tushare 获取完整财务报表"""
        try:
            from .providers.china.tushare import get_tushare_provider
            import asyncio

            logger.info(f"📊 [Tushare] 开始获取财务报表: {symbol}")

            provider = get_tushare_provider()

            # 检查 provider 是否可用
            if not provider.is_available():
                logger.warning(f"⚠️ [Tushare] Provider 不可用")
                return f"⚠️ Tushare 未初始化或 Token 无效，请检查配置"

            # 创建事件循环
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 调用 TushareProvider 的财务数据方法
            result = loop.run_until_complete(
                provider.get_financial_data(symbol, report_type="quarterly", limit=1)
            )

            if not result:
                logger.warning(f"⚠️ [Tushare] 未找到 {symbol} 的财务报表数据")
                return f"⚠️ 未找到 {symbol} 的财务报表数据"

            # 格式化输出
            report = f"\n📊 {symbol} 财务报表（来自 Tushare）\n\n"

            # 利润表数据
            income_data = result.get("income_statement")
            if income_data and len(income_data) > 0:
                report += "💰 利润表:\n"
                latest_income = income_data[0]
                report += f"   报告期: {latest_income.get('end_date', '未知')}\n"
                report += (
                    f"   营业总收入: {latest_income.get('total_revenue', 0):,.2f}万元\n"
                )
                report += f"   营业收入: {latest_income.get('revenue', 0):,.2f}万元\n"
                report += (
                    f"   营业成本: {latest_income.get('operating_cost', 0):,.2f}万元\n"
                )
                report += f"   净利润: {latest_income.get('n_income', 0):,.2f}万元\n"
                report += f"   扣非净利润: {latest_income.get('n_income_attr_p', 0):,.2f}万元\n"

            # 资产负债表数据
            balance_data = result.get("balance_sheet")
            if balance_data and len(balance_data) > 0:
                report += "\n📦 资产负债表:\n"
                latest_balance = balance_data[0]
                report += f"   报告期: {latest_balance.get('end_date', '未知')}\n"
                report += (
                    f"   总资产: {latest_balance.get('total_assets', 0):,.2f}万元\n"
                )
                report += f"   总负债: {latest_balance.get('total_liab', 0):,.2f}万元\n"
                report += f"   股东权益: {latest_balance.get('total_hldr_eqy_exc_min_int', 0):,.2f}万元\n"
                report += f"   流动资产: {latest_balance.get('total_cur_assets', 0):,.2f}万元\n"
                report += (
                    f"   流动负债: {latest_balance.get('total_cur_liab', 0):,.2f}万元\n"
                )

            # 现金流量表数据
            cashflow_data = result.get("cashflow_statement")
            if cashflow_data and len(cashflow_data) > 0:
                report += "\n💵 现金流量表:\n"
                latest_cashflow = cashflow_data[0]
                report += f"   报告期: {latest_cashflow.get('end_date', '未知')}\n"
                report += f"   经营活动现金流: {latest_cashflow.get('n_cashflow_act', 0):,.2f}万元\n"
                report += f"   投资活动现金流: {latest_cashflow.get('n_cashflow_inv_act', 0):,.2f}万元\n"
                report += f"   筹资活动现金流: {latest_cashflow.get('n_cash_flows_fnc_act', 0):,.2f}万元\n"

            logger.info(f"✅ [Tushare] 成功获取财务报表: {symbol}")
            return report

        except Exception as e:
            logger.error(f"❌ [Tushare] 获取财务报表失败: {symbol} - {e}")
            import traceback

            logger.error(f"❌ 堆栈跟踪:\n{traceback.format_exc()}")
            return f"❌ 获取 {symbol} 财务报表失败: {e}"

    def _get_akshare_fundamentals(self, symbol: str) -> str:
        """从 AKShare 生成基本面分析"""
        logger.debug(f"📊 [AKShare] 调用参数: symbol={symbol}")

        try:
            # AKShare 没有直接的基本面数据接口，使用生成分析
            logger.info(f"📊 [数据来源: AKShare-生成分析] 生成基本面分析: {symbol}")
            return self._generate_fundamentals_analysis(symbol)

        except Exception as e:
            logger.error(f"❌ [数据来源: AKShare异常] 生成基本面分析失败: {e}")
            return f"❌ 生成{symbol}基本面分析失败: {e}"

    def _get_valuation_indicators(self, symbol: str) -> Dict:
        """从stock_basic_info集合获取估值指标"""
        try:
            from tradingagents.config.database_manager import get_database_manager

            db_manager = get_database_manager()
            if not db_manager.is_mongodb_available():
                return {}

            client = db_manager.get_mongodb_client()
            db = client[db_manager.config.mongodb_config.database_name]

            # 从stock_basic_info集合获取估值指标
            collection = db["stock_basic_info"]
            result = collection.find_one({"ts_code": symbol})

            if result:
                return {
                    "pe": result.get("pe"),
                    "pb": result.get("pb"),
                    "pe_ttm": result.get("pe_ttm"),
                    "total_mv": result.get("total_mv"),
                    "circ_mv": result.get("circ_mv"),
                }
            return {}

        except Exception as e:
            logger.error(f"获取{symbol}估值指标失败: {e}")
            return {}

    def _format_financial_data(self, symbol: str, financial_data: List[Dict]) -> str:
        """格式化财务数据为报告"""
        try:
            if not financial_data or len(financial_data) == 0:
                return f"❌ 未找到{symbol}的财务数据"

            # 获取最新的财务数据
            latest = financial_data[0]

            # 构建报告
            report = f"📊 {symbol} 基本面数据（来自MongoDB）\n\n"

            # 基本信息
            report += f"📅 报告期: {latest.get('report_period', latest.get('end_date', '未知'))}\n"
            report += f"📈 数据来源: MongoDB财务数据库\n\n"

            # 财务指标
            report += "💰 财务指标:\n"
            revenue = latest.get("revenue") or latest.get("total_revenue")
            if revenue is not None:
                report += f"   营业总收入: {revenue:,.2f}\n"

            net_profit = latest.get("net_profit") or latest.get("net_income")
            if net_profit is not None:
                report += f"   净利润: {net_profit:,.2f}\n"

            total_assets = latest.get("total_assets")
            if total_assets is not None:
                report += f"   总资产: {total_assets:,.2f}\n"

            total_liab = latest.get("total_liab")
            if total_liab is not None:
                report += f"   总负债: {total_liab:,.2f}\n"

            total_equity = latest.get("total_equity")
            if total_equity is not None:
                report += f"   股东权益: {total_equity:,.2f}\n"

            # 估值指标 - 从stock_basic_info集合获取
            report += "\n📊 估值指标:\n"
            valuation_data = self._get_valuation_indicators(symbol)
            if valuation_data:
                pe = valuation_data.get("pe")
                if pe is not None:
                    report += f"   市盈率(PE): {pe:.2f}\n"

                pb = valuation_data.get("pb")
                if pb is not None:
                    report += f"   市净率(PB): {pb:.2f}\n"

                pe_ttm = valuation_data.get("pe_ttm")
                if pe_ttm is not None:
                    report += f"   市盈率TTM(PE_TTM): {pe_ttm:.2f}\n"

                total_mv = valuation_data.get("total_mv")
                if total_mv is not None:
                    report += f"   总市值: {total_mv:.2f}亿元\n"

                circ_mv = valuation_data.get("circ_mv")
                if circ_mv is not None:
                    report += f"   流通市值: {circ_mv:.2f}亿元\n"
            else:
                # 如果无法从stock_basic_info获取，尝试从财务数据计算
                pe = latest.get("pe")
                if pe is not None:
                    report += f"   市盈率(PE): {pe:.2f}\n"

                pb = latest.get("pb")
                if pb is not None:
                    report += f"   市净率(PB): {pb:.2f}\n"

                ps = latest.get("ps")
                if ps is not None:
                    report += f"   市销率(PS): {ps:.2f}\n"

            # 盈利能力
            report += "\n💹 盈利能力:\n"
            roe = latest.get("roe")
            if roe is not None:
                report += f"   净资产收益率(ROE): {roe:.2f}%\n"

            roa = latest.get("roa")
            if roa is not None:
                report += f"   总资产收益率(ROA): {roa:.2f}%\n"

            gross_margin = latest.get("gross_margin")
            if gross_margin is not None:
                report += f"   毛利率: {gross_margin:.2f}%\n"

            netprofit_margin = latest.get("netprofit_margin") or latest.get(
                "net_margin"
            )
            if netprofit_margin is not None:
                report += f"   净利率: {netprofit_margin:.2f}%\n"

            # 现金流
            n_cashflow_act = latest.get("n_cashflow_act")
            if n_cashflow_act is not None:
                report += "\n💰 现金流:\n"
                report += f"   经营活动现金流: {n_cashflow_act:,.2f}\n"

                n_cashflow_inv_act = latest.get("n_cashflow_inv_act")
                if n_cashflow_inv_act is not None:
                    report += f"   投资活动现金流: {n_cashflow_inv_act:,.2f}\n"

                c_cash_equ_end_period = latest.get("c_cash_equ_end_period")
                if c_cash_equ_end_period is not None:
                    report += f"   期末现金及等价物: {c_cash_equ_end_period:,.2f}\n"

            report += f"\n📝 共有 {len(financial_data)} 期财务数据\n"

            return report

        except Exception as e:
            logger.error(f"❌ 格式化财务数据失败: {e}")
            return f"❌ 格式化{symbol}财务数据失败: {e}"

    def _generate_fundamentals_analysis(self, symbol: str) -> str:
        """生成基本的基本面分析"""
        try:
            # 获取股票基本信息
            stock_info = self.get_stock_info(symbol)

            report = f"📊 {symbol} 基本面分析（生成）\n\n"
            report += f"📈 股票名称: {stock_info.get('name', '未知')}\n"
            report += f"🏢 所属行业: {stock_info.get('industry', '未知')}\n"
            report += f"📍 所属地区: {stock_info.get('area', '未知')}\n"
            report += f"📅 上市日期: {stock_info.get('list_date', '未知')}\n"
            report += f"🏛️ 交易所: {stock_info.get('exchange', '未知')}\n\n"

            report += "⚠️ 注意: 详细财务数据需要从数据源获取\n"
            report += "💡 建议: 启用MongoDB缓存以获取完整的财务数据\n"

            return report

        except Exception as e:
            logger.error(f"❌ 生成基本面分析失败: {e}")
            return f"❌ 生成{symbol}基本面分析失败: {e}"

    def _try_fallback_fundamentals(self, symbol: str) -> str:
        """基本面数据降级处理"""
        logger.error(f"🔄 {self.current_source.value}失败，尝试备用数据源获取基本面...")

        # 🔥 从数据库获取数据源优先级顺序（根据股票代码识别市场）
        fallback_order = self._get_data_source_priority_order(symbol)

        for source in fallback_order:
            if source != self.current_source and source in self.available_sources:
                try:
                    logger.info(f"🔄 尝试备用数据源获取基本面: {source.value}")

                    # 直接调用具体的数据源方法，避免递归
                    if source == ChinaDataSource.TUSHARE:
                        result = self._get_tushare_fundamentals(symbol)
                    elif source == ChinaDataSource.AKSHARE:
                        result = self._get_akshare_fundamentals(symbol)
                    else:
                        continue

                    if result and "❌" not in result:
                        logger.info(
                            f"✅ [数据来源: 备用数据源] 降级成功获取基本面: {source.value}"
                        )
                        return result
                    else:
                        logger.warning(f"⚠️ 备用数据源{source.value}返回错误结果")

                except Exception as e:
                    logger.error(f"❌ 备用数据源{source.value}异常: {e}")
                    continue

        # 所有数据源都失败，生成基本分析
        logger.warning(f"⚠️ [数据来源: 生成分析] 所有数据源失败，生成基本分析: {symbol}")
        return self._generate_fundamentals_analysis(symbol)

    def _get_mongodb_news(
        self, symbol: str, hours_back: int, limit: int
    ) -> List[Dict[str, Any]]:
        """从MongoDB获取新闻数据"""
        try:
            from tradingagents.dataflows.cache.mongodb_cache_adapter import (
                get_mongodb_cache_adapter,
            )

            adapter = get_mongodb_cache_adapter()

            # 从MongoDB获取新闻数据
            news_data = adapter.get_news_data(
                symbol, hours_back=hours_back, limit=limit
            )

            if news_data and len(news_data) > 0:
                logger.info(
                    f"✅ [数据来源: MongoDB-新闻] 成功获取: {symbol or '市场新闻'} ({len(news_data)}条)"
                )
                return news_data
            else:
                logger.warning(
                    f"⚠️ [数据来源: MongoDB] 未找到新闻: {symbol or '市场新闻'}，降级到其他数据源"
                )
                return self._try_fallback_news(symbol, hours_back, limit)

        except Exception as e:
            logger.error(f"❌ [数据来源: MongoDB] 获取新闻失败: {e}")
            return self._try_fallback_news(symbol, hours_back, limit)

    def _get_tushare_news(
        self, symbol: str, hours_back: int, limit: int
    ) -> List[Dict[str, Any]]:
        """从Tushare获取新闻数据"""
        try:
            # Tushare新闻功能暂时不可用，返回空列表
            logger.warning(f"⚠️ [数据来源: Tushare] Tushare新闻功能暂时不可用")
            return []

        except Exception as e:
            logger.error(f"❌ [数据来源: Tushare] 获取新闻失败: {e}")
            return []

    def _get_akshare_news(
        self, symbol: str, hours_back: int, limit: int
    ) -> List[Dict[str, Any]]:
        """从AKShare获取新闻数据"""
        try:
            # AKShare新闻功能暂时不可用，返回空列表
            logger.warning(f"⚠️ [数据来源: AKShare] AKShare新闻功能暂时不可用")
            return []

        except Exception as e:
            logger.error(f"❌ [数据来源: AKShare] 获取新闻失败: {e}")
            return []

    def _try_fallback_news(
        self, symbol: str, hours_back: int, limit: int
    ) -> List[Dict[str, Any]]:
        """新闻数据降级处理"""
        logger.error(f"🔄 {self.current_source.value}失败，尝试备用数据源获取新闻...")

        # 🔥 从数据库获取数据源优先级顺序（根据股票代码识别市场）
        fallback_order = self._get_data_source_priority_order(symbol)

        for source in fallback_order:
            if source != self.current_source and source in self.available_sources:
                try:
                    logger.info(f"🔄 尝试备用数据源获取新闻: {source.value}")

                    # 直接调用具体的数据源方法，避免递归
                    if source == ChinaDataSource.TUSHARE:
                        result = self._get_tushare_news(symbol, hours_back, limit)
                    elif source == ChinaDataSource.AKSHARE:
                        result = self._get_akshare_news(symbol, hours_back, limit)
                    else:
                        continue

                    if result and len(result) > 0:
                        logger.info(
                            f"✅ [数据来源: 备用数据源] 降级成功获取新闻: {source.value}"
                        )
                        return result
                    else:
                        logger.warning(f"⚠️ 备用数据源{source.value}未返回新闻")

                except Exception as e:
                    logger.error(f"❌ 备用数据源{source.value}异常: {e}")
                    continue

        # 所有数据源都失败
        logger.warning(
            f"⚠️ [数据来源: 所有数据源失败] 无法获取新闻: {symbol or '市场新闻'}"
        )
        return []

    # ========== 数据质量评分和验证功能 ==========

    def get_data_quality_score(self, symbol: str, data: Dict[str, Any]) -> float:
        """
        获取数据质量评分 (0-100)

        评分维度:
        - 数据完整性 (30分): 必需字段是否齐全
        - 数据一致性 (30分): 指标间逻辑关系是否正确
        - 数据时效性 (20分): 数据是否是最新的
        - 数据源可靠性 (20分): 数据源的可信度

        Args:
            symbol: 股票代码
            data: 待评分的数据字典

        Returns:
            float: 质量评分 (0-100)
        """
        score = 0.0
        max_score = 100.0

        # 1. 数据完整性检查 (30分)
        completeness_score = self._check_data_completeness(data)
        score += completeness_score * 0.3

        # 2. 数据一致性检查 (30分)
        consistency_score = self._check_data_consistency(symbol, data)
        score += consistency_score * 0.3

        # 3. 数据时效性检查 (20分)
        timeliness_score = self._check_data_timeliness(data)
        score += timeliness_score * 0.2

        # 4. 数据源可靠性 (20分)
        reliability_score = self._check_data_source_reliability()
        score += reliability_score * 0.2

        logger.debug(
            f"📊 [数据质量评分] {symbol}: {score:.1f}/100 "
            f"(完整:{completeness_score:.1f} 一致:{consistency_score:.1f} "
            f"时效:{timeliness_score:.1f} 可靠:{reliability_score:.1f})"
        )

        return min(score, max_score)

    def _check_data_completeness(self, data: Dict[str, Any]) -> float:
        """检查数据完整性"""
        required_fields = {
            # 基础价格数据
            "current_price",
            "open",
            "high",
            "low",
            "volume",
            # 基本面数据
            "market_cap",
            "PE",
            "PB",
        }

        optional_fields = {
            "MA5",
            "MA10",
            "MA20",
            "MA60",
            "RSI",
            "MACD",
            "turnover_rate",
            "ROE",
            "ROA",
        }

        score = 0.0
        total_weight = 1.0

        # 必需字段 (权重0.7)
        present_required = sum(
            1 for f in required_fields if f in data and data[f] is not None
        )
        if required_fields:
            required_score = (present_required / len(required_fields)) * 70
            score += required_score * 0.7

        # 可选字段 (权重0.3)
        present_optional = sum(
            1 for f in optional_fields if f in data and data[f] is not None
        )
        if optional_fields:
            optional_score = (present_optional / len(optional_fields)) * 30
            score += optional_score * 0.3

        return score

    def _check_data_consistency(self, symbol: str, data: Dict[str, Any]) -> float:
        """检查数据一致性"""
        score = 100.0
        issues = []

        # 检查1: high >= low
        if "high" in data and "low" in data:
            if data["high"] < data["low"]:
                issues.append("最高价 < 最低价")
                score -= 20

        # 检查2: current_price 在 high 和 low 之间
        if all(k in data for k in ["current_price", "high", "low"]):
            price = data["current_price"]
            if not (data["low"] <= price <= data["high"]):
                issues.append(f"当前价{price}不在最高最低价范围内")
                score -= 15

        # 检查3: 市值计算一致性
        if all(k in data for k in ["market_cap", "share_count", "current_price"]):
            try:
                market_cap = data["market_cap"]
                share_count = data["share_count"]
                price = data["current_price"]

                calculated_cap = (share_count * price) / 10000  # 转换为亿元
                if market_cap > 0:
                    diff_pct = abs((calculated_cap - market_cap) / market_cap) * 100
                    if diff_pct > 15:  # 超过15%误差
                        issues.append(f"市值计算不一致 (差异{diff_pct:.1f}%)")
                        score -= 10
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        # 检查4: PS比率一致性
        if all(k in data for k in ["market_cap", "revenue", "PS"]):
            try:
                calculated_ps = data["market_cap"] / data["revenue"]
                if data["revenue"] > 0:
                    diff_pct = abs((calculated_ps - data["PS"]) / data["PS"]) * 100
                    if diff_pct > 10:  # 超过10%误差
                        issues.append(f"PS比率计算不一致 (差异{diff_pct:.1f}%)")
                        score -= 15
            except (ValueError, TypeError, ZeroDivisionError):
                pass

        # 检查5: MA序列关系
        if all(k in data for k in ["MA5", "MA10", "MA20"]):
            ma5, ma10, ma20 = data["MA5"], data["MA10"], data["MA20"]
            # 上升趋势: MA5 > MA10 > MA20
            # 下降趋势: MA5 < MA10 < MA20
            # 如果MA5在MA10和MA20之间,可能有问题
            if not (ma10 < ma5 < ma20 or ma20 < ma5 < ma10):
                issues.append(f"MA序列关系异常: MA5={ma5}, MA10={ma10}, MA20={ma20}")
                score -= 5

        if issues:
            logger.debug(f"📊 [数据一致性检查] {symbol}: {', '.join(issues)}")

        return max(score, 0.0)

    def _check_data_timeliness(self, data: Dict[str, Any]) -> float:
        """检查数据时效性"""
        score = 100.0

        # 检查数据中的日期
        data_date = data.get("date") or data.get("trade_date") or data.get("timestamp")
        if data_date:
            try:
                from datetime import datetime

                # 尝试解析日期
                if isinstance(data_date, str):
                    data_date = datetime.strptime(data_date.split()[0], "%Y-%m-%d")
                elif isinstance(data_date, (int, float)):
                    # 假设是Unix时间戳
                    data_date = datetime.fromtimestamp(data_date)

                if data_date:
                    now = datetime.now()
                    days_old = (now - data_date).days

                    # 数据越新,分数越高
                    if days_old <= 1:
                        score = 100
                    elif days_old <= 7:
                        score = 80
                    elif days_old <= 30:
                        score = 60
                    else:
                        score = 40
            except Exception as e:
                logger.debug(f"日期解析失败: {e}")
                score = 50  # 无法判断,给中等分

        return score

    def _check_data_source_reliability(self) -> float:
        """检查数据源可靠性"""
        # 数据源可靠性评分
        reliability_scores = {
            ChinaDataSource.MONGODB: 95,  # 缓存数据,最可靠
            ChinaDataSource.TUSHARE: 90,  # 官方数据,高质量
            ChinaDataSource.BAOSTOCK: 75,  # 免费但稳定
            ChinaDataSource.AKSHARE: 70,  # 多源聚合,质量波动
        }

        score = reliability_scores.get(self.current_source, 60)
        return float(score)

    def get_best_source_for_metric(self, metric: str) -> str:
        """
        获取指定指标的最佳数据源

        重要修正:
        - 实时行情指标优先使用 AkShare (真正实时)
        - 基本面指标优先使用 Tushare (最准确)
        - 技术指标基于历史数据, Tushare 更可靠

        Args:
            metric: 指标名称,如 'PE', 'PB', 'PS', 'MA5', 'RSI', 'volume'

        Returns:
            str: 推荐的数据源名称
        """
        # 判断是否在交易时间 (需要实时数据)
        is_trading_hours = self._is_trading_hours()

        # 实时行情指标集合
        realtime_metrics = {
            "current_price",
            "open",
            "high",
            "low",
            "volume",
            "turnover_rate",
        }

        # 不同数据源的特长
        source_specialties = {
            # 基本面指标 - Tushare最准确
            "PE": ChinaDataSource.TUSHARE,
            "PB": ChinaDataSource.TUSHARE,
            "PS": ChinaDataSource.TUSHARE,
            "ROE": ChinaDataSource.TUSHARE,
            "ROA": ChinaDataSource.TUSHARE,
            "market_cap": ChinaDataSource.TUSHARE,
            "revenue": ChinaDataSource.TUSHARE,
            "total_assets": ChinaDataSource.TUSHARE,
            "net_profit": ChinaDataSource.TUSHARE,
            # 技术指标 - 基于历史数据,Tushare更可靠
            "MA5": ChinaDataSource.TUSHARE,
            "MA10": ChinaDataSource.TUSHARE,
            "MA20": ChinaDataSource.TUSHARE,
            "MA60": ChinaDataSource.TUSHARE,
            "RSI": ChinaDataSource.TUSHARE,
            "RSI6": ChinaDataSource.TUSHARE,
            "RSI12": ChinaDataSource.TUSHARE,
            "MACD": ChinaDataSource.TUSHARE,
            "BOLL": ChinaDataSource.TUSHARE,
            "BOLL_UPPER": ChinaDataSource.TUSHARE,
            "BOLL_LOWER": ChinaDataSource.TUSHARE,
            "BOLL_MIDDLE": ChinaDataSource.TUSHARE,
            # 实时行情 - 根据时间选择数据源
            # 盘中: AkShare (真正实时,秒级更新)
            # 盘后: Tushare (完整数据,经过清洗)
            "current_price": ChinaDataSource.AKSHARE
            if is_trading_hours
            else ChinaDataSource.TUSHARE,
            "open": ChinaDataSource.AKSHARE
            if is_trading_hours
            else ChinaDataSource.TUSHARE,
            "high": ChinaDataSource.AKSHARE
            if is_trading_hours
            else ChinaDataSource.TUSHARE,
            "low": ChinaDataSource.AKSHARE
            if is_trading_hours
            else ChinaDataSource.TUSHARE,
            "volume": ChinaDataSource.AKSHARE
            if is_trading_hours
            else ChinaDataSource.TUSHARE,
            "turnover_rate": ChinaDataSource.AKSHARE
            if is_trading_hours
            else ChinaDataSource.TUSHARE,
            # 默认
            "default": ChinaDataSource.TUSHARE,
        }

        best_source = source_specialties.get(metric, source_specialties["default"])

        # 如果是实时指标且在盘中,记录日志
        if metric in realtime_metrics and is_trading_hours:
            logger.info(
                f"📊 [盘中实时] {metric} 使用 {best_source.value} "
                f"(原因: {'盘中需要实时数据' if best_source == ChinaDataSource.AKSHARE else '盘后使用完整数据'})"
            )

        # 如果最佳数据源不可用,使用当前可用源
        if best_source not in self.available_sources:
            logger.warning(
                f"⚠️ {metric} 的最佳数据源 {best_source.value} 不可用, "
                f"使用当前数据源 {self.current_source.value}"
            )
            return self.current_source.value

        return best_source.value

    def _is_trading_hours(self) -> bool:
        """
        判断当前是否是A股交易时间

        A股交易时间:
        - 上午: 9:30 - 11:30
        - 下午: 13:00 - 15:00
        - 延后30分钟: 用于收盘后的分析 (15:00 - 15:30)

        Returns:
            bool: True表示需要实时数据
        """
        try:
            from datetime import datetime

            now = datetime.now()

            # 周末不交易
            if now.weekday() >= 5:  # 5=周六, 6=周日
                return False

            current_time = now.hour * 100 + now.minute  # 转换为HHMM格式,如930表示9:30

            # 上午时段: 9:30-11:30, 加上30分钟缓冲到12:00
            morning_start = 930
            morning_end = 1200

            # 下午时段: 13:00-15:30 (收盘后30分钟)
            afternoon_start = 1300
            afternoon_end = 1530

            is_morning = morning_start <= current_time <= morning_end
            is_afternoon = afternoon_start <= current_time <= afternoon_end

            return is_morning or is_afternoon

        except Exception as e:
            logger.warning(f"判断交易时间失败: {e}, 默认为非交易时间")
            return False

    def is_realtime_capable(self, source: ChinaDataSource) -> Dict[str, bool]:
        """
        判断数据源是否支持实时行情

        Args:
            source: 数据源枚举

        Returns:
            Dict[str, bool]: 各项实时能力的字典
            {
                'realtime_quote': 是否支持实时报价,
                'tick_data': 是否支持逐笔成交,
                'level2': 是否支持Level-2行情,
                'delay_seconds': 数据延迟秒数
            }
        """
        capabilities = {
            ChinaDataSource.MONGODB: {
                "realtime_quote": False,  # 缓存数据,非实时
                "tick_data": False,
                "level2": False,
                "delay_seconds": 0,
                "description": "缓存数据,来自其他数据源的历史快照",
            },
            ChinaDataSource.TUSHARE: {
                "realtime_quote": True,  # 支持,但有延迟
                "tick_data": True,  # 需要高级积分
                "level2": False,  # 不支持
                "delay_seconds": 900,  # 约15分钟延迟
                "description": "官方数据,但实时行情有15分钟延迟",
            },
            ChinaDataSource.AKSHARE: {
                "realtime_quote": True,  # ✅ 真正实时
                "tick_data": True,  # ✅ 支持
                "level2": True,  # ✅ 部分支持
                "delay_seconds": 1,  # 秒级延迟
                "description": "✅ 最佳实时数据源,来自东方财富/腾讯",
            },
            ChinaDataSource.BAOSTOCK: {
                "realtime_quote": False,  # 不支持实时
                "tick_data": False,
                "level2": False,
                "delay_seconds": 86400,  # T+1,次日更新
                "description": "仅提供历史数据,不支持实时行情",
            },
        }

        return capabilities.get(
            source,
            {
                "realtime_quote": False,
                "tick_data": False,
                "level2": False,
                "delay_seconds": 999999,
                "description": "未知数据源",
            },
        )

    async def get_data_with_validation(
        self, symbol: str, metric: str, period: str = "daily"
    ) -> tuple[Any, Dict]:
        """
        获取数据并自动验证

        Args:
            symbol: 股票代码
            metric: 指标名称 ('current_price', 'PE', 'volume', etc.)
            period: 数据周期

        Returns:
            tuple[Any, Dict]: (数据值, 验证结果字典)
        """
        # 获取最佳数据源
        best_source_name = self.get_best_source_for_metric(metric)
        logger.info(f"📊 [验证] 为 {metric} 选择数据源: {best_source_name}")

        # 获取数据
        data_str = self.get_stock_data(symbol, "2024-01-01", "2024-12-31", period)

        # 解析数据
        data = self._parse_data_string(data_str)

        if not data:
            return None, {"is_valid": False, "error": "无法获取数据"}

        # 提取请求的指标
        metric_value = data.get(metric)

        # 质量评分
        quality_score = self.get_data_quality_score(symbol, data)

        validation_result = {
            "is_valid": quality_score >= 60,
            "quality_score": quality_score,
            "source": best_source_name,
            "metric": metric,
            "value": metric_value,
            "data": data,
            "warnings": [],
            "errors": [],
        }

        # 根据质量评分添加警告
        if quality_score < 70:
            validation_result["warnings"].append(
                f"数据质量较低 ({quality_score:.1f}/100)"
            )
        if quality_score < 60:
            validation_result["errors"].append(
                f"数据质量不合格 ({quality_score:.1f}/100)"
            )

        return metric_value, validation_result

    async def cross_validate_metric(
        self, symbol: str, metric: str, sources: List[str] = None
    ) -> Dict:
        """
        多源交叉验证指标

        Args:
            symbol: 股票代码
            metric: 指标名称
            sources: 要验证的数据源列表,如果为None则使用所有可用源

        Returns:
            Dict: 交叉验证结果
        """
        if sources is None:
            sources = [s.value for s in self.available_sources]

        logger.info(f"📊 [交叉验证] 开始多源验证 {symbol} 的 {metric}")

        results = {}
        values = {}

        # 保存当前数据源
        original_source = self.current_source

        try:
            for source in sources:
                try:
                    # 切换数据源
                    source_enum = ChinaDataSource(source)
                    if source_enum in self.available_sources:
                        self.current_source = source_enum

                        # 获取数据
                        value, validation = await self.get_data_with_validation(
                            symbol, metric
                        )

                        if value is not None:
                            results[source] = {
                                "value": value,
                                "quality_score": validation.get("quality_score", 0),
                                "is_valid": validation.get("is_valid", False),
                            }
                            values[source] = value

                except Exception as e:
                    logger.warning(f"从 {source} 获取 {metric} 失败: {e}")
                    continue

        finally:
            # 恢复原始数据源
            self.current_source = original_source

        # 分析一致性
        cross_validation_result = self._analyze_cross_validation_results(
            symbol, metric, results, values
        )

        return cross_validation_result

    def _analyze_cross_validation_results(
        self, symbol: str, metric: str, results: Dict, values: Dict
    ) -> Dict:
        """分析交叉验证结果"""
        if not values:
            return {
                "symbol": symbol,
                "metric": metric,
                "is_valid": False,
                "error": "无法从任何数据源获取数据",
                "sources_checked": list(results.keys()),
            }

        # 计算统计信息
        value_list = list(values.values())
        num_sources = len(value_list)

        # 基本统计
        min_val = min(value_list)
        max_val = max(value_list)
        avg_val = sum(value_list) / num_sources

        # 计算标准差和变异系数
        variance = sum((x - avg_val) ** 2 for x in value_list) / num_sources
        std_dev = variance**0.5
        cv = (std_dev / avg_val * 100) if avg_val != 0 else 0

        # 判断一致性
        is_consistent = cv < 5  # 变异系数小于5%认为一致

        # 找出最可靠的数据源
        best_source = (
            max(results.items(), key=lambda x: x[1]["quality_score"])[0]
            if results
            else None
        )

        # 中位数作为推荐值
        sorted_values = sorted(value_list)
        if num_sources % 2 == 0:
            median_value = (
                sorted_values[num_sources // 2 - 1] + sorted_values[num_sources // 2]
            ) / 2
        else:
            median_value = sorted_values[num_sources // 2]

        return {
            "symbol": symbol,
            "metric": metric,
            "is_valid": is_consistent,
            "is_consistent": is_consistent,
            "num_sources": num_sources,
            "sources_checked": list(results.keys()),
            "values_by_source": values,
            "quality_scores": {k: v["quality_score"] for k, v in results.items()},
            "statistics": {
                "min": min_val,
                "max": max_val,
                "avg": avg_val,
                "median": median_value,
                "std_dev": std_dev,
                "cv_percent": cv,
            },
            "recommendation": {
                "best_source": best_source,
                "suggested_value": median_value,
                "confidence": max(0, min(1, 1 - cv / 10)),  # CV越小,置信度越高
            },
            "warnings": [] if is_consistent else [f"数据源间变异系数较高: {cv:.2f}%"],
            "errors": [] if num_sources > 0 else ["无法获取任何数据"],
        }

    def _parse_data_string(self, data_str: str) -> Dict[str, Any]:
        """
        解析数据字符串为字典

        这是一个简化实现,实际应该根据数据格式解析
        """
        if not data_str or isinstance(data_str, dict):
            return data_str or {}

        # 尝试解析JSON
        if data_str.startswith("{"):
            import json

            try:
                return json.loads(data_str)
            except json.JSONDecodeError:
                pass

        # 如果是表格格式,这里需要更复杂的解析
        # 暂时返回空字典
        logger.debug("无法解析数据字符串")
        return {}


# 全局数据源管理器实例
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
    """
    统一的中国股票数据获取接口
    自动使用配置的数据源，支持备用数据源

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        analysis_date: 分析日期（YYYY-MM-DD），用于判断实时行情

    Returns:
        str: 格式化的股票数据
    """
    from tradingagents.utils.logging_init import get_logger

    # 添加详细的股票代码追踪日志
    logger.info(
        f"🔍 [股票代码追踪] data_source_manager.get_china_stock_data_unified 接收到的股票代码: '{symbol}' (类型: {type(symbol)})"
    )
    logger.info(f"🔍 [股票代码追踪] 股票代码长度: {len(str(symbol))}")
    logger.info(f"🔍 [股票代码追踪] 股票代码字符: {list(str(symbol))}")

    manager = get_data_source_manager()
    logger.info(
        f"🔍 [股票代码追踪] 调用 manager.get_stock_data，传入参数: symbol='{symbol}', start_date='{start_date}', end_date='{end_date}', analysis_date='{analysis_date}'"
    )
    result = manager.get_stock_data(
        symbol, start_date, end_date, analysis_date=analysis_date
    )
    # 🔥 FIX: 处理返回类型错误（tuple vs str）
    if isinstance(result, tuple):
        logger.warning(f"⚠️ [类型修复] get_stock_data 返回了 tuple，提取第一个元素")
        result = result[0] if len(result) > 0 else None

    # 分析返回结果的详细信息
    if result and isinstance(result, str):
        lines = result.split("\n")
        data_lines = [line for line in lines if "2025-" in line and symbol in line]
        logger.info(
            f"🔍 [股票代码追踪] 返回结果统计: 总行数={len(lines)}, 数据行数={len(data_lines)}, 结果长度={len(result)}字符"
        )
        logger.info(f"🔍 [股票代码追踪] 返回结果前500字符: {result[:500]}")
        if len(data_lines) > 0:
            logger.info(
                f"🔍 [股票代码追踪] 数据行示例: 第1行='{data_lines[0][:100]}', 最后1行='{data_lines[-1][:100]}'"
            )
    else:
        logger.info(f"🔍 [股票代码追踪] 返回结果: None")
    return result


def get_china_stock_info_unified(symbol: str) -> Dict:
    """
    统一的中国股票信息获取接口

    Args:
        symbol: 股票代码

    Returns:
        Dict: 股票基本信息
    """
    manager = get_data_source_manager()
    return manager.get_stock_info(symbol)


# 全局数据源管理器实例
_data_source_manager = None


def get_data_source_manager() -> DataSourceManager:
    """获取全局数据源管理器实例"""
    global _data_source_manager
    if _data_source_manager is None:
        _data_source_manager = DataSourceManager()
    return _data_source_manager


# ==================== 兼容性接口 ====================
# 为了兼容 stock_data_service，提供相同的接口


def get_stock_data_service() -> DataSourceManager:
    """
    获取股票数据服务实例（兼容 stock_data_service 接口）

    ⚠️ 此函数为兼容性接口，实际返回 DataSourceManager 实例
    推荐直接使用 get_data_source_manager()
    """
    return get_data_source_manager()


# ==================== 美股数据源管理器 ====================


class USDataSourceManager:
    """
    美股数据源管理器

    支持的数据源：
    - yfinance: 股票价格和技术指标（免费）
    - alpha_vantage: 基本面和新闻数据（需要API Key）
    - finnhub: 备用数据源（需要API Key）
    - mongodb: 缓存数据源（最高优先级）
    """

    def __init__(self):
        """初始化美股数据源管理器"""
        # 检查是否启用 MongoDB 缓存
        self.use_mongodb_cache = self._check_mongodb_enabled()

        # 检查可用的数据源
        self.available_sources = self._check_available_sources()

        # 设置默认数据源
        self.default_source = self._get_default_source()
        self.current_source = self.default_source

        logger.info(f"📊 美股数据源管理器初始化完成")
        logger.info(
            f"   MongoDB缓存: {'✅ 已启用' if self.use_mongodb_cache else '❌ 未启用'}"
        )
        logger.info(f"   默认数据源: {self.default_source.value}")
        logger.info(f"   可用数据源: {[s.value for s in self.available_sources]}")

    def _check_mongodb_enabled(self) -> bool:
        """检查是否启用MongoDB缓存"""
        from tradingagents.config.runtime_settings import use_app_cache_enabled

        return use_app_cache_enabled()

    def _get_data_source_priority_order(
        self, symbol: Optional[str] = None
    ) -> List[USDataSource]:
        """
        从数据库获取美股数据源优先级顺序（用于降级）

        Args:
            symbol: 股票代码

        Returns:
            按优先级排序的数据源列表（不包含MongoDB）
        """
        try:
            # 从数据库读取数据源配置
            from app.core.database import get_mongo_db_sync

            db = get_mongo_db_sync()

            # 方法1: 从 datasource_groupings 集合读取（推荐）
            groupings_collection = db.datasource_groupings
            groupings = list(
                groupings_collection.find(
                    {"market_category_id": "us_stocks", "enabled": True}
                ).sort("priority", -1)
            )  # 降序排序，优先级高的在前

            if groupings:
                # 转换为 USDataSource 枚举
                # 🔥 数据源名称映射（数据库名称 → USDataSource 枚举）
                source_mapping = {
                    "yfinance": USDataSource.YFINANCE,
                    "yahoo_finance": USDataSource.YFINANCE,  # 别名
                    "alpha_vantage": USDataSource.ALPHA_VANTAGE,
                    "finnhub": USDataSource.FINNHUB,
                }

                result = []
                for grouping in groupings:
                    ds_name = grouping.get("data_source_name", "").lower()
                    if ds_name in source_mapping:
                        source = source_mapping[ds_name]
                        # 排除 MongoDB（MongoDB 是最高优先级，不参与降级）
                        if (
                            source != USDataSource.MONGODB
                            and source in self.available_sources
                        ):
                            result.append(source)

                if result:
                    logger.info(
                        f"✅ [美股数据源优先级] 从数据库读取: {[s.value for s in result]}"
                    )
                    return result

            logger.warning("⚠️ [美股数据源优先级] 数据库中没有配置，使用默认顺序")
        except Exception as e:
            logger.warning(f"⚠️ [美股数据源优先级] 从数据库读取失败: {e}，使用默认顺序")

        # 回退到默认顺序
        # 默认顺序：yfinance > Alpha Vantage > Finnhub
        default_order = [
            USDataSource.YFINANCE,
            USDataSource.ALPHA_VANTAGE,
            USDataSource.FINNHUB,
        ]
        # 只返回可用的数据源
        return [s for s in default_order if s in self.available_sources]

    def _get_default_source(self) -> USDataSource:
        """获取默认数据源"""
        # 如果启用MongoDB缓存，MongoDB作为最高优先级数据源
        if self.use_mongodb_cache:
            return USDataSource.MONGODB

        # 从环境变量获取，默认使用 yfinance
        env_source = os.getenv(
            "DEFAULT_US_DATA_SOURCE", DataSourceCode.YFINANCE
        ).lower()

        # 映射到枚举
        source_mapping: Dict[str, USDataSource] = {
            DataSourceCode.YFINANCE.value: USDataSource.YFINANCE,
            DataSourceCode.ALPHA_VANTAGE.value: USDataSource.ALPHA_VANTAGE,
            DataSourceCode.FINNHUB.value: USDataSource.FINNHUB,
        }

        return source_mapping.get(env_source, USDataSource.YFINANCE)

    def _check_available_sources(self) -> List[USDataSource]:
        """
        检查可用的数据源

        从数据库读取启用状态，并检查依赖是否满足
        """
        available = []

        # MongoDB 缓存
        if self.use_mongodb_cache:
            available.append(USDataSource.MONGODB)
            logger.info("✅ MongoDB缓存数据源可用")

        # 从数据库读取启用的数据源列表和配置
        enabled_sources_in_db = self._get_enabled_sources_from_db()
        datasource_configs = self._get_datasource_configs_from_db()

        # 检查 yfinance
        if "yfinance" in enabled_sources_in_db:
            try:
                import yfinance

                available.append(USDataSource.YFINANCE)
                logger.info("✅ yfinance数据源可用且已启用")
            except ImportError:
                logger.warning("⚠️ yfinance数据源不可用: 未安装 yfinance 库")
        else:
            logger.info("ℹ️ yfinance数据源已在数据库中禁用")

        # 检查 Alpha Vantage
        if "alpha_vantage" in enabled_sources_in_db:
            try:
                # 优先从数据库配置读取 API Key，其次从环境变量读取
                api_key = datasource_configs.get("alpha_vantage", {}).get(
                    "api_key"
                ) or os.getenv("ALPHA_VANTAGE_API_KEY")
                if api_key:
                    available.append(USDataSource.ALPHA_VANTAGE)
                    source = (
                        "数据库配置"
                        if datasource_configs.get("alpha_vantage", {}).get("api_key")
                        else "环境变量"
                    )
                    logger.info(
                        f"✅ Alpha Vantage数据源可用且已启用 (API Key来源: {source})"
                    )
                else:
                    logger.warning(
                        "⚠️ Alpha Vantage数据源不可用: API Key未配置（数据库和环境变量均未找到）"
                    )
            except Exception as e:
                logger.warning(f"⚠️ Alpha Vantage数据源检查失败: {e}")
        else:
            logger.info("ℹ️ Alpha Vantage数据源已在数据库中禁用")

        # 检查 Finnhub
        if "finnhub" in enabled_sources_in_db:
            try:
                # 优先从数据库配置读取 API Key，其次从环境变量读取
                api_key = datasource_configs.get("finnhub", {}).get(
                    "api_key"
                ) or os.getenv("FINNHUB_API_KEY")
                if api_key:
                    available.append(USDataSource.FINNHUB)
                    source = (
                        "数据库配置"
                        if datasource_configs.get("finnhub", {}).get("api_key")
                        else "环境变量"
                    )
                    logger.info(f"✅ Finnhub数据源可用且已启用 (API Key来源: {source})")
                else:
                    logger.warning(
                        "⚠️ Finnhub数据源不可用: API Key未配置（数据库和环境变量均未找到）"
                    )
            except Exception as e:
                logger.warning(f"⚠️ Finnhub数据源检查失败: {e}")
        else:
            logger.info("ℹ️ Finnhub数据源已在数据库中禁用")

        return available

    def _get_enabled_sources_from_db(self) -> List[str]:
        """从数据库读取启用的数据源列表"""
        try:
            from app.core.database import get_mongo_db_sync

            db = get_mongo_db_sync()

            # 从 datasource_groupings 集合读取
            groupings = list(
                db.datasource_groupings.find(
                    {"market_category_id": "us_stocks", "enabled": True}
                )
            )

            # 🔥 数据源名称映射（数据库名称 → 代码中使用的名称）
            name_mapping = {
                "alpha vantage": "alpha_vantage",
                "yahoo finance": "yfinance",
                "finnhub": "finnhub",
            }

            result = []
            for g in groupings:
                db_name = g.get("data_source_name", "").lower()
                # 使用映射表转换名称
                code_name = name_mapping.get(db_name, db_name)
                result.append(code_name)
                logger.debug(f"🔄 数据源名称映射: '{db_name}' → '{code_name}'")

            return result
        except Exception as e:
            logger.warning(f"⚠️ 从数据库读取启用的数据源失败: {e}")
            # 默认全部启用
            return ["yfinance", "alpha_vantage", "finnhub"]

    def _get_datasource_configs_from_db(self) -> dict:
        """从数据库读取数据源配置（包括 API Key）"""
        try:
            from app.core.database import get_mongo_db_sync

            db = get_mongo_db_sync()

            # 从 system_configs 集合读取激活的配置
            config = db.system_configs.find_one({"is_active": True})
            if not config:
                return {}

            # 提取数据源配置
            datasource_configs = config.get("data_source_configs", [])

            # 构建配置字典 {数据源名称: {api_key, api_secret, ...}}
            result = {}
            for ds_config in datasource_configs:
                name = ds_config.get("name", "").lower()
                result[name] = {
                    "api_key": ds_config.get("api_key", ""),
                    "api_secret": ds_config.get("api_secret", ""),
                    "config_params": ds_config.get("config_params", {}),
                }

            return result
        except Exception as e:
            logger.warning(f"⚠️ 从数据库读取数据源配置失败: {e}")
            return {}

    def get_current_source(self) -> USDataSource:
        """获取当前数据源"""
        return self.current_source

    def set_current_source(self, source: USDataSource) -> bool:
        """设置当前数据源"""
        if source in self.available_sources:
            self.current_source = source
            logger.info(f"✅ 美股数据源已切换到: {source.value}")
            return True
        else:
            logger.error(f"❌ 美股数据源不可用: {source.value}")
            return False


# 全局美股数据源管理器实例
_us_data_source_manager = None


def get_us_data_source_manager() -> USDataSourceManager:
    """获取全局美股数据源管理器实例"""
    global _us_data_source_manager
    if _us_data_source_manager is None:
        _us_data_source_manager = USDataSourceManager()
    return _us_data_source_manager
