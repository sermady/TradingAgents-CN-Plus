# -*- coding: utf-8 -*-
"""
交易决策结构化 Schema (P0-2)

定义 Pydantic 模型用于 LLM 结构化输出，替代 regex 提取。
被 signal_processing.py 和 trader.py 共享使用。
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TradeAction(str, Enum):
    """交易动作枚举"""
    BUY = "买入"
    HOLD = "持有"
    SELL = "卖出"


class TradingDecision(BaseModel):
    """LLM 结构化输出的交易决策 Schema"""

    action: TradeAction = Field(
        description="投资建议：买入、持有或卖出"
    )
    target_price: Optional[float] = Field(
        default=None,
        description="目标价位（具体数值），买入时应高于当前价，卖出时应低于当前价"
    )
    target_price_range: Optional[str] = Field(
        default=None,
        description="目标价格区间，如 '¥30.00-33.00'，当无法确定具体价位时使用"
    )
    confidence: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="决策置信度 (0-1)，1 表示完全确信"
    )
    risk_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="风险评分 (0-1)，1 表示极高风险"
    )
    reasoning: str = Field(
        default="基于综合分析的投资建议",
        description="决策的主要理由摘要（中文）"
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, v):
        """自动处理百分比形式的置信度"""
        if isinstance(v, (int, float)) and v > 1:
            return v / 100.0
        return float(v) if v is not None else 0.7

    @field_validator("risk_score", mode="before")
    @classmethod
    def normalize_risk_score(cls, v):
        """自动处理百分比形式的风险评分"""
        if isinstance(v, (int, float)) and v > 1:
            return v / 100.0
        return float(v) if v is not None else 0.5

    def to_signal_dict(self) -> dict:
        """转换为 SignalProcessor 兼容的 dict 格式"""
        return {
            "action": self.action.value,
            "target_price": self.target_price,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "reasoning": self.reasoning,
        }

    def to_extract_dict(self) -> dict:
        """转换为 extract_trading_decision 兼容的 dict 格式"""
        return {
            "recommendation": self.action.value,
            "target_price": self.target_price,
            "target_price_range": self.target_price_range,
            "confidence": self.confidence,
            "risk_score": self.risk_score,
            "warnings": [],
        }
