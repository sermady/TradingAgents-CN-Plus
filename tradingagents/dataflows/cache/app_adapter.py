#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
App 缓存读取适配器（TradingAgents -> app MongoDB 集合）
- 基本信息集合：stock_basic_info
- 行情集合：market_quotes

当启用 ta_use_app_cache 时，作为优先数据源；未命中部分由上层继续回退到直连数据源。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime

import pandas as pd
import logging

_logger = logging.getLogger("dataflows")

try:
    from tradingagents.config.database_manager import get_mongodb_client
except Exception:  # pragma: no cover - 弱依赖
    get_mongodb_client = None  # type: ignore

try:
    from tradingagents.dataflows.standardizers.stock_basic_standardizer import (
        standardize_stock_basic,
    )
except ImportError:
    standardize_stock_basic = None


BASICS_COLLECTION = "stock_basic_info"
QUOTES_COLLECTION = "market_quotes"


def _standardize_cached_data(doc: Dict[str, Any]) -> Dict[str, Any]:
    """标准化从缓存读取的数据"""
    if not doc:
        return {}

    if standardize_stock_basic:
        data_source = doc.get("data_source", "app_cache")
        return standardize_stock_basic(doc, data_source)

    code = doc.get("code") or doc.get("symbol", "")
    return {
        "code": code,
        "symbol": code,
        "name": doc.get("name", f"股票{code}"),
        "market": doc.get("market", "CN"),
        "exchange": doc.get("exchange", ""),
        "exchange_name": doc.get("exchange_name", ""),
        "area": doc.get("area", ""),
        "industry": doc.get("industry", ""),
        "list_date": doc.get("list_date", ""),
        "pe": doc.get("pe"),
        "pe_ttm": doc.get("pe_ttm"),
        "pb": doc.get("pb"),
        "total_mv": doc.get("total_mv"),
        "circ_mv": doc.get("circ_mv"),
        "turnover_rate": doc.get("turnover_rate"),
        "volume_ratio": doc.get("volume_ratio"),
        # 每股指标 (2026-02-02 新增)
        "eps": doc.get("eps"),
        "bps": doc.get("bps"),
        "ocfps": doc.get("ocfps"),
        "capital_rese_ps": doc.get("capital_rese_ps"),
        "undist_profit_ps": doc.get("undist_profit_ps"),
        # 同比增速指标 (2026-02-10 新增)
        "or_yoy": doc.get("or_yoy"),
        "q_profit_yoy": doc.get("q_profit_yoy"),
        "eps_yoy": doc.get("eps_yoy"),
        "roe_yoy": doc.get("roe_yoy"),
        "profit_dedt_yoy": doc.get("profit_dedt_yoy"),
        # 盈利能力指标 (2026-02-12 新增)
        "roe": doc.get("roe"),
        "roe_waa": doc.get("roe_waa"),
        "roe_dt": doc.get("roe_dt"),
        "roa": doc.get("roa"),
        "roa2": doc.get("roa2"),
        "grossprofit_margin": doc.get("grossprofit_margin"),
        "netprofit_margin": doc.get("netprofit_margin"),
        # 偿债能力指标 (2026-02-12 新增)
        "debt_to_assets": doc.get("debt_to_assets"),
        "current_ratio": doc.get("current_ratio"),
        "quick_ratio": doc.get("quick_ratio"),
        "cash_ratio": doc.get("cash_ratio"),
        # 营运能力指标 (2026-02-12 新增)
        "inv_turn": doc.get("inv_turn"),
        "ar_turn": doc.get("ar_turn"),
        "assets_turn": doc.get("assets_turn"),
        "data_source": doc.get("data_source", "app_cache"),
        "data_version": doc.get("data_version", 1),
        "last_sync": doc.get("last_sync", datetime.now().isoformat()),
    }


def get_basics_from_cache(
    stock_code: Optional[str] = None,
) -> Optional[Dict[str, Any] | List[Dict[str, Any]]]:
    """从 app 的 stock_basic_info 读取基础信息。"""
    if get_mongodb_client is None:
        return None
    client = get_mongodb_client()
    if not client:
        return None
    try:
        db_name = None
        try:
            from tradingagents.config.database_manager import get_database_manager  # type: ignore

            db_name = get_database_manager().mongodb_config.get(
                "database", "tradingagents"
            )
        except Exception:
            db_name = "tradingagents"
        db = client[db_name]
        coll = db[BASICS_COLLECTION]
        if stock_code:
            code6 = str(stock_code).zfill(6)
            try:
                _logger.debug(
                    f"[app_cache] 查询基础信息 | db={db_name} coll={BASICS_COLLECTION} code={code6}"
                )
            except Exception:
                pass
            doc = coll.find_one({"$or": [{"symbol": code6}, {"code": code6}]})
            if not doc:
                try:
                    _logger.debug(
                        f"[app_cache] 基础信息未命中 | db={db_name} coll={BASICS_COLLECTION} code={code6}"
                    )
                except Exception:
                    pass
                return None
            return _standardize_cached_data(doc)
        else:
            cursor = coll.find({})
            docs = list(cursor)
            if not docs:
                return None
            return [_standardize_cached_data(doc) for doc in docs]
    except Exception as e:
        try:
            _logger.debug(f"[app_cache] 基础信息读取异常（忽略）: {e}")
        except Exception:
            pass
        return None


def get_market_quote_dataframe(symbol: str) -> Optional[pd.DataFrame]:
    """从 app 的 market_quotes 读取单只股票的最新一条快照，并转为 DataFrame。"""
    if get_mongodb_client is None:
        return None
    client = get_mongodb_client()
    if not client:
        return None
    try:
        # 获取数据库
        from tradingagents.config.database_manager import get_database_manager  # type: ignore

        db_name = get_database_manager().mongodb_config.get("database", "tradingagents")
        db = client[db_name]
        coll = db[QUOTES_COLLECTION]
        code = str(symbol).zfill(6)
        try:
            _logger.debug(
                f"[app_cache] 查询行情 | db={db_name} coll={QUOTES_COLLECTION} code={code}"
            )
        except Exception:
            pass
        doc = coll.find_one({"code": code})
        if not doc:
            try:
                _logger.debug(
                    f"[app_cache] 行情未命中 | db={db_name} coll={QUOTES_COLLECTION} code={code}"
                )
            except Exception:
                pass
            return None
        # 构造 DataFrame，字段对齐 tushare 标准化映射
        # 🔧 FIX: Convert trade_date to datetime
        # MongoDB stores trade_date as YYYY-MM-DD string format
        trade_date = doc.get("trade_date")
        if trade_date:
            # Try YYYY-MM-DD format first (MongoDB format)
            if (
                isinstance(trade_date, str)
                and len(trade_date) == 10
                and trade_date[4] == "-"
            ):
                date_obj = pd.to_datetime(
                    trade_date, format="%Y-%m-%d", errors="coerce"
                )
                date_display = trade_date
            # Try YYYYMMDD format (alternative format)
            elif isinstance(trade_date, str) and len(str(trade_date)) == 8:
                date_obj = pd.to_datetime(
                    str(trade_date), format="%Y%m%d", errors="coerce"
                )
                date_display = (
                    date_obj.strftime("%Y-%m-%d") if pd.notna(date_obj) else trade_date
                )
            else:
                date_obj = pd.to_datetime(trade_date, errors="coerce")
                date_display = trade_date
        else:
            date_display = trade_date
            date_obj = None

        row = {
            "code": code,
            "date": date_display,
            "date_dt": date_obj,  # Add datetime column for proper sorting
            "open": doc.get("open"),
            "high": doc.get("high"),
            "low": doc.get("low"),
            "close": doc.get("close"),
            "volume": doc.get("volume"),
            "amount": doc.get("amount"),
            "pct_chg": doc.get("pct_chg"),
            "change": None,
        }
        df = pd.DataFrame([row])
        return df
    except Exception as e:
        try:
            _logger.debug(f"[app_cache] 行情读取异常（忽略）: {e}")
        except Exception:
            pass
        return None
