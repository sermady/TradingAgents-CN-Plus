# -*- coding: utf-8 -*-
"""数据库筛选服务

组合所有 Mixin 提供基于 MongoDB 的股票筛选功能。
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from app.core.database import get_mongo_db
from .query import QueryBuilderMixin
from .sort import SortMixin
from .enrichment import EnrichmentMixin
from .formatter import FormatterMixin

logger = logging.getLogger(__name__)


class DatabaseScreeningService(QueryBuilderMixin, SortMixin, EnrichmentMixin, FormatterMixin):
    """基于数据库的股票筛选服务"""

    def __init__(self):
        QueryBuilderMixin.__init__(self)
        self.collection_name = "stock_screening_view"

    async def screen_stocks(
        self,
        conditions: List[Dict[str, Any]],
        limit: int = 50,
        offset: int = 0,
        order_by: Optional[List[Dict[str, str]]] = None,
        source: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], int]:
        """基于数据库进行股票筛选

        Args:
            conditions: 筛选条件列表
            limit: 返回数量限制
            offset: 偏移量
            order_by: 排序条件
            source: 数据源（可选）

        Returns:
            Tuple[List[Dict], int]: (筛选结果, 总数量)
        """
        try:
            db = get_mongo_db()
            collection = db[self.collection_name]

            # 获取数据源优先级配置
            if not source:
                from app.core.unified_config_service import get_config_manager
                config = get_config_manager()
                data_source_configs = await config.get_data_source_configs_async()

                enabled_sources = [
                    ds.type.lower() for ds in data_source_configs
                    if ds.enabled and ds.type.lower() in ['tushare', 'akshare', 'baostock']
                ]

                if not enabled_sources:
                    enabled_sources = ['tushare', 'akshare', 'baostock']

                source = enabled_sources[0] if enabled_sources else 'tushare'

            # 构建查询条件
            query = await self._build_query(conditions)
            query["source"] = source

            logger.info(f"📋 数据库查询条件: {query}")

            # 构建排序条件
            sort_conditions = self._build_sort_conditions(order_by)

            # 获取总数
            total_count = await collection.count_documents(query)

            # 执行查询
            cursor = collection.find(query)

            if sort_conditions:
                cursor = cursor.sort(sort_conditions)

            cursor = cursor.skip(offset).limit(limit)

            results = []
            codes = []
            async for doc in cursor:
                result = self._format_result(doc)
                results.append(result)
                codes.append(doc.get("code"))

            # 批量查询财务数据
            if codes:
                await self._enrich_with_financial_data(results, codes)

            logger.info(f"✅ 数据库筛选完成: 总数={total_count}, 返回={len(results)}, 数据源={source}")

            return results, total_count

        except Exception as e:
            logger.error(f"❌ 数据库筛选失败: {e}")
            raise Exception(f"数据库筛选失败: {str(e)}")

    async def get_field_statistics(self, field: str) -> Dict[str, Any]:
        """获取字段的统计信息"""
        try:
            db_field = self.basic_fields.get(field)
            if not db_field:
                return {}

            db = get_mongo_db()
            collection = db[self.collection_name]

            pipeline = [
                {"$match": {db_field: {"$exists": True, "$ne": None}}},
                {"$group": {
                    "_id": None,
                    "min": {"$min": f"${db_field}"},
                    "max": {"$max": f"${db_field}"},
                    "avg": {"$avg": f"${db_field}"},
                    "count": {"$sum": 1}
                }}
            ]

            result = await collection.aggregate(pipeline).to_list(length=1)

            if result:
                stats = result[0]
                avg_value = stats.get("avg")
                return {
                    "field": field,
                    "min": stats.get("min"),
                    "max": stats.get("max"),
                    "avg": round(avg_value, 2) if avg_value is not None else None,
                    "count": stats.get("count", 0)
                }

            return {"field": field, "count": 0}

        except Exception as e:
            logger.error(f"获取字段统计失败: {e}")
            return {"field": field, "error": str(e)}

    async def get_available_values(self, field: str, limit: int = 100) -> List[str]:
        """获取字段的可选值列表"""
        try:
            db_field = self.basic_fields.get(field)
            if not db_field:
                return []

            db = get_mongo_db()
            collection = db[self.collection_name]

            values = await collection.distinct(db_field)
            values = [v for v in values if v is not None]
            values.sort()

            return values[:limit]

        except Exception as e:
            logger.error(f"获取字段可选值失败: {e}")
            return []


# 全局服务实例
_database_screening_service: Optional[DatabaseScreeningService] = None


def get_database_screening_service() -> DatabaseScreeningService:
    """获取数据库筛选服务实例"""
    global _database_screening_service
    if _database_screening_service is None:
        _database_screening_service = DatabaseScreeningService()
    return _database_screening_service
