# -*- coding: utf-8 -*-
"""
港股和美股服务基础类和工具函数
"""
import asyncio
from typing import Optional, Dict, List
from datetime import datetime
import logging
import json
from collections import defaultdict
from abc import abstractmethod

from tradingagents.dataflows.cache import get_cache

logger = logging.getLogger(__name__)


class ForeignStockBaseService:
    """港股和美股数据服务基础类"""

    # 缓存时间配置（秒）
    CACHE_TTL = {
        "HK": {
            "quote": 600,        # 10分钟（实时行情）
            "info": 86400,       # 1天（基础信息）
            "kline": 7200,       # 2小时（K线数据）
        },
        "US": {
            "quote": 600,        # 10分钟
            "info": 86400,       # 1天
            "kline": 7200,       # 2小时
        }
    }

    def __init__(self, db=None):
        """初始化服务

        Args:
            db: MongoDB 数据库连接（用于查询数据源优先级）
        """
        # 使用统一缓存系统（自动选择 MongoDB/Redis/File）
        self.cache = get_cache()

        # 保存数据库连接（用于查询数据源优先级）
        self.db = db

        # 🔥 请求锁字典（用于防止并发请求同一股票）
        self._request_locks = defaultdict(asyncio.Lock)

    def _parse_cached_data(self, cached_data: str, market: str, code: str) -> Optional[Dict]:
        """解析缓存的数据

        Args:
            cached_data: 缓存的数据（JSON字符串或字典）
            market: 市场类型（HK/US）
            code: 股票代码

        Returns:
            解析后的数据字典，如果解析失败返回 None
        """
        try:
            # 尝试解析JSON
            if isinstance(cached_data, str):
                data = json.loads(cached_data)
            else:
                data = cached_data

            # 确保包含必要字段
            if isinstance(data, dict):
                data['market'] = market
                data['code'] = code
                return data
            else:
                raise ValueError("缓存数据格式错误")
        except Exception as e:
            logger.warning(f"⚠️ 解析缓存数据失败: {e}")
            # 返回空数据，触发重新获取
            return None

    def _parse_cached_kline(self, cached_data: str) -> List[Dict]:
        """解析缓存的K线数据

        Args:
            cached_data: 缓存的K线数据（JSON字符串或列表）

        Returns:
            K线数据列表，如果解析失败返回空列表
        """
        try:
            # 尝试解析JSON
            if isinstance(cached_data, str):
                data = json.loads(cached_data)
            else:
                data = cached_data

            # 确保是列表
            if isinstance(data, list):
                return data
            else:
                raise ValueError("缓存K线数据格式错误")
        except Exception as e:
            logger.warning(f"⚠️ 解析缓存K线数据失败: {e}")
            # 返回空列表，触发重新获取
            return []

    def _safe_float(self, value, default=None):
        """安全地转换为浮点数，处理 'None' 字符串和空值

        Args:
            value: 待转换的值
            default: 默认值

        Returns:
            转换后的浮点数或默认值
        """
        if value is None or value == '' or value == 'None' or value == 'N/A':
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    async def _get_source_priority(self, market: str) -> List[str]:
        """从数据库获取数据源优先级（统一方法）
        🔥 复用 UnifiedStockService 的实现

        Args:
            market: 市场类型（HK/US/CN）

        Returns:
            数据源名称列表（按优先级排序）
        """
        market_category_map = {
            "CN": "a_shares",
            "HK": "hk_stocks",
            "US": "us_stocks"
        }

        market_category_id = market_category_map.get(market)

        try:
            # 从 datasource_groupings 集合查询
            groupings = await self.db.datasource_groupings.find({
                "market_category_id": market_category_id,
                "enabled": True
            }).sort("priority", -1).to_list(length=None)

            if groupings:
                priority_list = [g["data_source_name"] for g in groupings]
                logger.info(f"📊 [{market}数据源优先级] 从数据库读取: {priority_list}")
                return priority_list
        except Exception as e:
            logger.warning(f"⚠️ [{market}数据源优先级] 从数据库读取失败: {e}，使用默认顺序")

        # 默认优先级
        default_priority = {
            "CN": ["tushare", "akshare", "baostock"],
            "HK": ["yfinance", "akshare"],
            "US": ["yfinance", "alpha_vantage", "finnhub"]
        }
        priority_list = default_priority.get(market, [])
        logger.info(f"📊 [{market}数据源优先级] 使用默认: {priority_list}")
        return priority_list

    def _get_valid_sources(
        self,
        source_priority: List[str],
        source_handlers: Dict[str, tuple],
        market: str
    ) -> List[str]:
        """过滤有效数据源并去重

        Args:
            source_priority: 数据库中的优先级列表
            source_handlers: 数据源处理器映射
            market: 市场类型（用于日志）

        Returns:
            有效的数据源名称列表
        """
        # 过滤有效数据源并去重
        valid_priority = []
        seen = set()
        for source_name in source_priority:
            source_key = source_name.lower()
            # 只保留有效的数据源
            if source_key in source_handlers and source_key not in seen:
                seen.add(source_key)
                valid_priority.append(source_name)

        if not valid_priority:
            logger.warning(f"⚠️ 数据库中没有配置有效的{market}数据源，使用默认顺序")
            # 返回所有可用数据源
            valid_priority = list(source_handlers.keys())

        logger.info(f"📊 [{market}有效数据源] {valid_priority}")
        return valid_priority

    async def get_basic_info_template(self, code: str, force_refresh: bool = False) -> Dict:
        """通用的获取基础信息模板方法（消除HK/US服务重复）

        🔥 这个方法封装了完全相同的获取基础信息流程：
        1. 缓存检查（Redis → MongoDB → File）
        2. 按优先级尝试各个数据源
        3. 格式化并保存到缓存

        子类只需要定义：
        - market: 市场标识 ('HK' or 'US')
        - basic_info_cache_key: 基础信息缓存key后缀
        - basic_info_source_handlers: 基础信息数据源处理器映射
        - format_basic_info(): 格式化方法
        """
        # 1. 检查缓存（除非强制刷新）
        if not force_refresh:
            cache_key = self.cache.find_cached_stock_data(
                symbol=code,
                data_source=self.basic_info_cache_key
            )

            if cache_key:
                cached_data = self.cache.load_stock_data(cache_key)
                if cached_data:
                    logger.info(f"⚡ 从缓存获取{self.market}股基础信息: {code}")
                    return self._parse_cached_data(cached_data, self.market, code)

        logger.info(f"🔄 开始获取{self.market}股基础信息: {code} (force_refresh={force_refresh})")

        # 2. 从数据库获取数据源优先级（使用统一方法）
        source_priority = await self._get_source_priority(self.market)

        # 3. 按优先级尝试各个数据源
        info_data = None
        data_source = None

        valid_priority = self._get_valid_sources(
            source_priority,
            self.basic_info_source_handlers,
            self.market
        )

        if not valid_priority:
            logger.warning(f"⚠️ 数据库中没有配置有效的{self.market}股基础信息数据源，使用默认顺序")
            valid_priority = list(self.basic_info_source_handlers.keys())

        logger.info(f"📊 [{self.market}基础信息有效数据源] {valid_priority}")

        for source_name in valid_priority:
            source_key = source_name.lower()
            handler_name, handler_func = self.basic_info_source_handlers[source_key]
            try:
                # 🔥 使用 asyncio.to_thread 避免阻塞事件循环
                info_data = await asyncio.to_thread(handler_func, code)
                data_source = handler_name

                if info_data:
                    logger.info(f"✅ {data_source}获取{self.market}股基础信息成功: {code}")
                    break
            except Exception as e:
                logger.warning(f"⚠️ {source_name}获取基础信息失败: {e}")
                continue

        if not info_data:
            raise Exception(f"无法获取{self.market}股{code}的基础信息：所有数据源均失败")

        # 4. 格式化数据
        formatted_data = self.format_basic_info(info_data, code, data_source)

        # 5. 保存到缓存
        self.cache.save_stock_data(
            symbol=code,
            data=json.dumps(formatted_data, ensure_ascii=False),
            data_source=self.basic_info_cache_key
        )
        logger.info(f"💾 {self.market}股基础信息已缓存: {code}")

        return formatted_data

    @property
    @abstractmethod
    def basic_info_cache_key(self) -> str:
        """基础信息缓存key后缀"""
        raise NotImplementedError("子类必须实现 basic_info_cache_key 属性")

    @property
    @abstractmethod
    def basic_info_source_handlers(self) -> Dict:
        """基础信息数据源处理器映射"""
        raise NotImplementedError("子类必须实现 basic_info_source_handlers 属性")

    @abstractmethod
    def format_basic_info(self, data: Dict, code: str, source: str) -> Dict:
        """格式化基础信息数据"""
        raise NotImplementedError("子类必须实现 format_basic_info 方法")
    async def get_quote_template(self, code: str, force_refresh: bool = False) -> Dict:
        """通用的获取行情模板方法（消除HK/US服务重复）

        🔥 这个方法封装了完全相同的获取行情流程：
        1. 缓存检查（Redis → MongoDB → File）
        2. 请求去重（使用锁确保同一股票同时只有一个API调用）
        3. 按优先级尝试各个数据源
        4. 保存到缓存

        子类只需要定义：
        - market: 市场标识 ('HK' or 'US')
        - quote_source_handlers: 数据源处理器映射
        - format_quote(): 格式化方法
        """
        # 1. 检查缓存（除非强制刷新）
        if not force_refresh:
            cache_key = self.cache.find_cached_stock_data(
                symbol=code,
                data_source=self.quote_cache_key
            )

            if cache_key:
                cached_data = self.cache.load_stock_data(cache_key)
                if cached_data:
                    logger.info(f"⚡ 从缓存获取{self.market}股行情: {code}")
                    return self._parse_cached_data(cached_data, self.market, code)

        # 2. 🔥 请求去重：使用锁确保同一股票同时只有一个API调用
        request_key = f"{self.market}_quote_{code}_{force_refresh}"
        lock = self._request_locks[request_key]

        async with lock:
            # 🔥 再次检查缓存（可能在等待锁的过程中，其他请求已经完成并缓存了数据）
            cache_key = self.cache.find_cached_stock_data(
                symbol=code,
                data_source=self.quote_cache_key
            )
            if cache_key:
                cached_data = self.cache.load_stock_data(cache_key)
                if cached_data:
                    # 检查缓存时间，如果是最近1秒内的，说明是并发请求刚刚缓存的
                    try:
                        data_dict = json.loads(cached_data) if isinstance(cached_data, str) else cached_data
                        updated_at = data_dict.get('updated_at', '')
                        if updated_at:
                            cache_time = datetime.fromisoformat(updated_at)
                            time_diff = (datetime.now() - cache_time).total_seconds()
                            if time_diff < 1:  # 1秒内的缓存，说明是并发请求刚刚完成的
                                logger.info(f"⚡ [去重] 使用并发请求的结果: {code} (缓存时间: {time_diff:.2f}秒前)")
                                return self._parse_cached_data(cached_data, self.market, code)
                    except Exception as e:
                        logger.debug(f"检查缓存时间失败: {e}")

                    # 如果不是强制刷新，使用缓存
                    if not force_refresh:
                        logger.info(f"⚡ [去重后] 从缓存获取{self.market}股行情: {code}")
                        return self._parse_cached_data(cached_data, self.market, code)

            logger.info(f"🔄 开始获取{self.market}股行情: {code} (force_refresh={force_refresh})")

            # 3. 从数据库获取数据源优先级（使用统一方法）
            source_priority = await self._get_source_priority(self.market)

            # 4. 按优先级尝试各个数据源
            quote_data = None
            data_source = None

            # 过滤有效数据源并去重
            valid_priority = self._get_valid_sources(
                source_priority,
                self.quote_source_handlers,
                self.market
            )

            if not valid_priority:
                logger.warning(f"⚠️ 数据库中没有配置有效的{self.market}股数据源，使用默认顺序")
                valid_priority = list(self.quote_source_handlers.keys())

            logger.info(f"📊 [{self.market}有效数据源] {valid_priority} (股票: {code})")

            for source_name in valid_priority:
                source_key = source_name.lower()
                handler_name, handler_func = self.quote_source_handlers[source_key]
                try:
                    # 🔥 使用 asyncio.to_thread 避免阻塞事件循环
                    quote_data = await asyncio.to_thread(handler_func, code)
                    data_source = handler_name

                    if quote_data:
                        logger.info(f"✅ {data_source}获取{self.market}股行情成功: {code}")
                        break
                except Exception as e:
                    logger.warning(f"⚠️ {source_name}获取失败 ({code}): {e}")
                    continue

            if not quote_data:
                raise Exception(f"无法获取{self.market}股{code}的行情数据：所有数据源均失败")

            # 5. 格式化数据
            formatted_data = self.format_quote(quote_data, code, data_source)

            # 6. 保存到缓存
            self.cache.save_stock_data(
                symbol=code,
                data=json.dumps(formatted_data, ensure_ascii=False),
                data_source=self.quote_cache_key
            )
            logger.info(f"💾 {self.market}股行情已缓存: {code}")

            return formatted_data

    @property
    @abstractmethod
    def market(self) -> str:
        """市场标识 ('HK' or 'US')"""
        raise NotImplementedError("子类必须实现 market 属性")

    @property
    @abstractmethod
    def quote_cache_key(self) -> str:
        """行情缓存key后缀"""
        raise NotImplementedError("子类必须实现 quote_cache_key 属性")

    @property
    @abstractmethod
    def quote_source_handlers(self) -> Dict:
        """行情数据源处理器映射"""
        raise NotImplementedError("子类必须实现 quote_source_handlers 属性")

    @abstractmethod
    def format_quote(self, data: Dict, code: str, source: str) -> Dict:
        """格式化行情数据"""
        raise NotImplementedError("子类必须实现 format_quote 方法")

    # ==================== K线数据模板方法 ====================

    async def get_kline_template(
        self,
        code: str,
        period: str = "day",
        limit: int = 120,
        force_refresh: bool = False
    ) -> List[Dict]:
        """
        通用的获取K线数据模板方法（消除HK/US服务重复）

        🔥 这个方法封装了完全相同的获取K线流程：
        1. 缓存检查（Redis → MongoDB → File）
        2. 按优先级尝试各个数据源
        3. 保存到缓存

        子类只需要定义：
        - market: 市场标识 ('HK' or 'US')
        - kline_cache_key: K线缓存key后缀
        - kline_source_handlers: K线数据源处理器映射
        """
        cache_key_str = f"{self.market.lower()}_kline_{period}_{limit}"

        # 1. 检查缓存（除非强制刷新）
        if not force_refresh:
            cache_key = self.cache.find_cached_stock_data(
                symbol=code, data_source=cache_key_str
            )

            if cache_key:
                cached_data = self.cache.load_stock_data(cache_key)
                if cached_data:
                    logger.info(f"⚡ 从缓存获取{self.market}股K线: {code}")
                    return self._parse_cached_kline(cached_data)

        logger.info(f"🔄 开始获取{self.market}股K线: {code}, period={period}, limit={limit}")

        # 2. 从数据库获取数据源优先级
        source_priority = await self._get_source_priority(self.market)

        # 3. 按优先级尝试各个数据源
        kline_data = None
        data_source = None

        valid_priority = self._get_valid_sources(
            source_priority,
            self.kline_source_handlers,
            self.market
        )

        if not valid_priority:
            logger.warning(f"⚠️ 数据库中没有配置有效的{self.market}股K线数据源，使用默认顺序")
            valid_priority = list(self.kline_source_handlers.keys())

        logger.info(f"📊 [{self.market} K线有效数据源] {valid_priority}")

        for source_name in valid_priority:
            source_key = source_name.lower()
            handler_name, handler_func = self.kline_source_handlers[source_key]
            try:
                # 🔥 使用 asyncio.to_thread 避免阻塞事件循环
                kline_data = await asyncio.to_thread(handler_func, code, period, limit)
                data_source = handler_name

                if kline_data:
                    logger.info(f"✅ {data_source}获取{self.market}股K线成功: {code}")
                    break
            except Exception as e:
                logger.warning(f"⚠️ {source_name}获取K线失败: {e}")
                continue

        if not kline_data:
            raise Exception(f"无法获取{self.market}股{code}的K线数据：所有数据源均失败")

        # 4. 保存到缓存
        self.cache.save_stock_data(
            symbol=code,
            data=json.dumps(kline_data, ensure_ascii=False),
            data_source=cache_key_str,
        )
        logger.info(f"💾 {self.market}股K线已缓存: {code}")

        return kline_data

    @property
    @abstractmethod
    def kline_source_handlers(self) -> Dict:
        """K线数据源处理器映射"""
        raise NotImplementedError("子类必须实现 kline_source_handlers 属性")

    # ==================== 新闻数据模板方法 ====================

    async def get_news_template(
        self,
        code: str,
        days: int = 2,
        limit: int = 50,
        force_refresh: bool = False
    ) -> Dict:
        """
        通用的获取新闻数据模板方法（消除HK/US服务重复）

        🔥 这个方法封装了完全相同的获取新闻流程：
        1. 缓存检查（Redis → MongoDB → File）
        2. 按优先级尝试各个数据源
        3. 构建返回数据并保存到缓存

        子类只需要定义：
        - market: 市场标识 ('HK' or 'US')
        - news_source_handlers: 新闻数据源处理器映射
        """
        cache_key_str = f"{self.market.lower()}_news_{days}_{limit}"

        # 1. 尝试从缓存获取
        if not force_refresh:
            cache_key = self.cache.find_cached_stock_data(
                symbol=code, data_source=cache_key_str
            )

            if cache_key:
                cached_data = self.cache.load_stock_data(cache_key)
                if cached_data:
                    logger.info(f"⚡ 从缓存获取{self.market}股新闻: {code}")
                    return json.loads(cached_data)

        logger.info(f"📰 开始获取{self.market}股新闻: {code}, days={days}, limit={limit}")

        # 2. 从数据库获取数据源优先级
        source_priority = await self._get_source_priority(self.market)

        # 3. 按优先级尝试各个数据源
        news_data = None
        data_source = None

        valid_priority = self._get_valid_sources(
            source_priority,
            self.news_source_handlers,
            self.market
        )

        if not valid_priority:
            logger.warning(f"⚠️ 数据库中没有配置有效的{self.market}股新闻数据源，使用默认顺序")
            valid_priority = list(self.news_source_handlers.keys())

        logger.info(f"📊 [{self.market}新闻有效数据源] {valid_priority}")

        for source_name in valid_priority:
            source_key = source_name.lower()
            handler_name, handler_func = self.news_source_handlers[source_key]
            try:
                # 🔥 使用 asyncio.to_thread 避免阻塞事件循环
                news_data = await asyncio.to_thread(handler_func, code, days, limit)
                data_source = handler_name

                if news_data:
                    logger.info(f"✅ {data_source}获取{self.market}股新闻成功: {code}, 返回 {len(news_data)} 条")
                    break
            except Exception as e:
                logger.warning(f"⚠️ {source_name}获取新闻失败: {e}")
                continue

        if not news_data:
            logger.warning(f"⚠️ 无法获取{self.market}股{code}的新闻数据：所有数据源均失败")
            news_data = []
            data_source = "none"

        # 4. 构建返回数据
        result = {
            "code": code,
            "days": days,
            "limit": limit,
            "source": data_source,
            "items": news_data,
        }

        # 5. 缓存数据
        self.cache.save_stock_data(
            symbol=code,
            data=json.dumps(result, ensure_ascii=False),
            data_source=cache_key_str,
        )
        logger.info(f"💾 {self.market}股新闻已缓存: {code}")

        return result

    @property
    @abstractmethod
    def news_source_handlers(self) -> Dict:
        """新闻数据源处理器映射"""
        raise NotImplementedError("子类必须实现 news_source_handlers 属性")
