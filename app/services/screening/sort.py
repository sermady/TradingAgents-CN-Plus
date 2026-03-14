# -*- coding: utf-8 -*-
"""排序模块

提供 MongoDB 排序条件构建功能。
"""

from typing import Any, Dict, List, Optional, Tuple


class SortMixin:
    """排序 Mixin"""

    def _build_sort_conditions(self, order_by: Optional[List[Dict[str, str]]]) -> List[Tuple[str, int]]:
        """构建排序条件"""
        if not order_by:
            return [("total_mv", -1)]

        sort_conditions = []
        for order in order_by:
            field = order.get("field")
            direction = order.get("direction", "desc")

            db_field = self.basic_fields.get(field) if hasattr(self, 'basic_fields') else field
            if not db_field:
                continue

            sort_direction = -1 if direction.lower() == "desc" else 1
            sort_conditions.append((db_field, sort_direction))

        return sort_conditions
