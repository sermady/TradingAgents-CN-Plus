# -*- coding: utf-8 -*-
"""
执行层风险拦截网关 (Phase 3.1)

在交易决策执行前进行风险检查，包括：
- 仓位集中度检查（单一标的≤30%，板块≤50%）
- 目标价合理性检查（涨跌停限制）
- 置信度与风险一致性检查
- 流动性检查
"""

import os
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""

    LOW = "low"  # 低风险
    MEDIUM = "medium"  # 中等风险
    HIGH = "high"  # 高风险
    CRITICAL = "critical"  # 严重风险


class CheckStatus(Enum):
    """检查状态"""

    PASSED = "passed"  # 通过
    WARNING = "warning"  # 警告
    BLOCKED = "blocked"  # 拦截


@dataclass
class CheckResult:
    """单个检查结果"""

    check_name: str
    status: CheckStatus
    passed: bool
    message: str
    risk_level: RiskLevel = RiskLevel.LOW
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeDecision:
    """交易决策数据"""

    symbol: str  # 股票代码
    action: str  # 买入/持有/卖出
    current_price: float  # 当前价格
    target_price: float  # 目标价格
    confidence: float  # 置信度 (0-1)
    risk_score: float  # 风险评分 (0-1)
    position_ratio: float = 0.0  # 建议仓位比例 (0-1)
    stop_loss: Optional[float] = None  # 止损价
    sector: Optional[str] = None  # 所属板块


@dataclass
class ValidationResult:
    """验证结果"""

    passed: bool
    blocked: bool
    overall_risk_level: RiskLevel
    check_results: List[CheckResult]
    summary: str
    timestamp: str = field(default_factory=lambda: __import__("datetime").datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "overall_risk_level": self.overall_risk_level.value,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "check_results": [
                {
                    "check_name": r.check_name,
                    "status": r.status.value,
                    "passed": r.passed,
                    "message": r.message,
                    "risk_level": r.risk_level.value,
                    "details": r.details,
                }
                for r in self.check_results
            ],
        }


class ExecutionRiskGateway:
    """
    执行层风险拦截网关

    职责：
    1. 在交易决策执行前进行全面的风险检查
    2. 拦截违规或高风险的交易决策
    3. 记录风险检查结果用于后验验证
    """

    def __init__(self):
        # 风控参数配置 - 从环境变量读取，使用默认值作为后备
        self.config = {
            # 仓位集中度限制
            "max_single_position": float(os.getenv(
                "RISK_MAX_SINGLE_POSITION", "0.30"
            )),  # 单一标的最大30%
            "max_sector_position": float(os.getenv(
                "RISK_MAX_SECTOR_POSITION", "0.50"
            )),  # 单一板块最大50%
            # 涨跌停限制
            "limit_up_pct": float(os.getenv(
                "RISK_LIMIT_UP_PCT", "0.10"
            )),  # A股涨停10%
            "limit_down_pct": float(os.getenv(
                "RISK_LIMIT_DOWN_PCT", "0.10"
            )),  # A股跌停10%
            # 置信度要求
            "min_confidence": float(os.getenv(
                "RISK_MIN_CONFIDENCE", "0.5"
            )),  # 最低置信度50%
            "high_confidence_threshold": float(os.getenv(
                "RISK_HIGH_CONFIDENCE_THRESHOLD", "0.8"
            )),  # 高置信度阈值80%
            # 风险评分一致性检查
            "max_risk_score": float(os.getenv(
                "RISK_MAX_RISK_SCORE", "0.85"
            )),  # 最高风险评分85%
            # 目标价偏离限制
            "max_target_deviation": float(os.getenv(
                "RISK_MAX_TARGET_DEVIATION", "0.50"
            )),  # 目标价偏离当前价最大50%
        }

        # 记录配置加载（仅记录非敏感的配置项）
        logger.info(
            f"[ExecutionRiskGateway] 风控配置加载成功: "
            f"单仓上限={self.config['max_single_position']:.1%}, "
            f"板块上限={self.config['max_sector_position']:.1%}, "
            f"最低置信度={self.config['min_confidence']:.1%}"
        )

    def validate_trade_decision(
        self,
        decision: TradeDecision,
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        验证交易决策

        Args:
            decision: 交易决策
            context: 额外上下文信息（如当前持仓、板块分布等）

        Returns:
            ValidationResult: 验证结果
        """
        check_results: List[CheckResult] = []

        # 执行各项风险检查
        checks = [
            self._check_position_concentration(decision, context),
            self._check_target_price_reasonable(decision),
            self._check_confidence_risk_consistency(decision),
            self._check_confidence_threshold(decision),
            self._check_max_risk_score(decision),
            self._check_liquidity(decision, context),
        ]

        for check in checks:
            if check:  # 可能返回None如果检查不适用
                check_results.append(check)

        # 确定整体结果
        blocked = any(r.status == CheckStatus.BLOCKED for r in check_results)
        warnings = any(r.status == CheckStatus.WARNING for r in check_results)
        passed = not blocked and all(r.passed for r in check_results)

        # 确定整体风险等级
        if any(r.risk_level == RiskLevel.CRITICAL for r in check_results):
            overall_risk = RiskLevel.CRITICAL
        elif any(r.risk_level == RiskLevel.HIGH for r in check_results):
            overall_risk = RiskLevel.HIGH
        elif any(r.risk_level == RiskLevel.MEDIUM for r in check_results):
            overall_risk = RiskLevel.MEDIUM
        else:
            overall_risk = RiskLevel.LOW

        # 生成摘要
        if blocked:
            blocked_checks = [r.check_name for r in check_results if r.status == CheckStatus.BLOCKED]
            summary = f"交易决策被拦截: {', '.join(blocked_checks)}"
        elif warnings:
            warning_checks = [r.check_name for r in check_results if r.status == CheckStatus.WARNING]
            summary = f"交易决策通过但有警告: {', '.join(warning_checks)}"
        else:
            summary = "交易决策通过所有风险检查"

        logger.info(f"[ExecutionRiskGateway] {summary}")

        return ValidationResult(
            passed=passed,
            blocked=blocked,
            overall_risk_level=overall_risk,
            check_results=check_results,
            summary=summary,
        )

    def _check_position_concentration(
        self, decision: TradeDecision, context: Optional[Dict[str, Any]]
    ) -> CheckResult:
        """
        检查仓位集中度

        - 单一标的≤30%
        - 单一板块≤50%
        """
        check_name = "仓位集中度检查"
        details = {}

        # 检查单一标的仓位
        position_ratio = decision.position_ratio
        max_single = self.config["max_single_position"]

        if position_ratio > max_single:
            return CheckResult(
                check_name=check_name,
                status=CheckStatus.BLOCKED,
                passed=False,
                message=f"单一标的仓位{position_ratio:.1%}超过限制{max_single:.1%}",
                risk_level=RiskLevel.CRITICAL,
                details={"position_ratio": position_ratio, "max_allowed": max_single},
            )

        # 检查板块集中度（如果有上下文）
        if context and "sector_positions" in context:
            sector = decision.sector
            if sector:
                current_sector_ratio = context["sector_positions"].get(sector, 0)
                total_sector_ratio = current_sector_ratio + position_ratio
                max_sector = self.config["max_sector_position"]

                if total_sector_ratio > max_sector:
                    return CheckResult(
                        check_name=check_name,
                        status=CheckStatus.BLOCKED,
                        passed=False,
                        message=f"板块{sector}仓位{total_sector_ratio:.1%}超过限制{max_sector:.1%}",
                        risk_level=RiskLevel.CRITICAL,
                        details={
                            "sector": sector,
                            "current_ratio": current_sector_ratio,
                            "new_ratio": total_sector_ratio,
                            "max_allowed": max_sector,
                        },
                    )

        return CheckResult(
            check_name=check_name,
            status=CheckStatus.PASSED,
            passed=True,
            message=f"仓位集中度检查通过({position_ratio:.1%})",
            risk_level=RiskLevel.LOW,
            details={"position_ratio": position_ratio},
        )

    def _check_target_price_reasonable(self, decision: TradeDecision) -> CheckResult:
        """
        检查目标价合理性

        - 目标价必须在涨跌停范围内（A股±10%）
        - 目标价偏离当前价不能超过50%
        """
        check_name = "目标价合理性检查"

        current_price = decision.current_price
        target_price = decision.target_price

        if current_price <= 0:
            return CheckResult(
                check_name=check_name,
                status=CheckStatus.BLOCKED,
                passed=False,
                message="当前价格无效",
                risk_level=RiskLevel.CRITICAL,
                details={"current_price": current_price},
            )

        # 计算涨跌停价格（A股）
        limit_up = current_price * (1 + self.config["limit_up_pct"])
        limit_down = current_price * (1 - self.config["limit_down_pct"])

        # 检查目标价是否在涨跌停范围内
        if not (limit_down <= target_price <= limit_up):
            action_msg = "高于涨停价" if target_price > limit_up else "低于跌停价"
            return CheckResult(
                check_name=check_name,
                status=CheckStatus.BLOCKED,
                passed=False,
                message=f"目标价{target_price:.2f}{action_msg}({limit_down:.2f}-{limit_up:.2f})",
                risk_level=RiskLevel.CRITICAL,
                details={
                    "current_price": current_price,
                    "target_price": target_price,
                    "limit_up": limit_up,
                    "limit_down": limit_down,
                },
            )

        # 检查目标价偏离度
        deviation = abs(target_price - current_price) / current_price
        max_deviation = self.config["max_target_deviation"]

        if deviation > max_deviation:
            return CheckResult(
                check_name=check_name,
                status=CheckStatus.WARNING,
                passed=True,
                message=f"目标价偏离当前价{deviation:.1%}，超过建议阈值{max_deviation:.1%}",
                risk_level=RiskLevel.MEDIUM,
                details={
                    "deviation": deviation,
                    "max_deviation": max_deviation,
                },
            )

        return CheckResult(
            check_name=check_name,
            status=CheckStatus.PASSED,
            passed=True,
            message=f"目标价{target_price:.2f}在合理范围内",
            risk_level=RiskLevel.LOW,
            details={
                "current_price": current_price,
                "target_price": target_price,
                "deviation": deviation,
            },
        )

    def _check_confidence_risk_consistency(self, decision: TradeDecision) -> CheckResult:
        """
        检查置信度与风险评分的一致性

        - 高置信度(>0.7)但高风险评分(>0.6)是矛盾的
        - 低置信度(<0.5)但低风险评分(<0.3)可能过于乐观
        """
        check_name = "置信度风险一致性检查"

        confidence = decision.confidence
        risk_score = decision.risk_score

        # 高置信度但高风险评分 - 矛盾
        if confidence > 0.7 and risk_score > 0.6:
            return CheckResult(
                check_name=check_name,
                status=CheckStatus.WARNING,
                passed=True,
                message=f"高置信度({confidence:.0%})与高风险评分({risk_score:.0%})存在矛盾，建议重新评估",
                risk_level=RiskLevel.MEDIUM,
                details={"confidence": confidence, "risk_score": risk_score},
            )

        # 低置信度但低风险评分 - 可能过于乐观
        if confidence < 0.5 and risk_score < 0.3:
            return CheckResult(
                check_name=check_name,
                status=CheckStatus.WARNING,
                passed=True,
                message=f"低置信度({confidence:.0%})与低风险评分({risk_score:.0%})可能不匹配",
                risk_level=RiskLevel.MEDIUM,
                details={"confidence": confidence, "risk_score": risk_score},
            )

        return CheckResult(
            check_name=check_name,
            status=CheckStatus.PASSED,
            passed=True,
            message="置信度与风险评分一致性良好",
            risk_level=RiskLevel.LOW,
            details={"confidence": confidence, "risk_score": risk_score},
        )

    def _check_confidence_threshold(self, decision: TradeDecision) -> CheckResult:
        """
        检查置信度是否达到最低要求
        """
        check_name = "置信度阈值检查"

        confidence = decision.confidence
        min_confidence = self.config["min_confidence"]

        if confidence < min_confidence:
            return CheckResult(
                check_name=check_name,
                status=CheckStatus.BLOCKED,
                passed=False,
                message=f"置信度{confidence:.0%}低于最低要求{min_confidence:.0%}",
                risk_level=RiskLevel.HIGH,
                details={"confidence": confidence, "min_required": min_confidence},
            )

        # 检查是否达到高置信度
        high_threshold = self.config["high_confidence_threshold"]
        if confidence >= high_threshold:
            return CheckResult(
                check_name=check_name,
                status=CheckStatus.PASSED,
                passed=True,
                message=f"置信度{confidence:.0%}达到高置信度标准",
                risk_level=RiskLevel.LOW,
                details={"confidence": confidence, "threshold": high_threshold},
            )

        return CheckResult(
            check_name=check_name,
            status=CheckStatus.PASSED,
            passed=True,
            message=f"置信度{confidence:.0%}满足最低要求",
            risk_level=RiskLevel.LOW,
            details={"confidence": confidence, "min_required": min_confidence},
        )

    def _check_max_risk_score(self, decision: TradeDecision) -> CheckResult:
        """
        检查风险评分是否超过最大允许值
        """
        check_name = "风险评分上限检查"

        risk_score = decision.risk_score
        max_risk = self.config["max_risk_score"]

        if risk_score > max_risk:
            return CheckResult(
                check_name=check_name,
                status=CheckStatus.BLOCKED,
                passed=False,
                message=f"风险评分{risk_score:.0%}超过最大允许值{max_risk:.0%}",
                risk_level=RiskLevel.CRITICAL,
                details={"risk_score": risk_score, "max_allowed": max_risk},
            )

        return CheckResult(
            check_name=check_name,
            status=CheckStatus.PASSED,
            passed=True,
            message=f"风险评分{risk_score:.0%}在允许范围内",
            risk_level=RiskLevel.LOW,
            details={"risk_score": risk_score, "max_allowed": max_risk},
        )

    def _check_liquidity(
        self, decision: TradeDecision, context: Optional[Dict[str, Any]]
    ) -> CheckResult:
        """
        流动性检查

        - 订单规模 vs 市场深度
        - 最小交易量要求
        """
        check_name = "流动性检查"

        # 如果没有上下文，跳过详细检查
        if not context:
            return CheckResult(
                check_name=check_name,
                status=CheckStatus.PASSED,
                passed=True,
                message="无流动性数据，跳过检查",
                risk_level=RiskLevel.LOW,
                details={},
            )

        # 检查日均成交量
        avg_volume = context.get("avg_daily_volume", 0)
        if avg_volume > 0:
            # 假设建议仓位对应的金额
            position_value = decision.position_ratio * 1000000  # 假设100万账户
            estimated_shares = position_value / decision.current_price

            # 检查是否超过日均成交量的10%
            max_shares = avg_volume * 0.10
            if estimated_shares > max_shares:
                return CheckResult(
                    check_name=check_name,
                    status=CheckStatus.WARNING,
                    passed=True,
                    message=f"建议交易量{estimated_shares:.0f}股超过日均成交量的10%({max_shares:.0f}股)",
                    risk_level=RiskLevel.MEDIUM,
                    details={
                        "estimated_shares": estimated_shares,
                        "max_shares": max_shares,
                        "avg_volume": avg_volume,
                    },
                )

        return CheckResult(
            check_name=check_name,
            status=CheckStatus.PASSED,
            passed=True,
            message="流动性检查通过",
            risk_level=RiskLevel.LOW,
            details={},
        )

    def validate_from_analysis_result(
        self, analysis_result: Dict[str, Any]
    ) -> ValidationResult:
        """
        从分析结果创建交易决策并验证

        Args:
            analysis_result: 分析结果字典，包含 decision 等字段

        Returns:
            ValidationResult: 验证结果
        """
        decision_data = analysis_result.get("decision", {})

        # 提取交易决策
        decision = TradeDecision(
            symbol=decision_data.get("symbol", analysis_result.get("symbol", "")),
            action=decision_data.get("recommendation", "未知"),
            current_price=float(decision_data.get("current_price", 0)),
            target_price=float(decision_data.get("target_price", 0)),
            confidence=float(decision_data.get("confidence", 0.5)),
            risk_score=float(decision_data.get("risk_score", 0.5)),
            position_ratio=self._extract_position_ratio(decision_data.get("position_suggestion", "")),
            stop_loss=decision_data.get("stop_loss"),
        )

        return self.validate_trade_decision(decision)

    def _extract_position_ratio(self, position_suggestion: str) -> float:
        """
        从仓位建议文本中提取仓位比例
        """
        import re

        # 匹配百分比
        match = re.search(r'(\d+)%', position_suggestion)
        if match:
            return float(match.group(1)) / 100

        # 匹配文字描述
        if "满仓" in position_suggestion or "全仓" in position_suggestion:
            return 1.0
        elif "重仓" in position_suggestion:
            return 0.7
        elif "中等仓位" in position_suggestion or "半仓" in position_suggestion:
            return 0.5
        elif "轻仓" in position_suggestion:
            return 0.2
        elif "空仓" in position_suggestion or "清仓" in position_suggestion:
            return 0.0

        # 默认中等仓位
        return 0.3


# 全局网关实例
_execution_risk_gateway: Optional[ExecutionRiskGateway] = None


def get_execution_risk_gateway() -> ExecutionRiskGateway:
    """获取全局执行风险网关实例"""
    global _execution_risk_gateway
    if _execution_risk_gateway is None:
        _execution_risk_gateway = ExecutionRiskGateway()
    return _execution_risk_gateway
