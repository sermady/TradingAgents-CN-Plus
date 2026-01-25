# -*- coding: utf-8 -*-
"""
测试股票数据Fixtures
"""

import pytest
from typing import Dict, Any, List


@pytest.fixture
def sample_stock_a() -> Dict[str, Any]:
    """
    样本A股数据
    """
    return {
        "code": "000001",
        "name": "平安银行",
        "market": "sz",
        "industry": "银行",
        "sector": "金融",
        "list_date": "1991-04-03",
        "is_active": True,
        "description": "平安银行是中国领先的商业银行之一",
    }


@pytest.fixture
def sample_stock_b() -> Dict[str, Any]:
    """
    样本B股数据
    """
    return {
        "code": "600519",
        "name": "贵州茅台",
        "market": "sh",
        "industry": "白酒",
        "sector": "消费",
        "list_date": "2001-08-27",
        "is_active": True,
        "description": "贵州茅台是中国著名的白酒品牌",
    }


@pytest.fixture
def sample_stock_hk() -> Dict[str, Any]:
    """
    样本港股数据
    """
    return {
        "code": "00700",
        "name": "腾讯控股",
        "market": "hk",
        "industry": "科技",
        "sector": "互联网",
        "list_date": "2004-06-16",
        "is_active": True,
        "description": "腾讯控股是中国的互联网巨头",
    }


@pytest.fixture
def sample_stock_us() -> Dict[str, Any]:
    """
    样本美股数据
    """
    return {
        "code": "AAPL",
        "name": "Apple Inc.",
        "market": "us",
        "industry": "科技",
        "sector": "消费电子",
        "list_date": "1980-12-12",
        "is_active": True,
        "description": "Apple Inc. 是全球知名的科技公司",
    }


@pytest.fixture
def sample_stocks_list(
    sample_stock_a: Dict[str, Any],
    sample_stock_b: Dict[str, Any],
    sample_stock_hk: Dict[str, Any],
    sample_stock_us: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    样本股票列表
    """
    return [sample_stock_a, sample_stock_b, sample_stock_hk, sample_stock_us]


@pytest.fixture
def sample_price_data() -> Dict[str, Any]:
    """
    样本价格数据
    """
    return {
        "code": "000001",
        "date": "2024-01-15",
        "open": 10.50,
        "high": 10.80,
        "low": 10.30,
        "close": 10.75,
        "volume": 1000000,
        "amount": 10750000.0,
        "change": 0.25,
        "change_percent": 2.38,
    }


@pytest.fixture
def sample_technical_indicators() -> Dict[str, Any]:
    """
    样本技术指标数据
    """
    return {
        "code": "000001",
        "date": "2024-01-15",
        "ma5": 10.60,
        "ma10": 10.45,
        "ma20": 10.30,
        "ma60": 10.15,
        "rsi_6": 65.5,
        "rsi_12": 58.3,
        "rsi_24": 52.1,
        "macd_dif": 0.15,
        "macd_dea": 0.10,
        "macd_bar": 0.05,
        "kdj_k": 70.5,
        "kdj_d": 65.2,
        "kdj_j": 80.1,
        "boll_upper": 11.20,
        "boll_middle": 10.60,
        "boll_lower": 10.00,
    }


@pytest.fixture
def sample_fundamental_data() -> Dict[str, Any]:
    """
    样本基本面数据
    """
    return {
        "code": "000001",
        "report_date": "2023-12-31",
        "total_assets": 3500000000000,  # 总资产
        "total_liabilities": 3200000000000,  # 总负债
        "net_assets": 300000000000,  # 净资产
        "revenue": 150000000000,  # 营业收入
        "net_profit": 30000000000,  # 净利润
        "eps": 1.55,  # 每股收益
        "pe": 7.5,  # 市盈率
        "pb": 0.65,  # 市净率
        "roe": 10.5,  # 净资产收益率
        "debt_to_asset_ratio": 91.4,  # 资产负债率
        "current_ratio": 0.95,  # 流动比率
        "quick_ratio": 0.92,  # 速动比率
        "gross_profit_margin": 35.2,  # 毛利率
        "net_profit_margin": 20.0,  # 净利率
    }


@pytest.fixture
def sample_analysis_request() -> Dict[str, Any]:
    """
    样本分析请求
    """
    return {
        "stock_code": "000001",
        "analysis_type": "comprehensive",
        "depth_level": 3,
        "enable_market_analyst": True,
        "enable_news_analyst": True,
        "enable_social_media_analyst": True,
        "enable_fundamentals_analyst": True,
    }


@pytest.fixture
def sample_analysis_result() -> Dict[str, Any]:
    """
    样本分析结果
    """
    return {
        "id": "analysis_123",
        "stock_code": "000001",
        "stock_name": "平安银行",
        "analysis_type": "comprehensive",
        "depth_level": 3,
        "status": "completed",
        "created_at": "2024-01-15T10:30:00Z",
        "completed_at": "2024-01-15T10:35:00Z",
        "analysts": {
            "market_analyst": {
                "recommendation": "buy",
                "confidence": 0.75,
                "summary": "技术指标显示上涨趋势",
            },
            "news_analyst": {
                "recommendation": "hold",
                "confidence": 0.65,
                "summary": "新闻情绪中性偏正面",
            },
            "fundamentals_analyst": {
                "recommendation": "buy",
                "confidence": 0.70,
                "summary": "基本面稳健，估值合理",
            },
        },
        "researchers": {
            "bull_researcher": "看涨论点：银行业景气度提升",
            "bear_researcher": "看跌论点：利率上升影响盈利",
        },
        "risk_assessment": {
            "risk_level": "medium",
            "position_size": 0.15,
            "stop_loss": 9.80,
        },
        "trading_decision": {
            "action": "buy",
            "target_price": 12.00,
            "confidence": 0.70,
        },
    }
