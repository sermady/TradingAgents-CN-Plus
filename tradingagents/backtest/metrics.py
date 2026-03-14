# -*- coding: utf-8 -*-
"""
绩效指标计算模块

提供全面的量化绩效指标计算，包括：
- 收益率指标（总收益、年化收益）
- 风险指标（波动率、最大回撤、下行风险）
- 风险调整收益（夏普、索提诺、卡尔玛）
- 交易统计（胜率、盈亏比、平均持仓期）
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime
from scipy import stats

from .models import DailySnapshot, Trade, BacktestResult
from tradingagents.utils.logging_init import get_logger

logger = get_logger("backtest.metrics")


class PerformanceMetrics:
    """
    量化绩效指标计算器

    提供全面的策略绩效评估，符合量化行业标准。
    """

    def __init__(self, risk_free_rate: float = 0.03):
        """
        初始化绩效计算器

        Args:
            risk_free_rate: 无风险利率（年化），默认3%
        """
        self.risk_free_rate = risk_free_rate
        self.daily_rf_rate = risk_free_rate / 252  # 日无风险利率

        logger.info(f"📊 绩效指标计算器初始化: 无风险利率={risk_free_rate*100:.1f}%")

    def calculate_all_metrics(self, snapshots: List[DailySnapshot],
                              trades: List[Trade],
                              initial_cash: float) -> Dict[str, Any]:
        """
        计算所有绩效指标

        Args:
            snapshots: 每日快照列表
            trades: 交易列表
            initial_cash: 初始资金

        Returns:
            绩效指标字典
        """
        if not snapshots:
            logger.warning("⚠️ 无快照数据，无法计算绩效指标")
            return self._empty_metrics()

        # 提取数据
        dates = [s.date for s in snapshots]
        equity = [s.total_value for s in snapshots]
        returns = [s.daily_return for s in snapshots]

        df = pd.DataFrame({
            'date': dates,
            'equity': equity,
            'returns': returns
        })

        # 计算各类指标
        metrics = {}

        # ========== 收益率指标 ==========
        metrics['total_return'] = self._calculate_total_return(equity, initial_cash)
        metrics['annual_return'] = self._calculate_annual_return(metrics['total_return'], len(snapshots))
        metrics['cumulative_returns'] = self._calculate_cumulative_returns(returns)

        # ========== 风险指标 ==========
        metrics['volatility'] = self._calculate_volatility(returns)
        metrics['downside_deviation'] = self._calculate_downside_deviation(returns)
        metrics['max_drawdown'] = self._calculate_max_drawdown(equity)
        metrics['avg_drawdown'] = self._calculate_avg_drawdown(equity)
        metrics['var_95'] = self._calculate_var(returns, confidence=0.95)
        metrics['cvar_95'] = self._calculate_cvar(returns, confidence=0.95)

        # ========== 风险调整收益 ==========
        metrics['sharpe_ratio'] = self._calculate_sharpe_ratio(returns)
        metrics['sortino_ratio'] = self._calculate_sortino_ratio(returns)
        metrics['calmar_ratio'] = self._calculate_calmar_ratio(metrics['annual_return'], metrics['max_drawdown'])
        metrics['information_ratio'] = self._calculate_information_ratio(returns)  # 需要基准

        # ========== 交易统计 ==========
        if trades:
            trade_metrics = self._calculate_trade_metrics(trades)
            metrics.update(trade_metrics)

        # ========== 胜负统计 ==========
        metrics['win_days'] = sum(1 for r in returns if r > 0)
        metrics['lose_days'] = sum(1 for r in returns if r < 0)
        metrics['win_day_pct'] = metrics['win_days'] / len(returns) if returns else 0

        # ========== 其他指标 ==========
        metrics['skewness'] = self._calculate_skewness(returns)
        metrics['kurtosis'] = self._calculate_kurtosis(returns)

        return metrics

    # ==================== 收益率指标 ====================

    def _calculate_total_return(self, equity: List[float], initial_cash: float) -> float:
        """计算总收益率"""
        if not equity or initial_cash == 0:
            return 0.0
        return (equity[-1] - initial_cash) / initial_cash

    def _calculate_annual_return(self, total_return: float, num_days: int) -> float:
        """计算年化收益率"""
        if num_days == 0:
            return 0.0
        years = num_days / 252
        if years == 0:
            return 0.0
        return (1 + total_return) ** (1 / years) - 1

    def _calculate_cumulative_returns(self, returns: List[float]) -> List[float]:
        """计算累计收益率"""
        cumulative = [1.0]
        for r in returns:
            cumulative.append(cumulative[-1] * (1 + r))
        return cumulative[1:]

    # ==================== 风险指标 ====================

    def _calculate_volatility(self, returns: List[float], annualize: bool = True) -> float:
        """
        计算波动率（标准差）

        Args:
            returns: 日收益率序列
            annualize: 是否年化
        """
        if not returns or len(returns) < 2:
            return 0.0
        vol = np.std(returns, ddof=1)
        if annualize:
            vol *= np.sqrt(252)
        return vol

    def _calculate_downside_deviation(self, returns: List[float],
                                     threshold: float = 0.0) -> float:
        """
        计算下行偏差（仅考虑负收益）

        Args:
            returns: 日收益率序列
            threshold: 阈值（默认0，即只考虑亏损）
        """
        if not returns:
            return 0.0
        downside = [r for r in returns if r < threshold]
        if not downside:
            return 0.0
        dd = np.std(downside, ddof=1) * np.sqrt(252)
        return dd

    def _calculate_max_drawdown(self, equity: List[float]) -> float:
        """
        计算最大回撤

        最大回撤 = max((峰值 - 当前值) / 峰值)
        """
        if not equity:
            return 0.0

        peak = equity[0]
        max_dd = 0.0

        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return max_dd

    def _calculate_avg_drawdown(self, equity: List[float]) -> float:
        """计算平均回撤"""
        if not equity:
            return 0.0

        drawdowns = []
        peak = equity[0]

        for value in equity:
            if value > peak:
                peak = value
            dd = (peak - value) / peak if peak > 0 else 0
            if dd > 0:
                drawdowns.append(dd)

        return np.mean(drawdowns) if drawdowns else 0.0

    def _calculate_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """
        计算VaR（风险价值）

        历史模拟法：在给定置信度下的最大损失
        """
        if not returns:
            return 0.0
        return np.percentile(returns, (1 - confidence) * 100)

    def _calculate_cvar(self, returns: List[float], confidence: float = 0.95) -> float:
        """
        计算CVaR（条件风险价值，也称为Expected Shortfall）

        超过VaR的平均损失
        """
        if not returns:
            return 0.0
        var = self._calculate_var(returns, confidence)
        tail_losses = [r for r in returns if r <= var]
        return np.mean(tail_losses) if tail_losses else var

    # ==================== 风险调整收益 ====================

    def _calculate_sharpe_ratio(self, returns: List[float]) -> float:
        """
        计算夏普比率

        Sharpe = (E[R] - Rf) / σ(R)
        """
        if not returns or len(returns) < 2:
            return 0.0

        mean_return = np.mean(returns) * 252  # 年化
        excess_return = mean_return - self.risk_free_rate
        volatility = self._calculate_volatility(returns)

        if volatility == 0:
            return 0.0

        return excess_return / volatility

    def _calculate_sortino_ratio(self, returns: List[float]) -> float:
        """
        计算索提诺比率

        Sortino = (E[R] - Rf) / σ_downside(R)
        只考虑下行波动
        """
        if not returns:
            return 0.0

        mean_return = np.mean(returns) * 252
        excess_return = mean_return - self.risk_free_rate
        downside_dev = self._calculate_downside_deviation(returns)

        if downside_dev == 0:
            return 0.0 if excess_return <= 0 else float('inf')

        return excess_return / downside_dev

    def _calculate_calmar_ratio(self, annual_return: float, max_drawdown: float) -> float:
        """
        计算卡尔玛比率

        Calmar = 年化收益 / 最大回撤
        """
        if max_drawdown == 0:
            return 0.0
        return annual_return / max_drawdown

    def _calculate_information_ratio(self, returns: List[float],
                                     benchmark_returns: Optional[List[float]] = None) -> float:
        """
        计算信息比率

        IR = (策略收益 - 基准收益) / 跟踪误差
        """
        if not returns:
            return 0.0

        # 如果没有提供基准收益，使用0作为基准
        if benchmark_returns is None:
            benchmark_returns = [0.0] * len(returns)
        elif len(benchmark_returns) != len(returns):
            logger.warning("基准收益长度与策略收益不一致，使用0基准")
            benchmark_returns = [0.0] * len(returns)

        excess_returns = [r - b for r, b in zip(returns, benchmark_returns)]

        if not excess_returns:
            return 0.0

        mean_excess = np.mean(excess_returns) * 252
        tracking_error = np.std(excess_returns, ddof=1) * np.sqrt(252)

        if tracking_error == 0:
            return 0.0

        return mean_excess / tracking_error

    # ==================== 交易统计 ====================

    def _calculate_trade_metrics(self, trades: List[Trade]) -> Dict[str, Any]:
        """
        计算交易相关指标
        """
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'profit_loss_ratio': 0.0,
                'avg_trade_pnl': 0.0,
            }

        # 按买卖配对计算盈亏（简化处理）
        buy_trades = {t.symbol: t for t in trades if t.side.value == 'buy'}
        sell_trades = {t.symbol: t for t in trades if t.side.value == 'sell'}

        pnls = []
        for symbol, buy_trade in buy_trades.items():
            if symbol in sell_trades:
                sell_trade = sell_trades[symbol]
                # 简化盈亏计算
                buy_cost = buy_trade.amount + buy_trade.commission + buy_trade.stamp_duty
                sell_revenue = sell_trade.amount - sell_trade.commission - sell_trade.stamp_duty
                pnl = sell_revenue - buy_cost
                pnls.append(pnl)

        if not pnls:
            return {
                'total_trades': len(trades),
                'win_rate': 0.0,
                'profit_loss_ratio': 0.0,
                'avg_trade_pnl': 0.0,
            }

        winning_trades = [p for p in pnls if p > 0]
        losing_trades = [p for p in pnls if p < 0]

        win_rate = len(winning_trades) / len(pnls) if pnls else 0
        avg_win = np.mean(winning_trades) if winning_trades else 0
        avg_loss = np.mean(losing_trades) if losing_trades else 0
        profit_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        return {
            'total_trades': len(trades),
            'profitable_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'avg_trade_pnl': np.mean(pnls),
            'gross_profit': sum(winning_trades),
            'gross_loss': sum(losing_trades),
        }

    # ==================== 其他指标 ====================

    def _calculate_skewness(self, returns: List[float]) -> float:
        """计算偏度（收益分布的不对称性）"""
        if not returns or len(returns) < 3:
            return 0.0
        return stats.skew(returns)

    def _calculate_kurtosis(self, returns: List[float]) -> float:
        """计算峰度（收益分布的尾部厚度）"""
        if not returns or len(returns) < 4:
            return 0.0
        return stats.kurtosis(returns, fisher=False)

    # ==================== 工具方法 ====================

    def _empty_metrics(self) -> Dict[str, Any]:
        """返回空指标字典"""
        return {
            'total_return': 0.0,
            'annual_return': 0.0,
            'volatility': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'win_rate': 0.0,
            'total_trades': 0,
        }

    def format_metrics_summary(self, metrics: Dict[str, Any]) -> str:
        """
        格式化绩效指标摘要

        Args:
            metrics: 绩效指标字典

        Returns:
            格式化的字符串
        """
        summary = f"""
╔═══════════════════════════════════════════════════════════════╗
║                        回测绩效报告                             ║
╚═══════════════════════════════════════════════════════════════╝

📈 收益指标
─────────────────────────────────────────────────────────────
  总收益率:      {metrics.get('total_return', 0)*100:8.2f}%
  年化收益率:    {metrics.get('annual_return', 0)*100:8.2f}%

⚠️  风险指标
─────────────────────────────────────────────────────────────
  波动率:        {metrics.get('volatility', 0)*100:8.2f}%
  最大回撤:      {metrics.get('max_drawdown', 0)*100:8.2f}%
  平均回撤:      {metrics.get('avg_drawdown', 0)*100:8.2f}%
  VaR (95%):     {metrics.get('var_95', 0)*100:8.2f}%
  CVaR (95%):    {metrics.get('cvar_95', 0)*100:8.2f}%

📊 风险调整收益
─────────────────────────────────────────────────────────────
  夏普比率:      {metrics.get('sharpe_ratio', 0):8.2f}
  索提诺比率:    {metrics.get('sortino_ratio', 0):8.2f}
  卡尔玛比率:    {metrics.get('calmar_ratio', 0):8.2f}

📋 交易统计
─────────────────────────────────────────────────────────────
  总交易次数:    {metrics.get('total_trades', 0):8d}
  胜率:          {metrics.get('win_rate', 0)*100:7.1f}%
  盈亏比:        {metrics.get('profit_loss_ratio', 0):8.2f}

📅 交易日统计
─────────────────────────────────────────────────────────────
  盈利天数:      {metrics.get('win_days', 0):8d}
  亏损天数:      {metrics.get('lose_days', 0):8d}
  胜日比例:      {metrics.get('win_day_pct', 0)*100:7.1f}%

📐 分布特征
─────────────────────────────────────────────────────────────
  偏度:          {metrics.get('skewness', 0):8.2f}
  峰度:          {metrics.get('kurtosis', 0):8.2f}
"""
        return summary
