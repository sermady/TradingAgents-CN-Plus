# -*- coding: utf-8 -*-
"""外股数据服务基类

提供统一的港股和美股数据服务，消除95-98%的重复代码。
支持按需获取+缓存模式，避免重复请求触发速率限制。

使用示例:
    class HKDataService(ForeignDataBaseService):
        def __init__(self):
            super().__init__(market_type='hk', region='HK')
            self.providers = {
                "yahoo": HKStockProvider(),
                "akshare": ImprovedHKStockProvider()
            }

        def _normalize_stock_info(self, stock_info: dict, source: str) -> dict:
            # 港股特定的标准化逻辑
            normalized = super()._normalize_stock_info(stock_info, source)
            normalized.update({
                "currency": stock_info.get("currency", "HKD"),
                "exchange": stock_info.get("exchange", "HKEX"),
                "market": stock_info.get("market", "香港交易所"),
                "area": stock_info.get("area", "香港")
            })
            return normalized
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import logging

from app.core.database import get_mongo_db
from app.core.config import settings

logger = logging.getLogger(__name__)


class ForeignDataBaseService(ABC):
    """外股数据服务基类

    提供统一的港股和美股数据获取、缓存和标准化功能。

    Attributes:
        market_type: 市场类型（'hk' 或 'us'）
        region: 区域标识（'HK' 或 'US'）
        collection_name: MongoDB集合名称
        cache_hours: 缓存时长（小时）
        default_source: 默认数据源
    """

    def __init__(self, market_type: str, region: str, init_db: bool = True):
        """初始化外股数据服务

        Args:
            market_type: 市场类型（'hk' 或 'us'）
            region: 区域标识（'HK' 或 'US'）
            init_db: 是否初始化数据库连接（默认True）
        """
        # 延迟数据库初始化，避免在测试时出错
        self.db = None
        self.settings = settings
        self._init_db = init_db

        # 市场标识
        self.market_type = market_type
        self.region = region

        # 数据提供器映射（由子类填充）
        self.providers = {}

        # 缓存配置
        cache_hours_attr = f'{market_type.upper()}_DATA_CACHE_HOURS'
        default_source_attr = f'{market_type.upper()}_DEFAULT_DATA_SOURCE'

        self.cache_hours = getattr(settings, cache_hours_attr, 24)
        self.default_source = getattr(settings, default_source_attr, 'yahoo')

        # MongoDB集合名称
        self.collection_name = f'stock_basic_info_{market_type}'

        self.logger = logging.getLogger(self.__class__.__name__)

    def _get_db(self):
        """获取数据库连接（延迟初始化）"""
        if self.db is None and self._init_db:
            self.db = get_mongo_db()
        return self.db

    async def initialize(self):
        """初始化数据服务"""
        self.logger.info(f"✅ {self.region}股数据服务初始化完成")

    async def get_stock_info(
        self,
        stock_code: str,
        source: Optional[str] = None,
        force_refresh: bool = False
    ) -> Optional[Dict[str, Any]]:
        """获取股票基础信息（按需获取+缓存）

        Args:
            stock_code: 股票代码
            source: 数据源，None则使用默认数据源
            force_refresh: 是否强制刷新（忽略缓存）

        Returns:
            股票信息字典，失败返回None
        """
        try:
            # 使用默认数据源
            if source is None:
                source = self.default_source

            # 标准化股票代码
            normalized_code = self._normalize_code(stock_code)

            # 检查缓存
            if not force_refresh:
                cached_info = await self._get_cached_info(normalized_code, source)
                if cached_info:
                    self.logger.debug(f"✅ 使用缓存数据: {normalized_code} ({source})")
                    return cached_info

            # 从数据源获取
            provider = self.providers.get(source)
            if not provider:
                self.logger.error(f"❌ 不支持的数据源: {source}")
                return None

            self.logger.info(f"🔄 从 {source} 获取{self.region}股信息: {stock_code}")
            stock_info = provider.get_stock_info(stock_code)

            if not stock_info or not stock_info.get('name'):
                self.logger.warning(f"⚠️ 获取失败或数据无效: {stock_code} ({source})")
                return None

            # 标准化并保存到缓存
            normalized_info = self._normalize_stock_info(stock_info, source)
            normalized_info["code"] = normalized_code
            normalized_info["source"] = source
            normalized_info["updated_at"] = datetime.now()

            await self._save_to_cache(normalized_info)

            self.logger.info(f"✅ 获取成功: {normalized_code} - {stock_info.get('name')} ({source})")
            return normalized_info

        except Exception as e:
            self.logger.error(f"❌ 获取{self.region}股信息失败: {stock_code} ({source}): {e}")
            return None

    async def _get_cached_info(self, code: str, source: str) -> Optional[Dict[str, Any]]:
        """从缓存获取股票信息

        Args:
            code: 标准化后的股票代码
            source: 数据源

        Returns:
            缓存的股票信息，不存在或过期返回None
        """
        try:
            cache_expire_time = datetime.now() - timedelta(hours=self.cache_hours)

            db = self._get_db()
            collection = getattr(db, self.collection_name)
            cached = await collection.find_one({
                "code": code,
                "source": source,
                "updated_at": {"$gte": cache_expire_time}
            })

            return cached

        except Exception as e:
            self.logger.error(f"❌ 读取缓存失败: {code} ({source}): {e}")
            return None

    async def _save_to_cache(self, stock_info: Dict[str, Any]) -> bool:
        """保存股票信息到缓存

        Args:
            stock_info: 标准化后的股票信息

        Returns:
            是否保存成功
        """
        try:
            db = self._get_db()
            collection = getattr(db, self.collection_name)

            await collection.update_one(
                {"code": stock_info["code"], "source": stock_info["source"]},
                {"$set": stock_info},
                upsert=True
            )
            return True

        except Exception as e:
            self.logger.error(f"❌ 保存缓存失败: {stock_info.get('code')} ({stock_info.get('source')}): {e}")
            return False

    def _normalize_code(self, stock_code: str) -> str:
        """标准化股票代码

        Args:
            stock_code: 原始股票代码

        Returns:
            标准化后的股票代码
        """
        # 默认实现：去除空格并转大写
        # 子类可以重写此方法提供特定的标准化逻辑
        return stock_code.strip().upper()

    def _normalize_stock_info(self, stock_info: Dict, source: str) -> Dict:
        """标准化股票信息格式

        Args:
            stock_info: 原始股票信息
            source: 数据源

        Returns:
            标准化后的股票信息
        """
        normalized = {
            "name": stock_info.get("name", ""),
            "currency": stock_info.get("currency", "USD"),
            "exchange": stock_info.get("exchange", "NASDAQ"),
            "market": stock_info.get("market", "美国市场"),
            "area": stock_info.get("area", "美国"),
        }

        # 可选字段
        optional_fields = [
            "industry", "sector", "list_date", "total_mv", "circ_mv",
            "pe", "pb", "ps", "pcf", "market_cap", "shares_outstanding",
            "float_shares", "employees", "website", "description"
        ]

        for field in optional_fields:
            if field in stock_info and stock_info[field]:
                normalized[field] = stock_info[field]

        return normalized


# 导出
__all__ = ['ForeignDataBaseService']
