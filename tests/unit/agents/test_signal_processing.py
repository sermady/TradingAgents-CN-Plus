# -*- coding: utf-8 -*-
"""
测试信号处理模块

测试范围:
- SignalProcessor初始化
- 信号处理功能
- JSON解析
- 简单决策提取
- 智能价格推算
- 股票类型检测
- 货币单位处理
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tradingagents.graph.signal_processing import SignalProcessor


@pytest.mark.unit
def test_signal_processor_initialization():
    """测试信号处理器初始化"""
    # Arrange
    mock_llm = Mock()

    # Act
    processor = SignalProcessor(mock_llm)

    # Assert
    assert processor is not None
    assert processor.quick_thinking_llm == mock_llm


@pytest.mark.unit
def test_process_signal_buy():
    """测试处理买入信号"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    full_signal = "综合分析后，最终交易建议：**买入**\n目标价位：$180\n置信度：0.75"

    # Act
    result = processor.process_signal(full_signal, "AAPL")

    # Assert
    assert result["action"] == "买入"
    assert result["target_price"] == 180.0
    assert result["confidence"] == 0.75


@pytest.mark.unit
def test_process_signal_sell():
    """测试处理卖出信号"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    full_signal = "综合分析后，最终交易建议：**卖出**\n目标价位：$150\n风险评分：0.5"

    # Act
    result = processor.process_signal(full_signal, "AAPL")

    # Assert
    assert result["action"] == "卖出"
    assert result["target_price"] == 150.0
    assert result["risk_score"] == 0.5


@pytest.mark.unit
def test_process_signal_hold():
    """测试持有信号"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    full_signal = "建议：持有\n目标价位：$165-$175"

    # Act
    result = processor.process_signal(full_signal, "AAPL")

    # Assert
    assert result["action"] == "持有"
    assert result["target_price_range"] is not None


@pytest.mark.unit
def test_process_signal_with_current_price_buy():
    """测试带当前价的买入信号处理"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    full_signal = "建议：买入"  # 没有明确目标价
    current_price = 150.0

    # Act
    result = processor.process_signal(full_signal, "AAPL", current_price)

    # Assert
    # 买入时目标价 = 当前价 * 1.15
    expected_target = 150.0 * 1.15
    assert abs(result["target_price"] - expected_target) < 0.01


@pytest.mark.unit
def test_process_signal_with_current_price_sell():
    """测试带当前价的卖出信号处理"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    full_signal = "建议：卖出"  # 没有明确目标价
    current_price = 150.0

    # Act
    result = processor.process_signal(full_signal, "AAPL", current_price)

    # Assert
    # 卖出时目标价 = 当前价 * 0.9
    expected_target = 150.0 * 0.9
    assert abs(result["target_price"] - expected_target) < 0.01


@pytest.mark.unit
def test_process_signal_china_stock():
    """测试中国股票信号处理"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    # 模拟JSON响应，包含人民币价格
    mock_llm.invoke.return_value.content = (
        '{"action": "买入", "target_price": 120, "confidence": 0.8}'
    )
    full_signal = mock_llm.invoke.return_value.content

    # Act
    result = processor.process_signal(full_signal, "000001")

    # Assert
    assert result["action"] == "买入"
    assert result["target_price"] == 120.0


@pytest.mark.unit
def test_process_signal_empty_input():
    """测试空输入处理"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    # Act
    result = processor.process_signal("", "AAPL")

    # Assert
    assert result["action"] == "持有"  # 默认持有
    assert "输入信号无效" in result["reasoning"]


@pytest.mark.unit
def test_process_signal_json_parsing():
    """测试JSON解析"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    # 模拟包含JSON的响应
    full_signal = '综合分析：\n{"action": "买入", "target_price": 180, "confidence": 0.75, "risk_score": 0.4}'

    # Mock LLM invoke
    mock_llm.invoke.return_value = Mock(content=full_signal)

    # Act
    result = processor.process_signal(full_signal, "AAPL")

    # Assert
    assert result["action"] == "买入"
    assert result["target_price"] == 180.0
    assert result["confidence"] == 0.75
    assert result["risk_score"] == 0.4


@pytest.mark.unit
def test_process_signal_simple_extraction():
    """测试简单决策提取"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    # 模拟没有JSON的简单文本响应
    full_signal = "经过分析，最终交易建议：**买入**\n目标价位：$180"

    # Mock LLM invoke with non-JSON response
    mock_llm.invoke.return_value = Mock(content=full_signal)

    # Act
    result = processor.process_signal(full_signal, "AAPL")

    # Assert
    # 应该回退到简单提取
    assert result["action"] == "买入"
    assert result["target_price"] == 180.0


@pytest.mark.unit
def test_process_signal_price_pattern_extraction():
    """测试价格模式提取"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    # 测试各种价格格式
    test_cases = [
        ("目标价位：$45.50", 45.50),
        ("目标价：$190", 190.0),
        ("目标价位：¥120", 120.0),
        ("价格: 45.50美元", 45.50),
        ("价格45.50元", 45.50),
    ]

    for test_signal, expected_price in test_cases:
        result = processor._extract_simple_decision(test_signal)

        # Assert
        assert result["target_price"] == expected_price


@pytest.mark.unit
def test_process_signal_invalid_action():
    """测试无效动作处理"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    # 模拟JSON中的无效动作
    full_signal = '{"action": "invalid", "target_price": 180}'

    mock_llm.invoke.return_value = Mock(content=full_signal)

    # Act
    result = processor.process_signal(full_signal, "AAPL")

    # Assert
    # 无效动作应该被映射为持有
    assert result["action"] == "持有"


@pytest.mark.unit
def test_process_smart_price_estimation():
    """测试智能价格推算"""
    # Arrange
    processor = SignalProcessor(mock_llm)

    # 测试买入时的智能推算
    current_price = 150.0
    test_cases = [
        ("建议：买入，涨幅15%", 172.5),  # 当前价 * 1.15
        ("建议：买入，涨幅20%", 180.0),  # 当前价 * 1.2
        ("建议：卖出，跌幅10%", 135.0),  # 当前价 * 0.9
    ]

    for text, expected in test_cases:
        result = processor._smart_price_estimation(text, "买入", is_china=False)

        # Assert
        assert abs(result - expected) < 0.01


@pytest.mark.unit
def test_process_signal_error_handling():
    """测试错误处理"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    # 模拟LLM调用失败
    mock_llm.invoke.side_effect = Exception("LLM调用失败")

    full_signal = "测试信号"

    # Act
    result = processor.process_signal(full_signal, "AAPL")

    # Assert
    # 应该回退到默认决策
    assert result["action"] == "持有"


@pytest.mark.unit
def test_process_signal_json_parse_error():
    """测试JSON解析错误处理"""
    # Arrange
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    # 模拟无法解析的JSON
    full_signal = "无效的JSON内容"

    mock_llm.invoke.return_value = Mock(content=full_signal)

    # Act
    result = processor.process_signal(full_signal, "AAPL")

    # Assert
    # 解析失败时应该回退到简单提取
    assert result is not None
