# -*- coding: utf-8 -*-
"""查询构建模块

提供 MongoDB 查询条件构建功能。
"""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class QueryBuilderMixin:
    """查询构建 Mixin"""

    def __init__(self):
        # 支持的基础信息字段映射
        self.basic_fields = {
            # 基本信息
            "code": "code",
            "name": "name",
            "industry": "industry",
            "area": "area",
            "market": "market",
            "list_date": "list_date",

            # 市值信息 (亿元)
            "total_mv": "total_mv",
            "circ_mv": "circ_mv",
            "market_cap": "total_mv",

            # 财务指标
            "pe": "pe",
            "pb": "pb",
            "pe_ttm": "pe_ttm",
            "pb_mrq": "pb_mrq",
            "roe": "roe",

            # 交易指标
            "turnover_rate": "turnover_rate",
            "volume_ratio": "volume_ratio",

            # 实时行情字段
            "pct_chg": "pct_chg",
            "amount": "amount",
            "close": "close",
            "volume": "volume",
        }

        # 支持的操作符
        self.operators = {
            ">": "$gt",
            "<": "$lt",
            ">=": "$gte",
            "<=": "$lte",
            "==": "$eq",
            "!=": "$ne",
            "between": "$between",
            "in": "$in",
            "not_in": "$nin",
            "contains": "$regex",
        }

    async def can_handle_conditions(self, conditions: List[Dict[str, Any]]) -> bool:
        """检查是否可以完全通过数据库筛选处理这些条件"""
        for condition in conditions:
            field = condition.get("field") if isinstance(condition, dict) else condition.field
            operator = condition.get("operator") if isinstance(condition, dict) else condition.operator

            if field not in self.basic_fields:
                logger.debug(f"字段 {field} 不支持数据库筛选")
                return False

            if operator not in self.operators:
                logger.debug(f"操作符 {operator} 不支持数据库筛选")
                return False

        return True

    async def _build_query(self, conditions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """构建MongoDB查询条件"""
        query = {}

        for condition in conditions:
            field = condition.get("field") if isinstance(condition, dict) else condition.field
            operator = condition.get("operator") if isinstance(condition, dict) else condition.operator
            value = condition.get("value") if isinstance(condition, dict) else condition.value

            logger.info(f"🔍 [_build_query] 处理条件: field={field}, operator={operator}, value={value}")

            db_field = self.basic_fields.get(field)
            if not db_field:
                logger.warning(f"⚠️ [_build_query] 字段 {field} 不在 basic_fields 映射中，跳过")
                continue

            logger.info(f"✅ [_build_query] 字段映射: {field} -> {db_field}")

            if operator == "between":
                if isinstance(value, list) and len(value) == 2:
                    query[db_field] = {
                        "$gte": value[0],
                        "$lte": value[1]
                    }
            elif operator == "contains":
                query[db_field] = {
                    "$regex": str(value),
                    "$options": "i"
                }
            elif operator in self.operators:
                mongo_op = self.operators[operator]
                query[db_field] = {mongo_op: value}

        return query

    def _separate_conditions(self, conditions: List[Dict[str, Any]]) -> tuple:
        """分离基础信息条件和实时行情条件"""
        quote_fields = {"pct_chg", "amount", "close", "volume"}

        basic_conditions = []
        quote_conditions = []

        for condition in conditions:
            field = condition.get("field") if isinstance(condition, dict) else condition.field
            if field in quote_fields:
                quote_conditions.append(condition)
            else:
                basic_conditions.append(condition)

        return basic_conditions, quote_conditions
