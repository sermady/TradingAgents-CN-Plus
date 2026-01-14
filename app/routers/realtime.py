# -*- coding: utf-8 -*-
"""
实时行情相关 API

提供股票实时行情数据和市场状态查询功能
- 统一响应包: {success, data, message, timestamp}
- 所有端点均需鉴权 (Bearer Token)
- 路径前缀在 main.py 中挂载为 /api，当前路由自身前缀为 /realtime
"""
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
import logging

from app.routers.auth_db import get_current_user
from app.core.response import ok

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/realtime", tags=["realtime"])


# ==================== 请求/响应模型 ====================

class BatchQuoteRequest(BaseModel):
    """批量获取行情请求"""
    symbols: List[str] = Field(..., description="股票代码列表", min_length=1, max_length=50)
    market_type: str = Field(default="A股", description="市场类型: A股/港股/美股")


class RealtimeQuoteResponse(BaseModel):
    """实时行情响应"""
    symbol: str = Field(..., description="股票代码")
    name: Optional[str] = Field(None, description="股票名称")
    price: float = Field(..., description="当前/收盘价")
    change: float = Field(default=0.0, description="涨跌额")
    change_pct: float = Field(default=0.0, description="涨跌幅")
    open: Optional[float] = Field(None, description="开盘价")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    pre_close: Optional[float] = Field(None, description="昨收价")
    volume: Optional[float] = Field(None, description="成交量(股)")
    amount: Optional[float] = Field(None, description="成交额(元)")
    market_status: str = Field(default="unknown", description="市场状态")
    market_status_desc: str = Field(default="状态未知", description="市场状态描述")
    is_realtime: bool = Field(default=False, description="是否为实时数据")
    timestamp: str = Field(..., description="数据时间戳")
    source: str = Field(..., description="数据源")


class MarketStatusResponse(BaseModel):
    """市场状态响应"""
    market_type: str = Field(..., description="市场类型")
    status: str = Field(..., description="状态码: trading/pre_market/post_market/closed/lunch_break")
    status_desc: str = Field(..., description="状态描述")
    is_trading_day: bool = Field(..., description="是否交易日")
    next_session: Optional[Dict[str, str]] = Field(None, description="下一交易时段")


# ==================== API 端点 ====================

@router.get("/quote/{symbol}", response_model=dict)
async def get_realtime_quote(
    symbol: str,
    market_type: str = Query(default="A股", description="市场类型: A股/港股/美股"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取单只股票的实时行情

    参数：
    - symbol: 股票代码（6位数字，如 000001）
    - market_type: 市场类型（A股/港股/美股）

    返回：
    - 实时行情数据，包含价格、涨跌幅、成交量等
    - 市场状态信息（交易中/盘前/盘后/休市）
    """
    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        manager = get_data_source_manager()
        quote = manager.get_realtime_quote(symbol, market_type)

        if quote is None:
            raise HTTPException(
                status_code=404,
                detail=f"无法获取股票 {symbol} 的实时行情"
            )

        return ok(data=quote, message="获取实时行情成功")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取实时行情失败 {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quotes/batch", response_model=dict)
async def get_realtime_quotes_batch(
    request: BatchQuoteRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    批量获取股票实时行情

    参数：
    - symbols: 股票代码列表（最多50只）
    - market_type: 市场类型

    返回：
    - 成功获取的行情数据字典 {symbol: quote_data}
    - 获取失败的股票列表
    """
    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        manager = get_data_source_manager()

        results = {}
        failed = []

        for symbol in request.symbols:
            try:
                quote = manager.get_realtime_quote(symbol, request.market_type)
                if quote:
                    results[symbol] = quote
                else:
                    failed.append(symbol)
            except Exception as e:
                logger.warning(f"批量获取行情失败 {symbol}: {e}")
                failed.append(symbol)

        return ok(
            data={
                "quotes": results,
                "failed": failed,
                "success_count": len(results),
                "failed_count": len(failed)
            },
            message=f"成功获取 {len(results)} 只股票行情"
        )

    except Exception as e:
        logger.error(f"批量获取实时行情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-status", response_model=dict)
async def get_market_status(
    market_type: str = Query(default="A股", description="市场类型: A股/港股/美股"),
    current_user: dict = Depends(get_current_user)
):
    """
    获取市场状态

    参数：
    - market_type: 市场类型（A股/港股/美股）

    返回：
    - status: 状态码 (trading/pre_market/post_market/closed/lunch_break)
    - status_desc: 状态描述
    - is_trading_day: 是否交易日
    - next_session: 下一交易时段信息
    """
    try:
        from tradingagents.utils.trading_hours import (
            get_market_status as get_status,
            is_trading_day,
            get_next_trading_session
        )

        status, status_desc = get_status(market_type)
        trading_day = is_trading_day(market_type)
        next_session = get_next_trading_session(market_type)

        return ok(
            data={
                "market_type": market_type,
                "status": status,
                "status_desc": status_desc,
                "is_trading_day": trading_day,
                "next_session": {
                    "start": next_session[0],
                    "end": next_session[1]
                } if next_session else None
            },
            message="获取市场状态成功"
        )

    except Exception as e:
        logger.error(f"获取市场状态失败 {market_type}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/should-use-realtime", response_model=dict)
async def should_use_realtime(
    analysis_date: str = Query(..., description="分析日期 (YYYY-MM-DD 或 'today')"),
    market_type: str = Query(default="A股", description="市场类型"),
    current_user: dict = Depends(get_current_user)
):
    """
    判断是否应该使用实时数据

    根据以下条件判断：
    1. 分析日期是否是今天
    2. 当前是否在交易时段内
    3. 实时行情功能是否启用

    参数：
    - analysis_date: 分析日期
    - market_type: 市场类型

    返回：
    - should_use: 是否应使用实时数据
    - reason: 判断原因
    """
    try:
        from tradingagents.dataflows.data_source_manager import get_data_source_manager
        from tradingagents.utils.trading_hours import get_market_status, is_trading_hours
        from datetime import datetime

        manager = get_data_source_manager()
        should_use = manager.should_use_realtime_data(analysis_date, market_type)

        # 构建原因说明
        today = datetime.now().strftime("%Y-%m-%d")
        is_today = (analysis_date == "today" or analysis_date == today)
        is_trading = is_trading_hours(market_type)
        status, status_desc = get_market_status(market_type)

        if should_use:
            reason = f"分析日期是今天，且当前{status_desc}，使用实时数据"
        elif not is_today:
            reason = f"分析日期({analysis_date})不是今天，使用历史数据"
        else:
            reason = f"当前{status_desc}，使用收盘数据"

        return ok(
            data={
                "should_use": should_use,
                "reason": reason,
                "analysis_date": analysis_date,
                "is_today": is_today,
                "market_status": status,
                "market_status_desc": status_desc,
                "is_trading_hours": is_trading
            },
            message="判断完成"
        )

    except Exception as e:
        logger.error(f"判断实时数据使用失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
