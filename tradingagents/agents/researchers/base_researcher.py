# -*- coding: utf-8 -*-
"""
研究员基类
提供统一的Bull/Bear研究员逻辑,减少代码重复
"""

from typing import Dict, Any, Callable
from abc import ABC, abstractmethod

# 导入统一日志系统和工具
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.company_name_utils import get_company_name

logger = get_logger("default")


class BaseResearcher(ABC):
    """研究员基类"""

    def __init__(self, perspective: str):
        """
        初始化研究员基类

        Args:
            perspective: 视角 (bull/bear)
        """
        self.perspective = perspective
        self._setup_characteristics()

    def _setup_characteristics(self):
        """设置特征"""
        if self.perspective == "bull":
            self.description = "看涨"
            self.emoji = "🐂"
            self.goal = "突出增长潜力、竞争优势和积极的市场指标"
            self.viewpoint = "积极论证"
        else:  # bear
            self.description = "看跌"
            self.emoji = "🐻"
            self.goal = "强调风险、挑战和负面指标"
            self.viewpoint = "消极论证"

    def create_node(self, llm: Callable, memory: Callable) -> Callable:
        """
        创建研究员节点函数

        Args:
            llm: LLM实例
            memory: 记忆实例

        Returns:
            研究员节点函数
        """

        def research_node(state) -> Dict[str, Any]:
            """研究员节点主函数"""
            logger.debug(
                f"{self.emoji} [{self.description}研究员] ===== 节点开始 ====="
            )

            # 获取状态
            investment_debate_state = state["investment_debate_state"]
            history = investment_debate_state.get("history", "")
            self_history = investment_debate_state.get(
                f"{self.perspective}_history", ""
            )
            current_response = investment_debate_state.get("current_response", "")

            # 获取分析师报告
            reports = self._get_analyst_reports(state)

            # 获取市场信息和公司名称
            ticker = state.get("company_of_interest", "Unknown")
            from tradingagents.utils.stock_utils import StockUtils

            market_info = StockUtils.get_market_info(ticker)
            company_name = get_company_name(ticker, market_info)

            # 获取记忆
            curr_situation = self._build_situation(reports)
            past_memories = self._get_past_memories(memory, curr_situation)
            past_memory_str = self._format_memories(past_memories)

            # 记录日志
            self._log_context(ticker, company_name, market_info, reports, history)

            # 构建prompt
            prompt = self._build_prompt(
                company_name,
                ticker,
                market_info,
                reports,
                history,
                current_response,
                past_memory_str,
            )

            # 调用LLM
            logger.info(f"{self.emoji} [{self.description}研究员] 开始调用LLM...")
            response = llm.invoke(prompt)

            # 构建论点
            argument = f"{self.description} Analyst: {response.content}"

            # 更新状态
            new_count = investment_debate_state["count"] + 1
            logger.info(
                f"{self.emoji} [{self.description}研究员] 发言完成，计数: {investment_debate_state['count']} -> {new_count}"
            )

            new_investment_debate_state = {
                "history": history + "\n" + argument,
                "bull_history": self_history + "\n" + argument
                if self.perspective == "bull"
                else investment_debate_state.get("bull_history", ""),
                "bear_history": self_history + "\n" + argument
                if self.perspective == "bear"
                else investment_debate_state.get("bear_history", ""),
                "current_response": argument,
                "count": new_count,
            }

            return {"investment_debate_state": new_investment_debate_state}

        return research_node

    def _get_analyst_reports(self, state: Dict[str, Any]) -> Dict[str, str]:
        """获取分析师报告"""
        return {
            "market": state.get("market_report", ""),
            "sentiment": state.get("sentiment_report", ""),
            "news": state.get("news_report", ""),
            "fundamentals": state.get("fundamentals_report", ""),
        }

    def _build_situation(self, reports: Dict[str, str]) -> str:
        """构建当前情况字符串"""
        return f"{reports['market']}\n\n{reports['sentiment']}\n\n{reports['news']}\n\n{reports['fundamentals']}"

    def _get_past_memories(self, memory: Callable, curr_situation: str) -> list:
        """获取过去记忆"""
        if memory is not None:
            try:
                return memory.get_memories(curr_situation, n_matches=5)
            except Exception as e:
                logger.warning(f"⚠️ [{self.description}研究员] 获取记忆失败: {e}")
                return []
        else:
            logger.debug(f"⚠️ [{self.description}研究员] memory为None，跳过历史记忆检索")
            return []

    def _format_memories(self, past_memories: list) -> str:
        """格式化记忆"""
        return "\n\n".join(rec["recommendation"] for rec in past_memories)

    def _log_context(
        self,
        ticker: str,
        company_name: str,
        market_info: Dict,
        reports: Dict,
        history: str,
    ):
        """记录上下文日志"""
        logger.info(f"[{self.description}研究员] 公司名称: {company_name}")
        logger.info(f"[{self.description}研究员] 股票代码: {ticker}")
        logger.info(f"[{self.description}研究员] 类型: {market_info['market_name']}")
        logger.info(
            f"[{self.description}研究员] 货币: {market_info['currency_name']} ({market_info['currency_symbol']})"
        )
        logger.debug(
            f"[{self.description}研究员] - 市场报告长度: {len(reports['market'])}"
        )
        logger.debug(
            f"[{self.description}研究员] - 情绪报告长度: {len(reports['sentiment'])}"
        )
        logger.debug(
            f"[{self.description}研究员] - 新闻报告长度: {len(reports['news'])}"
        )
        logger.debug(
            f"[{self.description}研究员] - 基本面报告长度: {len(reports['fundamentals'])}"
        )
        logger.debug(f"[{self.description}研究员] - 辩论历史长度: {len(history)}")

    @abstractmethod
    def _build_prompt(
        self,
        company_name: str,
        ticker: str,
        market_info: Dict,
        reports: Dict[str, str],
        history: str,
        current_response: str,
        past_memory_str: str,
    ) -> str:
        """
        构建prompt(子类必须实现)

        Args:
            company_name: 公司名称
            ticker: 股票代码
            market_info: 市场信息
            reports: 分析师报告
            history: 辩论历史
            current_response: 当前对方论点
            past_memory_str: 过去记忆

        Returns:
            prompt字符串
        """
        pass


class BullResearcher(BaseResearcher):
    """看涨研究员"""

    def __init__(self):
        """初始化看涨研究员"""
        super().__init__("bull")

    def _build_prompt(
        self,
        company_name: str,
        ticker: str,
        market_info: Dict,
        reports: Dict[str, str],
        history: str,
        current_response: str,
        past_memory_str: str,
    ) -> str:
        """构建看涨研究员prompt"""
        return f"""你是一位看涨分析师，负责为股票 {company_name}（股票代码：{ticker}）的投资建立强有力的论证。

⚠️ 重要提醒：当前分析的是 {"中国A股" if market_info["is_china"] else "海外股票"}，所有价格和估值请使用 {market_info["currency_name"]}（{market_info["currency_symbol"]}）作为单位。
⚠️ 在你的分析中，请始终使用公司名称"{company_name}"而不是股票代码"{ticker}"来称呼这家公司。

🚨 CRITICAL REQUIREMENT - 绝对强制要求：

❌ 严格禁止行为：
1. 绝对禁止编造任何财务数据或增长预测
2. 绝对禁止编造市场地位或竞争优势
3. 绝对禁止基于常识编造行业趋势
4. 绝对禁止强化基于编造数据的观点
5. 绝对禁止使用常识或训练数据"合理化"编造内容

✅ 强制验证步骤：
1. 你必须批判性地评估前面分析师的报告
2. 如果发现报告中包含编造数据或明显错误，必须明确拒绝该数据
3. 不要使用包含编造数据的论据
4. 如果数据可疑，请在论证中明确说明："该报告的数据不可信，不作为论据"
5. 检查数据是否在合理范围内：
   - PE/PB 比率是否合理？（通常 PE: 5-100, PB: 0.5-5）
   - ROE 是否在合理范围？（通常 5%-30%）
   - 增长率是否合理？（通常 0-50%，不包含异常高值）
   - 估值方法是否一致？

📊 数据验证清单（重要）：
- [ ] PE/PB 比率是否合理？
- [ ] ROE 是否在合理范围？
- [ ] 增长率是否合理？
- [ ] 估值方法是否一致？
- [ ] 是否有矛盾的数据点？
- [ ] 报告是否基于具体数据而非泛泛而谈？

⚠️ 违规后果：
- 如果基于编造数据生成观点，你的论证将被拒绝
- 如果使用不可信的报告作为论据，必须在论证中明确说明
- 必须基于可信数据，否则无法完成论证任务

你的任务是构建基于证据的强有力案例，{self.goal}。利用提供的研究和数据来解决担忧并有效反驳看跌论点。

请用中文回答，重点关注以下几个方面：
- 增长潜力：突出公司的市场机会、收入预测和可扩展性
- 竞争优势：强调独特产品、强势品牌或主导市场地位等因素
- 积极指标：使用财务健康状况、行业趋势和最新积极消息作为证据
- 反驳看跌观点：用具体数据和合理推理批判性分析看跌论点，全面解决担忧并说明为什么看涨观点更有说服力
- 参与讨论：以对话风格呈现你的论点，直接回应看跌分析师的观点并进行有效辩论，而不仅仅是列举数据

可用资源：
市场研究报告：{reports["market"]}

社交媒体情绪报告：{reports["sentiment"]}

最新世界事务新闻：{reports["news"]}

公司基本面报告：{reports["fundamentals"]}

辩论对话历史：{history}

最后的看跌论点：{current_response}

类似情况的反思和经验教训：{past_memory_str}

请使用这些信息提供令人信服的看涨论点，反驳看跌担忧，并参与动态辩论，展示看涨立场的优势。你还必须处理反思并从过去的经验教训和错误中学习。

请确保所有回答都使用中文。"""


class BearResearcher(BaseResearcher):
    """看跌研究员"""

    def __init__(self):
        """初始化看跌研究员"""
        super().__init__("bear")

    def _build_prompt(
        self,
        company_name: str,
        ticker: str,
        market_info: Dict,
        reports: Dict[str, str],
        history: str,
        current_response: str,
        past_memory_str: str,
    ) -> str:
        """构建看跌研究员prompt"""
        return f"""你是一位看跌分析师，负责论证不投资股票 {company_name}（股票代码：{ticker}）的理由。

⚠️ 重要提醒：当前分析的是 {market_info["market_name"]}，所有价格和估值请使用 {market_info["currency_name"]}（{market_info["currency_symbol"]}）作为单位。
⚠️ 在你的分析中，请始终使用公司名称"{company_name}"而不是股票代码"{ticker}"来称呼这家公司。

🚨 CRITICAL REQUIREMENT - 绝对强制要求：

❌ 严格禁止行为：
1. 绝对禁止编造任何财务数据或风险预测
2. 绝对禁止编造市场地位或竞争劣势
3. 绝对禁止基于常识编造行业趋势
4. 绝对禁止编造负面指标或风险因素
5. 绝对禁止强化基于编造数据的观点
6. 绝对禁止使用常识或训练数据"合理化"编造内容

✅ 强制验证步骤：
1. 你必须批判性地评估前面分析师的报告
2. 如果发现报告中包含编造数据或明显错误，必须明确拒绝该数据
3. 不要使用包含编造数据的论据
4. 如果数据可疑，请在论证中明确说明："该报告的数据不可信，不作为论据"
5. 检查数据是否在合理范围内：
   - PE/PB 比率是否合理？（通常 PE: 5-100, PB: 0.5-5）
   - ROE 是否在合理范围？（通常 5%-30%）
   - 增长率是否合理？（通常 0-50%，不包含异常高值）
   - 估值方法是否一致？
   - 是否有矛盾的数据点？

📊 数据验证清单（重要）：
- [ ] PE/PB 比率是否合理？
- [ ] ROE 是否在合理范围？
- [ ] 增长率是否合理？
- [ ] 估值方法是否一致？
- [ ] 是否有矛盾的数据点？
- [ ] 报告是否基于具体数据而非泛泛而谈？

⚠️ 违规后果：
- 如果基于编造数据生成观点，你的论证将被拒绝
- 如果使用不可信的报告作为论据，必须在论证中明确说明
- 必须基于可信数据，否则无法完成论证任务

你的目标是提出合理的论证，{self.goal}。利用提供的研究和数据来突出潜在的不利因素并有效反驳看涨论点。

请用中文回答，重点关注以下几个方面：

- 风险和挑战：突出市场饱和、财务不稳定或宏观经济威胁等可能阻碍股票表现的因素
- 竞争劣势：强调市场地位较弱、创新下降或来自竞争对手威胁等脆弱性
- 负面指标：使用财务数据、市场趋势或最近不利消息的证据来支持你的立场
- 反驳看涨观点：用具体数据和合理推理批判性分析看涨论点，揭露弱点或过度乐观的假设
- 参与讨论：以对话风格呈现你的论点，直接回应看涨分析师的观点并进行有效辩论，而不仅仅是列举事实

可用资源：

市场研究报告：{reports["market"]}

社交媒体情绪报告：{reports["sentiment"]}

最新世界事务新闻：{reports["news"]}

公司基本面报告：{reports["fundamentals"]}

以下是辩论：

辩论对话历史：
{history}

最后的看涨论点：{current_response}

类似情况的反思和经验教训：{past_memory_str}

请使用这些信息提供令人信服的看跌论点，反驳看涨声明，并参与动态辩论，展示投资该股票的风险和弱点。你还必须处理反思并从过去的经验教训和错误中学习。

请确保所有回答都使用中文。"""


# 工厂函数
def create_researcher(perspective: str) -> BaseResearcher:
    """
    创建研究员实例

    Args:
        perspective: 视角 (bull/bear)

    Returns:
        研究员实例
    """
    if perspective == "bull":
        return BullResearcher()
    elif perspective == "bear":
        return BearResearcher()
    else:
        raise ValueError(f"不支持的视角: {perspective}")
