# -*- coding: utf-8 -*-
"""
Market Analyst 单元测试

测试市场分析师的核心功能：
- 技术指标计算
- 市场分析师节点执行
- 边界情况和错误处理
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch

from tradingagents.technical.indicators import TechnicalIndicators


@pytest.mark.unit
def test_technical_indicators_init():
    """测试技术指标计算器初始化"""
    indicator = TechnicalIndicators()
    assert indicator is not None


@pytest.mark.unit
def test_rsi_calculation():
    """测试RSI计算"""
    indicator = TechnicalIndicators()

    prices = [10.0 + i * 0.1 for i in range(50)]
    df = pd.DataFrame({"close": prices})

    result = indicator.calculate_rsi(df, period=14)

    assert result is not None
    assert "rsi14" in result.columns
    rsi_value = result["rsi14"].iloc[-1]
    if not pd.isna(rsi_value):
        assert 0 <= rsi_value <= 100


@pytest.mark.unit
def test_macd_calculation():
    """测试MACD计算"""
    indicator = TechnicalIndicators()

    prices = [10.0 + i * 0.1 for i in range(50)]
    df = pd.DataFrame({"close": prices})

    result = indicator.calculate_macd(df)

    assert result is not None
    assert "macd_dif" in result.columns
    assert "macd_dea" in result.columns
    assert "macd" in result.columns


@pytest.mark.unit
def test_insufficient_data_ma():
    """测试数据不足情况"""
    indicator = TechnicalIndicators()

    prices = [10.0, 10.1, 10.2]
    df = pd.DataFrame({"close": prices})

    result = indicator.calculate_ma(df, periods=[5])

    assert result is not None
    assert "ma5" in result.columns


@pytest.mark.unit
def test_empty_data():
    """测试空数据情况"""
    indicator = TechnicalIndicators()

    df = pd.DataFrame({"close": []})

    result = indicator.calculate_ma(df, periods=[5])

    assert result is not None


# =============================================================================
# 市场分析师节点测试 - 边界情况和错误处理
# =============================================================================


@pytest.mark.unit
@patch("tradingagents.agents.analysts.market_analyst.get_company_name")
@patch("tradingagents.agents.analysts.market_analyst.StockUtils")
def test_market_analyst_node_creation(mock_stock_utils, mock_get_name):
    """测试市场分析师节点创建"""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst

    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {"market_name": "深圳A股"}

    mock_llm = Mock()
    analyst_node = create_market_analyst(mock_llm)

    assert analyst_node is not None
    assert callable(analyst_node)


@pytest.mark.unit
@patch("tradingagents.agents.analysts.market_analyst.get_company_name")
@patch("tradingagents.agents.analysts.market_analyst.StockUtils")
def test_market_analyst_with_valid_data(mock_stock_utils, mock_get_name):
    """测试市场数据可用时正常生成报告"""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst

    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {"market_name": "深圳A股"}

    mock_response = Mock()
    mock_response.content = "# 技术分析报告\n\n## 趋势分析\n上升趋势。"
    mock_llm = Mock()
    mock_llm.invoke.return_value = mock_response

    analyst_node = create_market_analyst(mock_llm)

    state = {
        "trade_date": "2024-06-01",
        "company_of_interest": "000001",
        "market_data": "MA5: 10.5\nMA10: 10.2\nRSI: 65\n成交量: 15000手",
        "data_quality_score": 0.9,
        "data_sources": {"market": "tushare"},
        "data_issues": {},
    }

    result = analyst_node(state)

    assert "market_report" in result
    assert result["market_report"] == mock_response.content
    mock_llm.invoke.assert_called_once()


@pytest.mark.unit
@patch("tradingagents.agents.analysts.market_analyst.get_company_name")
@patch("tradingagents.agents.analysts.market_analyst.StockUtils")
def test_market_analyst_volume_unit_in_prompt(mock_stock_utils, mock_get_name):
    """测试提示词中包含成交量单位说明"""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst

    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {"market_name": "深圳A股"}

    mock_response = Mock()
    mock_response.content = "技术分析报告"
    mock_llm = Mock()
    mock_llm.invoke.return_value = mock_response

    analyst_node = create_market_analyst(mock_llm)

    state = {
        "trade_date": "2024-06-01",
        "company_of_interest": "000001",
        "market_data": "成交量: 15000手",
        "data_quality_score": 0.9,
        "data_sources": {"market": "tushare"},
        "data_issues": {},
    }

    result = analyst_node(state)

    # 验证LLM被调用，且提示词中包含成交量单位
    assert "market_report" in result
    mock_llm.invoke.assert_called_once()

    # 检查调用参数中包含成交量单位说明
    call_args = mock_llm.invoke.call_args
    messages = call_args[0][0]
    system_message = messages[0][1]
    assert "手" in system_message
    assert "1手=100股" in system_message


@pytest.mark.unit
@patch("tradingagents.agents.analysts.market_analyst.get_company_name")
@patch("tradingagents.agents.analysts.market_analyst.StockUtils")
def test_market_analyst_data_unavailable(mock_stock_utils, mock_get_name):
    """测试市场数据不可用时生成警告报告"""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst

    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {"market_name": "深圳A股"}

    mock_response = Mock()
    mock_response.content = "技术分析报告（数据有限）"
    mock_llm = Mock()
    mock_llm.invoke.return_value = mock_response

    analyst_node = create_market_analyst(mock_llm)

    state = {
        "trade_date": "2024-06-01",
        "company_of_interest": "000001",
        "market_data": "❌ 数据获取失败",
        "data_quality_score": 0.0,
        "data_sources": {"market": "failed"},
        "data_issues": {"market": [{"message": "连接超时"}]},
    }

    result = analyst_node(state)

    assert "market_report" in result
    # 即使数据不可用，市场分析师仍然调用LLM（与社交媒体分析师不同）
    mock_llm.invoke.assert_called_once()


@pytest.mark.unit
@patch("tradingagents.agents.analysts.market_analyst.get_company_name")
@patch("tradingagents.agents.analysts.market_analyst.StockUtils")
def test_market_analyst_empty_data(mock_stock_utils, mock_get_name):
    """测试空市场数据时生成警告报告"""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst

    mock_get_name.return_value = "浦发银行"
    mock_stock_utils.get_market_info.return_value = {"market_name": "上海A股"}

    mock_response = Mock()
    mock_response.content = "技术分析报告（无数据）"
    mock_llm = Mock()
    mock_llm.invoke.return_value = mock_response

    analyst_node = create_market_analyst(mock_llm)

    state = {
        "trade_date": "2024-06-01",
        "company_of_interest": "600000",
        "market_data": "",
        "data_quality_score": 0.0,
        "data_sources": {},
        "data_issues": {},
    }

    result = analyst_node(state)

    assert "market_report" in result
    mock_llm.invoke.assert_called_once()


@pytest.mark.unit
@patch("tradingagents.agents.analysts.market_analyst.get_company_name")
@patch("tradingagents.agents.analysts.market_analyst.StockUtils")
def test_market_analyst_with_data_issues(mock_stock_utils, mock_get_name):
    """测试有数据质量问题时记录日志"""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst

    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {"market_name": "深圳A股"}

    mock_response = Mock()
    mock_response.content = "技术分析报告"
    mock_llm = Mock()
    mock_llm.invoke.return_value = mock_response

    analyst_node = create_market_analyst(mock_llm)

    state = {
        "trade_date": "2024-06-01",
        "company_of_interest": "000001",
        "market_data": "MA5: 10.5\nRSI: 65",
        "data_quality_score": 0.7,
        "data_sources": {"market": "akshare"},
        "data_issues": {
            "market": [
                {"message": "MA10数据缺失"},
                {"message": "成交量数据不完整"},
            ]
        },
    }

    result = analyst_node(state)

    # 即使有数据问题，仍然继续分析
    assert "market_report" in result
    mock_llm.invoke.assert_called_once()


@pytest.mark.unit
@patch("tradingagents.agents.analysts.market_analyst.get_company_name")
@patch("tradingagents.agents.analysts.market_analyst.StockUtils")
def test_market_analyst_different_data_sources(mock_stock_utils, mock_get_name):
    """测试不同数据源的处理（tushare/akshare/baostock）"""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst

    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {"market_name": "深圳A股"}

    data_sources = ["tushare", "akshare", "baostock"]

    for source in data_sources:
        mock_response = Mock()
        mock_response.content = f"{source}数据源分析报告"
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response

        analyst_node = create_market_analyst(mock_llm)

        state = {
            "trade_date": "2024-06-01",
            "company_of_interest": "000001",
            "market_data": "MA5: 10.5\n成交量: 15000手",
            "data_quality_score": 0.85,
            "data_sources": {"market": source},
            "data_issues": {},
        }

        result = analyst_node(state)

        assert "market_report" in result
        # 验证数据源信息被传递到提示词
        call_args = mock_llm.invoke.call_args
        messages = call_args[0][0]
        system_message = messages[0][1]
        assert source in system_message


@pytest.mark.unit
@patch("tradingagents.agents.analysts.market_analyst.get_company_name")
@patch("tradingagents.agents.analysts.market_analyst.StockUtils")
def test_market_analyst_llm_error(mock_stock_utils, mock_get_name):
    """测试LLM调用失败时的错误处理"""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst

    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {"market_name": "深圳A股"}

    mock_llm = Mock()
    mock_llm.invoke.side_effect = Exception("API调用失败")

    analyst_node = create_market_analyst(mock_llm)

    state = {
        "trade_date": "2024-06-01",
        "company_of_interest": "000001",
        "market_data": "MA5: 10.5\nRSI: 65",
        "data_quality_score": 0.9,
        "data_sources": {"market": "tushare"},
        "data_issues": {},
    }

    result = analyst_node(state)

    # 应该返回错误信息而不是抛出异常
    assert "market_report" in result
    assert "❌ 技术分析失败" in result["market_report"]
    assert "API调用失败" in result["market_report"]


@pytest.mark.unit
@patch("tradingagents.agents.analysts.market_analyst.get_company_name")
@patch("tradingagents.agents.analysts.market_analyst.StockUtils")
def test_market_analyst_volume_ratio_analysis(mock_stock_utils, mock_get_name):
    """测试量比分析在提示词中的说明"""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst

    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {"market_name": "深圳A股"}

    mock_response = Mock()
    mock_response.content = "量比分析报告"
    mock_llm = Mock()
    mock_llm.invoke.return_value = mock_response

    analyst_node = create_market_analyst(mock_llm)

    # 测试放量情况（量比>=1.5）
    state = {
        "trade_date": "2024-06-01",
        "company_of_interest": "000001",
        "market_data": (
            "当前价: 11.00\n"
            "成交量: 25000手\n"
            "5日均量: 10000手\n"
            "量比: 2.5"
        ),
        "data_quality_score": 0.9,
        "data_sources": {"market": "tushare"},
        "data_issues": {},
    }

    result = analyst_node(state)

    assert "market_report" in result
    mock_llm.invoke.assert_called_once()

    # 验证提示词中包含量比分析说明
    call_args = mock_llm.invoke.call_args
    messages = call_args[0][0]
    system_message = messages[0][1]
    assert "量比" in system_message
    assert "放量" in system_message


@pytest.mark.unit
@patch("tradingagents.agents.analysts.market_analyst.get_company_name")
@patch("tradingagents.agents.analysts.market_analyst.StockUtils")
def test_market_analyst_return_format(mock_stock_utils, mock_get_name):
    """测试返回格式一致性"""
    from tradingagents.agents.analysts.market_analyst import create_market_analyst

    mock_get_name.return_value = "平安银行"
    mock_stock_utils.get_market_info.return_value = {"market_name": "深圳A股"}

    mock_response = Mock()
    mock_response.content = "技术分析报告"
    mock_llm = Mock()
    mock_llm.invoke.return_value = mock_response

    analyst_node = create_market_analyst(mock_llm)

    state = {
        "trade_date": "2024-06-01",
        "company_of_interest": "000001",
        "market_data": "MA5: 10.5",
        "data_quality_score": 0.9,
        "data_sources": {},
        "data_issues": {},
    }

    result = analyst_node(state)

    assert "market_report" in result
    assert "messages" in result
    assert isinstance(result["messages"], list)
    assert len(result["messages"]) == 1
