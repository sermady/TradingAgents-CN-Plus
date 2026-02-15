# -*- coding: utf-8 -*-
"""消息服务基类

提供统一的查询和搜索功能，用于InternalMessageService和SocialMediaService。
提取公共逻辑，消除95%的search_messages重复代码。

使用示例:
    class InternalMessageService(MessageBaseService):
        @property
        def collection_name(self) -> str:
            return "internal_messages"

        def _build_access_level_filter(self, query: dict) -> dict:
            # 内部消息特定的访问级别过滤
            query['access_level'] = {'$ne': 'restricted'}
            return query
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Callable
import logging

from app.core.database import get_database

logger = logging.getLogger(__name__)


class MessageBaseService(ABC):
    """消息服务基类

    提供统一的查询和搜索功能，支持策略模式的过滤条件。

    Attributes:
        collection_name: MongoDB集合名称，由子类实现
    """

    def __init__(self):
        """初始化消息服务基类"""
        self.db = None
        self.collection = None
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def collection_name(self) -> str:
        """MongoDB集合名称

        Returns:
            str: 集合名称

        Raises:
            NotImplementedError: 必须由子类实现
        """
        raise NotImplementedError("子类必须实现 collection_name 属性")

    async def _get_collection(self):
        """获取MongoDB集合实例"""
        if self.collection is None:
            await self.initialize()
        return self.collection

    async def initialize(self):
        """初始化服务"""
        try:
            self.db = get_database()
            self.collection = getattr(self.db, self.collection_name)
            self.logger.info(f"✅ {self.__class__.__name__}初始化成功")
        except Exception as e:
            self.logger.error(f"❌ {self.__class__.__name__}初始化失败: {e}")
            raise

    async def search_messages(
        self,
        query: str,
        symbol: str = None,
        limit: int = 50,
        extra_filters: Optional[Dict[str, Any]] = None,
        filter_strategy: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> List[Dict[str, Any]]:
        """统一的全文搜索方法

        Args:
            query: 搜索关键词
            symbol: 股票代码（可选）
            limit: 返回数量限制
            extra_filters: 额外的MongoDB过滤条件（可选）
            filter_strategy: 过滤策略函数，接收query并返回修改后的query（可选）

        Returns:
            List[Dict]: 消息列表

        Example:
            # 内部消息使用access_level过滤
            messages = await service.search_messages(
                query="年报",
                symbol="000001",
                filter_strategy=self._access_level_filter
            )

            # 社交消息使用platform过滤
            messages = await service.search_messages(
                query="股票分析",
                extra_filters={"platform": "twitter"}
            )
        """
        try:
            from app.utils.search_utils import execute_text_search

            collection = await self._get_collection()

            # 构建基础过滤条件
            filters = {}
            if symbol:
                filters['symbol'] = symbol

            # 应用额外过滤条件
            if extra_filters:
                filters.update(extra_filters)

            # 应用过滤策略
            if filter_strategy:
                filters = filter_strategy(filters)

            # 执行搜索
            return await execute_text_search(
                collection=collection,
                query=query,
                symbol=symbol,
                limit=limit,
                extra_filters=filters if filters else None
            )

        except Exception as e:
            self.logger.error(f"❌ 消息搜索失败: {e}")
            return []

    async def query_messages(
        self,
        filters: Dict[str, Any],
        sort_by: str = "created_time",
        sort_order: int = -1,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """统一的查询方法

        Args:
            filters: MongoDB查询条件
            sort_by: 排序字段
            sort_order: 排序方向（-1倒序，1正序）
            skip: 跳过文档数
            limit: 返回数量限制

        Returns:
            List[Dict]: 消息列表
        """
        try:
            collection = await self._get_collection()

            # 执行查询
            cursor = collection.find(filters)
            cursor = cursor.sort(sort_by, sort_order)
            cursor = cursor.skip(skip).limit(limit)

            messages = await cursor.to_list(length=limit)

            self.logger.debug(f"📊 查询到 {len(messages)} 条消息")
            return messages

        except Exception as e:
            self.logger.error(f"❌ 消息查询失败: {e}")
            return []

    async def get_latest_messages(
        self,
        symbol: str = None,
        limit: int = 20,
        extra_filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """获取最新消息（便捷方法）

        Args:
            symbol: 股票代码（可选）
            limit: 返回数量限制
            extra_filters: 额外的过滤条件

        Returns:
            List[Dict]: 最新消息列表
        """
        filters = {}
        if symbol:
            filters['symbol'] = symbol

        if extra_filters:
            filters.update(extra_filters)

        return await self.query_messages(
            filters=filters,
            sort_by="created_time",
            sort_order=-1,
            limit=limit
        )


class InternalMessageServiceBase(MessageBaseService):
    """内部消息服务基类

    提供内部消息特定的过滤策略。
    """

    @property
    def collection_name(self) -> str:
        return "internal_messages"

    def _access_level_filter(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """访问级别过滤策略

        排除受限级别的消息。

        Args:
            query: 原始查询条件

        Returns:
            Dict: 添加了访问级别过滤的查询条件
        """
        query['access_level'] = {'$ne': 'restricted'}
        return query

    async def search_messages(
        self,
        query: str,
        symbol: str = None,
        access_level: str = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """内部消息搜索

        Args:
            query: 搜索关键词
            symbol: 股票代码
            access_level: 访问级别过滤
            limit: 返回数量限制

        Returns:
            List[Dict]: 消息列表
        """
        extra_filters = {}
        if access_level:
            extra_filters["access_level"] = access_level

        return await super().search_messages(
            query=query,
            symbol=symbol,
            limit=limit,
            extra_filters=extra_filters if extra_filters else None,
            filter_strategy=self._access_level_filter
        )


class SocialMediaServiceBase(MessageBaseService):
    """社交媒体消息服务基类

    提供社交媒体特定的过滤策略。
    """

    @property
    def collection_name(self) -> str:
        return "social_media_messages"

    def _platform_filter(self, query: Dict[str, Any], platform: str) -> Dict[str, Any]:
        """平台过滤策略

        Args:
            query: 原始查询条件
            platform: 平台名称

        Returns:
            Dict: 添加了平台过滤的查询条件
        """
        query['platform'] = platform
        return query

    async def search_messages(
        self,
        query: str,
        symbol: str = None,
        platform: str = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """社交媒体消息搜索

        Args:
            query: 搜索关键词
            symbol: 股票代码
            platform: 平台过滤
            limit: 返回数量限制

        Returns:
            List[Dict]: 消息列表
        """
        extra_filters = {}
        if platform:
            extra_filters["platform"] = platform

        return await super().search_messages(
            query=query,
            symbol=symbol,
            limit=limit,
            extra_filters=extra_filters if extra_filters else None
        )


# 导出
__all__ = [
    'MessageBaseService',
    'InternalMessageServiceBase',
    'SocialMediaServiceBase',
]
