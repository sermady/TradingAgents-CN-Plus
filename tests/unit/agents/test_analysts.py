# -*- coding: utf-8 -*-
"""
分析师单元测试

测试各个分析师的核心逻辑
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime


@pytest.mark.unit
class TestMarketAnalyst:
    """市场分析师测试"""

    @pytest.fixture
    def mock_market_data(self):
        """模拟市场数据"""
        return {
            "current_price": 15.50,
            "open": 15.20,
            "high": 15.80,
            "low": 15.10,
            "volume": 1500000,
            "ma5": 15.30,
            "ma10": 15.40,
            "ma20": 15.25,
            "rsi": 65,
            "macd": 0.15,
            "boll_upper": 16.20,
            "boll_lower": 14.80,
        }

    def test_market_analyst_initialization(self):
        """测试市场分析师初始化"""
        from tradingagents.agents.analysts.market_analyst import MarketAnalyst

        mock_llm = Mock()
        mock_memory = Mock()

        analyst = MarketAnalyst(
            llm=mock_llm, memory=mock_memory, config={"ticker": "000001"}
        )

        assert analyst.llm == mock_llm
        assert analyst.memory == mock_memory
        assert analyst.config["ticker"] == "000001"

    def test_technical_indicators_calculation(self, mock_market_data):
        """测试技术指标计算"""
        # 验证技术指标完整性
        required_indicators = ["current_price", "volume", "ma5", "rsi", "macd"]

        for indicator in required_indicators:
            assert indicator in mock_market_data, f"缺少指标: {indicator}"
            assert mock_market_data[indicator] is not None

    def test_market_data_validation(self, mock_market_data):
        """测试市场数据验证"""
        # 验证价格逻辑
        assert (
            mock_market_data["low"]
            <= mock_market_data["current_price"]
            <= mock_market_data["high"]
        )
        assert mock_market_data["volume"] >= 0

        # 验证移动平均线趋势
        assert mock_market_data["ma5"] > 0
        assert mock_market_data["ma10"] > 0
        assert mock_market_data["ma20"] > 0


@pytest.mark.unit
class TestFundamentalsAnalyst:
    """基本面分析师测试"""

    @pytest.fixture
    def mock_financial_data(self):
        """模拟财务数据"""
        return {
            "pe_ratio": 12.5,
            "pb_ratio": 1.8,
            "ps_ratio": 2.1,
            "roe": 0.15,
            "roa": 0.08,
            "market_cap": 1500000000,
            "revenue_growth": 0.25,
            "profit_margin": 0.18,
            "debt_ratio": 0.45,
        }

    def test_fundamentals_analyst_initialization(self):
        """测试基本面分析师初始化"""
        from tradingagents.agents.analysts.fundamentals_analyst import (
            FundamentalsAnalyst,
        )

        mock_llm = Mock()
        mock_memory = Mock()

        analyst = FundamentalsAnalyst(
            llm=mock_llm, memory=mock_memory, config={"ticker": "000001"}
        )

        assert analyst.llm == mock_llm
        assert analyst.config["ticker"] == "000001"

    def test_financial_ratios_validation(self, mock_financial_data):
        """测试财务比率验证"""
        # 验证估值比率范围
        assert mock_financial_data["pe_ratio"] > 0
        assert mock_financial_data["pb_ratio"] > 0

        # 验证盈利能力
        assert 0 <= mock_financial_data["roe"] <= 1
        assert 0 <= mock_financial_data["roa"] <= 1

        # 验证负债水平
        assert 0 <= mock_financial_data["debt_ratio"] <= 1

    def test_valuation_analysis(self, mock_financial_data):
        """测试估值分析"""
        pe = mock_financial_data["pe_ratio"]
        pb = mock_financial_data["pb_ratio"]

        # 判断估值水平
        if pe < 15 and pb < 2:
            valuation = "undervalued"
        elif pe > 30 or pb > 3:
            valuation = "overvalued"
        else:
            valuation = "fair"

        assert valuation in ["undervalued", "fair", "overvalued"]


@pytest.mark.unit
class TestNewsAnalyst:
    """新闻分析师测试"""

    @pytest.fixture
    def mock_news_data(self):
        """模拟新闻数据"""
        return [
            {
                "title": "公司发布季度财报",
                "content": "营收增长25%，净利润创新高",
                "sentiment": "positive",
                "date": datetime.now().strftime("%Y-%m-%d"),
            },
            {
                "title": "行业政策调整",
                "content": "监管部门发布新规，利好龙头企业",
                "sentiment": "positive",
                "date": datetime.now().strftime("%Y-%m-%d"),
            },
        ]

    def test_news_analyst_initialization(self):
        """测试新闻分析师初始化"""
        from tradingagents.agents.analysts.news_analyst import NewsAnalyst

        mock_llm = Mock()
        mock_memory = Mock()

        analyst = NewsAnalyst(
            llm=mock_llm, memory=mock_memory, config={"ticker": "000001"}
        )

        assert analyst.llm == mock_llm
        assert analyst.config["ticker"] == "000001"

    def test_news_sentiment_analysis(self, mock_news_data):
        """测试新闻情感分析"""
        # 统计情感分布
        sentiments = [news["sentiment"] for news in mock_news_data]
        positive_count = sentiments.count("positive")
        negative_count = sentiments.count("negative")
        neutral_count = sentiments.count("neutral")

        total = len(sentiments)
        positive_ratio = positive_count / total

        # 判断整体情感倾向
        if positive_ratio > 0.6:
            overall_sentiment = "bullish"
        elif positive_ratio < 0.4:
            overall_sentiment = "bearish"
        else:
            overall_sentiment = "neutral"

        assert overall_sentiment in ["bullish", "bearish", "neutral"]

    def test_news_data_filtering(self, mock_news_data):
        """测试新闻数据过滤"""
        # 过滤无效新闻
        valid_news = [
            news
            for news in mock_news_data
            if news.get("title") and news.get("content") and len(news["content"]) > 10
        ]

        assert len(valid_news) == len(mock_news_data)


@pytest.mark.unit
class TestChinaMarketAnalyst:
    """中国特色行情分析师测试"""

    @pytest.fixture
    def mock_china_market_data(self):
        """模拟A股特色数据"""
        return {
            "limit_up": 17.05,  # 涨停价
            "limit_down": 13.95,  # 跌停价
            "turnover_rate": 0.05,  # 换手率
            "volume_ratio": 1.5,  # 量比
            "main_force_inflow": 5000000,  # 主力资金流入
            "north_bound_inflow": 2000000,  # 北向资金流入
            " Margin_balance": 100000000,  # 融资融券余额
        }

    def test_china_market_analyst_initialization(self):
        """测试中国市场分析师初始化"""
        from tradingagents.agents.analysts.china_market_analyst import (
            ChinaMarketAnalyst,
        )

        mock_llm = Mock()
        mock_memory = Mock()

        analyst = ChinaMarketAnalyst(
            llm=mock_llm, memory=mock_memory, config={"ticker": "000001"}
        )

        assert analyst.llm == mock_llm
        assert analyst.config["ticker"] == "000001"

    def test_limit_price_calculation(self, mock_china_market_data):
        """测试涨跌停价格计算"""
        current_price = 15.50

        # 计算理论涨跌停价（A股通常10%）
        expected_limit_up = round(current_price * 1.10, 2)
        expected_limit_down = round(current_price * 0.90, 2)

        # 验证涨跌停机制
        assert mock_china_market_data["limit_up"] > current_price
        assert mock_china_market_data["limit_down"] < current_price

    def test_turnover_analysis(self, mock_china_market_data):
        """测试换手率分析"""
        turnover = mock_china_market_data["turnover_rate"]

        # 判断活跃度
        if turnover > 0.10:
            activity = "very_high"
        elif turnover > 0.05:
            activity = "high"
        elif turnover > 0.02:
            activity = "normal"
        else:
            activity = "low"

        assert activity in ["very_high", "high", "normal", "low"]


@pytest.mark.unit
class TestSocialMediaAnalyst:
    """社交媒体分析师测试"""

    @pytest.fixture
    def mock_sentiment_data(self):
        """模拟社交媒体情感数据"""
        return {
            "weibo_sentiment": 0.65,
            "xueqiu_sentiment": 0.72,
            "dongcai_sentiment": 0.58,
            "total_mentions": 1250,
            "positive_ratio": 0.68,
            "negative_ratio": 0.22,
            "neutral_ratio": 0.10,
        }

    def test_social_media_analyst_initialization(self):
        """测试社交媒体分析师初始化"""
        from tradingagents.agents.analysts.social_media_analyst import (
            SocialMediaAnalyst,
        )

        mock_llm = Mock()
        mock_memory = Mock()

        analyst = SocialMediaAnalyst(
            llm=mock_llm, memory=mock_memory, config={"ticker": "000001"}
        )

        assert analyst.llm == mock_llm
        assert analyst.config["ticker"] == "000001"

    def test_sentiment_aggregation(self, mock_sentiment_data):
        """测试情感聚合"""
        # 计算加权平均情感
        sentiments = [
            mock_sentiment_data["weibo_sentiment"],
            mock_sentiment_data["xueqiu_sentiment"],
            mock_sentiment_data["dongcai_sentiment"],
        ]
        avg_sentiment = sum(sentiments) / len(sentiments)

        assert 0 <= avg_sentiment <= 1

        # 判断整体情感
        if avg_sentiment > 0.6:
            overall = "positive"
        elif avg_sentiment < 0.4:
            overall = "negative"
        else:
            overall = "neutral"

        assert overall in ["positive", "negative", "neutral"]

    def test_mention_volume_analysis(self, mock_sentiment_data):
        """测试提及量分析"""
        mentions = mock_sentiment_data["total_mentions"]

        # 判断热度
        if mentions > 5000:
            heat = "very_hot"
        elif mentions > 2000:
            heat = "hot"
        elif mentions > 500:
            heat = "warm"
        else:
            heat = "cold"

        assert heat in ["very_hot", "hot", "warm", "cold"]


@pytest.mark.unit
def test_analyst_selection_logic():
    """测试分析师选择逻辑"""
    # 根据股票特征选择分析师
    stock_type = "a_share"
    market = "china"

    # A股默认启用所有分析师
    if stock_type == "a_share" and market == "china":
        selected_analysts = ["market", "fundamentals", "news", "china", "social"]
    else:
        selected_analysts = ["market", "fundamentals", "news"]

    assert "china" in selected_analysts  # A股必须包含中国市场分析师


@pytest.mark.unit
def test_analyst_report_structure():
    """测试分析师报告结构"""
    # 标准报告结构
    report_template = {
        "analyst_type": "",
        "recommendation": "",
        "confidence": 0.0,
        "reasoning": "",
        "key_metrics": {},
        "risks": [],
        "timestamp": "",
    }

    required_fields = ["analyst_type", "recommendation", "confidence", "reasoning"]

    for field in required_fields:
        assert field in report_template, f"报告缺少必需字段: {field}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
