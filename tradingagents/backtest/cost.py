# -*- coding: utf-8 -*-
"""
交易成本模型模块

实现A股市场的交易成本计算，包括：
- 佣金（双向收取，最低5元）
- 印花税（仅卖方收取，千分之一）
- 过户费（双向收取，万分之0.2）
- 滑点成本（非线性模型）
"""

from typing import Tuple, Dict, Any
from decimal import Decimal, ROUND_HALF_UP

from .models import Order, Trade, Side
from tradingagents.utils.logging_init import get_logger

logger = get_logger("backtest.cost")


class TransactionCost:
    """
    A股交易成本计算器

    费用结构（2024年标准）：
    1. 佣金：双向，万分之2.5-3，最低5元
    2. 印花税：仅卖方，千分之一（0.1%）
    3. 过户费：双向，万分之0.2（仅沪市）
    """

    def __init__(self, config: Any):
        """
        初始化交易成本计算器

        Args:
            config: 回测配置
        """
        self.commission_rate = config.commission_rate       # 佣金率（默认万三）
        self.min_commission = config.min_commission         # 最低佣金（默认5元）
        self.stamp_duty_rate = config.stamp_duty_rate       # 印花税率（默认千分之一）
        self.slippage_rate = config.slippage_rate           # 滑点率（默认千分之一）

        logger.info(f"💰 交易成本配置: 佣金={self.commission_rate*10000:.1f}‰, "
                   f"印花税={self.stamp_duty_rate*1000:.1f}‰(卖), "
                   f"滑点={self.slippage_rate*1000:.1f}‰")

    def calculate_buy_cost(self, price: float, quantity: int,
                           market_snapshot: Any = None) -> Tuple[float, float, float]:
        """
        计算买入成本

        买入费用 = 佣金 + 过户费
        注意：买入不收印花税

        Args:
            price: 成交价格
            quantity: 成交数量
            market_snapshot: 市场快照（用于计算滑点）

        Returns:
            (总费用, 佣金, 印花税)
        """
        amount = price * quantity

        # 计算佣金
        commission = max(amount * self.commission_rate, self.min_commission)

        # 买入无印花税
        stamp_duty = 0.0

        # 过户费（简化处理，实际仅沪市收取）
        transfer_fee = amount * 0.00002  # 万分之0.2

        total_cost = commission + stamp_duty + transfer_fee

        logger.debug(f"买入费用计算: 金额={amount:.2f}, 佣金={commission:.2f}, "
                    f"印花税={stamp_duty:.2f}, 过户费={transfer_fee:.2f}, 总计={total_cost:.2f}")

        return total_cost, commission, stamp_duty

    def calculate_sell_cost(self, price: float, quantity: int,
                            market_snapshot: Any = None) -> Tuple[float, float, float]:
        """
        计算卖出成本

        卖出费用 = 佣金 + 印花税 + 过户费
        印花税仅卖方收取（千分之一）

        Args:
            price: 成交价格
            quantity: 成交数量
            market_snapshot: 市场快照（用于计算滑点）

        Returns:
            (总费用, 佣金, 印花税)
        """
        amount = price * quantity

        # 计算佣金
        commission = max(amount * self.commission_rate, self.min_commission)

        # 计算印花税（仅卖方）
        stamp_duty = amount * self.stamp_duty_rate

        # 过户费
        transfer_fee = amount * 0.00002  # 万分之0.2

        total_cost = commission + stamp_duty + transfer_fee

        logger.debug(f"卖出费用计算: 金额={amount:.2f}, 佣金={commission:.2f}, "
                    f"印花税={stamp_duty:.2f}, 过户费={transfer_fee:.2f}, 总计={total_cost:.2f}")

        return total_cost, commission, stamp_duty

    def calculate_total_cost(self, order: Order, fill_price: float,
                            fill_quantity: int) -> Dict[str, float]:
        """
        计算交易总成本

        Args:
            order: 订单
            fill_price: 成交价格
            fill_quantity: 成交数量

        Returns:
            费用字典 {
                'commission': 佣金,
                'stamp_duty': 印花税,
                'transfer_fee': 过户费,
                'total_cost': 总成本
            }
        """
        amount = fill_price * fill_quantity

        if order.side == Side.BUY:
            cost, commission, stamp_duty = self.calculate_buy_cost(fill_price, fill_quantity)
        else:
            cost, commission, stamp_duty = self.calculate_sell_cost(fill_price, fill_quantity)

        # 过户费
        transfer_fee = amount * 0.00002

        return {
            'commission': commission,
            'stamp_duty': stamp_duty,
            'transfer_fee': transfer_fee,
            'total_cost': cost
        }

    def estimate_slippage(self, order: Order, market_snapshot: Any) -> float:
        """
        估算滑点成本

        A股滑点特点：
        - 大盘股：约5-15bps
        - 中盘股：约15-25bps
        - 小盘股：约25-50bps
        - 微盘股：>100bps

        简化模型：基础滑点率 × 流动性因子

        Args:
            order: 订单
            market_snapshot: 市场快照

        Returns:
            估算的滑点比例
        """
        # 基础滑点
        base_slippage = self.slippage_rate

        # 根据换手率调整（换手率越高，流动性越好，滑点越小）
        if hasattr(market_snapshot, 'turnover_rate'):
            turnover = market_snapshot.turnover_rate
            if turnover > 5:  # 高换手
                liquidity_factor = 0.5
            elif turnover > 2:
                liquidity_factor = 0.8
            elif turnover > 1:
                liquidity_factor = 1.0
            else:  # 低换手，滑点更大
                liquidity_factor = 1.5
        else:
            liquidity_factor = 1.0

        # 根据订单金额调整（金额越大，滑点越大）
        amount = order.quantity * (order.price or market_snapshot.close)
        if amount > 10000000:  # >1000万
            size_factor = 2.0
        elif amount > 1000000:  # >100万
            size_factor = 1.3
        else:
            size_factor = 1.0

        estimated_slippage = base_slippage * liquidity_factor * size_factor

        logger.debug(f"滑点估算: 基础={self.slippage_rate*1000:.1f}‰, "
                    f"流动性因子={liquidity_factor}, "
                    f"规模因子={size_factor}, "
                    f"估算={estimated_slippage*1000:.1f}‰")

        return estimated_slippage


class MarketImpactCalculator:
    """
    市场冲击计算器（高级模型）

    大额交易会对价格产生影响，Almgren-Chriss模型的简化实现。
    """

    def __init__(self, config: Any):
        self.config = config
        self.max_volume_ratio = config.max_volume_ratio  # 最大成交量占比

    def calculate_market_impact(self, order_quantity: int, daily_volume: int,
                                order_side: Side) -> float:
        """
        计算市场冲击

        简化公式：
        impact = a * (Q/V)^b

        其中：
        - Q: 订单数量
        - V: 日成交量
        - a: 冲击系数（约0.1-1.0，取决于股票流动性）
        - b: 幂指数（约0.5-1.0）

        Args:
            order_quantity: 订单数量
            daily_volume: 日成交量
            order_side: 订单方向

        Returns:
            市场冲击比例（价格变动百分比）
        """
        if daily_volume == 0:
            return 0.01  # 无成交量时默认1%冲击

        volume_ratio = order_quantity / daily_volume

        # 超过流动性限制，拒绝交易
        if volume_ratio > self.max_volume_ratio:
            logger.warning(f"订单量占成交量比例过高: {volume_ratio*100:.1f}% > {self.max_volume_ratio*100:.1f}%")
            return float('inf')  # 表示无法成交

        # 市场冲击模型（简化版Almgren-Chriss）
        # a = 0.5 (中等流动性股票)
        # b = 0.5 (平方根影响)
        a = 0.5
        b = 0.5

        impact = a * (volume_ratio ** b)

        # 买入推高价格，卖出压低价格
        if order_side == Side.BUY:
            return impact
        else:
            return -impact
