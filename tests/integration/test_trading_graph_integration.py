# -*- coding: utf-8 -*-
"""
TradingAgentsGraph 集成测试

测试核心交易逻辑流程，使用 Mock 模拟 LLM 调用
"""

import pytest
import os
import sys
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# 确保项目根目录在路径中
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)


@pytest.mark.integration
class TestTradingAgentsGraph:
    """TradingAgentsGraph 集成测试类"""

    @pytest.fixture
    def mock_config(self):
        """创建测试配置"""
        return {
            "project_dir": os.path.join(project_root, "test_data"),
            "llm_provider": "openai",
            "quick_think_llm": "gpt-3.5-turbo",
            "deep_think_llm": "gpt-4",
            "backend_url": "https://api.openai.com/v1",
            "quick_model_config": {
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 180,
            },
            "deep_model_config": {
                "max_tokens": 4000,
                "temperature": 0.7,
                "timeout": 180,
            },
            "use_deep_model_for_trader": False,
            "use_deep_model_for_researchers": False,
            "use_deep_model_for_risk_mgmt": False,
            "analysis_date": datetime.now().strftime("%Y-%m-%d"),
        }

    @pytest.fixture
    def mock_llm_response(self):
        """模拟 LLM 响应"""

        def create_mock_response(content: str):
            mock = Mock()
            mock.content = content
            return mock

        return create_mock_response

    @pytest.fixture
    def sample_market_data(self):
        """示例市场数据"""
        return {
            "current_price": 15.50,
            "open": 15.20,
            "high": 15.80,
            "low": 15.10,
            "volume": 1500000,
            "ma5": 15.30,
            "ma10": 15.40,
            "ma20": 15.25,
        }

    def test_trading_graph_initialization(self, mock_config):
        """测试 TradingAgentsGraph 初始化"""
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        # 使用 patch 来模拟 LLM 初始化
        with patch(
            "tradingagents.graph.trading_graph.create_llm_by_provider"
        ) as mock_create_llm:
            mock_llm = Mock()
            mock_create_llm.return_value = mock_llm

            # 创建实例
            graph = TradingAgentsGraph(
                selected_analysts=["market", "fundamentals"], config=mock_config
            )

            # 验证属性
            assert graph.selected_analysts == ["market", "fundamentals"]
            assert graph.config == mock_config
            assert graph.debug == False

    def test_trading_graph_initialization_with_analysts(self, mock_config):
        """测试不同分析师组合的初始化"""
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        with patch(
            "tradingagents.graph.trading_graph.create_llm_by_provider"
        ) as mock_create_llm:
            mock_create_llm.return_value = Mock()

            # 测试所有分析师
            all_analysts = ["market", "social", "news", "fundamentals", "china"]
            graph = TradingAgentsGraph(
                selected_analysts=all_analysts, config=mock_config
            )
            assert graph.selected_analysts == all_analysts

            # 测试部分分析师
            partial_analysts = ["market", "fundamentals"]
            graph2 = TradingAgentsGraph(
                selected_analysts=partial_analysts, config=mock_config
            )
            assert graph2.selected_analysts == partial_analysts

    def test_trading_graph_config_setup(self, mock_config):
        """测试配置设置"""
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        with patch(
            "tradingagents.graph.trading_graph.create_llm_by_provider"
        ) as mock_create_llm:
            mock_create_llm.return_value = Mock()

            graph = TradingAgentsGraph(config=mock_config)

            # 验证配置被正确设置
            assert graph.config["llm_provider"] == "openai"
            assert graph.config["quick_think_llm"] == "gpt-3.5-turbo"
            assert graph.config["deep_think_llm"] == "gpt-4"


@pytest.mark.integration
class TestTradingDecisionFlow:
    """交易决策流程集成测试"""

    @pytest.fixture
    def mock_trading_decision(self):
        """模拟交易决策数据"""
        return {
            "recommendation": "买入",
            "target_price": 18.50,
            "confidence": 0.75,
            "risk_score": 0.4,
            "stop_loss": 16.50,
            "position_suggestion": "中等仓位 (40-60%)",
            "time_horizon": "1-3个月",
            "warnings": [],
        }

    def test_extract_trading_decision_structure(self, mock_trading_decision):
        """测试交易决策数据结构完整性"""
        # 验证必需字段
        required_fields = [
            "recommendation",
            "target_price",
            "confidence",
            "risk_score",
            "stop_loss",
            "position_suggestion",
            "time_horizon",
        ]

        for field in required_fields:
            assert field in mock_trading_decision, f"缺少必需字段: {field}"

    def test_trading_decision_validation(self, mock_trading_decision):
        """测试交易决策验证逻辑"""
        # 验证置信度范围
        assert 0 <= mock_trading_decision["confidence"] <= 1

        # 验证风险评分范围
        assert 0 <= mock_trading_decision["risk_score"] <= 1

        # 验证目标价为正数
        assert mock_trading_decision["target_price"] > 0

        # 验证止损价低于目标价
        assert (
            mock_trading_decision["stop_loss"] < mock_trading_decision["target_price"]
        )


@pytest.mark.integration
class TestAnalystIntegration:
    """分析师集成测试"""

    @pytest.fixture
    def analyst_configs(self):
        """分析师配置数据"""
        return {
            "market": {
                "name": "MarketAnalyst",
                "data_requirements": ["price", "volume", "indicators"],
            },
            "fundamentals": {
                "name": "FundamentalsAnalyst",
                "data_requirements": ["financial_statements", "ratios"],
            },
            "news": {"name": "NewsAnalyst", "data_requirements": ["news", "sentiment"]},
            "social": {
                "name": "SocialMediaAnalyst",
                "data_requirements": ["social_sentiment", "trends"],
            },
            "china": {
                "name": "ChinaMarketAnalyst",
                "data_requirements": ["a_share_specifics", "policy"],
            },
        }

    def test_analyst_data_requirements(self, analyst_configs):
        """测试分析师数据需求定义"""
        for analyst_type, config in analyst_configs.items():
            assert "name" in config, f"{analyst_type} 缺少名称"
            assert "data_requirements" in config, f"{analyst_type} 缺少数据需求"
            assert len(config["data_requirements"]) > 0, f"{analyst_type} 数据需求为空"


@pytest.mark.unit
def test_memory_text_truncation():
    """测试文本截断功能"""
    from tradingagents.agents.utils.memory import FinancialSituationMemory

    # 创建模拟配置
    config = {
        "llm_provider": "openai",
        "embedding": "text-embedding-3-small",
        "backend_url": "http://localhost:8000/v1",
    }

    memory = FinancialSituationMemory("test_agent", config)

    # 测试正常文本（不需要截断）
    short_text = "这是一个短文本。"
    result, was_truncated = memory._smart_text_truncation(short_text, max_length=100)
    assert result == short_text
    assert was_truncated == False

    # 测试长文本截断
    long_text = "这是一个句子。" * 1000  # 约8000字符
    result, was_truncated = memory._smart_text_truncation(long_text, max_length=1000)
    assert len(result) <= 1000
    assert was_truncated == True


@pytest.mark.unit
def test_memory_llm_extraction_fallback():
    """测试 LLM 提炼失败时的回退逻辑"""
    from tradingagents.agents.utils.memory import FinancialSituationMemory

    config = {
        "llm_provider": "openai",
        "embedding": "text-embedding-3-small",
        "backend_url": "http://localhost:8000/v1",
    }

    memory = FinancialSituationMemory("test_agent", config)

    # 测试当 client 为 DISABLED 时的回退
    memory.client = "DISABLED"

    long_text = "测试文本。" * 3000  # 约18000字符
    result = memory._extract_key_info_with_llm(long_text, max_length=8000)

    # 验证结果不为空且长度符合要求
    assert result is not None
    assert len(result) <= 8000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
