# -*- coding: utf-8 -*-
"""
组合管理模块

实现投资组合的创建、更新和管理，包括：
- 持仓管理
- 现金管理
- 订单处理
- T+1可用数量管理
"""

from typing import Dict, List, Optional, Any
from datetime import date, datetime
from decimal import Decimal

from .models import Order, Position, CashAccount, Trade, Side, OrderStatus
from .cost import TransactionCost
from tradingagents.utils.logging_init import get_logger

logger = get_logger("backtest.portfolio")


class Portfolio:
    """
    投资组合管理器

    管理回测过程中的持仓、现金和订单。
    """

    def __init__(self, initial_cash: float, cost_calculator: TransactionCost):
        """
        初始化投资组合

        Args:
            initial_cash: 初始资金
            cost_calculator: 交易成本计算器
        """
        self.initial_cash = initial_cash
        self.cash_account = CashAccount(initial_cash=initial_cash, cash=initial_cash)
        self.cost_calculator = cost_calculator

        # 持仓字典 {symbol: Position}
        self.positions: Dict[str, Position] = {}

        # 待处理订单列表
        self.pending_orders: List[Order] = []

        # 成交记录
        self.trades: List[Trade] = []

        # T+1 今日买入记录（用于更新明日可用数量）
        self.today_buys: Dict[str, int] = {}

        logger.info(f"💼 投资组合初始化: 初始资金={initial_cash:,.2f}元")

    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """
        获取组合总价值

        Args:
            current_prices: 当前价格字典 {symbol: price}

        Returns:
            总价值 = 现金 + 持仓市值
        """
        total_value = self.cash_account.cash

        for symbol, position in self.positions.items():
            if symbol in current_prices:
                position.update_price(current_prices[symbol])
                total_value += position.market_value

        return total_value

    def get_position(self, symbol: str) -> Optional[Position]:
        """获取指定股票的持仓"""
        return self.positions.get(symbol)

    def get_all_positions(self) -> Dict[str, Position]:
        """获取所有持仓"""
        return self.positions.copy()

    def submit_order(self, order: Order) -> bool:
        """
        提交订单

        Args:
            order: 订单对象

        Returns:
            是否提交成功
        """
        # 验证订单
        if order.side == Side.SELL:
            position = self.get_position(order.symbol)
            if not position or position.quantity == 0:
                logger.warning(f"⚠️ 卖出订单失败: {order.symbol} 无持仓")
                return False

        # 买入检查资金
        if order.side == Side.BUY:
            required_cash = order.quantity * (order.price or 0)
            estimated_commission = max(required_cash * self.cost_calculator.commission_rate,
                                       self.cost_calculator.min_commission)
            total_required = required_cash + estimated_commission

            if total_required > self.cash_account.cash:
                logger.warning(f"⚠️ 买入订单失败: 资金不足 "
                             f"(需要{total_required:,.2f}, 可用{self.cash_account.cash:,.2f})")
                return False

        self.pending_orders.append(order)
        logger.info(f"📝 订单已提交: {order.side.value} {order.symbol} "
                   f"{order.quantity}股 @{order.price or '市价'}")
        return True

    def execute_order(self, order: Order, fill_price: float,
                     market_snapshot: Any) -> Optional[Trade]:
        """
        执行订单

        Args:
            order: 待执行订单
            fill_price: 成交价格
            market_snapshot: 市场快照

        Returns:
            成交记录（如果成交成功）
        """
        # 计算交易成本
        cost_info = self.cost_calculator.calculate_total_cost(order, fill_price, order.quantity)

        # 创建成交记录
        trade = Trade(
            symbol=order.symbol,
            side=order.side,
            quantity=order.quantity,
            price=fill_price,
            amount=fill_price * order.quantity,
            commission=cost_info['commission'],
            stamp_duty=cost_info['stamp_duty'],
            trade_time=market_snapshot.date,
            order_id=order.order_id
        )

        # 更新持仓和现金
        if order.side == Side.BUY:
            self._process_buy(trade)
        else:
            self._process_sell(trade)

        # 更新订单状态
        order.status = OrderStatus.FILLED
        order.filled_quantity = order.quantity
        order.filled_price = fill_price
        order.filled_time = datetime.now()
        order.commission = trade.commission
        order.stamp_duty = trade.stamp_duty

        self.trades.append(trade)
        self.pending_orders.remove(order)

        logger.info(f"✅ 订单成交: {trade.side.value} {trade.symbol} "
                   f"{trade.quantity}股 @{trade.price:.2f} "
                   f"(佣金={trade.commission:.2f}, 印花税={trade.stamp_duty:.2f})")

        return trade

    def _process_buy(self, trade: Trade):
        """处理买入成交"""
        total_cost = trade.amount + trade.commission + trade.stamp_duty

        # 扣除现金
        self.cash_account.cash -= total_cost
        self.cash_account.commission_paid += trade.commission
        self.cash_account.stamp_duty_paid += trade.stamp_duty

        # 更新持仓
        if trade.symbol not in self.positions:
            self.positions[trade.symbol] = Position(symbol=trade.symbol)

        position = self.positions[trade.symbol]

        # 计算新的平均成本
        old_cost = position.avg_cost * position.quantity
        new_cost = old_cost + trade.amount
        new_quantity = position.quantity + trade.quantity
        position.avg_cost = new_cost / new_quantity if new_quantity > 0 else 0

        # 更新数量
        position.quantity += trade.quantity
        # 今日买入不可用（T+1）
        position.last_price = trade.price

        # 记录今日买入
        self.today_buys[trade.symbol] = self.today_buys.get(trade.symbol, 0) + trade.quantity

    def _process_sell(self, trade: Trade):
        """处理卖出成交"""
        total_proceeds = trade.amount - trade.commission - trade.stamp_duty

        # 增加现金
        self.cash_account.cash += total_proceeds
        self.cash_account.commission_paid += trade.commission
        self.cash_account.stamp_duty_paid += trade.stamp_duty

        # 更新持仓
        position = self.positions.get(trade.symbol)
        if position:
            # 计算已实现盈亏
            cost_basis = position.avg_cost * trade.quantity
            realized_pnl = trade.amount - cost_basis - trade.commission - trade.stamp_duty

            position.quantity -= trade.quantity
            position.available_quantity -= trade.quantity  # 先扣可用数量
            self.cash_account.realized_pnl += realized_pnl

            # 如果持仓清空，移除
            if position.quantity == 0:
                del self.positions[trade.symbol]

            logger.debug(f"💰 卖出盈亏: {realized_pnl:+,.2f}元")

    def update_available_quantity(self):
        """
        更新可用数量（T+1制度）

        每日开始时调用，将昨天的买入转为可用
        """
        for symbol, position in self.positions.items():
            # 昨天买入的数量今天可用
            if symbol in self.today_buys:
                position.available_quantity += self.today_buys[symbol]

        # 清空今日买入记录
        self.today_buys.clear()

        logger.debug("🔄 T+1可用数量已更新")

    def update_positions_price(self, prices: Dict[str, float]):
        """
        更新持仓价格

        Args:
            prices: 价格字典 {symbol: price}
        """
        total_unrealized_pnl = 0

        for symbol, position in self.positions.items():
            if symbol in prices:
                position.update_price(prices[symbol])
                total_unrealized_pnl += position.unrealized_pnl

        logger.debug(f"📊 持仓更新: 浮动盈亏={total_unrealized_pnl:+,.2f}元")

    def get_portfolio_summary(self, current_prices: Dict[str, float]) -> Dict[str, Any]:
        """
        获取组合摘要

        Args:
            current_prices: 当前价格字典

        Returns:
            组合摘要字典
        """
        total_value = self.get_total_value(current_prices)
        positions_value = total_value - self.cash_account.cash

        return {
            'total_value': total_value,
            'cash': self.cash_account.cash,
            'positions_value': positions_value,
            'positions_count': len(self.positions),
            'realized_pnl': self.cash_account.realized_pnl,
            'unrealized_pnl': sum(p.unrealized_pnl for p in self.positions.values()),
            'total_pnl': self.cash_account.realized_pnl +
                        sum(p.unrealized_pnl for p in self.positions.values()),
            'commission_paid': self.cash_account.commission_paid,
            'stamp_duty_paid': self.cash_account.stamp_duty_paid,
        }

    def cancel_pending_orders(self, symbol: Optional[str] = None):
        """
        取消待处理订单

        Args:
            symbol: 指定股票代码，None表示取消所有
        """
        if symbol:
            to_cancel = [o for o in self.pending_orders if o.symbol == symbol]
            for order in to_cancel:
                order.status = OrderStatus.CANCELLED
                self.pending_orders.remove(order)
            logger.info(f"🚫 已取消 {symbol} 的 {len(to_cancel)} 个订单")
        else:
            count = len(self.pending_orders)
            for order in self.pending_orders:
                order.status = OrderStatus.CANCELLED
            self.pending_orders.clear()
            logger.info(f"🚫 已取消所有待处理订单 ({count}个)")

    def get_exposure(self, current_prices: Dict[str, float]) -> Dict[str, float]:
        """
        获取组合暴露度

        Args:
            current_prices: 当前价格字典

        Returns:
            {
                'total_exposure': 总暴露度,
                'long_exposure': 多头暴露,
                'net_exposure': 净暴露,
            }
        """
        total_value = self.get_total_value(current_prices)
        if total_value == 0:
            return {'total_exposure': 0, 'long_exposure': 0, 'net_exposure': 0}

        long_value = sum(p.market_value for p in self.positions.values())

        return {
            'total_exposure': long_value / total_value,
            'long_exposure': long_value / total_value,
            'net_exposure': long_value / total_value,  # 仅做多时等于多头暴露
        }
