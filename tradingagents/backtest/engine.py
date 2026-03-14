# -*- coding: utf-8 -*-
"""
核心回测引擎

提供完整的量化回测能力，支持：
- 历史数据回放
- 订单执行模拟
- A股交易约束
- 绩效指标计算
"""

from typing import Dict, List, Optional, Any, Callable
from datetime import date, datetime, timedelta
from pathlib import Path
import json

import pandas as pd
import numpy as np

from .models import (
    BacktestConfig, BacktestResult, Order, Trade, Side, OrderStatus,
    Position, DailySnapshot, MarketSnapshot, AStockInfo
)
from .portfolio import Portfolio
from .constraints import AStockConstraints
from .cost import TransactionCost, MarketImpactCalculator
from .metrics import PerformanceMetrics
from tradingagents.utils.logging_init import get_logger

logger = get_logger("backtest.engine")


class BacktestEngine:
    """
    A股量化回测引擎

    核心功能：
    1. 加载历史数据
    2. 执行交易策略
    3. 应用A股交易约束
    4. 计算交易成本
    5. 生成绩效报告
    """

    def __init__(self, config: BacktestConfig):
        """
        初始化回测引擎

        Args:
            config: 回测配置
        """
        self.config = config

        # 初始化组件
        self.cost_calculator = TransactionCost(config)
        self.constraints = AStockConstraints(config)
        self.portfolio = Portfolio(config.initial_cash, self.cost_calculator)
        self.metrics_calculator = PerformanceMetrics()
        self.impact_calculator = MarketImpactCalculator(config)

        # 数据存储
        self.price_data: Dict[str, pd.DataFrame] = {}  # {symbol: OHLCV DataFrame}
        self.stock_info: Dict[str, AStockInfo] = {}    # 股票信息
        self.daily_snapshots: List[DailySnapshot] = []

        # 信号生成器（与多智能体系统集成）
        self.signal_generator: Optional[Callable] = None

        logger.info("🚀 回测引擎初始化完成")
        logger.info(f"   回测期间: {config.start_date} ~ {config.end_date}")
        logger.info(f"   初始资金: {config.initial_cash:,.2f}元")

    # ==================== 数据加载 ====================

    def load_data(self, symbols: List[str], data_source: Optional[Any] = None):
        """
        加载历史数据

        使用 BacktestDataLoader 直接从 Provider 层获取原始 DataFrame，
        支持 MongoDB 缓存 → Tushare → AKShare → BaoStock 自动降级。

        Args:
            symbols: 股票代码列表（6位纯数字，如 '000001'）
            data_source: 自定义数据源（可选，传入则跳过默认加载器）
        """
        if data_source is not None:
            # 用户提供了自定义数据源
            self._load_from_custom_source(symbols, data_source)
            return

        from .data_loader import BacktestDataLoader

        loader = BacktestDataLoader()
        self.price_data = loader.load_symbols(
            symbols, self.config.start_date, self.config.end_date
        )

        logger.info(f"✅ 数据加载完成: {len(self.price_data)}/{len(symbols)} 只股票")

    def load_dataframe(self, symbol: str, df: pd.DataFrame):
        """
        直接加载 DataFrame（用于单元测试或自定义数据）

        Args:
            symbol: 股票代码
            df: DataFrame，必须包含 date, open, high, low, close 列
        """
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
        self.price_data[symbol] = df
        logger.info(f"📥 直接加载 {symbol}: {len(df)} 条记录")

    def _load_from_custom_source(self, symbols: List[str], data_source: Any):
        """从自定义数据源加载"""
        logger.info(f"📥 从自定义数据源加载 {len(symbols)} 只股票")
        for symbol in symbols:
            try:
                df = data_source.get_daily_data(
                    symbol=symbol,
                    start_date=self.config.start_date,
                    end_date=self.config.end_date
                )
                if df is not None and not df.empty:
                    self.price_data[symbol] = df
            except Exception as e:
                logger.warning(f"  ❌ {symbol}: {e}")

    # ==================== 回测执行 ====================

    def run(self, signal_generator: Optional[Callable] = None) -> BacktestResult:
        """
        运行回测

        Args:
            signal_generator: 信号生成函数
                接收参数: (当前日期, 组合状态, 市场数据)
                返回: 订单列表

        Returns:
            回测结果
        """
        self.signal_generator = signal_generator

        logger.info("=" * 60)
        logger.info("🎬 开始回测")
        logger.info("=" * 60)

        start_time = datetime.now()

        # 获取交易日期列表
        trading_dates = self._get_trading_dates()
        logger.info(f"📅 交易日数量: {len(trading_dates)}")

        # 逐日回放
        for i, trade_date in enumerate(trading_dates, 1):
            self._process_trading_day(trade_date, i, len(trading_dates))

        # 计算绩效指标
        result = self._generate_result(start_time, datetime.now())

        logger.info("=" * 60)
        logger.info("✅ 回测完成")
        logger.info("=" * 60)

        return result

    def _get_trading_dates(self) -> List[date]:
        """获取交易日期列表"""
        all_dates = set()

        for df in self.price_data.values():
            if 'date' in df.columns:
                dates = df['date'].dt.date.unique()
                all_dates.update(dates)

        trading_dates = sorted(all_dates)
        return trading_dates

    def _process_trading_day(self, trade_date: date, current: int, total: int):
        """
        处理单个交易日

        Args:
            trade_date: 交易日期
            current: 当前天数
            total: 总天数
        """
        logger.debug(f"📅 [{current}/{total}] {trade_date}")

        # 1. 更新T+1可用数量（每日开始时执行）
        self.portfolio.update_available_quantity()

        # 2. 获取当日市场数据
        market_data = self._get_market_snapshot(trade_date)

        # 3. 更新持仓价格
        current_prices = {symbol: data['close'] for symbol, data in market_data.items()}
        self.portfolio.update_positions_price(current_prices)

        # 4. 生成交易信号
        if self.signal_generator:
            orders = self.signal_generator(trade_date, self.portfolio, market_data)
            if orders:
                for order in orders:
                    self.portfolio.submit_order(order)

        # 5. 执行待处理订单
        self._execute_pending_orders(trade_date, market_data)

        # 6. 记录每日快照
        self._record_daily_snapshot(trade_date, current_prices)

    def _get_market_snapshot(self, trade_date: date) -> Dict[str, Any]:
        """获取市场快照数据"""
        market_data = {}

        for symbol, df in self.price_data.items():
            # 查找当日数据
            mask = df['date'].dt.date == trade_date
            if mask.any():
                row = df[mask].iloc[0]
                market_data[symbol] = row

        return market_data

    def _execute_pending_orders(self, trade_date: date, market_data: Dict[str, Any]):
        """执行待处理订单"""
        if not self.portfolio.pending_orders:
            return

        logger.debug(f"   📋 待处理订单: {len(self.portfolio.pending_orders)}个")

        # 复制列表，避免在迭代时修改
        orders = list(self.portfolio.pending_orders)

        for order in orders:
            if order.symbol not in market_data:
                # 无市场数据，无法执行
                order.status = OrderStatus.REJECTED
                order.reason = "无市场数据"
                self.portfolio.pending_orders.remove(order)
                continue

            row = market_data[order.symbol]

            # 创建市场快照
            snapshot = MarketSnapshot(
                symbol=order.symbol,
                date=trade_date,
                open=row.get('open', 0),
                high=row.get('high', 0),
                low=row.get('low', 0),
                close=row.get('close', 0),
                pre_close=row.get('pre_close', row.get('close', 0)),
                volume=row.get('volume', 0),
                amount=row.get('amount', 0),
                turnover_rate=row.get('turnover_rate', 0)
            )

            # 检查约束
            can_execute, reason = self.constraints.can_execute_order(
                order,
                self.portfolio.get_position(order.symbol) or Position(symbol=order.symbol),
                snapshot
            )

            if not can_execute:
                order.status = OrderStatus.REJECTED
                order.reason = reason
                self.portfolio.pending_orders.remove(order)
                logger.debug(f"   ❌ 订单被拒绝: {reason}")
                continue

            # 计算执行价格（考虑滑点）
            fill_price, can_fill = self.constraints.adjust_execution_price(
                order, snapshot, self.config.slippage_rate
            )

            if not can_fill:
                order.status = OrderStatus.REJECTED
                order.reason = "价格限制（涨跌停）"
                self.portfolio.pending_orders.remove(order)
                continue

            # 执行订单
            self.portfolio.execute_order(order, fill_price, snapshot)

    def _record_daily_snapshot(self, trade_date: date, current_prices: Dict[str, float]):
        """记录每日快照"""
        summary = self.portfolio.get_portfolio_summary(current_prices)

        # 计算日收益率
        daily_return = 0.0
        if self.daily_snapshots:
            prev_value = self.daily_snapshots[-1].total_value
            daily_return = (summary['total_value'] - prev_value) / prev_value if prev_value > 0 else 0

        snapshot = DailySnapshot(
            date=trade_date,
            total_value=summary['total_value'],
            cash=summary['cash'],
            positions_value=summary['positions_value'],
            daily_pnl=summary['total_pnl'],
            daily_return=daily_return,
            positions=self.portfolio.get_all_positions().copy()
        )

        # 计算回撤
        if self.daily_snapshots:
            peak = max(s.total_value for s in self.daily_snapshots)
            snapshot.drawdown = (peak - snapshot.total_value) / peak if peak > 0 else 0

        self.daily_snapshots.append(snapshot)

    # ==================== 结果生成 ====================

    def _generate_result(self, start_time: datetime, end_time: datetime) -> BacktestResult:
        """生成回测结果"""
        # 计算绩效指标
        metrics = self.metrics_calculator.calculate_all_metrics(
            self.daily_snapshots,
            self.portfolio.trades,
            self.config.initial_cash
        )

        result = BacktestResult(
            config=self.config,
            total_return=metrics.get('total_return', 0),
            annual_return=metrics.get('annual_return', 0),
            sharpe_ratio=metrics.get('sharpe_ratio', 0),
            sortino_ratio=metrics.get('sortino_ratio', 0),
            calmar_ratio=metrics.get('calmar_ratio', 0),
            max_drawdown=metrics.get('max_drawdown', 0),
            win_rate=metrics.get('win_rate', 0),
            profit_loss_ratio=metrics.get('profit_loss_ratio', 0),
            total_trades=metrics.get('total_trades', 0),
            profitable_trades=metrics.get('profitable_trades', 0),
            losing_trades=metrics.get('losing_trades', 0),
            avg_trade_pnl=metrics.get('avg_trade_pnl', 0),
            equity_curve=[s.total_value for s in self.daily_snapshots],
            daily_snapshots=self.daily_snapshots.copy(),
            trades=self.portfolio.trades.copy(),
            start_time=start_time,
            end_time=end_time,
            elapsed_seconds=(end_time - start_time).total_seconds()
        )

        return result

    def print_result(self, result: BacktestResult):
        """打印回测结果"""
        metrics = {
            'total_return': result.total_return,
            'annual_return': result.annual_return,
            'volatility': np.std([s.daily_return for s in result.daily_snapshots]) * np.sqrt(252),
            'max_drawdown': result.max_drawdown,
            'sharpe_ratio': result.sharpe_ratio,
            'sortino_ratio': result.sortino_ratio,
            'calmar_ratio': result.calmar_ratio,
            'win_rate': result.win_rate,
            'profit_loss_ratio': result.profit_loss_ratio,
            'total_trades': result.total_trades,
            'win_days': sum(1 for s in result.daily_snapshots if s.daily_return > 0),
            'lose_days': sum(1 for s in result.daily_snapshots if s.daily_return < 0),
            'win_day_pct': sum(1 for s in result.daily_snapshots if s.daily_return > 0) / len(result.daily_snapshots) if result.daily_snapshots else 0,
        }

        summary = self.metrics_calculator.format_metrics_summary(metrics)
        print(summary)

    def save_result(self, result: BacktestResult, filepath: str):
        """保存回测结果到文件"""
        data = {
            'config': {
                'start_date': str(self.config.start_date),
                'end_date': str(self.config.end_date),
                'initial_cash': self.config.initial_cash,
            },
            'metrics': {
                'total_return': result.total_return,
                'annual_return': result.annual_return,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'win_rate': result.win_rate,
            },
            'equity_curve': result.equity_curve,
            'trades_count': len(result.trades),
        }

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"💾 结果已保存: {filepath}")
        self.unrealized_pnl = 0
        self.last_price = 0
