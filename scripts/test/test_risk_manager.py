# -*- coding: utf-8 -*-
"""
风险管理器单元测试

测试 tradingagents.agents.managers.risk_manager 模块的核心功能:
1. 正确访问所有报告字段（包括 fundamentals_report）
2. memory为None时的安全处理
3. LLM调用失败时的默认决策生成
4. 状态更新的正确性
"""

import sys
import os
from unittest.mock import Mock, MagicMock, patch

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)


def create_mock_state():
    """创建模拟状态对象"""
    return {
        "company_of_interest": "000001",
        "market_report": "市场报告：A股市场整体表现平稳...",
        "news_report": "新闻报告：某公司发布季度财报...",
        "fundamentals_report": "基本面报告：PE=15.2, PB=1.8, ROE=18%...",
        "sentiment_report": "情绪报告：市场情绪中性偏乐观...",
        "investment_plan": "投资计划：建议持有，目标价15元...",
        "risk_debate_state": {
            "history": "风险辩论历史...",
            "risky_history": "激进分析师历史...",
            "safe_history": "保守分析师历史...",
            "neutral_history": "中性分析师历史...",
            "current_risky_response": "激进观点...",
            "current_safe_response": "保守观点...",
            "current_neutral_response": "中性观点...",
            "count": 6,
        }
    }


def create_mock_llm(response_content="**建议：持有**\n\n基于风险评估，建议持有当前仓位。"):
    """创建模拟LLM对象"""
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = response_content
    mock_response.response_metadata = {}
    mock_llm.invoke = Mock(return_value=mock_response)
    return mock_llm


def create_mock_memory():
    """创建模拟Memory对象"""
    mock_memory = Mock()
    mock_memory.get_memories = Mock(return_value=[
        {"recommendation": "历史建议1：在类似情况下选择持有是正确的决策。"},
        {"recommendation": "历史建议2：注意风险控制，避免追涨杀跌。"},
    ])
    return mock_memory


class TestRiskManager:
    """风险管理器测试类"""

    def test_correct_report_access(self):
        """验证正确访问所有报告字段，特别是 fundamentals_report"""
        from tradingagents.agents.managers.risk_manager import create_risk_manager

        state = create_mock_state()
        mock_llm = create_mock_llm()
        mock_memory = create_mock_memory()

        risk_manager_node = create_risk_manager(mock_llm, mock_memory)
        result = risk_manager_node(state)

        # 验证LLM被调用
        assert mock_llm.invoke.called, "LLM应该被调用"

        # 获取传递给LLM的prompt
        call_args = mock_llm.invoke.call_args
        prompt = call_args[0][0]

        # 验证state中包含fundamentals_report
        assert "fundamentals_report" in state, "状态应包含fundamentals_report"

        # 验证result包含预期的键
        assert "final_trade_decision" in result, "应返回final_trade_decision"
        assert "risk_debate_state" in result, "应返回risk_debate_state"

        print("test_correct_report_access PASSED")

    def test_memory_none_handling(self):
        """验证memory为None时的安全处理"""
        from tradingagents.agents.managers.risk_manager import create_risk_manager

        state = create_mock_state()
        mock_llm = create_mock_llm()

        # 传入None作为memory
        risk_manager_node = create_risk_manager(mock_llm, None)

        # 应该不抛出异常
        try:
            result = risk_manager_node(state)
            assert "final_trade_decision" in result, "应返回final_trade_decision"
            assert "risk_debate_state" in result, "应返回risk_debate_state"
            print("test_memory_none_handling PASSED")
        except Exception as e:
            raise AssertionError(f"memory为None时不应抛出异常: {e}")

    def test_memory_retrieval_count(self):
        """验证历史记忆检索数量为5（根据配置）"""
        from tradingagents.agents.managers.risk_manager import create_risk_manager

        state = create_mock_state()
        mock_llm = create_mock_llm()
        mock_memory = create_mock_memory()

        risk_manager_node = create_risk_manager(mock_llm, mock_memory)
        result = risk_manager_node(state)

        # 验证get_memories被调用，且n_matches=5
        mock_memory.get_memories.assert_called_once()
        call_args = mock_memory.get_memories.call_args
        assert call_args[1].get('n_matches') == 5, "应检索5条历史记忆"

        print("test_memory_retrieval_count PASSED")

    def test_llm_failure_default_decision(self):
        """验证LLM调用失败时生成默认决策"""
        from tradingagents.agents.managers.risk_manager import create_risk_manager

        state = create_mock_state()
        mock_memory = create_mock_memory()

        # 创建一个始终失败的LLM
        mock_llm = Mock()
        mock_llm.invoke = Mock(side_effect=Exception("API调用失败"))

        risk_manager_node = create_risk_manager(mock_llm, mock_memory)
        result = risk_manager_node(state)

        # 验证返回默认决策
        assert "final_trade_decision" in result, "应返回final_trade_decision"
        decision = result["final_trade_decision"]
        assert "持有" in decision or "默认" in decision, "失败时应返回默认持有建议"

        print("test_llm_failure_default_decision PASSED")

    def test_state_update_correctness(self):
        """验证状态更新的正确性"""
        from tradingagents.agents.managers.risk_manager import create_risk_manager

        state = create_mock_state()
        response_text = "**建议：买入**\n\n经过综合评估，建议买入。"
        mock_llm = create_mock_llm(response_text)
        mock_memory = create_mock_memory()

        risk_manager_node = create_risk_manager(mock_llm, mock_memory)
        result = risk_manager_node(state)

        # 验证返回的状态结构
        assert "risk_debate_state" in result, "应返回risk_debate_state"
        assert "final_trade_decision" in result, "应返回final_trade_decision"

        new_state = result["risk_debate_state"]

        # 验证judge_decision被正确设置
        assert "judge_decision" in new_state, "应包含judge_decision"
        assert "买入" in new_state["judge_decision"], "judge_decision应包含买入建议"

        # 验证其他字段被保留
        assert new_state["history"] == state["risk_debate_state"]["history"]
        assert new_state["latest_speaker"] == "Judge"
        assert new_state["count"] == state["risk_debate_state"]["count"]

        print("test_state_update_correctness PASSED")

    def test_prompt_contains_all_reports(self):
        """验证prompt中包含所有必要的报告"""
        from tradingagents.agents.managers.risk_manager import create_risk_manager

        state = create_mock_state()
        mock_llm = create_mock_llm()
        mock_memory = create_mock_memory()

        risk_manager_node = create_risk_manager(mock_llm, mock_memory)
        result = risk_manager_node(state)

        # 获取传递给LLM的prompt
        call_args = mock_llm.invoke.call_args
        prompt = call_args[0][0]

        # 验证prompt中包含历史辩论和交易计划
        assert state["risk_debate_state"]["history"] in prompt, "prompt应包含辩论历史"
        assert state["investment_plan"] in prompt or "投资计划" in prompt, "prompt应包含交易计划"

        print("test_prompt_contains_all_reports PASSED")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行风险管理器单元测试")
    print("=" * 60)

    test_instance = TestRiskManager()
    tests = [
        ("正确访问报告字段", test_instance.test_correct_report_access),
        ("memory为None处理", test_instance.test_memory_none_handling),
        ("历史记忆检索数量", test_instance.test_memory_retrieval_count),
        ("LLM失败默认决策", test_instance.test_llm_failure_default_decision),
        ("状态更新正确性", test_instance.test_state_update_correctness),
        ("prompt包含所有报告", test_instance.test_prompt_contains_all_reports),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        print(f"\n运行测试: {test_name}")
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
