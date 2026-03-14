# -*- coding: utf-8 -*-
"""
回测引擎数据模型

定义回测过程中使用的核心数据结构。
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal


class Side(str, Enum):
    """订单方向"""
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """订单类型"""
    MARKET = "market"      # 市价单
    LIMIT = "limit"        # 限价单
    STOP = "stop"          # 止损单


class OrderStatus(str, Enum):
    """订单状态"""
    PENDING = "pending"        # 待执行
    FILLED = "filled"          # 已成交
    PARTIAL = "partial"        # 部分成交
    CANCELLED = "cancelled"    # 已取消
    REJECTED = "rejected"      # 已拒绝
    EXPIRED = "expired"        # 已过期


@dataclass
class Order:
    """订单数据结构"""
    symbol: str                          # 股票代码
    side: Side                           # 买卖方向
    order_type: OrderType                # 订单类型
    quantity: int                        # 数量（股）
    price: Optional[float] = None        # 限价（限价单）
    stop_price: Optional[float] = None   # 止损价（止损单）
    create_time: datetime = field(default_factory=datetime.now)
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0             # 已成交数量
    filled_price: Optional[float] = None # 成交价格
    filled_time: Optional[datetime] = None
    commission: float = 0.0              # 手续费
    stamp_duty: float = 0.0              # 印花税
    reason: Optional[str] = None         # 拒绝原因
    order_id: Optional[str] = None

    def __post_init__(self):
        if self.order_id is None:
            self.order_id = f"{self.symbol}_{self.create_time.strftime('%Y%m%d%H%M%S%f')}"


@dataclass
class Position:
    """持仓数据结构"""
    symbol: str                          # 股票代码
    quantity: int = 0                    # 持仓数量（股）
    available_quantity: int = 0          # 可用数量（股）
    avg_cost: float = 0.0                # 平均成本
    market_value: float = 0.0            # 市值
    unrealized_pnl: float = 0.0          # 浮动盈亏
    last_price: float = 0.0              # 最新价

    def update_price(self, price: float):
        """更新最新价格，重新计算市值和浮动盈亏"""
        self.last_price = price
        self.market_value = self.quantity * price
        self.unrealized_pnl = (price - self.avg_cost) * self.quantity


@dataclass
class CashAccount:
    """现金账户"""
    initial_cash: float = 1000000.0      # 初始资金
    cash: float = 1000000.0              # 可用现金
    total_pnl: float = 0.0               # 总盈亏
    realized_pnl: float = 0.0            # 已实现盈亏
    commission_paid: float = 0.0         # 已付手续费
    stamp_duty_paid: float = 0.0         # 已付印花税

    @property
    def total_value(self) -> float:
        """总权益 = 现金 + 已实现盈亏"""
        return self.cash + self.realized_pnl


@dataclass
class Trade:
    """成交记录"""
    symbol: str
    side: Side
    quantity: int
    price: float
    amount: float                        # 成交金额
    commission: float                    # 手续费
    stamp_duty: float                    # 印花税
    trade_time: datetime
    order_id: Optional[str] = None


@dataclass
class DailySnapshot:
    """每日快照（用于计算绩效指标）"""
    date: date
    total_value: float                   # 总权益
    cash: float                          # 现金
    positions_value: float               # 持仓市值
    daily_pnl: float                     # 日盈亏
    daily_return: float                  # 日收益率
    positions: Dict[str, Position] = field(default_factory=dict)
    drawdown: float = 0.0                # 回撤


@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: date
    end_date: date
    initial_cash: float = 1000000.0

    # 交易成本配置
    commission_rate: float = 0.0003      # 佣金率（万三）
    min_commission: float = 5.0          # 最低佣金
    stamp_duty_rate: float = 0.001       # 印花税率（千分之一，仅卖方）
    slippage_rate: float = 0.001         # 滑点率（千分之一）

    # A股特定约束
    t_plus_one: bool = True              # T+1交易制度
    limit_up_threshold: float = 0.10     # 涨停阈值（10%）
    limit_down_threshold: float = 0.10   # 跌停阈值（10%）
    st_limit_threshold: float = 0.05     # ST股涨跌幅（5%）

    # 风险控制
    max_position_pct: float = 0.30       # 单只股票最大仓位
    max_total_position_pct: float = 0.95 # 最大总仓位
    stop_loss_pct: Optional[float] = None  # 止损比例

    # 执行配置
    execute_at: str = "close"            # 执行价格：open/close/vwap
    price_adjustment: str = "none"       # 复权方式：none/qfq/hfq

    # 流动性约束
    max_volume_ratio: float = 0.10       # 最大成交量占比（10%）


@dataclass
class BacktestResult:
    """回测结果"""
    config: BacktestConfig

    # 绩效指标
    total_return: float = 0.0            # 总收益率
    annual_return: float = 0.0           # 年化收益率
    sharpe_ratio: float = 0.0            # 夏普比率
    sortino_ratio: float = 0.0           # 索提诺比率
    calmar_ratio: float = 0.0            # 卡尔玛比率
    max_drawdown: float = 0.0            # 最大回撤
    win_rate: float = 0.0                # 胜率
    profit_loss_ratio: float = 0.0       # 盈亏比

    # 交易统计
    total_trades: int = 0                # 总交易次数
    profitable_trades: int = 0           # 盈利交易次数
    losing_trades: int = 0               # 亏损交易次数
    avg_trade_pnl: float = 0.0           # 平均交易盈亏
    avg_holding_period: float = 0.0      # 平均持仓天数

    # 路径数据
    equity_curve: List[float] = field(default_factory=list)
    daily_snapshots: List[DailySnapshot] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)

    # 元数据
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    elapsed_seconds: float = 0.0


# A股特定数据模型

@dataclass
class AStockInfo:
    """A股股票信息"""
    symbol: str
    name: str
    list_date: date
    delist_date: Optional[date] = None
    is_st: bool = False                  # 是否ST
    is_suspend: bool = False             # 是否停牌
    limit_up_price: Optional[float] = None   # 涨停价
    limit_down_price: Optional[float] = None # 跌停价

    def update_limits(self, pre_close: float):
        """根据昨收价更新涨跌停价"""
        if self.is_st:
            self.limit_up_price = pre_close * (1 + 0.05)
            self.limit_down_price = pre_close * (1 - 0.05)
        else:
            # 主板10%，创业板/科创板20%
            self.limit_up_price = pre_close * (1 + 0.10)  # 简化处理
            self.limit_down_price = pre_close * (1 - 0.10)


@dataclass
class MarketSnapshot:
    """市场快照（特定时点的行情数据）"""
    symbol: str
    date: date
    open: float
    high: float
    low: float
    close: float
    pre_close: float
    volume: float                        # 成交量（股）
    amount: float                        # 成交额（元）
    turnover_rate: float = 0.0           # 换手率
    is_limit_up: bool = False            # 是否涨停
    is_limit_down: bool = False          # 是否跌停
    is_suspend: bool = False             # 是否停牌

    def check_limit_status(self, limit_up: float, limit_down: float):
        """检查涨跌停状态"""
        self.is_limit_up = abs(self.close - limit_up) < 0.01
        self.is_limit_down = abs(self.close - limit_down) < 0.01
