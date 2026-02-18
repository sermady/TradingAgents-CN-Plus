# -*- coding: utf-8 -*-
"""
配置管理器
负责数据源配置的管理和读取
"""

import os
from typing import TYPE_CHECKING, Any, Dict, Optional, Set

from tradingagents.utils.logging_manager import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("agents")


class ConfigManager:
    """配置管理器 - 处理数据源配置相关操作"""

    def __init__(self):
        """初始化配置管理器"""
        self._config_cache: Dict[str, Any] = {}
        self._enabled_sources_cache: Optional[Set[str]] = None

    def check_mongodb_enabled(self) -> bool:
        """检查是否启用MongoDB缓存"""
        from tradingagents.config.runtime_settings import use_app_cache_enabled

        return use_app_cache_enabled()

    def get_default_source(self, use_mongodb_cache: bool = False):
        """
        获取默认数据源

        Args:
            use_mongodb_cache: 是否启用MongoDB缓存

        Returns:
            ChinaDataSource: 默认数据源
        """
        # 延迟导入，避免循环导入
        from tradingagents.dataflows.data_sources.enums import ChinaDataSource
        from tradingagents.constants import DataSourceCode

        # 如果启用MongoDB缓存，MongoDB作为最高优先级数据源
        if use_mongodb_cache:
            return ChinaDataSource.MONGODB

        # 从环境变量获取，默认使用AKShare作为第一优先级数据源
        env_source = os.getenv(
            "DEFAULT_CHINA_DATA_SOURCE", DataSourceCode.AKSHARE
        ).lower()

        # 映射到枚举
        source_mapping = {
            DataSourceCode.TUSHARE.value: ChinaDataSource.TUSHARE,
            DataSourceCode.AKSHARE.value: ChinaDataSource.AKSHARE,
            DataSourceCode.BAOSTOCK.value: ChinaDataSource.BAOSTOCK,
        }

        return source_mapping.get(env_source, ChinaDataSource.AKSHARE)

    def get_enabled_sources_from_db(self) -> Set[str]:
        """
        从数据库读取启用的数据源列表

        Returns:
            Set[str]: 启用的数据源名称集合
        """
        if self._enabled_sources_cache is not None:
            return self._enabled_sources_cache

        try:
            from app.core.database import get_mongo_db_sync

            db = get_mongo_db_sync()

            # 从 system_configs 集合读取
            config_data = db.system_configs.find_one(
                {"is_active": True}, sort=[("version", -1)]
            )

            if config_data and config_data.get("data_source_configs"):
                data_source_configs = config_data.get("data_source_configs", [])

                # 提取已启用的数据源类型
                enabled_sources = set()
                for ds in data_source_configs:
                    if ds.get("enabled", True):
                        ds_type = ds.get("type", "").lower()
                        enabled_sources.add(ds_type)

                logger.info(
                    f"✅ [数据源配置] 从数据库读取到已启用的数据源: {enabled_sources}"
                )
                self._enabled_sources_cache = enabled_sources
                return enabled_sources
            else:
                logger.warning(
                    "⚠️ [数据源配置] 数据库中没有数据源配置，将检查所有已安装的数据源"
                )
        except Exception as e:
            logger.warning(
                f"⚠️ [数据源配置] 从数据库读取失败: {e}，将检查所有已安装的数据源"
            )

        # 默认所有数据源都启用
        default_sources = {"mongodb", "tushare", "akshare", "baostock"}
        self._enabled_sources_cache = default_sources
        return default_sources

    def get_datasource_configs_from_db(self) -> dict:
        """
        从数据库读取数据源配置（包括 API Key）

        Returns:
            dict: 数据源配置字典
        """
        try:
            from app.core.database import get_mongo_db_sync

            db = get_mongo_db_sync()

            # 从 system_configs 集合读取激活的配置
            config = db.system_configs.find_one({"is_active": True})
            if not config:
                return {}

            # 提取数据源配置
            datasource_configs = config.get("data_source_configs", [])

            # 构建配置字典
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

    def identify_market_category(self, symbol: Optional[str]) -> Optional[str]:
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

    def clear_cache(self):
        """清除配置缓存"""
        self._config_cache.clear()
        self._enabled_sources_cache = None
