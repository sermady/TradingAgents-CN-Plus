# -*- coding: utf-8 -*-
"""
量化风险指标计算器 (P1-2)

从历史价格数据计算专业的量化风险指标，注入风险辩论 prompt，
替代纯 LLM 文本辩论中缺乏的定量分析。

指标:
- VaR (95%/99%): Value at Risk
- CVaR (ES): Conditional VaR / Expected Shortfall
- 最大回撤 (MDD): Maximum Drawdown
- 年化波动率: Annualized Volatility
- Beta (vs 沪深300): 系统性风险
- Sharpe Ratio: 风险调整后收益
- 下行波动率: Downside Deviation
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional

from tradingagents.utils.logging_init import get_logger

logger = get_logger("quant_risk")


@dataclass(frozen=True)
class RiskMetrics:
    """量化风险指标结果 (不可变)"""

    # Value at Risk
    var_95: Optional[float] = None  # 95% VaR (日收益率)
    var_99: Optional[float] = None  # 99% VaR (日收益率)

    # Expected Shortfall
    cvar_95: Optional[float] = None  # 95% CVaR
    cvar_99: Optional[float] = None  # 99% CVaR

    # 波动性
    annualized_volatility: Optional[float] = None  # 年化波动率
    downside_volatility: Optional[float] = None  # 下行波动率

    # 回撤
    max_drawdown: Optional[float] = None  # 最大回撤
    max_drawdown_duration: Optional[int] = None  # 最大回撤持续天数

    # 相对指标
    beta: Optional[float] = None  # Beta (vs benchmark)
    sharpe_ratio: Optional[float] = None  # Sharpe Ratio

    # 元数据
    data_days: int = 0  # 使用的数据天数
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "var_95": self.var_95,
            "var_99": self.var_99,
            "cvar_95": self.cvar_95,
            "cvar_99": self.cvar_99,
            "annualized_volatility": self.annualized_volatility,
            "downside_volatility": self.downside_volatility,
            "max_drawdown": self.max_drawdown,
            "max_drawdown_duration": self.max_drawdown_duration,
            "beta": self.beta,
            "sharpe_ratio": self.sharpe_ratio,
            "data_days": self.data_days,
            "warnings": list(self.warnings),
        }

    def format_for_prompt(self) -> str:
        """格式化为可注入 LLM prompt 的文本"""
        lines = ["=== 量化风险指标 ==="]

        if self.data_days < 20:
            lines.append(f"⚠️ 数据仅 {self.data_days} 天，指标可靠性较低")
            lines.append("")

        if self.var_95 is not None:
            lines.append(f"VaR(95%): {self.var_95:.2%} (日)")
            lines.append(f"  含义: 在95%置信度下，单日最大亏损不超过 {abs(self.var_95):.2%}")
        if self.var_99 is not None:
            lines.append(f"VaR(99%): {self.var_99:.2%} (日)")

        if self.cvar_95 is not None:
            lines.append(f"CVaR(95%): {self.cvar_95:.2%}")
            lines.append(f"  含义: 当亏损超过VaR时，平均亏损为 {abs(self.cvar_95):.2%}")

        if self.annualized_volatility is not None:
            lines.append(f"年化波动率: {self.annualized_volatility:.2%}")
            vol = self.annualized_volatility
            if vol < 0.15:
                lines.append("  评级: 低波动")
            elif vol < 0.30:
                lines.append("  评级: 中等波动")
            elif vol < 0.50:
                lines.append("  评级: 高波动")
            else:
                lines.append("  评级: 极高波动")

        if self.downside_volatility is not None:
            lines.append(f"下行波动率: {self.downside_volatility:.2%}")

        if self.max_drawdown is not None:
            lines.append(f"最大回撤: {self.max_drawdown:.2%}")
            if self.max_drawdown_duration is not None:
                lines.append(f"最大回撤持续天数: {self.max_drawdown_duration} 天")

        if self.beta is not None:
            lines.append(f"Beta (vs 沪深300): {self.beta:.3f}")
            if self.beta > 1.2:
                lines.append("  含义: 高于市场波动，进攻型")
            elif self.beta < 0.8:
                lines.append("  含义: 低于市场波动，防御型")
            else:
                lines.append("  含义: 接近市场波动")

        if self.sharpe_ratio is not None:
            lines.append(f"Sharpe Ratio (年化): {self.sharpe_ratio:.3f}")
            if self.sharpe_ratio > 1.0:
                lines.append("  评级: 优秀的风险调整收益")
            elif self.sharpe_ratio > 0.5:
                lines.append("  评级: 良好的风险调整收益")
            elif self.sharpe_ratio > 0:
                lines.append("  评级: 正收益但风险补偿不足")
            else:
                lines.append("  评级: 负收益")

        if self.warnings:
            lines.append("")
            lines.append("风险警告:")
            for w in self.warnings:
                lines.append(f"  - {w}")

        return "\n".join(lines)


class QuantRiskCalculator:
    """
    量化风险指标计算器

    纯数值计算，不依赖外部库 (仅使用 math/statistics)，
    避免引入 numpy/scipy 的硬性依赖。
    """

    # A股年化交易日
    TRADING_DAYS_PER_YEAR = 244

    # 无风险利率 (中国10年期国债收益率近似值)
    RISK_FREE_RATE = 0.025

    def calculate(
        self,
        prices: List[float],
        benchmark_prices: Optional[List[float]] = None,
    ) -> RiskMetrics:
        """
        计算量化风险指标

        Args:
            prices: 历史收盘价列表 (按时间正序，最旧在前)
            benchmark_prices: 基准(沪深300)收盘价列表 (同长度)

        Returns:
            RiskMetrics 不可变结果对象
        """
        warnings = []

        if not prices or len(prices) < 2:
            return RiskMetrics(
                data_days=len(prices) if prices else 0,
                warnings=["价格数据不足，无法计算风险指标"],
            )

        data_days = len(prices)
        if data_days < 20:
            warnings.append(f"仅 {data_days} 天数据，指标统计意义有限 (建议至少 60 天)")

        # 计算日收益率
        returns = self._calculate_returns(prices)

        # VaR (历史模拟法)
        var_95 = self._calculate_var(returns, 0.05)
        var_99 = self._calculate_var(returns, 0.01)

        # CVaR (Expected Shortfall)
        cvar_95 = self._calculate_cvar(returns, 0.05)
        cvar_99 = self._calculate_cvar(returns, 0.01)

        # 年化波动率
        ann_vol = self._calculate_annualized_volatility(returns)

        # 下行波动率
        downside_vol = self._calculate_downside_volatility(returns)

        # 最大回撤
        mdd, mdd_duration = self._calculate_max_drawdown(prices)

        # Beta (需要基准数据)
        beta = None
        if benchmark_prices and len(benchmark_prices) == len(prices):
            benchmark_returns = self._calculate_returns(benchmark_prices)
            beta = self._calculate_beta(returns, benchmark_returns)

        # Sharpe Ratio
        sharpe = self._calculate_sharpe_ratio(returns)

        # 风险警告
        if mdd is not None and mdd < -0.20:
            warnings.append(f"最大回撤达 {mdd:.1%}，历史风险较高")
        if ann_vol is not None and ann_vol > 0.40:
            warnings.append(f"年化波动率 {ann_vol:.1%}，属于高波动股票")
        if beta is not None and beta > 1.5:
            warnings.append(f"Beta {beta:.2f}，系统性风险敞口较大")

        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            cvar_99=cvar_99,
            annualized_volatility=ann_vol,
            downside_volatility=downside_vol,
            max_drawdown=mdd,
            max_drawdown_duration=mdd_duration,
            beta=beta,
            sharpe_ratio=sharpe,
            data_days=data_days,
            warnings=warnings,
        )

    # ==================== 内部计算方法 ====================

    def _calculate_returns(self, prices: List[float]) -> List[float]:
        """计算日对数收益率"""
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] > 0 and prices[i] > 0:
                returns.append(math.log(prices[i] / prices[i - 1]))
            else:
                returns.append(0.0)
        return returns

    def _calculate_var(self, returns: List[float], alpha: float) -> Optional[float]:
        """历史模拟法 VaR"""
        if len(returns) < 10:
            return None
        sorted_returns = sorted(returns)
        index = int(len(sorted_returns) * alpha)
        index = max(0, min(index, len(sorted_returns) - 1))
        return sorted_returns[index]

    def _calculate_cvar(self, returns: List[float], alpha: float) -> Optional[float]:
        """Expected Shortfall (CVaR)"""
        if len(returns) < 10:
            return None
        sorted_returns = sorted(returns)
        cutoff = int(len(sorted_returns) * alpha)
        cutoff = max(1, cutoff)
        tail = sorted_returns[:cutoff]
        return sum(tail) / len(tail) if tail else None

    def _calculate_annualized_volatility(self, returns: List[float]) -> Optional[float]:
        """年化波动率"""
        if len(returns) < 5:
            return None
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        daily_vol = math.sqrt(variance)
        return daily_vol * math.sqrt(self.TRADING_DAYS_PER_YEAR)

    def _calculate_downside_volatility(self, returns: List[float]) -> Optional[float]:
        """下行波动率 (仅计算负收益)"""
        negative_returns = [r for r in returns if r < 0]
        if len(negative_returns) < 3:
            return None
        variance = sum(r ** 2 for r in negative_returns) / len(negative_returns)
        daily_downside = math.sqrt(variance)
        return daily_downside * math.sqrt(self.TRADING_DAYS_PER_YEAR)

    def _calculate_max_drawdown(
        self, prices: List[float]
    ) -> tuple[Optional[float], Optional[int]]:
        """最大回撤及持续天数"""
        if len(prices) < 2:
            return None, None

        peak = prices[0]
        max_dd = 0.0
        peak_idx = 0
        trough_idx = 0
        max_dd_duration = 0

        for i, price in enumerate(prices):
            if price > peak:
                peak = price
                peak_idx = i
            drawdown = (price - peak) / peak if peak > 0 else 0
            if drawdown < max_dd:
                max_dd = drawdown
                trough_idx = i
                max_dd_duration = trough_idx - peak_idx

        return max_dd, max_dd_duration

    def _calculate_beta(
        self, returns: List[float], benchmark_returns: List[float]
    ) -> Optional[float]:
        """Beta = Cov(Ri, Rm) / Var(Rm)"""
        n = min(len(returns), len(benchmark_returns))
        if n < 10:
            return None

        r = returns[:n]
        b = benchmark_returns[:n]
        mean_r = sum(r) / n
        mean_b = sum(b) / n

        cov = sum((r[i] - mean_r) * (b[i] - mean_b) for i in range(n)) / (n - 1)
        var_b = sum((b[i] - mean_b) ** 2 for i in range(n)) / (n - 1)

        return cov / var_b if var_b > 0 else None

    def _calculate_sharpe_ratio(self, returns: List[float]) -> Optional[float]:
        """年化 Sharpe Ratio"""
        if len(returns) < 20:
            return None

        mean_daily = sum(returns) / len(returns)
        variance = sum((r - mean_daily) ** 2 for r in returns) / (len(returns) - 1)
        std_daily = math.sqrt(variance)

        if std_daily == 0:
            return None

        ann_return = mean_daily * self.TRADING_DAYS_PER_YEAR
        ann_std = std_daily * math.sqrt(self.TRADING_DAYS_PER_YEAR)

        return (ann_return - self.RISK_FREE_RATE) / ann_std


# 全局实例
_calculator = None


def get_quant_risk_calculator() -> QuantRiskCalculator:
    """获取 QuantRiskCalculator 单例"""
    global _calculator
    if _calculator is None:
        _calculator = QuantRiskCalculator()
    return _calculator
