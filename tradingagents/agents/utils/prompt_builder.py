# -*- coding: utf-8 -*-
"""
Prompt构建工具

统一构建辩论者和研究员的Prompt，消除重复代码
"""
from typing import Dict


class PromptBuilder:
    """Prompt构建工具类

    统一管理所有辩论者和研究员的Prompt构建逻辑
    """

    def __init__(self):
        """初始化Prompt构建器"""
        pass

    def build_debator_prompt(
        self,
        role: str,  # aggressive, conservative, neutral
        description: str,
        goal: str,
        focus: str,
        reports: Dict[str, str],
        history: str,
        current_responses: Dict[str, str],
        trader_decision: str
    ) -> str:
        """
        构建辩论者prompt

        Args:
            role: 辩论者角色（aggressive/conservative/neutral）
            description: 辩论者描述
            goal: 辩论者目标
            focus: 关注点
            reports: 分析师报告
            history: 辩论历史
            current_responses: 其他辩论者的最新回应
            trader_decision: 交易员决策

        Returns:
            prompt字符串
        """
        # 格式化历史对话
        history_text = self._format_debate_history(history)

        # 格式化其他回应
        other_responses_text = self._format_other_responses(current_responses)

        # 构建prompt
        prompt = f"""作为{description}，您的职责是{goal}。

在评估{trader_decision}时，请重点关注{focus}——即使这些伴随着较高的风险。

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
"""

        # P1-2: 注入量化风险指标
        quant_risk = reports.get("quant_risk", "")
        if quant_risk:
            prompt += f"""
量化风险指标（请基于这些定量数据支撑或质疑风险论点）：
{quant_risk}
"""

        prompt += f"""
以下是当前对话历史：
{history_text}

{other_responses_text}

积极参与，解决提出的任何具体担忧，反驳他们逻辑中的弱点，并断言承担风险的好处以超越市场常规。
专注于辩论和说服，而不仅仅是呈现数据。挑战每个反驳点，强调为什么高风险方法是最优的。

请用中文以对话方式输出，就像您在说话一样，不使用任何特殊格式。"""
        return prompt

    def build_researcher_prompt(
        self,
        role: str,  # bull, bear
        description: str,
        company_name: str,
        ticker: str,
        reports: Dict[str, str]
    ) -> str:
        """
        构建研究员prompt

        Args:
            role: 研究员角色（bull/bear）
            description: 研究员描述
            company_name: 公司名称
            ticker: 股票代码
            reports: 分析师报告

        Returns:
            prompt字符串
        """
        # 角色名称
        role_name = "看涨" if role == "bull" else "看跌"

        prompt = f"""作为{role_name}研究员，您的主要职责是分析{company_name}（{ticker}）。

请提供全面、深入的股票分析报告，帮助投资团队做出明智的决策。

请包含以下关键部分：

## 1. 公司概况和基本面分析
- 公司基本信息：业务描述、主要产品/服务
- 财务健康状况：收入、利润、现金流、负债水平
- 行业地位：市场份额、竞争优势
- 管理团队：经验和质量

## 2. 市场技术分析
- 趋势分析：价格走势、交易量变化
- 支撑位和阻力位：关键价格水平
- 技术指标信号：RSI、MACD等
- 市场情绪：投资者情绪、舆论评价

## 3. 风险评估
- 主要风险因素：行业、监管、财务等
- 潜在机会：新产品、市场扩张等
- 时间框架：短期、中期、长期展望

## 4. 投资建议
- 明确立场：买入/持有/卖出
- 目标价格：具体价位
- 时间范围：建议的投资周期
- 置信度：高/中/低

以下分析报告供参考：
市场研究报告：{reports["market"]}
社交媒体情绪报告：{reports["sentiment"]}
最新世界事务报告：{reports["news"]}
公司基本面报告：{reports["fundamentals"]}

请基于以上要求，提供详细、专业、有数据支撑的分析报告。用中文输出。"""
        return prompt

    def _format_debate_history(self, history: str) -> str:
        """
        格式化辩论历史

        Args:
            history: 辩论历史

        Returns:
            格式化后的历史文本
        """
        if not history:
            return "暂无历史记录"

        lines = history.split("\n")
        formatted_lines = []

        for i, line in enumerate(lines[:10], 1):  # 只保留最近10轮
            formatted_line = f"{i}. {line}"
            formatted_lines.append(formatted_line)

        return "\n".join(formatted_lines)

    def _format_other_responses(self, current_responses: Dict[str, str]) -> str:
        """
        格式化其他辩论者的回应

        Args:
            current_responses: 其他辩论者的回应

        Returns:
            格式化后的回应文本
        """
        parts = []

        if current_responses.get("safe"):
            parts.append(f"安全分析师的最后论点：{current_responses['safe']}")
        if current_responses.get("neutral"):
            parts.append(f"中性分析师的最后论点：{current_responses['neutral']}")

        if parts:
            return "以下是其他辩论者的最新回应：\n" + "\n".join(parts)
        else:
            return "暂无其他辩论者的回应"


# 便捷函数
def build_debator_prompt(
    role: str,
    description: str,
    goal: str,
    focus: str,
    reports: Dict[str, str],
    history: str,
    current_responses: Dict[str, str],
    trader_decision: str
) -> str:
    """便捷函数：构建辩论者prompt"""
    builder = PromptBuilder()
    return builder.build_debator_prompt(
        role=role,
        description=description,
        goal=goal,
        focus=focus,
        reports=reports,
        history=history,
        current_responses=current_responses,
        trader_decision=trader_decision
    )


def build_researcher_prompt(
    role: str,
    description: str,
    company_name: str,
    ticker: str,
    reports: Dict[str, str]
) -> str:
    """便捷函数：构建研究员prompt"""
    builder = PromptBuilder()
    return builder.build_researcher_prompt(
        role=role,
        description=description,
        company_name=company_name,
        ticker=ticker,
        reports=reports
    )
