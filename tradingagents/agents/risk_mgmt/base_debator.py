# -*- coding: utf-8 -*-
"""
风险辩论者基类
提供统一的辩论者逻辑,减少代码重复
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


class BaseDebator(ABC):
    """风险辩论者基类"""

    def __init__(self, debator_type: str):
        """
        初始化辩论者基类

        Args:
            debator_type: 辩论者类型 (risky/safe/neutral)
        """
        self.debator_type = debator_type
        self._setup_characteristics()

    def _setup_characteristics(self):
        """设置辩论者特征"""
        if self.debator_type == "risky":
            self.description = "激进"
            self.emoji = "🔥"
            self.goal = "积极倡导高回报、高风险的投资机会"
            self.focus = "潜在上涨空间、增长潜力和创新收益"
        elif self.debator_type == "safe":
            self.description = "安全/保守"
            self.emoji = "🛡️"
            self.goal = "保护资产、最小化波动性，确保稳定、可靠的增长"
            self.focus = "稳定性、安全性和风险缓解"
        else:  # neutral
            self.description = "中性"
            self.emoji = "⚖️"
            self.goal = "提供平衡的视角，权衡潜在收益和风险"
            self.focus = "全面的方法，评估上行和下行风险"

    def create_node(self, llm: Callable) -> Callable:
        """
        创建辩论者节点函数

        Args:
            llm: LLM实例

        Returns:
            辩论者节点函数
        """

        def debator_node(state) -> Dict[str, Any]:
            """辩论者节点主函数"""
            logger.debug(
                f"{self.emoji} [{self.description}分析师] ===== 节点开始 ====="
            )

            # 获取状态
            risk_debate_state = state["risk_debate_state"]
            history = risk_debate_state.get("history", "")
            self_history = risk_debate_state.get(f"{self.debator_type}_history", "")

            # 获取其他辩论者的最新回应
            current_responses = self._get_current_responses(risk_debate_state)

            # 获取分析师报告
            reports = self._get_analyst_reports(state)

            # 获取交易员决策
            trader_decision = state.get("trader_investment_plan", "")

            # 记录输入数据长度
            self._log_input_statistics(
                reports, history, current_responses, trader_decision
            )

            # 构建prompt
            prompt = self._build_prompt(
                reports, history, current_responses, trader_decision
            )

            # 调用LLM
            logger.info(f"{self.emoji} [{self.description}分析师] 开始调用LLM...")
            llm_start_time = time.time()

            response = llm.invoke(prompt)

            llm_elapsed = time.time() - llm_start_time
            logger.info(
                f"{self.emoji} [{self.description}分析师] LLM调用完成，耗时: {llm_elapsed:.2f}秒"
            )

            # 构建论点
            argument = f"{self.description} Analyst: {response.content}"

            # P1-4: 辩论质量评估
            from tradingagents.graph.debate_quality import (
                evaluate_argument_quality,
                compute_cumulative_evidence_strength,
            )

            quality_scores = evaluate_argument_quality(
                text=response.content, history=history, role=self.debator_type
            )
            prev_quality = risk_debate_state.get("argument_quality", 0.0)

            # 更新状态
            new_count = risk_debate_state["count"] + 1
            new_quality = compute_cumulative_evidence_strength(
                quality_scores, prev_quality, new_count
            )

            logger.info(
                f"{self.emoji} [{self.description}分析师] 发言完成，计数: {risk_debate_state['count']} -> {new_count}，"
                f"论点质量: {prev_quality:.3f} -> {new_quality:.3f}"
            )

            new_risk_debate_state = {
                "history": history + "\n" + argument,
                "risky_history": risk_debate_state.get("risky_history", ""),
                "safe_history": risk_debate_state.get("safe_history", ""),
                "neutral_history": risk_debate_state.get("neutral_history", ""),
                "latest_speaker": self.debator_type.capitalize(),
                "current_risky_response": risk_debate_state.get(
                    "current_risky_response", ""
                ),
                "current_safe_response": risk_debate_state.get(
                    "current_safe_response", ""
                ),
                "current_neutral_response": risk_debate_state.get(
                    "current_neutral_response", ""
                ),
                f"current_{self.debator_type}_response": argument,
                "count": new_count,
                "argument_quality": new_quality,
            }

            return {"risk_debate_state": new_risk_debate_state}

        return debator_node

    @abstractmethod
    def _build_prompt(
        self,
        reports: Dict[str, str],
        history: str,
        current_responses: Dict[str, str],
        trader_decision: str,
    ) -> str:
        """
        构建辩论者prompt(子类必须实现)

        Args:
            reports: 分析师报告
            history: 辩论历史
            current_responses: 其他辩论者的最新回应
            trader_decision: 交易员决策

        Returns:
            prompt字符串
        """
        pass

    def _get_current_responses(
        self, risk_debate_state: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        获取其他辩论者的最新回应

        Args:
            risk_debate_state: 风险辩论状态

        Returns:
            当前回应字典
        """
        return {
            "risky": risk_debate_state.get("current_risky_response", ""),
            "safe": risk_debate_state.get("current_safe_response", ""),
            "neutral": risk_debate_state.get("current_neutral_response", ""),
        }

    def _get_analyst_reports(self, state: Dict[str, Any]) -> Dict[str, str]:
        """
        获取所有分析师报告

        Args:
            state: 状态字典

        Returns:
            报告字典
        """
        reports = {
            "market": state.get("market_report", ""),
            "sentiment": state.get("sentiment_report", ""),
            "news": state.get("news_report", ""),
            "fundamentals": state.get("fundamentals_report", ""),
        }

        # P1-2: 注入量化风险指标文本
        quant_risk_text = state.get("quant_risk_text", "")
        if quant_risk_text:
            reports["quant_risk"] = quant_risk_text

        return reports

    def _log_input_statistics(
        self,
        reports: Dict[str, str],
        history: str,
        current_responses: Dict[str, str],
        trader_decision: str,
    ):
        """
        记录输入数据统计

        Args:
            reports: 分析师报告
            history: 辩论历史
            current_responses: 其他辩论者的回应
            trader_decision: 交易员决策
        """
        logger.info(f"{self.emoji} [{self.description}分析师] 输入数据长度统计:")
        logger.info(f"  - market_report: {len(reports['market']):,} 字符")
        logger.info(f"  - sentiment_report: {len(reports['sentiment']):,} 字符")
        logger.info(f"  - news_report: {len(reports['news']):,} 字符")
        logger.info(f"  - fundamentals_report: {len(reports['fundamentals']):,} 字符")
        logger.info(f"  - trader_decision: {len(trader_decision):,} 字符")
        logger.info(f"  - history: {len(history):,} 字符")

        total_length = (
            len(reports["market"])
            + len(reports["sentiment"])
            + len(reports["news"])
            + len(reports["fundamentals"])
            + len(trader_decision)
            + len(history)
            + len(current_responses.get("risky", ""))
            + len(current_responses.get("safe", ""))
            + len(current_responses.get("neutral", ""))
        )
        logger.info(
            f"  - 总Prompt长度: {total_length:,} 字符 (~{total_length // 4:,} tokens)"
        )


class AggressiveDebator(BaseDebator):
    """激进风险辩论者"""

    def __init__(self):
        """初始化激进辩论者"""
        super().__init__("risky")

    def _build_prompt(
        self,
        reports: Dict[str, str],
        history: str,
        current_responses: Dict[str, str],
        trader_decision: str,
    ) -> str:
        """构建激进辩论者prompt"""
        from tradingagents.agents.utils.prompt_builder import build_debator_prompt

        return build_debator_prompt(
            role="aggressive",
            description=self.description,
            goal=self.goal,
            focus=self.focus,
            reports=reports,
            history=history,
            current_responses=current_responses,
            trader_decision=trader_decision
        )


class ConservativeDebator(BaseDebator):
    """安全/保守风险辩论者"""

    def __init__(self):
        """初始化保守辩论者"""
        super().__init__("safe")

    def _build_prompt(
        self,
        reports: Dict[str, str],
        history: str,
        current_responses: Dict[str, str],
        trader_decision: str,
    ) -> str:
        """构建保守辩论者prompt"""
        from tradingagents.agents.utils.prompt_builder import build_debator_prompt

        return build_debator_prompt(
            role="conservative",
            description=self.description,
            goal=self.goal,
            focus=self.focus,
            reports=reports,
            history=history,
            current_responses=current_responses,
            trader_decision=trader_decision
        )


class NeutralDebator(BaseDebator):
    """中性风险辩论者"""

    def __init__(self):
        """初始化中性辩论者"""
        super().__init__("neutral")

    def _build_prompt(
        self,
        reports: Dict[str, str],
        history: str,
        current_responses: Dict[str, str],
        trader_decision: str,
    ) -> str:
        """构建中性辩论者prompt"""
        from tradingagents.agents.utils.prompt_builder import build_debator_prompt

        return build_debator_prompt(
            role="neutral",
            description=self.description,
            goal=self.goal,
            focus=self.focus,
            reports=reports,
            history=history,
            current_responses=current_responses,
            trader_decision=trader_decision
        )


# 工厂函数
def create_debator(debator_type: str) -> BaseDebator:
    """
    创建辩论者实例

    Args:
        debator_type: 辩论者类型 (risky/safe/neutral)

    Returns:
        辩论者实例
    """
    if debator_type == "risky":
        return AggressiveDebator()
    elif debator_type == "safe":
        return ConservativeDebator()
    elif debator_type == "neutral":
        return NeutralDebator()
    else:
        raise ValueError(f"不支持的辩论者类型: {debator_type}")
