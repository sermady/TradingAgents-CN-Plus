# -*- coding: utf-8 -*-
"""
使用统计服务
管理模型使用记录和成本统计

使用 BaseCRUDService 基类重构，复用标准 CRUD 方法。
保留复杂统计聚合逻辑。
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, cast
from collections import defaultdict

from app.services.crud import BaseCRUDService
from app.core.database import get_mongo_db
from app.models.config import UsageRecord, UsageStatistics

logger = logging.getLogger("app.services.usage_statistics_service")


class UsageStatisticsService(BaseCRUDService):
    """使用统计服务

    继承 BaseCRUDService 获得标准 CRUD 操作。
    保留复杂统计聚合逻辑。
    """

    @property
    def collection_name(self) -> str:
        """MongoDB 集合名称"""
        return "token_usage"

    async def add_usage_record(self, record: UsageRecord) -> bool:
        """添加使用记录"""
        record_dict = record.model_dump(exclude={"id"})
        doc_id = await self.create(record_dict)

        if doc_id:
            logger.info(f"[OK] 添加使用记录成功: {record.provider}/{record.model_name}")
            return True
        else:
            logger.error("[ERROR] 添加使用记录失败")
            return False

    async def get_usage_records(
        self,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[UsageRecord]:
        """获取使用记录"""
        # 构建查询条件
        filters = {}
        if provider:
            filters["provider"] = provider
        if model_name:
            filters["model_name"] = model_name
        if start_date or end_date:
            filters["timestamp"] = {}
            if start_date:
                filters["timestamp"]["$gte"] = start_date.isoformat()
            if end_date:
                filters["timestamp"]["$lte"] = end_date.isoformat()

        # 使用基类的 list 方法
        docs = await self.list(
            filters=filters,
            sort=[("timestamp", -1)],
            limit=limit
        )

        records = []
        for doc in docs:
            records.append(UsageRecord(**doc))

        logger.info(f"[OK] 获取使用记录成功: {len(records)} 条")
        return records

    async def get_usage_statistics(
        self,
        days: int = 7,
        provider: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> UsageStatistics:
        """获取使用统计（保留聚合逻辑）"""
        try:
            db = await self._get_db()

            # 计算时间范围
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # 构建查询条件
            filters: Dict[str, Any] = {
                "timestamp": {
                    "$gte": start_date.isoformat(),
                    "$lte": end_date.isoformat(),
                }
            }
            if provider:
                filters["provider"] = provider
            if model_name:
                filters["model_name"] = model_name

            # 获取所有记录
            cursor = db[self.collection_name].find(filters)
            records = []
            async for doc in cursor:
                records.append(doc)

            # 统计数据
            stats = UsageStatistics()
            stats.total_requests = len(records)

            # 按货币统计成本
            cost_by_currency: Dict[str, float] = defaultdict(float)

            by_provider: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                    "cost_by_currency": defaultdict(float),
                }
            )
            by_model: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                    "cost_by_currency": defaultdict(float),
                }
            )
            by_date: Dict[str, Dict[str, Any]] = defaultdict(
                lambda: {
                    "requests": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0,
                    "cost_by_currency": defaultdict(float),
                }
            )

            for record in records:
                cost = record.get("cost", 0.0)
                currency = record.get("currency", "CNY")

                # 总计
                stats.total_input_tokens += record.get("input_tokens", 0)
                stats.total_output_tokens += record.get("output_tokens", 0)
                stats.total_cost += cost
                cost_by_currency[currency] += cost

                # 按供应商统计
                provider_key = record.get("provider", "unknown")
                provider_data = by_provider[provider_key]
                provider_data["requests"] = int(provider_data["requests"]) + 1
                provider_data["input_tokens"] = int(
                    provider_data["input_tokens"]
                ) + record.get("input_tokens", 0)
                provider_data["output_tokens"] = int(
                    provider_data["output_tokens"]
                ) + record.get("output_tokens", 0)
                provider_data["cost"] = float(provider_data["cost"]) + cost
                cast(Dict[str, Any], provider_data["cost_by_currency"])[currency] = (
                    float(
                        cast(Dict[str, Any], provider_data["cost_by_currency"]).get(
                            currency, 0.0
                        )
                    )
                    + cost
                )

                # 按模型统计
                model_key = f"{record.get('provider', 'unknown')}/{record.get('model_name', 'unknown')}"
                model_data = by_model[model_key]
                model_data["requests"] = int(model_data["requests"]) + 1
                model_data["input_tokens"] = int(
                    model_data["input_tokens"]
                ) + record.get("input_tokens", 0)
                model_data["output_tokens"] = int(
                    model_data["output_tokens"]
                ) + record.get("output_tokens", 0)
                model_data["cost"] = float(model_data["cost"]) + cost
                cast(Dict[str, Any], model_data["cost_by_currency"])[currency] = (
                    float(
                        cast(Dict[str, Any], model_data["cost_by_currency"]).get(
                            currency, 0.0
                        )
                    )
                    + cost
                )

                # 按日期统计
                timestamp = record.get("timestamp", "")
                if timestamp:
                    date_key = timestamp[:10]  # YYYY-MM-DD
                    date_data = by_date[date_key]
                    date_data["requests"] = int(date_data["requests"]) + 1
                    date_data["input_tokens"] = int(
                        date_data["input_tokens"]
                    ) + record.get("input_tokens", 0)
                    date_data["output_tokens"] = int(
                        date_data["output_tokens"]
                    ) + record.get("output_tokens", 0)
                    date_data["cost"] = float(date_data["cost"]) + cost
                    cast(Dict[str, Any], date_data["cost_by_currency"])[currency] = (
                        float(
                            cast(Dict[str, Any], date_data["cost_by_currency"]).get(
                                currency, 0.0
                            )
                        )
                        + cost
                    )

            # 转换 defaultdict 为普通 dict
            stats.cost_by_currency = dict(cost_by_currency)
            stats.by_provider = {
                k: {**v, "cost_by_currency": dict(v["cost_by_currency"])}
                for k, v in by_provider.items()
            }
            stats.by_model = {
                k: {**v, "cost_by_currency": dict(v["cost_by_currency"])}
                for k, v in by_model.items()
            }
            stats.by_date = {
                k: {**v, "cost_by_currency": dict(v["cost_by_currency"])}
                for k, v in by_date.items()
            }

            logger.info(f"[OK] 获取使用统计成功: {stats.total_requests} 条记录")
            return stats

        except Exception as e:
            logger.error(f"[ERROR] 获取使用统计失败: {e}")
            return UsageStatistics()

    async def get_cost_by_provider(self, days: int = 7) -> Dict[str, float]:
        """获取按供应商的成本统计"""
        stats = await self.get_usage_statistics(days=days)
        return {provider: data["cost"] for provider, data in stats.by_provider.items()}

    async def get_cost_by_model(self, days: int = 7) -> Dict[str, float]:
        """获取按模型的成本统计"""
        stats = await self.get_usage_statistics(days=days)
        return {model: data["cost"] for model, data in stats.by_model.items()}

    async def get_daily_cost(self, days: int = 7) -> Dict[str, float]:
        """获取每日成本统计"""
        stats = await self.get_usage_statistics(days=days)
        return {date: data["cost"] for date, data in stats.by_date.items()}

    async def delete_old_records(self, days: int = 90) -> int:
        """删除旧记录"""
        cutoff_date = datetime.now() - timedelta(days=days)
        deleted_count = await self._delete_many(
            {"timestamp": {"$lt": cutoff_date.isoformat()}}
        )

        if deleted_count > 0:
            logger.info(f"[OK] 删除旧记录成功: {deleted_count} 条")
        return deleted_count

    async def _delete_many(self, filter_query: Dict[str, Any]) -> int:
        """批量删除（内部方法）"""
        try:
            db = await self._get_db()
            result = await db[self.collection_name].delete_many(filter_query)
            return result.deleted_count
        except Exception as e:
            logger.error(f"[ERROR] 批量删除失败: {e}")
            return 0


# 创建全局实例
usage_statistics_service = UsageStatisticsService()
