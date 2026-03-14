# -*- coding: utf-8 -*-
"""
多智能体系统集成适配器

将多智能体系统的决策信号转换为回测引擎可执行的订单。
"""

from typing import Dict, List, Any, Optional
from datetime import date

from .models import Order, Side, OrderType
from .engine import BacktestEngine
from tradingagents.utils.logging_init import get_logger

logger = get_logger("backtest.agent_adapter")


class AgentSignalAdapter:
    """
    智能体信号适配器

    将多智能体系统的决策转换为可执行的订单。
    """

    def __init__(self, backtest_engine: BacktestEngine):
        """
        初始化适配器

        Args:
            backtest_engine: 回测引擎实例
        """
        self.engine = backtest_engine
        self.signal_cache: Dict[str, Dict[str, Any]] = {}  # 缓存信号

    def parse_agent_decision(self, decision: Dict[str, Any],
                            current_date: date,
                            portfolio_state: Any) -> List[Order]:
        """
        解析智能体决策，生成订单

        Args:
            decision: 智能体决策字典
                {
                    'action': '买入/持有/卖出',
                    'target_price': float,
                    'confidence': float,
                    'risk_score': float,
                    'symbol': str,
                    'quantity': int (可选)
                }
            current_date: 当前日期
            portfolio_state: 组合状态

        Returns:
            订单列表
        """
        orders = []
        action = decision.get('action', '')
        symbol = decision.get('symbol', '')

        if not symbol or action == '持有':
            return orders

        # 获取目标价格
        target_price = decision.get('target_price')

        # 确定数量
        quantity = self._calculate_quantity(
            decision,
            portfolio_state,
            symbol
        )

        if quantity <= 0:
            return orders

        # 确定订单方向
        if action == '买入':
            side = Side.BUY
        elif action == '卖出':
            side = Side.SELL
        else:
            logger.warning(f"未知的动作类型: {action}")
            return orders

        # 创建订单
        order = Order(
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT if target_price else OrderType.MARKET,
            quantity=quantity,
            price=target_price
        )

        orders.append(order)

        logger.info(f"📊 信号转订单: {action} {symbol} {quantity}股 "
                   f"@{target_price or '市价'} (置信度={decision.get('confidence', 0):.2f})")

        return orders

    def _calculate_quantity(self, decision: Dict[str, Any],
                           portfolio_state: Any,
                           symbol: str) -> int:
        """
        计算订单数量

        策略：
        - 买入：基于可用现金和目标仓位
        - 卖出：基于当前持仓

        Args:
            decision: 决策字典
            portfolio_state: 组合状态
            symbol: 股票代码

        Returns:
            数量（股，必须是100的整数倍）
        """
        action = decision.get('action', '')
        quantity = decision.get('quantity')

        # 如果决策中指定了数量，直接使用
        if quantity:
            # 调整为100的整数倍
            return (quantity // 100) * 100

        total_value = portfolio_state.get_total_value({})

        if action == '买入':
            # 根据置信度决定仓位
            confidence = decision.get('confidence', 0.5)
            risk_score = decision.get('risk_score', 0.5)

            # 基础仓位 = 置信度 × 风险调整系数
            base_position_pct = confidence * (1 - risk_score * 0.5)

            # 最大单只股票仓位限制
            max_pct = self.engine.config.max_position_pct
            position_pct = min(base_position_pct, max_pct)

            # 计算目标金额
            target_amount = total_value * position_pct

            # 获取目标价格
            target_price = decision.get('target_price')
            if not target_price or target_price <= 0:
                # 使用当前价格
                position = portfolio_state.get_position(symbol)
                target_price = position.last_price if position else 0

            if target_price <= 0:
                logger.warning(f"⚠️ {symbol} 价格无效，无法计算数量")
                return 0

            # 计算数量（考虑预留手续费）
            estimated_cost = target_price * 100 * (1 + 0.0003)  # 预估万三佣金
            max_shares = int(portfolio_state.cash_account.cash / estimated_cost)

            # 目标数量
            target_shares = int(target_amount / target_price)

            # 取较小值，且是100的整数倍
            quantity = min(max_shares, target_shares)
            quantity = (quantity // 100) * 100

            return max(0, quantity)

        elif action == '卖出':
            # 卖出全部持仓
            position = portfolio_state.get_position(symbol)
            if position:
                return position.available_quantity
            return 0

        return 0

    def create_signal_generator(self, agent_graph: Any,
                              symbols: List[str]):
        """
        创建信号生成器函数

        将多智能体图包装为回测引擎可用的信号生成器。

        Args:
            agent_graph: TradingAgentsGraph 实例
            symbols: 股票列表

        Returns:
            信号生成函数
        """
        def signal_generator(trade_date: date, portfolio: Any,
                           market_data: Dict[str, Any]) -> List[Order]:
            """
            回测信号生成器

            在每个交易日调用，生成当天的交易信号。

            Args:
                trade_date: 交易日期
                portfolio: 当前组合状态
                market_data: 市场数据

            Returns:
                订单列表
            """
            all_orders = []

            for symbol in symbols:
                # 检查是否有市场数据
                if symbol not in market_data:
                    continue

                # 检查是否已缓存当日信号
                cache_key = f"{symbol}_{trade_date}"
                if cache_key in self.signal_cache:
                    decision = self.signal_cache[cache_key]
                else:
                    # 调用多智能体系统生成决策
                    try:
                        final_state, decision = agent_graph.propagate(
                            company_name=symbol,
                            trade_date=trade_date
                        )

                        # 缓存决策
                        self.signal_cache[cache_key] = decision

                    except Exception as e:
                        logger.error(f"❌ {symbol} {trade_date} 信号生成失败: {e}")
                        continue

                # 转换为订单
                orders = self.parse_agent_decision(
                    decision,
                    trade_date,
                    portfolio
                )

                all_orders.extend(orders)

            return all_orders

        return signal_generator


# 简化的使用示例函数

def run_agent_backtest(
    agent_graph: Any,
    symbols: List[str],
    start_date: date,
    end_date: date,
    initial_cash: float = 1000000.0
) -> Dict[str, Any]:
    """
    运行基于智能体的回测

    Args:
        agent_graph: TradingAgentsGraph 实例
        symbols: 股票列表
        start_date: 回测开始日期
        end_date: 回测结束日期
        initial_cash: 初始资金

    Returns:
        回测结果摘要
    """
    from .models import BacktestConfig
    from .engine import BacktestEngine

    # 创建回测配置
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_cash=initial_cash
    )

    # 创建回测引擎
    engine = BacktestEngine(config)

    # 加载数据
    engine.load_data(symbols)

    # 创建信号适配器
    adapter = AgentSignalAdapter(engine)

    # 创建信号生成器
    signal_gen = adapter.create_signal_generator(agent_graph, symbols)

    # 运行回测
    result = engine.run(signal_gen)

    # 打印结果
    engine.print_result(result)

    return result
