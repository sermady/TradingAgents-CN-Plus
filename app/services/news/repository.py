# -*- coding: utf-8 -*-
"""新闻数据仓储层

提供新闻数据的底层数据访问操作。
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

from pymongo import ReplaceOne
from pymongo.errors import BulkWriteError
from app.core.database import get_database

from .models import NewsQueryParams, NewsStats
from .utils import convert_objectid_to_str, standardize_news_data

logger = logging.getLogger(__name__)


class NewsRepositoryMixin:
    """新闻数据仓储混入类"""

    _indexes_ensured = False

    def _get_collection(self):
        """获取新闻数据集合"""
        db = get_database()
        return db.stock_news

    async def _ensure_indexes(self):
        """确保必要的索引存在"""
        if self._indexes_ensured:
            return

        try:
            collection = self._get_collection()
            logger.info("Checking and creating news data indexes...")

            # 唯一索引：防止重复新闻（URL+标题+发布时间）
            await collection.create_index([
                ("url", 1),
                ("title", 1),
                ("publish_time", 1)
            ], unique=True, name="url_title_time_unique", background=True)

            # 单字段索引
            await collection.create_index([("symbol", 1)], name="symbol_index", background=True)
            await collection.create_index([("symbols", 1)], name="symbols_index", background=True)
            await collection.create_index([("publish_time", -1)], name="publish_time_desc", background=True)
            await collection.create_index([("data_source", 1)], name="data_source_index", background=True)
            await collection.create_index([("category", 1)], name="category_index", background=True)
            await collection.create_index([("sentiment", 1)], name="sentiment_index", background=True)
            await collection.create_index([("importance", 1)], name="importance_index", background=True)
            await collection.create_index([("updated_at", -1)], name="updated_at_index", background=True)

            # 复合索引
            await collection.create_index([
                ("symbol", 1),
                ("publish_time", -1)
            ], name="symbol_time_index", background=True)

            self._indexes_ensured = True
            logger.info("News data indexes check completed")
        except Exception as e:
            logger.warning(f"Warning creating indexes (may already exist): {e}")

    async def _save_news_batch(
        self,
        news_list: List[Dict[str, Any]],
        data_source: str,
        market: str,
        now: datetime
    ) -> int:
        """批量保存新闻数据（内部方法）

        Args:
            news_list: 新闻数据列表
            data_source: 数据源标识
            market: 市场标识
            now: 当前时间

        Returns:
            保存的记录数量
        """
        collection = self._get_collection()
        operations = []

        for news in news_list:
            standardized = standardize_news_data(news, data_source, market, now)

            filter_query = {
                "url": standardized["url"],
                "title": standardized["title"],
                "publish_time": standardized["publish_time"]
            }

            operations.append(ReplaceOne(filter_query, standardized, upsert=True))

        if not operations:
            return 0

        try:
            result = await collection.bulk_write(operations)
            return result.upserted_count + result.modified_count
        except BulkWriteError as e:
            write_errors = e.details.get('writeErrors', [])
            error_count = len(write_errors)
            success_count = len(operations) - error_count

            for i, error in enumerate(write_errors[:3], 1):
                logger.warning(f"Error {i}: {error.get('errmsg', 'Unknown')}")

            return success_count

    async def _query_news(self, params: NewsQueryParams) -> List[Dict[str, Any]]:
        """查询新闻数据（内部方法）

        Args:
            params: 查询参数

        Returns:
            新闻数据列表
        """
        collection = self._get_collection()
        query = {}

        if params.symbol:
            query["symbol"] = params.symbol
        if params.symbols:
            query["symbols"] = {"$in": params.symbols}
        if params.start_time or params.end_time:
            time_query = {}
            if params.start_time:
                time_query["$gte"] = params.start_time
            if params.end_time:
                time_query["$lte"] = params.end_time
            query["publish_time"] = time_query
        if params.category:
            query["category"] = params.category
        if params.sentiment:
            query["sentiment"] = params.sentiment
        if params.importance:
            query["importance"] = params.importance
        if params.data_source:
            query["data_source"] = params.data_source
        if params.keywords:
            query["$text"] = {"$search": " ".join(params.keywords)}

        cursor = collection.find(query)
        cursor = cursor.sort(params.sort_by, params.sort_order)
        cursor = cursor.skip(params.skip).limit(params.limit)

        results = await cursor.to_list(length=None)
        return convert_objectid_to_str(results)

    async def _get_statistics(
        self,
        symbol: str = None,
        start_time: datetime = None,
        end_time: datetime = None
    ) -> NewsStats:
        """获取新闻统计信息（内部方法）

        Args:
            symbol: 股票代码
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            新闻统计信息
        """
        collection = self._get_collection()
        match_stage = {}

        if symbol:
            match_stage["symbol"] = symbol
        if start_time or end_time:
            time_query = {}
            if start_time:
                time_query["$gte"] = start_time
            if end_time:
                time_query["$lte"] = end_time
            match_stage["publish_time"] = time_query

        pipeline = []
        if match_stage:
            pipeline.append({"$match": match_stage})

        pipeline.append({
            "$group": {
                "_id": None,
                "total_count": {"$sum": 1},
                "positive_count": {"$sum": {"$cond": [{"$eq": ["$sentiment", "positive"]}, 1, 0]}},
                "negative_count": {"$sum": {"$cond": [{"$eq": ["$sentiment", "negative"]}, 1, 0]}},
                "neutral_count": {"$sum": {"$cond": [{"$eq": ["$sentiment", "neutral"]}, 1, 0]}},
                "high_importance_count": {"$sum": {"$cond": [{"$eq": ["$importance", "high"]}, 1, 0]}},
                "medium_importance_count": {"$sum": {"$cond": [{"$eq": ["$importance", "medium"]}, 1, 0]}},
                "low_importance_count": {"$sum": {"$cond": [{"$eq": ["$importance", "low"]}, 1, 0]}},
                "categories": {"$push": "$category"},
                "sources": {"$push": "$data_source"}
            }
        })

        result = await collection.aggregate(pipeline).to_list(length=1)

        if result:
            data = result[0]
            categories = {}
            for cat in data.get("categories", []):
                categories[cat] = categories.get(cat, 0) + 1

            sources = {}
            for src in data.get("sources", []):
                sources[src] = sources.get(src, 0) + 1

            return NewsStats(
                total_count=data.get("total_count", 0),
                positive_count=data.get("positive_count", 0),
                negative_count=data.get("negative_count", 0),
                neutral_count=data.get("neutral_count", 0),
                high_importance_count=data.get("high_importance_count", 0),
                medium_importance_count=data.get("medium_importance_count", 0),
                low_importance_count=data.get("low_importance_count", 0),
                categories=categories,
                sources=sources
            )

        return NewsStats()

    async def _delete_old_news(self, days_to_keep: int) -> int:
        """删除过期新闻（内部方法）

        Args:
            days_to_keep: 保留天数

        Returns:
            删除的记录数量
        """
        collection = self._get_collection()
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        result = await collection.delete_many({
            "publish_time": {"$lt": cutoff_date}
        })

        return result.deleted_count

    async def _search_news(
        self,
        query_text: str,
        symbol: str = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """全文搜索新闻（内部方法）

        Args:
            query_text: 搜索文本
            symbol: 股票代码过滤
            limit: 返回数量限制

        Returns:
            搜索结果列表
        """
        collection = self._get_collection()
        query = {"$text": {"$search": query_text}}

        if symbol:
            query["symbol"] = symbol

        cursor = collection.find(
            query,
            {"score": {"$meta": "textScore"}}
        ).sort([("score", {"$meta": "textScore"})]).limit(limit)

        results = await cursor.to_list(length=None)
        return convert_objectid_to_str(results)
