# -*- coding: utf-8 -*-
"""
TradingAgents-CN 回测引擎模块

提供专业的量化回测能力，支持A股市场特定约束。

核心组件:
- engine: 回测引擎核心
- models: 数据模型定义
- constraints: A股交易约束（T+1、涨跌停、停牌等）
- cost: 交易成本模型（佣金、印花税、滑点）
- metrics: 绩效指标计算（夏普、最大回撤、卡尔玛等）
- portfolio: 组合管理
- agent_adapter: 多智能体系统集成适配器

使用示例:
    from tradingagents.backtest import BacktestEngine, BacktestConfig
    from datetime import date

    config = BacktestConfig(
        start_date=date(2023, 1, 1),
        end_date=date(2023, 12, 31),
        initial_cash=1000000.0
    )

    engine = BacktestEngine(config)
    engine.load_data(['000001.SZ', '600000.SH'])
    result = engine.run(signal_generator)
    engine.print_result(result)
"""

__version__ = "1.0.0"

from .models import (
    BacktestConfig, BacktestResult, Order, Position,
    Trade, DailySnapshot, Side, OrderType, OrderStatus,
    MarketSnapshot, AStockInfo, CashAccount,
)
from .portfolio import Portfolio
from .metrics import PerformanceMetrics
from .constraints import AStockConstraints
from .cost import TransactionCost, MarketImpactCalculator
from .engine import BacktestEngine
from .data_loader import BacktestDataLoader
from .agent_adapter import AgentSignalAdapter, run_agent_backtest

__all__ = [
    # 核心引擎
    "BacktestEngine",

    # 数据模型
    "BacktestConfig",
    "BacktestResult",
    "Order",
    "Position",
    "Trade",
    "DailySnapshot",
    "Side",
    "OrderType",
    "OrderStatus",

    # 组件
    "Portfolio",
    "PerformanceMetrics",
    "AStockConstraints",
    "TransactionCost",
    "MarketImpactCalculator",

    # 集成
    "AgentSignalAdapter",
    "BacktestDataLoader",
    "run_agent_backtest",
]
