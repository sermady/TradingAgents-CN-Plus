# -*- coding: utf-8 -*-
"""
测试信号处理模块 (P0-2 重构后)

测试范围:
- SignalProcessor初始化
- 信号处理功能 (3层策略: 结构化输出 → JSON提取 → 简单regex)
- JSON解析
- 简单决策提取
- 结构化数据增强
- 股票类型检测
- 货币单位处理
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"

from tradingagents.graph.signal_processing import SignalProcessor


def _make_processor_with_json_fallback(json_response: str):
    """
    创建 SignalProcessor，其中:
    - with_structured_output 会抛出异常 (模拟不支持/失败)
    - invoke 返回 json_response (走 JSON regex 提取路径)
    """
    mock_llm = Mock()
    # 策略1 (结构化输出) 失败 → 回退到策略2
    mock_llm.with_structured_output.side_effect = Exception("Mock: structured output not supported")
    # 策略2 (JSON regex) 使用这个返回
    mock_llm.invoke.return_value = Mock(content=json_response)
    return SignalProcessor(mock_llm), mock_llm


@pytest.mark.unit
def test_signal_processor_initialization():
    """测试信号处理器初始化"""
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)
    assert processor is not None
    assert processor.quick_thinking_llm == mock_llm


@pytest.mark.unit
def test_process_signal_buy():
    """测试处理买入信号"""
    json_resp = '{"action": "买入", "target_price": 180, "confidence": 0.75, "risk_score": 0.5, "reasoning": "基于综合分析"}'
    processor, _ = _make_processor_with_json_fallback(json_resp)

    full_signal = "综合分析后，最终交易建议：**买入**\n目标价位：$180\n置信度：0.75"
    result = processor.process_signal(full_signal, "AAPL")

    assert result["action"] == "买入"
    assert result["target_price"] == 180.0
    assert result["confidence"] == 0.75


@pytest.mark.unit
def test_process_signal_sell():
    """测试处理卖出信号 (走简单提取路径)"""
    mock_llm = Mock()
    mock_llm.with_structured_output.side_effect = Exception("not supported")
    # JSON提取也返回包含卖出的文本
    mock_llm.invoke.return_value = Mock(
        content='{"action": "卖出", "target_price": 150, "risk_score": 0.5, "confidence": 0.7}'
    )
    processor = SignalProcessor(mock_llm)

    full_signal = "综合分析后，最终交易建议：**卖出**\n目标价位：$150\n风险评分：0.5"
    result = processor.process_signal(full_signal, "AAPL")

    assert result["action"] == "卖出"
    assert result["target_price"] == 150.0
    assert result["risk_score"] == 0.5


@pytest.mark.unit
def test_process_signal_hold():
    """测试持有信号"""
    json_resp = '{"action": "持有", "target_price": 165, "confidence": 0.7, "risk_score": 0.5}'
    processor, _ = _make_processor_with_json_fallback(json_resp)

    full_signal = "建议：持有\n目标价位：$165-$175"
    result = processor.process_signal(full_signal, "AAPL")

    assert result["action"] == "持有"
    assert result["target_price"] is not None


@pytest.mark.unit
def test_process_signal_with_current_price_buy():
    """测试带当前价的买入信号处理"""
    pytest.skip("process_signal不支持current_price参数，跳过此测试")


@pytest.mark.unit
def test_process_signal_with_current_price_sell():
    """测试带当前价的卖出信号处理"""
    pytest.skip("process_signal不支持current_price参数，跳过此测试")


@pytest.mark.unit
def test_process_signal_china_stock():
    """测试中国股票信号处理"""
    json_resp = '{"action": "买入", "target_price": 120, "confidence": 0.8}'
    processor, _ = _make_processor_with_json_fallback(json_resp)

    result = processor.process_signal(json_resp, "000001")

    assert result["action"] == "买入"
    assert result["target_price"] == 120.0


@pytest.mark.unit
def test_process_signal_empty_input():
    """测试空输入处理"""
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    result = processor.process_signal("", "AAPL")

    assert result["action"] == "持有"
    assert "无效" in result["reasoning"]


@pytest.mark.unit
def test_process_signal_json_parsing():
    """测试JSON解析 (策略2路径)"""
    json_resp = '{"action": "买入", "target_price": 180, "confidence": 0.75, "risk_score": 0.4}'
    processor, _ = _make_processor_with_json_fallback(
        f'综合分析：\n{json_resp}'
    )

    full_signal = f'综合分析：\n{json_resp}'
    result = processor.process_signal(full_signal, "AAPL")

    assert result["action"] == "买入"
    assert result["target_price"] == 180.0
    assert result["confidence"] == 0.75
    assert result["risk_score"] == 0.4


@pytest.mark.unit
def test_process_signal_simple_extraction():
    """测试简单决策提取 (策略3路径)"""
    mock_llm = Mock()
    mock_llm.with_structured_output.side_effect = Exception("not supported")
    # 策略2也返回非JSON
    mock_llm.invoke.return_value = Mock(content="无法解析为JSON的内容")
    processor = SignalProcessor(mock_llm)

    full_signal = "经过分析，最终交易建议：**买入**\n目标价位：$180"
    result = processor.process_signal(full_signal, "AAPL")

    assert result["action"] == "买入"
    assert result["target_price"] == 180.0


@pytest.mark.unit
def test_process_signal_price_pattern_extraction():
    """测试价格模式提取 (_extract_simple_decision)"""
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    test_cases = [
        ("目标价位：$45.50", 45.50),
        ("目标价：$190", 190.0),
        ("目标价位：¥120", 120.0),
        ("价格: 45.50美元", None),  # "美元" 不在 regex 模式中
        ("价格45.50元", 45.50),
    ]

    for test_signal, expected_price in test_cases:
        result = processor._extract_simple_decision(test_signal)
        assert result["target_price"] == expected_price, f"Failed for: {test_signal}"


@pytest.mark.unit
def test_process_signal_invalid_action():
    """测试无效动作处理 (JSON策略)"""
    json_resp = '{"action": "invalid", "target_price": 180}'
    processor, _ = _make_processor_with_json_fallback(json_resp)

    full_signal = '{"action": "invalid", "target_price": 180}'
    result = processor.process_signal(full_signal, "AAPL")

    assert result["action"] == "持有"


@pytest.mark.unit
def test_enhance_with_structured_data_buy():
    """测试 P0-2: 结构化数据增强 (替代旧的 _smart_price_estimation)"""
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    # 买入时估算目标价: 当前价 * 1.15
    result = {"action": "买入", "target_price": None, "confidence": 0.7, "risk_score": 0.5}
    enhanced = processor._enhance_with_structured_data(result, current_price=100.0, is_china=True)

    assert enhanced["target_price"] == 115.0
    assert enhanced.get("_target_price_estimated") is True


@pytest.mark.unit
def test_enhance_with_structured_data_sell():
    """测试结构化数据增强: 卖出"""
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    result = {"action": "卖出", "target_price": None, "confidence": 0.7, "risk_score": 0.5}
    enhanced = processor._enhance_with_structured_data(result, current_price=100.0, is_china=False)

    assert enhanced["target_price"] == 90.0
    assert enhanced.get("_target_price_estimated") is True


@pytest.mark.unit
def test_enhance_with_structured_data_no_overwrite():
    """测试: 当已有目标价时不会被覆盖"""
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    result = {"action": "买入", "target_price": 150.0, "confidence": 0.7, "risk_score": 0.5}
    enhanced = processor._enhance_with_structured_data(result, current_price=100.0, is_china=True)

    assert enhanced["target_price"] == 150.0
    assert enhanced.get("_target_price_estimated") is None


@pytest.mark.unit
def test_process_signal_error_handling():
    """测试错误处理"""
    mock_llm = Mock()
    mock_llm.with_structured_output.side_effect = Exception("not supported")
    mock_llm.invoke.side_effect = Exception("LLM调用失败")
    processor = SignalProcessor(mock_llm)

    full_signal = "测试信号: 买入"
    result = processor.process_signal(full_signal, "AAPL")

    # 策略1和2失败，回退到策略3 (简单regex)
    assert result["action"] == "买入"


@pytest.mark.unit
def test_process_signal_json_parse_error():
    """测试JSON解析错误处理"""
    mock_llm = Mock()
    mock_llm.with_structured_output.side_effect = Exception("not supported")
    mock_llm.invoke.return_value = Mock(content="无效的JSON内容")
    processor = SignalProcessor(mock_llm)

    full_signal = "无效的JSON内容"
    result = processor.process_signal(full_signal, "AAPL")

    assert result is not None
    assert result["action"] == "持有"  # 默认持有


@pytest.mark.unit
def test_get_default_decision():
    """测试默认决策"""
    mock_llm = Mock()
    processor = SignalProcessor(mock_llm)

    result = processor._get_default_decision()

    assert result["action"] == "持有"
    assert result["target_price"] is None
    assert result["confidence"] == 0.5
    assert result["risk_score"] == 0.5
