# -*- coding: utf-8 -*-
"""结果格式化模块

提供查询结果格式化功能。
"""

from typing import Any, Dict


class FormatterMixin:
    """格式化 Mixin"""

    def _format_result(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """格式化查询结果，统一使用后端字段名"""
        code = doc.get("code", "")
        market_type = "A股"

        result = {
            "code": doc.get("code"),
            "name": doc.get("name"),
            "industry": doc.get("industry"),
            "area": doc.get("area"),
            "market": market_type,
            "board": doc.get("market"),
            "exchange": doc.get("sse"),
            "list_date": doc.get("list_date"),

            "total_mv": doc.get("total_mv"),
            "circ_mv": doc.get("circ_mv"),

            "pe": doc.get("pe"),
            "pb": doc.get("pb"),
            "pe_ttm": doc.get("pe_ttm"),
            "pb_mrq": doc.get("pb_mrq"),
            "roe": doc.get("roe"),

            "turnover_rate": doc.get("turnover_rate"),
            "volume_ratio": doc.get("volume_ratio"),

            "close": doc.get("close"),
            "pct_chg": doc.get("pct_chg"),
            "amount": doc.get("amount"),
            "volume": doc.get("volume"),
            "open": doc.get("open"),
            "high": doc.get("high"),
            "low": doc.get("low"),

            "ma20": None,
            "rsi14": None,
            "kdj_k": None,
            "kdj_d": None,
            "kdj_j": None,
            "dif": None,
            "dea": None,
            "macd_hist": None,

            "source": doc.get("source", "database"),
            "updated_at": doc.get("updated_at"),
        }

        return {k: v for k, v in result.items() if v is not None}
