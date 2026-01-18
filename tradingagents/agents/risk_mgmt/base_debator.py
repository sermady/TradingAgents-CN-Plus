# -*- coding: utf-8 -*-
"""
风险辩论者基类
提供统一的辩论者逻辑,减少代码重复
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional

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

            # 更新状态
            new_count = risk_debate_state["count"] + 1
            logger.info(
                f"{self.emoji} [{self.description}分析师] 发言完成，计数: {risk_debate_state['count']} -> {new_count}"
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
        return {
            "market": state.get("market_report", ""),
            "sentiment": state.get("sentiment_report", ""),
            "news": state.get("news_report", ""),
            "fundamentals": state.get("fundamentals_report", ""),
        }

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
        other_responses_text = self._format_other_responses(current_responses)

        prompt = f"""作为{self.description}风险分析师，您的职责是{self.goal}。

在评估交易员的决策或计划时，请重点关注{self.focus}——即使这些伴随着较高的风险。

使用提供的市场数据和情绪分析来加强您的论点，并挑战对立观点。

具体来说，请直接回应保守和中性分析师提出的每个观点，用数据驱动的反驳和有说服力的推理进行反击。

以下是交易员的决策：

{trader_decision}

您的任务是通过质疑和批评保守和中性立场来为交易员的决策创建一个令人信服的案例，证明为什么您的高回报视角提供了最佳的前进道路。

将以下来源的见解纳入您的论点：

市场研究报告：{reports["market"]}

社交媒体情绪报告：{reports["sentiment"]}

最新世界事务报告：{reports["news"]}

公司基本面报告：{reports["fundamentals"]}

以下是当前对话历史：{history}

{other_responses_text}

积极参与，解决提出的任何具体担忧，反驳他们逻辑中的弱点，并断言承担风险的好处以超越市场常规。

专注于辩论和说服，而不仅仅是呈现数据。挑战每个反驳点，强调为什么高风险方法是最优的。

请用中文以对话方式输出，就像您在说话一样，不使用任何特殊格式。"""

        return prompt

    def _format_other_responses(self, current_responses: Dict[str, str]) -> str:
        """格式化其他辩论者的回应"""
        responses = []

        if current_responses.get("safe"):
            responses.append(f"安全分析师的最后论点：{current_responses['safe']}")

        if current_responses.get("neutral"):
            responses.append(f"中性分析师的最后论点：{current_responses['neutral']}")

        return "\n".join(responses) if responses else "暂无其他辩论者的回应"


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
        other_responses_text = self._format_other_responses(current_responses)

        prompt = f"""作为安全/保守风险分析师，您的主要目标是{self.goal}。您优先考虑稳定性、安全性和风险缓解，仔细评估潜在损失、经济衰退和市场波动。

在评估交易员的决策或计划时，请批判性地审查高风险要素，指出决策可能使公司面临不当风险的地方，以及更谨慎的替代方案如何能够确保长期收益。

以下是交易员的决策：

{trader_decision}

您的任务是积极反驳激进和中性分析师的论点，突出他们的观点可能忽视的潜在威胁或未能优先考虑可持续性的地方。

直接回应他们的观点，利用以下数据来源为交易员决策的低风险方法调整建立令人信服的案例：

市场研究报告：{reports["market"]}

社交媒体情绪报告：{reports["sentiment"]}

最新世界事务报告：{reports["news"]}

公司基本面报告：{reports["fundamentals"]}

以下是当前对话历史：{history}

{other_responses_text}

通过质疑他们的乐观态度并强调他们可能忽视的潜在下行风险来参与讨论。

解决他们的每个反驳点，展示为什么保守立场最终是公司资产最安全的道路。

专注于辩论和批评他们的论点，证明低风险策略相对于他们方法的优势。

请用中文以对话方式输出，就像您在说话一样，不使用任何特殊格式。"""

        return prompt

    def _format_other_responses(self, current_responses: Dict[str, str]) -> str:
        """格式化其他辩论者的回应"""
        responses = []

        if current_responses.get("risky"):
            responses.append(f"激进分析师的最后论点：{current_responses['risky']}")

        if current_responses.get("neutral"):
            responses.append(f"中性分析师的最后论点：{current_responses['neutral']}")

        return "\n".join(responses) if responses else "暂无其他辩论者的回应"


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
        other_responses_text = self._format_other_responses(current_responses)

        prompt = f"""作为中性风险分析师，您的角色是提供平衡的视角，权衡交易员决策或计划的潜在收益和风险。您优先考虑全面的方法，评估上行和下行风险，同时考虑更广泛的市场趋势、潜在的经济变化和多元化策略。

以下是交易员的决策：

{trader_decision}

您的任务是挑战激进和安全分析师，指出每种观点可能过于乐观或过于谨慎的地方。

使用以下数据来源的见解来支持调整交易员决策的温和、可持续策略：

市场研究报告：{reports["market"]}

社交媒体情绪报告：{reports["sentiment"]}

最新世界事务报告：{reports["news"]}

公司基本面报告：{reports["fundamentals"]}

以下是当前对话历史：{history}

{other_responses_text}

通过批判性地分析双方来积极参与，解决激进和保守论点中的弱点，倡导更平衡的方法。

挑战他们的每个观点，说明为什么适度风险策略可能提供两全其美的效果，既提供增长潜力又防范极端波动。

专注于辩论而不是简单地呈现数据，旨在表明平衡的观点可以带来最可靠的结果。

请用中文以对话方式输出，就像您在说话一样，不使用任何特殊格式。"""

        return prompt

    def _format_other_responses(self, current_responses: Dict[str, str]) -> str:
        """格式化其他辩论者的回应"""
        responses = []

        if current_responses.get("risky"):
            responses.append(f"激进分析师的最后论点：{current_responses['risky']}")

        if current_responses.get("safe"):
            responses.append(f"安全分析师的最后论点：{current_responses['safe']}")

        return "\n".join(responses) if responses else "暂无其他辩论者的回应"


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
