# -*- coding: utf-8 -*-
"""报告提取工具类

统一处理从 TradingAgents 的 state 对象中提取各种报告的逻辑。
替代 simple_analysis_service.py 中重复的报告提取逻辑。
"""

from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class ReportExtractor:
    """统一报告提取工具"""

    # 标准报告字段列表
    REPORT_FIELDS = [
        "market_report",
        "sentiment_report",
        "news_report",
        "fundamentals_report",
        "technical_report",
        "china_analysis_report",
        "investment_plan",
        "trader_investment_plan",
        "final_trade_decision",
        "risk_assessment_report",
        "debate_summary",
    ]

    # 投资辩论状态字段
    INVESTMENT_DEBATE_FIELDS = [
        "bull_history",
        "bear_history",
        "bull_latest",
        "bear_latest",
        "judge_decision",
    ]

    # 风险辩论状态字段
    RISK_DEBATE_FIELDS = [
        "risky_history",
        "safe_history",
        "neutral_history",
        "judge_decision",
    ]

    # 辩论字段映射（用于报告输出）
    DEBATE_FIELD_MAPPING = {
        "bull_history": "bull_researcher",
        "bear_history": "bear_researcher",
        "judge_decision": "research_team_decision",
        "risky_history": "risky_analyst",
        "safe_history": "safe_analyst",
        "neutral_history": "neutral_analyst",
    }

    @staticmethod
    def _get_field_value(obj: Any, field: str) -> Any:
        """从对象或字典中获取字段值

        Args:
            obj: 对象或字典
            field: 字段名

        Returns:
            字段值，如果不存在则返回 None
        """
        if obj is None:
            return None
        if hasattr(obj, field):
            return getattr(obj, field)
        if isinstance(obj, dict) and field in obj:
            return obj[field]
        return None

    @classmethod
    def _extract_single_report(cls, state: Any, field: str) -> Optional[str]:
        """提取单个报告字段

        Args:
            state: State 对象或字典
            field: 报告字段名

        Returns:
            报告内容字符串，如果内容无效则返回 None
        """
        value = cls._get_field_value(state, field)

        if isinstance(value, str) and len(value.strip()) > 10:
            return value.strip()

        return None

    @classmethod
    def extract_reports(cls, state: Any) -> Dict[str, str]:
        """从 state 中提取所有报告

        Args:
            state: TradingAgents 的 state 对象或字典

        Returns:
            Dict[str, str]: 报告名称到内容的映射
        """
        reports = {}

        for field in cls.REPORT_FIELDS:
            content = cls._extract_single_report(state, field)
            if content:
                reports[field] = content
                logger.info(f"📊 [REPORTS] 提取报告: {field} - 长度: {len(content)}")
            else:
                logger.debug(f"⚠️ [REPORTS] 跳过报告: {field} - 内容为空或太短")

        return reports

    @classmethod
    def extract_debate_state(
        cls,
        state: Any,
        debate_type: str = "investment"
    ) -> Dict[str, str]:
        """提取辩论状态报告

        Args:
            state: TradingAgents 的 state 对象或字典
            debate_type: "investment" 或 "risk"

        Returns:
            Dict[str, str]: 辩论相关字段的内容
        """
        debate_state = {}

        # 确定辩论状态字段名
        if debate_type == "investment":
            state_field = "investment_debate_state"
            debate_fields = cls.INVESTMENT_DEBATE_FIELDS
        elif debate_type == "risk":
            state_field = "risk_debate_state"
            debate_fields = cls.RISK_DEBATE_FIELDS
        else:
            logger.warning(f"⚠️ 未知的辩论类型: {debate_type}")
            return debate_state

        # 获取辩论状态对象
        debate_obj = cls._get_field_value(state, state_field)
        if not debate_obj:
            logger.debug(f"⚠️ 未找到 {state_field}")
            return debate_state

        # 提取各个辩论字段
        for field in debate_fields:
            value = cls._get_field_value(debate_obj, field)

            if isinstance(value, str) and len(value.strip()) > 10:
                debate_state[field] = value.strip()
                logger.info(f"📊 [DEBATE] 提取 {debate_type} 辩论字段: {field} - 长度: {len(value.strip())}")
            elif field == "judge_decision" and debate_obj is not None:
                # 对于 judge_decision，如果没有找到字符串值，使用整个对象
                debate_state[field] = str(debate_obj)
                logger.info(f"📊 [DEBATE] 提取 {debate_type} 辩论字段: {field} (使用对象字符串)")

        return debate_state

    @classmethod
    def extract_all_content(cls, state: Any) -> Dict[str, Any]:
        """提取所有相关内容（报告 + 辩论状态）

        Args:
            state: TradingAgents 的 state 对象或字典

        Returns:
            Dict 包含:
                - reports: 标准报告
                - investment_debate: 投资辩论状态
                - risk_debate: 风险辩论状态
        """
        result = {
            "reports": {},
            "investment_debate": {},
            "risk_debate": {},
        }

        try:
            # 提取标准报告
            result["reports"] = cls.extract_reports(state)

            # 提取投资辩论状态
            investment_debate = cls.extract_debate_state(state, "investment")
            result["investment_debate"] = investment_debate

            # 提取风险辩论状态
            risk_debate = cls.extract_debate_state(state, "risk")
            result["risk_debate"] = risk_debate

            # 将辩论内容合并到 reports 中（保持向后兼容）
            for field, content in investment_debate.items():
                report_key = cls.DEBATE_FIELD_MAPPING.get(field, field)
                result["reports"][report_key] = content

            for field, content in risk_debate.items():
                report_key = cls.DEBATE_FIELD_MAPPING.get(field, field)
                # 避免覆盖投资辩论的 judge_decision
                if report_key not in result["reports"] or field != "judge_decision":
                    result["reports"][report_key] = content

            total_reports = len(result["reports"])
            logger.info(f"📊 [REPORTS] 从 state 中提取到 {total_reports} 个报告: {list(result['reports'].keys())}")

        except Exception as e:
            logger.warning(f"⚠️ 提取报告时出错: {e}")

        return result

    @classmethod
    def get_report_summary(cls, reports: Dict[str, str]) -> Dict[str, Any]:
        """获取报告摘要信息

        Args:
            reports: 报告字典

        Returns:
            包含报告统计信息的字典
        """
        if not reports:
            return {
                "total_count": 0,
                "total_length": 0,
                "average_length": 0,
                "report_names": [],
                "has_content": False,
            }

        total_count = len(reports)
        total_length = sum(len(content) for content in reports.values())
        average_length = total_length // total_count if total_count > 0 else 0

        return {
            "total_count": total_count,
            "total_length": total_length,
            "average_length": average_length,
            "report_names": list(reports.keys()),
            "has_content": total_count > 0,
        }

    @classmethod
    def extract_reports_with_fallback(
        cls,
        state: Any,
        fallback_data: Optional[Dict] = None
    ) -> Dict[str, str]:
        """提取报告，支持降级处理

        当从 state 提取失败时，尝试从 fallback_data 中提取

        Args:
            state: TradingAgents 的 state 对象或字典
            fallback_data: 降级数据源（如 decision 或 detailed_analysis）

        Returns:
            Dict[str, str]: 报告名称到内容的映射
        """
        try:
            # 首先尝试从 state 提取
            result = cls.extract_all_content(state)
            reports = result["reports"]

            if reports:
                return reports

            # 如果 state 中没有报告，尝试降级提取
            if fallback_data and isinstance(fallback_data, dict):
                logger.info("📊 降级：尝试从 fallback_data 中提取报告")
                fallback_reports = {}

                for key, value in fallback_data.items():
                    if isinstance(value, str) and len(value) > 50:
                        fallback_reports[key] = value

                if fallback_reports:
                    logger.info(f"📊 降级：从 fallback_data 中提取到 {len(fallback_reports)} 个报告")
                    return fallback_reports

        except Exception as e:
            logger.warning(f"⚠️ 提取报告时出错: {e}")

            # 尝试降级提取
            if fallback_data and isinstance(fallback_data, dict):
                try:
                    fallback_reports = {}
                    for key, value in fallback_data.items():
                        if isinstance(value, str) and len(value) > 50:
                            fallback_reports[key] = value

                    if fallback_reports:
                        logger.info(f"📊 降级：从 fallback_data 中提取到 {len(fallback_reports)} 个报告")
                        return fallback_reports

                except Exception as fallback_error:
                    logger.warning(f"⚠️ 降级提取也失败: {fallback_error}")

        return {}


class StateConverter:
    """State 对象转换工具"""

    @staticmethod
    def to_dict(state: Any) -> Dict[str, Any]:
        """将 state 对象转换为字典

        Args:
            state: State 对象或字典

        Returns:
            字典形式的 state
        """
        if state is None:
            return {}

        if isinstance(state, dict):
            return state

        # 尝试将对象转换为字典
        try:
            if hasattr(state, "__dict__"):
                return state.__dict__
            if hasattr(state, "dict"):
                return state.dict()
            if hasattr(state, "model_dump"):
                return state.model_dump()
        except Exception as e:
            logger.warning(f"⚠️ 转换 state 为字典时出错: {e}")

        # 最后尝试使用 vars
        try:
            return vars(state)
        except TypeError:
            pass

        return {}

    @staticmethod
    def get_nested_value(obj: Any, path: str, default=None):
        """获取嵌套值，支持点号路径如 'investment_debate_state.bull_history'

        Args:
            obj: 对象或字典
            path: 点号分隔的路径
            default: 默认值

        Returns:
            路径对应的值，如果不存在则返回 default
        """
        if obj is None:
            return default

        parts = path.split(".")
        current = obj

        for part in parts:
            if current is None:
                return default

            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default

        return current

    @classmethod
    def extract_nested_reports(cls, state: Any, paths: List[str]) -> Dict[str, Any]:
        """从嵌套路径中提取多个报告

        Args:
            state: State 对象或字典
            paths: 点号分隔的路径列表

        Returns:
            路径到值的映射
        """
        result = {}

        for path in paths:
            value = cls.get_nested_value(state, path)
            if value is not None:
                result[path] = value

        return result
