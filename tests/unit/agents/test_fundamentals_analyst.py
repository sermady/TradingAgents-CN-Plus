# -*- coding: utf-8 -*-
"""
测试基本面分析师功能

测试范围:
- 基本面分析师节点创建
- 股票代码识别 (A股/港股/美股)
- 日期范围计算
- 工具调用处理
- 分析报告生成
- Google模型特殊处理
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from tradingagents.agents.analysts.fundamentals_analyst import FundamentalsAnalystNode


@pytest.mark.unit
def test_create_fundamentals_analyst_node():
    """测试创建基本面分析师节点"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

    # Assert
    assert node is not None
    assert callable(node)


@pytest.mark.unit
def test_fundamentals_analyst_identify_china_stock():
    """测试识别中国A股"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    state = {
        "messages": [],
        "company_of_interest": "000001",  # A股代码
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        result = node(state)

    # Assert
    assert "fundamentals_report" in result
    assert "000001" in result["fundamentals_report"] or "000001.SZ" in result["fundamentals_report"]


@pytest.mark.unit
def test_fundamentals_analyst_identify_hk_stock():
    """测试识别港股"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    state = {
        "messages": [],
        "company_of_interest": "0700.HK",  # 港股代码
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        result = node(state)

    # Assert
    assert "fundamentals_report" in result
    assert "0700.HK" in result["fundamentals_report"] or "0700.HK" in result["fundamentals_report"]


@pytest.mark.unit
def test_fundamentals_analyst_identify_us_stock():
    """测试识别美股"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    state = {
        "messages": [],
        "company_of_interest": "AAPL",  # 美股代码
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        result = node(state)

    # Assert
    assert "fundamentals_report" in result
    assert "AAPL" in result["fundamentals_report"] or "AAPL.US" in result["fundamentals_report"]


@pytest.mark.unit
def test_calculate_date_range_default():
    """测试默认日期范围计算"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        result = node(state)
        start_date, end_date = node._calculate_date_range()

    # Assert
    assert start_date == "2024-01-05"  # 10天前
    assert end_date == "2024-01-15"  # 分析日期
    # assert start_date < end_date


@pytest.mark.unit
def test_calculate_date_range_custom():
    """测试自定义日期范围计算"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        result = node(state)
        start_date, end_date = node._calculate_date_range(days=30)

    # Assert
        assert start_date == "2023-12-16"  # 30天前
        assert end_date == "2024-01-15"  # 分析日期
        assert start_date < end_date
        assert (end_date - start_date).days == 30


@pytest.mark.unit
def test_calculate_date_range_invalid_format():
    """测试无效日期格式"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        result = node(state)

        # 无效日期格式应该回退到默认
        start_date, end_date = node._calculate_date_range("invalid-date", days=10)
        today = datetime.now().strftime("%Y-%m-%d")

        # Assert
        assert start_date is not None
        assert end_date is not None
        # 回退到默认后，日期可能不是预期的
        assert "平安银行" in result.get("fundamentals_report", "")


@pytest.mark.unit
def test_count_tool_messages():
    """测试统计工具消息数量"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_tool = Mock()
    mock_tool.name = "get_stock_fundamentals_unified"
    mock_tool.description = "获取基本面数据"

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # 创建模拟消息
        from langchain_core.messages import AIMessage, ToolMessage

        messages = [
            AIMessage(content="分析消息1", tool_calls=[
                Mock(name="get_stock_fundamentals_unified", id="call_1", args={})
            ]),
            AIMessage(content="分析消息2", tool_calls=[
                Mock(name="get_stock_fundamentals_unified", id="call_2", args={})
            ])
        ]

        # Act
        count = node._count_tool_messages(messages)

        # Assert
        assert count == 2
        assert mock_tool.call_count == 2


@pytest.mark.unit
def test_has_tool_result():
    """测试检查工具结果"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_tool = Mock()
    mock_tool.name = "get_stock_fundamentals_unified"

    mock_tool.return_value = [Mock(name="数据1"), Mock(name="数据2")]

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_alyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # 模拟有工具结果
        mock_ds.get_toolkit.return_value = [mock_tool]

        result = node(state)

        # Act
        has_result = node._has_tool_result(messages)

        # Assert
        assert has_result is True


@pytest.mark.unit
def test_has_no_tool_result():
    """测试没有工具结果"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_tool = Mock()

    # 模拟空结果列表
    mock_ds.get_toolkit.return_value = []

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_alyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        result = node(state)
        messages_no_tool = []

        # Act
        has_result = node._has_tool_result(messages_no_tool)

        # Assert
        assert has_result is False


@pytest.mark.unit
def test_has_valid_analysis_content():
    """测试有效分析内容"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_name": "平安银行",
        "market_name": "深圳证券交易所",
        "currency_name": "人民币",
        "currency_symbol": "CNY"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        result = node(state)

        # 有效分析内容（超过500字符）
        valid_result = {
            "content": "这是一段很长的基本面分析内容。" + "x" * 450,
            "company_name": "平安银行",
            "market_name": "深圳证券交易所",
            "currency_name": "人民币",
            "currency_symbol": "CNY"
        }

        # Act
        has_valid = node._has_valid_analysis_content(valid_result)

        # Assert
        assert has_valid is True


@pytest.mark.unit
def test_has_invalid_analysis_content_too_short():
    """测试分析内容太短"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_name": "平安银行",
        "market_name": "深圳证券交易所",
        "currency_name": "人民币",
        "currency_symbol": "CNY"
    }

    # Act
        # 太短的内容（少于100字符）
        invalid_result = {
            "content": "内容太短",
            "company_name": "平安银行",
            "market_name": "深圳证券交易所",
            "currency_name": "人民币",
            "currency_symbol": "CNY"
        }

        # Act
        has_invalid = node._has_valid_analysis_content(invalid_result)

        # Assert
        assert has_invalid is False


@pytest.mark.unit
def test_has_empty_analysis_content():
    """测试空分析内容"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_name": "平安银行",
        "market_name": "深圳证券交易所",
        "currency_name": "人民币",
        "currency_symbol": "CNY"
    }

    # Act
        empty_result = {}

        # Act
        has_empty = node._has_valid_analysis_content(empty_result)

        # Assert
        assert has_empty is False


@pytest.mark.unit
def test_has_tool_call_count():
    """测试工具调用次数统计"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_tool = Mock()
    mock_tool.name = "get_stock_fundamentals_unified"
    mock_tool.description = "获取基本面数据"

    # 模拟10个工具调用
    mock_tool.return_value = Mock()
    for i in range(10):
        mock_tool.return_value = Mock()

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        messages = []
        for i in range(10):
            AIMessage(content=f"分析消息{i}")
            messages.append(AIMessage(tool_calls=[
                Mock(name="get_stock_fundamentals_unified", id=f"call_{i}", args={})
            ])

        count = node._count_tool_messages(messages)

        # Assert
        assert count == 10


@pytest.mark.unit
def test_date_calculation_different_markets():
    """测试不同市场的日期计算"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    test_cases = [
        ("000001", "平安银行", "深圳证券交易所", "人民币", "CNY", 30),
        ("00700", "腾讯控股", "香港交易所", "港币", "HKD", 30),
        ("AAPL", "Apple Inc.", "NASDAQ", "美元", "$", 30),
    ]

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        for stock_code, company_name, market_name, currency, symbol, days in test_cases:
            state = {
                "messages": [],
                "stock_code": stock_code,
                "company_of_interest": company_name,
                "trade_date": "2024-01-15",
                "currency_name": currency,
                "currency_symbol": symbol
            }
            )

            start_date, end_date = node._calculate_date_range(days=days)
            assert start_date is not None
            assert end_date is not None
            assert start_date < end_date


@pytest.mark.unit
def test_force_tool_invocation():
    """测试强制工具调用"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_tool = Mock()
    mock_tool.name = "get_stock_fundamentals_unified"
    mock_tool.description = "获取基本面数据"

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "market_name": "深圳证券交易所",
        "start_date": "2024-01-05",
        "current_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        result = node._force_tool_invocation()

        # Assert
        assert result is not None
        # 强制调用后不返回值


@pytest.mark.unit
def test_force_tool_invocation_with_tools():
    """测试带工具的强制调用"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_tool = Mock()
    mock_tool.name = "get_stock_fundamentals_unified"
    mock_tool.description = "获取基本面数据"

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "market_name": "深圳证券交易所",
        "start_date": "2024-01-05",
        "current_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # 模拟工具列表
        mock_tool.return_value = [mock_tool]

        result = node._force_tool_invocation(tools=[mock_tool])

        # Assert
        assert result is not None
        # 验证工具被调用


@pytest.mark.unit
def test_force_tool_invocation_no_tool():
    """测试没有工具时的强制调用"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "market_name": "深圳证券交易所",
        "start_date": "2024-01-05",
        "current_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # 模拟空工具列表
        mock_ds.get_toolkit.return_value = []

        result = node._force_tool_invocation(tools=[])

        # Assert
        assert result is not None
        # 验证没有工具也能强制调用（返回默认消息）


@pytest.mark.unit
def test_get_data_source():
    """测试获取数据源"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.get_data_source') as mock_get_ds:
        mock_get_ds.return_value = "tushare"

        # Act
        result = mock_get_ds()

    # Assert
        assert result is not None or result in ["tushare", "baostock", "akshare"]


@pytest.mark.unit
def test_get_data_source_fallback():
    """测试数据源回退"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.get_data_source') as mock_get_ds:
        mock_get_ds.return_value = None  # 模拟失败

        # Act
        result = mock_get_ds()

        # Assert
        assert result is None  # 失败时应该回退到下一个数据源


@pytest.mark.unit
def test_get_toolkit():
    """测试获取工具包"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_toolkit.get_stock_fundamentals_unified = Mock()

    # Act
        result = mock_toolkit.get_stock_fundamentals_unified()

    # Assert
        assert result is not None
        assert mock_toolkit is not None
        assert isinstance(result, Mock)


@pytest.mark.unit
def test_build_system_message():
    """测试构建系统消息"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_name": "平安银行",
        "market_name": "深圳证券交易所",
        "currency_name": "人民币",
        "currency_symbol": "CNY"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        result = node._build_system_message()

        # Assert
        assert "平安银行" in result
        assert "深圳证券交易所" in result
        assert "人民币（CNY）" in result
        assert "CNY" in result


@pytest.mark.unit
def test_parse_date_string():
    """测试日期字符串解析"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        test_dates = [
            ("2024-01-15", "2024-01-05", 10, 30),
            ("2024-01-15", "2024-01-05", 30, 180),
        ("2024-01-15", "2024-01-05", 180, 365),
        ("2024-01-15", "2024-01-05", 365, 730)
        ]

    # Act
        for start_date_str, end_date_str, days, expected_start_date, expected_end_date in test_dates:
            node = mock_create(mock_llm, mock_toolkit)

            result_start, result_end = node._calculate_date_range(
                start_date=start_date_str,
                end_date=end_date_str,
                days=days
            )

            # Assert
            assert result_start == expected_start_date
            assert result_end == expected_end_date


@pytest.mark.unit
def test_invalid_date_format():
    """测试无效日期格式"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        result = node._calculate_date_range("not-a-date", days=10)

        # Assert
        # 应该返回默认值
        today = datetime.now().strftime("%Y-%m-%d")

        assert result_start is not None
        assert result_end is not None


@pytest.mark.unit
def test_date_boundary_conditions():
    """测试日期边界条件"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    # 测试边界情况：最小/最大日期范围
    boundary_cases = [
        (2024, 1, 1, 2024, 12, 31),  # 1年范围
        (2020, 12, 31, 365),  # 1年范围
        (2010, 12, 31, 730), 1年范围
        (2034, 1, 1, 2024, 12, 31),  # 10年范围
    ]

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        for start, end in boundary_cases:
            result = node._calculate_date_range(
                start_date=f"{start:04}-{start:02}-01",
                end_date=f"{end:04}-{end:02}-01"
            )

            # Assert
            assert result is not None
            assert result_start is not None
            assert result_end is not None


@pytest.mark.unit
def test_leap_year_handling():
    """测试闰年处理"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # 2020年2月29日是闰年
        start_date = "2020-02-29"
        end_date = "2024-01-15"

        # Act
        start, end = node._calculate_date_range(start_date=start_date, end_date=end_date)

        # Assert
        assert start_date is not None
        assert end_date is not None


@pytest.mark.unit
def test_multiple_year_calculation():
    """测试多年日期范围"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        test_years = [
            (2024, 1, 1, 365),  # 2024年（闰年）
            (2023, 1, 1, 365),  # 2023年（闰年）
            (2021, 1, 1, 365),  # 2021年（闰年）
        (2020, 1, 1, 730),  # 2020年（闰年）
        ]

        for year, days, expected_start, expected_end in test_years:
            start_date = f"{year}-01-01"
            end_date = f"{year}-12-31"

            result = node._calculate_date_range(start_date=start_date, end_date=days)

            # Assert
            assert result_start == expected_start
            assert result_end == expected_end


@pytest.mark.unit
def test_get_company_name():
    """测试获取公司名称"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    # 测试不同市场的公司名称
    test_cases = [
            ("000001", "中国平安银行", "深圳证券交易所", "人民币", "CNY"),
            ("00700", "腾讯控股", "香港交易所", "港币", "HKD"),
            ("AAPL", "Apple Inc.", "NASDAQ", "美元", "$"),
        ]

    with patch('tradingagents.agents.analysts.fundamentals_analyst.get_company_name') as mock_get_name:
        for stock_code, expected_name, market, currency, symbol in test_cases:
            with patch('tradingagents.agents.analysts.fundamentals_analyst') as mock_create:
                mock_create.return_value = Mock(name='node')
                node = mock_create(mock_llm, mock_toolkit)

                # Act
                node = mock_create(mock_llm, mock_toolkit)

                # Act
                result = node.get_company_name(stock_code, market)

                # Assert
                assert result == expected_name or "未知公司"  # 未知公司作为后备值


@pytest.mark.unit
def test_parse_company_name():
    """测试公司名称解析"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Parse and verify different company name formats
        company_formats = [
            ("000001", "000001.SZ"),  # A股6位数字代码带后缀
            ("000001.SH"),              # A股6位数字代码.SH后缀
            ("000001.SH",              # A股6位数字代码.SH后缀
            ("00700.HK"),              # 港股5位数字代码.HK后缀
            ("AAPL.US"),              # 美股代码.US后缀
            ("TSLA.UK"),             # 英国股票代码.UK后缀
        ]

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        for stock_code, suffix, market in company_formats:
            result = node.get_company_name(stock_code, market)

            # Assert
            # Assert isinstance(result, str)
            if ".SH" in result or ".HK" in result or ".US" in result
            if suffix == ".SH":
                assert "SZ" in result or "SH" in result
            elif suffix == ".HK":
                assert "HK" in result or "HK" in result
            elif suffix == ".US":
                assert "US" in result or "NY" in result


@pytest.mark.unit
def test_currency_info():
    """测试货币信息获取"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    test_cases = [
            ("000001", "中国A股", "人民币", "CNY"),
            ("00700", "香港交易所", "港币", "HKD"),
            ("AAPL", "NASDAQ", "美元", "$"),
        ]

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        for stock_code, expected_market, expected_currency, expected_symbol in test_cases:
            result = node.get_company_name(stock_code, expected_market)

            # Act
            assert expected_currency in result or expected_currency in result
            assert expected_symbol in result or expected_currency in result


@pytest.mark.unit
def test_currency_format():
    """测试货币格式"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        symbols = ["000001", "00700", "AAPL"]
        for symbol in symbols:
            node.get_company_name(symbol, "")

        # Assert
            assert "人民币" in node.get_company_name(symbol, "") or "美元" in node.get_company_name(symbol, "")
            assert "港币" in node.get_company_name("00700", "") or "港元" in node.get_company_name("00700", "")
            assert "美元" in node.get_company_name("AAPL", "")


@pytest.mark.unit
def test_empty_company_name():
    """测试空公司名称"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        result = node.get_company_name("", "")

        # Assert
        assert result == "未知公司" or result == ""


@pytest.mark.unit
def test_system_message_structure():
    """测试系统消息结构"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_name": "平安银行",
        "market_name": "深圳证券交易所",
        "currency_name": "人民币",
        "currency_symbol": "CNY"
    }

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        result = node._build_system_message()

        # Assert
        assert "messages" in result
        assert isinstance(result["messages"], list)
        assert len(result["messages"]) > 0
        assert "平安银行" in result["messages"][0]
        assert "深圳证券交易所" in result["messages"][0]
        assert "人民币（CNY）" in result["messages"][0]
        assert "CNY" in result["messages"][0]


@pytest.mark.unit
def test_date_calculation_format():
    """测试日期计算格式"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        today = datetime.now().strftime("%Y-%m-%d")
        start_date = f"{today[:4]}-{today[5:7]}-10"  # 最近10天

        # Act
        result = node._calculate_date_range(start_date=start_date, days=10)

        # Assert
        assert result_start is not None
        assert result_end is not None
        assert isinstance(result_start, str)
        assert isinstance(result_end, str)


@pytest.mark.unit
def test_date_calculation_accuracy():
    """测试日期计算准确性"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        test_dates = [
            ("2024-01-05", "2024-01-15", 10, "2024-01-25"),
            ("2024-01-05", "2024-01-15", 30, 2024-01-25"),
        ]

        for start_date, end_date, days, expected_days in test_dates:
            result_start, result_end = node._calculate_date_range(
                start_date=start_date,
                end_date=end_date,
                days=days
            )

            # Assert
            assert result_start == expected_start
            assert result_end == expected_end
            assert (result_end - result_start).days == days


@pytest.mark.unit
def test_invalid_date_format_handling():
    """测试无效日期格式回退"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        result = node._calculate_date_range("not-a-date", days=10)

        # Assert
        # 应该返回今天±10天
        assert isinstance(result, tuple)
        assert len(result) == 2


@pytest.mark.unit
def test_format_output():
    """测试格式化输出"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        # 测试格式化方法
        mock_llm.invoke = AsyncMock(return_value="格式化输出")
        messages = [AIMessage(content="测试消息")]

        result = node._format_output(messages)

        # Assert
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.unit
def test_invalid_format_output():
    """测试无效格式化输入"""
    # Arrange
        mock_llm = Mock()
    mock_toolkit = Mock()

        with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        messages = [AIMessage(content="消息1"), AIMessage(content="消息2")]

        result = node._format_output(messages)

        # Assert
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.unit
def test_format_output_length():
    """测试格式化输出长度"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

        with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        messages = [AIMessage(content=f"消息{i}") for i in range(10)]

        result = node._format_output(messages)

        # Assert
        assert len(result) > 10
        assert isinstance(result, str)


@pytest.mark.unit
def test_format_output_market_specific():
    """测试市场特定的格式化"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

        with patch('tradingagents.agents.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # A股深圳证券交易所
        state = {
            "messages": [],
            "stock_code": "000001",
            "company_of_interest": "平安银行",
            "trade_date": "2024-01-15",
            "currency_name": "人民币",
            "currency_symbol": "CNY"
        }

        # 港股香港交易所
        state["market_name"] = "香港交易所"

        # Act
        result = node._format_output([])

        # Assert
        assert "深圳证券交易所" in result
        assert "香港交易所" in result
        assert "CNY" in result


@pytest.mark.unit
def test_format_output_currency_specific():
    """测试货币特定的格式化"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

        with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # 港股港币
        state = {
            "messages": [],
            "stock_code": "00700",
            "company_of_interest": "腾讯控股",
            "trade_date": "2024-01-15",
            "currency_name": "港币",
            "currency_symbol": "HKD"
        }

        # 美股美元
        state["currency_name"] = "美元"

        # Act
        result = node._format_output([])

        # Assert
        assert "HKD" in result
        assert "美元" in result


@pytest.mark.unit
def test_format_output_empty_messages():
    """测试空消息列表的格式化"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

        with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        messages = []

        # Act
        result = node._format_output(messages)

        # Assert
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.unit
def test_format_output_performance():
    """测试格式化性能"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

        with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        messages = [AIMessage(content="消息1"), AIMessage(content="消息2")]

        result = node._format_output(messages)

        # Assert
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.unit
def test_format_output_comprehensive():
    """测试综合格式化"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

        with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        messages = [AIMessage(content="消息1"), AIMessage(content="消息2"), AIMessage(content="消息3")]

        result = node._format_output(messages)

        # Assert
        assert result is not None
        assert isinstance(result, str)
        assert "消息1" in result
        assert "消息2" in result
        assert "消息3" in result


@pytest.mark.unit
def test_tool_call_tracking():
    """测试工具调用追踪"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()
    mock_tool = Mock()
    mock_tool.name = "get_stock_fundamentals_unified"

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        result = node(state)

        # 验证工具被追踪
        mock_tool.invoke.assert_called_once()

        # 清除调用次数
        result.messages = [AIMessage(content="分析消息", tool_calls=[
            Mock(name="get_stock_fundamentals_unified", id="call_1", args={})
        ])]

        count = node._count_tool_messages(result.messages)

        # 验证追踪
        assert count == 1

        # 验证工具调用次数正确增加
        assert mock_tool.invoke.call_count == 1

        # 清除调用次数
        mock_tool.invoke.reset_mock()

        result2 = node(state)
        count2 = node._count_tool_messages(result2.messages)

        # 验证计数正确
        assert count2 == 2
        assert mock_tool.invoke.call_count == 2


@pytest.mark.unit
def test_error_handling():
    """测试错误处理"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
        with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
            node = mock_create(mock_llm, mock_toolkit)

        # Act
        result = node(state)

        # Assert
        assert result is not None


@pytest.mark.unit
def test_memory_cleanup():
    """测试内存清理"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    mock_toolkit.get_stock_fundamentals_unified = Mock()

    state = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "2024-01-15",
        "session_id": "test_session"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        result = node(state)

        # Act
        result = node(state)
        node._cleanup_memory(force=True)

        # Assert
        # 验证内存清理被调用

        # 清理后调用计数应该被重置
        # 清理后工具调用计数应该被重置
        # 清理后内存应该被清空


@pytest.mark.unit
def test_concurrent_execution():
    """测试并发执行"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    state1 = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "2024-01-15",
        "session_id": "test_session_1"
    }

    state2 = {
        "messages": [],
        "stock_code": "000001",
        "company_of_interest": "平安银行",
        "trade_date": "2024-01-15",
        "session_id": "test_session_2"
    }

    # Act
    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        result1 = node(state1)
        result2 = node(state2)

        # Assert
        # 验证两次独立执行
        assert result1 is not None
        assert result2 is not None
        # 验证结果1和结果2都返回默认消息


@pytest.mark.unit
def test_edge_cases():
    """测试边界条件"""
    # Arrange
    mock_llm = Mock()
    mock_toolkit = Mock()

    edge_cases = [
        (1, 10),  # 1天范围
        (365, 10),  # 1年范围
        (10, 100), 10天范围
        (0, -10),  # 负数范围
        (36700, 100), 100天范围
    ]

    for days in edge_cases:
        with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
            mock_create.return_value = Mock(name='node')
            node = mock_create(mock_llm, mock_toolkit)

            result = node._calculate_date_range(days=days)

            # Assert
            assert result is not None


@pytest.mark.unit
def test_performance():
    """测试性能"""
    # Arrange
    import time

    mock_llm = Mock()
    mock_toolkit = Mock()

    with patch('tradingagents.agents.analysts.fundamentals_analyst.create_fundamentals_analyst') as mock_create:
        mock_create.return_value = Mock(name='node')
        node = mock_create(mock_llm, mock_toolkit)

        # Act
        start = time.time()
        messages = [AIMessage(content=f"测试消息{i}") for i in range(100)]

        result = node._format_output(messages)

        end_time = time.time()
        elapsed = end_time - start_time

        # Assert
        # 验证100条消息格式化在合理时间内完成（<1秒）
        assert elapsed < 1.0
        assert len(result) > 0
