# -*- coding: utf-8 -*-
"""新闻数据服务

提供统一的新闻数据存储、查询和管理功能。
"""
import logging
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta

from app.core.database import get_database, get_mongo_db_sync

from .models import NewsQueryParams, NewsStats
from .repository import NewsRepositoryMixin
from .utils import convert_objectid_to_str, standardize_news_data

logger = logging.getLogger(__name__)


class NewsDataService(NewsRepositoryMixin):
    """新闻数据服务"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._db = None
        self._collection = None

    async def save_news_data(
        self,
        news_data: Union[Dict[str, Any], List[Dict[str, Any]]],
        data_source: str,
        market: str = "CN"
    ) -> int:
        """
        保存新闻数据

        Args:
            news_data: 新闻数据（单条或多条）
            data_source: 数据源标识
            market: 市场标识

        Returns:
            保存的记录数量
        """
        try:
            await self._ensure_indexes()
            now = datetime.utcnow()

            # 标准化数据
            if isinstance(news_data, dict):
                news_list = [news_data]
            else:
                news_list = news_data

            if not news_list:
                return 0

            # 记录前3条数据的详细信息
            for i, news in enumerate(news_list[:3], 1):
                self.logger.info(f"News {i}: symbol={news.get('symbol')}, title={news.get('title', '')[:50]}...")

            saved_count = await self._save_news_batch(news_list, data_source, market, now)
            self.logger.info(f"News data saved: {saved_count} records (source: {data_source})")
            return saved_count

        except Exception as e:
            self.logger.error(f"Failed to save news data: {e}")
            return 0

    def save_news_data_sync(
        self,
        news_data: Union[Dict[str, Any], List[Dict[str, Any]]],
        data_source: str,
        market: str = "CN"
    ) -> int:
        """
        保存新闻数据（同步版本）
        用于非异步上下文，使用同步的 PyMongo 客户端

        Args:
            news_data: 新闻数据（单条或多条）
            data_source: 数据源标识
            market: 市场标识

        Returns:
            保存的记录数量
        """
        try:
            from pymongo import ReplaceOne
            from pymongo.errors import BulkWriteError

            db = get_mongo_db_sync()
            collection = db.stock_news
            now = datetime.utcnow()

            if isinstance(news_data, dict):
                news_list = [news_data]
            else:
                news_list = news_data

            if not news_list:
                return 0

            operations = []
            for i, news in enumerate(news_list, 1):
                standardized = standardize_news_data(news, data_source, market, now)

                if i <= 3:
                    self.logger.info(f"News {i}: symbol={standardized.get('symbol')}, title={standardized.get('title', '')[:50]}...")

                filter_query = {
                    "url": standardized.get("url"),
                    "title": standardized.get("title"),
                    "publish_time": standardized.get("publish_time")
                }
                operations.append(ReplaceOne(filter_query, standardized, upsert=True))

            if operations:
                result = collection.bulk_write(operations)
                saved_count = result.upserted_count + result.modified_count
                self.logger.info(f"News data saved: {saved_count} records (source: {data_source})")
                return saved_count

            return 0

        except BulkWriteError as e:
            write_errors = e.details.get('writeErrors', [])
            error_count = len(write_errors)
            success_count = len(operations) - error_count if 'operations' in dir() else 0

            for i, error in enumerate(write_errors[:3], 1):
                self.logger.warning(f"Error {i}: {error.get('errmsg', 'Unknown')}")

            return success_count

        except Exception as e:
            self.logger.error(f"Failed to save news data: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return 0

    async def query_news(self, params: NewsQueryParams) -> List[Dict[str, Any]]:
        """
        查询新闻数据

        Args:
            params: 查询参数

        Returns:
            新闻数据列表
        """
        try:
            self.logger.info(f"Querying news data: symbol={params.symbol}, limit={params.limit}")
            results = await self._query_news(params)
            self.logger.info(f"Query completed: {len(results)} records returned")
            return results
        except Exception as e:
            self.logger.error(f"Failed to query news data: {e}", exc_info=True)
            return []

    async def get_latest_news(
        self,
        symbol: str = None,
        limit: int = 10,
        hours_back: int = 24
    ) -> List[Dict[str, Any]]:
        """
        获取最新新闻

        Args:
            symbol: 股票代码，为空则获取所有新闻
            limit: 返回数量限制
            hours_back: 回溯小时数

        Returns:
            最新新闻列表
        """
        start_time = datetime.utcnow() - timedelta(hours=hours_back)

        params = NewsQueryParams(
            symbol=symbol,
            start_time=start_time,
            limit=limit,
            sort_by="publish_time",
            sort_order=-1
        )

        return await self.query_news(params)

    async def get_news_statistics(
        self,
        symbol: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> NewsStats:
        """
        获取新闻统计信息

        Args:
            symbol: 股票代码
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            新闻统计信息
        """
        try:
            return await self._get_statistics(symbol, start_time, end_time)
        except Exception as e:
            self.logger.error(f"Failed to get news statistics: {e}")
            return NewsStats()

    async def delete_old_news(self, days_to_keep: int = 90) -> int:
        """
        删除过期新闻

        Args:
            days_to_keep: 保留天数

        Returns:
            删除的记录数量
        """
        try:
            deleted_count = await self._delete_old_news(days_to_keep)
            self.logger.info(f"Deleted old news: {deleted_count} records")
            return deleted_count
        except Exception as e:
            self.logger.error(f"Failed to delete old news: {e}")
            return 0

    async def search_news(
        self,
        query_text: str,
        symbol: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        全文搜索新闻

        Args:
            query_text: 搜索文本
            symbol: 股票代码过滤
            limit: 返回数量限制

        Returns:
            搜索结果列表
        """
        try:
            results = await self._search_news(query_text, symbol, limit)
            self.logger.info(f"Full-text search returned {len(results)} results")
            return results
        except Exception as e:
            self.logger.error(f"Full-text search failed: {e}")
            return []


# 全局服务实例
_service_instance = None


async def get_news_data_service() -> NewsDataService:
    """获取新闻数据服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = NewsDataService()
        logger.info("News data service initialized")
    return _service_instance
