# -*- coding: utf-8 -*-
"""
交易图单元测试

测试 tradingagents.graph.trading_graph 模块的核心功能:
1. LLM 提供商创建
2. TradingAgentsGraph 初始化
3. 配置处理
4. 辩论轮次配置正确性
"""

import sys
import os
from unittest.mock import Mock, MagicMock, patch

# 添加项目根目录到路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)


class TestLLMProviderCreation:
    """LLM提供商创建测试类"""

    def test_google_provider_requires_api_key(self):
        """验证Google提供商需要API Key"""
        from tradingagents.graph.trading_graph import create_llm_by_provider

        # 临时清除环境变量
        original_key = os.environ.pop('GOOGLE_API_KEY', None)

        try:
            create_llm_by_provider(
                provider="google",
                model="gemini-2.5-flash",
                backend_url="https://generativelanguage.googleapis.com/v1beta",
                temperature=0.7,
                max_tokens=2000,
                timeout=60
            )
            raise AssertionError("应该抛出ValueError")
        except ValueError as e:
            assert "GOOGLE_API_KEY" in str(e), "错误信息应包含GOOGLE_API_KEY"
            print("test_google_provider_requires_api_key PASSED")
        finally:
            if original_key:
                os.environ['GOOGLE_API_KEY'] = original_key

    def test_dashscope_provider_creation(self):
        """验证DashScope提供商可以创建（使用mock）"""
        with patch.dict(os.environ, {'DASHSCOPE_API_KEY': 'test-key'}):
            from tradingagents.graph.trading_graph import create_llm_by_provider

            llm = create_llm_by_provider(
                provider="dashscope",
                model="qwen-turbo",
                backend_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                temperature=0.7,
                max_tokens=2000,
                timeout=60
            )

            assert llm is not None, "LLM实例应该被创建"
            print("test_dashscope_provider_creation PASSED")

    def test_deepseek_provider_requires_api_key(self):
        """验证DeepSeek提供商需要API Key"""
        from tradingagents.graph.trading_graph import create_llm_by_provider

        # 临时清除环境变量
        original_key = os.environ.pop('DEEPSEEK_API_KEY', None)

        try:
            create_llm_by_provider(
                provider="deepseek",
                model="deepseek-chat",
                backend_url="https://api.deepseek.com/v1",
                temperature=0.7,
                max_tokens=2000,
                timeout=60
            )
            raise AssertionError("应该抛出ValueError")
        except ValueError as e:
            assert "DEEPSEEK_API_KEY" in str(e), "错误信息应包含DEEPSEEK_API_KEY"
            print("test_deepseek_provider_requires_api_key PASSED")
        finally:
            if original_key:
                os.environ['DEEPSEEK_API_KEY'] = original_key

    def test_openai_provider_with_api_key(self):
        """验证OpenAI提供商可以使用传入的API Key"""
        from tradingagents.graph.trading_graph import create_llm_by_provider

        llm = create_llm_by_provider(
            provider="openai",
            model="gpt-4o-mini",
            backend_url="https://api.openai.com/v1",
            temperature=0.7,
            max_tokens=2000,
            timeout=60,
            api_key="test-api-key"
        )

        assert llm is not None, "LLM实例应该被创建"
        print("test_openai_provider_with_api_key PASSED")


class TestTradingAgentsGraph:
    """交易图测试类"""

    def test_default_config_values(self):
        """验证默认配置值正确"""
        from tradingagents.default_config import DEFAULT_CONFIG

        # 验证辩论轮次配置
        assert "max_debate_rounds" in DEFAULT_CONFIG, "应包含max_debate_rounds配置"
        assert "max_risk_discuss_rounds" in DEFAULT_CONFIG, "应包含max_risk_discuss_rounds配置"

        assert DEFAULT_CONFIG["max_debate_rounds"] == 3, "牛熊辩论应为3轮"
        assert DEFAULT_CONFIG["max_risk_discuss_rounds"] == 2, "风险讨论应为2轮"

        print("test_default_config_values PASSED")

    def test_analyst_tool_call_limits(self):
        """验证分析师工具调用限制配置"""
        from tradingagents.default_config import DEFAULT_CONFIG

        assert "analyst_tool_call_limits" in DEFAULT_CONFIG, "应包含工具调用限制配置"

        limits = DEFAULT_CONFIG["analyst_tool_call_limits"]
        assert limits["fundamentals"] == 1, "基本面分析师应为1次"
        assert limits["market"] == 3, "市场分析师应为3次"
        assert limits["news"] == 3, "新闻分析师应为3次"
        assert limits["social_media"] == 3, "社交媒体分析师应为3次"

        print("test_analyst_tool_call_limits PASSED")

    def test_memory_n_matches_config(self):
        """验证历史记忆检索配置"""
        from tradingagents.default_config import DEFAULT_CONFIG

        assert "memory_n_matches" in DEFAULT_CONFIG, "应包含memory_n_matches配置"
        assert DEFAULT_CONFIG["memory_n_matches"] == 5, "历史记忆检索应为5条"

        print("test_memory_n_matches_config PASSED")

    def test_llm_provider_config(self):
        """验证LLM提供商配置"""
        from tradingagents.default_config import DEFAULT_CONFIG

        assert "llm_provider" in DEFAULT_CONFIG, "应包含llm_provider配置"
        assert "deep_think_llm" in DEFAULT_CONFIG, "应包含deep_think_llm配置"
        assert "quick_think_llm" in DEFAULT_CONFIG, "应包含quick_think_llm配置"

        # 验证修复后的模型名称
        assert DEFAULT_CONFIG["deep_think_llm"] != "o4-mini", "不应使用无效的o4-mini模型"

        print("test_llm_provider_config PASSED")


class TestDebateRounds:
    """辩论轮次测试类"""

    def test_debate_count_calculation(self):
        """验证辩论计数计算正确"""
        from tradingagents.default_config import DEFAULT_CONFIG

        max_debate_rounds = DEFAULT_CONFIG["max_debate_rounds"]

        # 牛熊辩论: 每轮 = Bull发言 + Bear发言 = 2次交锋
        # 3轮 = 6次交锋
        expected_exchanges = max_debate_rounds * 2
        assert expected_exchanges == 6, f"预期6次交锋，实际{expected_exchanges}"

        print("test_debate_count_calculation PASSED")

    def test_risk_discussion_count_calculation(self):
        """验证风险讨论计数计算正确"""
        from tradingagents.default_config import DEFAULT_CONFIG

        max_risk_rounds = DEFAULT_CONFIG["max_risk_discuss_rounds"]

        # 风险讨论: 每轮 = Risky + Safe + Neutral = 3次发言
        # 2轮 = 6次发言
        expected_speeches = max_risk_rounds * 3
        assert expected_speeches == 6, f"预期6次发言，实际{expected_speeches}"

        print("test_risk_discussion_count_calculation PASSED")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("开始运行交易图单元测试")
    print("=" * 60)

    test_classes = [
        ("LLM提供商创建测试", TestLLMProviderCreation),
        ("交易图配置测试", TestTradingAgentsGraph),
        ("辩论轮次测试", TestDebateRounds),
    ]

    passed = 0
    failed = 0

    for class_name, test_class in test_classes:
        print(f"\n--- {class_name} ---")
        instance = test_class()

        for method_name in dir(instance):
            if method_name.startswith("test_"):
                print(f"\n运行: {method_name}")
                try:
                    getattr(instance, method_name)()
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
