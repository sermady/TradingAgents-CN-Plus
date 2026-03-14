# -*- coding: utf-8 -*-
"""
A股交易约束模块

实现中国A股市场的特定交易规则和约束，包括：
- T+1交易制度
- 涨跌停板限制
- 停牌处理
- ST股特殊限制
- 最小交易单位（100股=1手）
"""

from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP

from .models import Order, Position, MarketSnapshot, AStockInfo, Side, OrderStatus

# 导入日志模块
from tradingagents.utils.logging_init import get_logger

logger = get_logger("backtest.constraints")


class AStockConstraints:
    """
    A股交易约束管理器

    确保回测过程中的交易符合A股市场的实际规则。
    """

    # A股常量
    LOT_SIZE = 100                    # 最小交易单位（手）
    MIN_PRICE_TICK = 0.01             # 最小价格变动单位（元）

    def __init__(self, config: Any):
        """
        初始化约束管理器

        Args:
            config: 回测配置对象
        """
        self.config = config
        self.st_stocks: set = set()           # ST股票集合
        self.suspend_stocks: Dict[str, Tuple[date, date]] = {}  # 停牌股票 {symbol: (start, end)}
        self.delisted_stocks: set = set()     # 退市股票集合

        logger.info("✅ A股交易约束管理器初始化完成")

    def is_tradable(self, symbol: str, trade_date: date,
                    market_snapshot: Optional[MarketSnapshot] = None) -> Tuple[bool, str]:
        """
        检查股票在指定日期是否可交易

        Args:
            symbol: 股票代码
            trade_date: 交易日期
            market_snapshot: 市场快照（可选）

        Returns:
            (是否可交易, 原因说明)
        """
        # 检查是否退市
        if symbol in self.delisted_stocks:
            return False, f"股票{symbol}已退市"

        # 检查是否停牌
        if symbol in self.suspend_stocks:
            suspend_start, suspend_end = self.suspend_stocks[symbol]
            if suspend_start <= trade_date <= (suspend_end or date.max):
                return False, f"股票{symbol}停牌中"

        # 检查市场快照
        if market_snapshot:
            if market_snapshot.is_suspend:
                return False, f"股票{symbol}当日停牌"

        return True, "可交易"

    def can_execute_order(self, order: Order, current_position: Position,
                          market_snapshot: MarketSnapshot) -> Tuple[bool, str]:
        """
        检查订单是否可以执行（T+1、涨跌停等约束）

        Args:
            order: 待执行订单
            current_position: 当前持仓
            market_snapshot: 市场快照

        Returns:
            (是否可执行, 原因说明)
        """
        # 检查股票是否可交易
        tradable, reason = self.is_tradable(order.symbol, market_snapshot.date, market_snapshot)
        if not tradable:
            return False, reason

        # T+1检查：买入的股票当日不能卖出
        if order.side == Side.SELL:
            if not self._can_sell_today(order.symbol, current_position):
                return False, f"T+1限制：{order.symbol}今日不可卖出"

        # 涨跌停检查
        if not self._check_limit_constraint(order, market_snapshot):
            return False, self._get_limit_rejection_reason(order, market_snapshot)

        # 数量检查
        if not self._check_quantity_constraint(order, current_position):
            return False, "数量不足或不合规"

        return True, "可执行"

    def validate_order_quantity(self, symbol: str, quantity: int,
                                side: Side, current_position: Position) -> Tuple[bool, int, str]:
        """
        验证并调整订单数量（手数、卖出时可用数量等）

        Args:
            symbol: 股票代码
            quantity: 原始数量
            side: 买卖方向
            current_position: 当前持仓

        Returns:
            (是否有效, 调整后数量, 原因说明)
        """
        # 必须是100股的整数倍
        adjusted_qty = (quantity // self.LOT_SIZE) * self.LOT_SIZE

        if adjusted_qty == 0:
            return False, 0, f"数量必须≥{self.LOT_SIZE}股的整数倍"

        # 卖出数量不能超过可用数量
        if side == Side.SELL:
            if adjusted_qty > current_position.available_quantity:
                # 自动调整为最大可用数量（必须是100的倍数）
                max_available = (current_position.available_quantity // self.LOT_SIZE) * self.LOT_SIZE
                if max_available == 0:
                    return False, 0, "无可用持仓"
                adjusted_qty = max_available
                return True, adjusted_qty, f"数量已调整为最大可用持仓{adjusted_qty}股"

        return True, adjusted_qty, "数量有效"

    def calculate_frozen_cash(self, order: Order, market_snapshot: MarketSnapshot,
                             commission_rate: float) -> float:
        """
        计算买入订单所需冻结资金（T+1制度）

        Args:
            order: 订单
            market_snapshot: 市场快照
            commission_rate: 佣金率

        Returns:
            冻结资金金额
        """
        if order.side == Side.SELL:
            return 0.0

        # 使用限价或当前价
        price = order.price if order.price else market_snapshot.close
        amount = price * order.quantity

        # 预估佣金
        commission = max(amount * commission_rate, self.config.min_commission)

        return amount + commission

    def adjust_execution_price(self, order: Order, market_snapshot: MarketSnapshot,
                               slippage_rate: float) -> Tuple[float, bool]:
        """
        根据滑点和涨跌停调整执行价格

        Args:
            order: 订单
            market_snapshot: 市场快照
            slippage_rate: 滑点率

        Returns:
            (调整后价格, 是否执行成功)
        """
        base_price = order.price if order.price and order.order_type != "market" else market_snapshot.close

        # 买入滑点向上，卖出滑点向下
        if order.side == Side.BUY:
            adjusted_price = base_price * (1 + slippage_rate)
        else:
            adjusted_price = base_price * (1 - slippage_rate)

        # 价格精度调整
        adjusted_price = self._round_price(adjusted_price)

        # 涨跌停限制
        if order.side == Side.BUY and market_snapshot.is_limit_up:
            # 涨停板买入可能无法成交
            if adjusted_price >= market_snapshot.limit_up_price - 0.01:
                return adjusted_price, False  # 无法成交

        if order.side == Side.SELL and market_snapshot.is_limit_down:
            # 跌停板卖出可能无法成交
            if adjusted_price <= market_snapshot.limit_down_price + 0.01:
                return adjusted_price, False  # 无法成交

        # 检查是否超出涨跌停范围
        limit_up = market_snapshot.close * (1 + self.config.limit_up_threshold)
        limit_down = market_snapshot.close * (1 - self.config.limit_down_threshold)

        if adjusted_price > limit_up:
            adjusted_price = limit_up
        elif adjusted_price < limit_down:
            adjusted_price = limit_down

        return adjusted_price, True

    # ==================== 私有方法 ====================

    def _can_sell_today(self, symbol: str, position: Position) -> bool:
        """
        检查是否可以今日卖出（T+1规则）

        T+1规则：今天买入的股票，明天才能卖出
        """
        # 可用数量 = 总持仓 - 今日买入
        return position.available_quantity >= self.LOT_SIZE

    def _check_limit_constraint(self, order: Order,
                                market_snapshot: MarketSnapshot) -> bool:
        """
        检查涨跌停约束
        """
        # 涨停板通常不能买入（一字板）
        if order.side == Side.BUY and market_snapshot.is_limit_up:
            # 除非是限价单且价格等于涨停价（可能排队成交）
            if order.order_type == "limit" and order.price:
                return abs(order.price - market_snapshot.limit_up_price) < 0.02
            return False

        # 跌停板通常不能卖出（一字板）
        if order.side == Side.SELL and market_snapshot.is_limit_down:
            if order.order_type == "limit" and order.price:
                return abs(order.price - market_snapshot.limit_down_price) < 0.02
            return False

        return True

    def _get_limit_rejection_reason(self, order: Order,
                                    market_snapshot: MarketSnapshot) -> str:
        """获取涨跌停拒绝原因"""
        if market_snapshot.is_limit_up:
            return f"{order.symbol}已涨停，无法买入"
        if market_snapshot.is_limit_down:
            return f"{order.symbol}已跌停，无法卖出"
        return "价格限制"

    def _check_quantity_constraint(self, order: Order,
                                   current_position: Position) -> bool:
        """
        检查数量约束
        """
        # 买入：检查资金是否足够（在外部检查）
        # 卖出：检查持仓是否足够
        if order.side == Side.SELL:
            return order.quantity <= current_position.available_quantity

        return True

    def _round_price(self, price: float) -> float:
        """
        价格精度调整（A股最小变动单位0.01元）
        """
        return float(Decimal(str(price)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    # ==================== 公共方法 ====================

    def update_stock_status(self, symbol: str, status_info: Dict[str, Any]):
        """
        更新股票状态（ST、停牌等）

        Args:
            symbol: 股票代码
            status_info: 状态信息字典
                - is_st: 是否ST
                - suspend_start: 停牌开始日期
                - suspend_end: 停牌结束日期
                - is_delisted: 是否退市
        """
        if status_info.get('is_st'):
            self.st_stocks.add(symbol)
        else:
            self.st_stocks.discard(symbol)

        if status_info.get('suspend_start'):
            self.suspend_stocks[symbol] = (
                status_info['suspend_start'],
                status_info.get('suspend_end')
            )
        elif symbol in self.suspend_stocks:
            del self.suspend_stocks[symbol]

        if status_info.get('is_delisted'):
            self.delisted_stocks.add(symbol)

    def get_lot_size(self, symbol: str) -> int:
        """获取最小交易单位"""
        return self.LOT_SIZE

    def is_st_stock(self, symbol: str) -> bool:
        """检查是否为ST股票"""
        return symbol in self.st_stocks
