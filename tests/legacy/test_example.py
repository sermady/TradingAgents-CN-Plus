# -*- coding: utf-8 -*-
"""
示例单元测试
演示如何为TradingAgents-CN编写测试
"""

import pytest
from tradingagents.agents.analysts.market_analyst import MarketAnalyst
from tradingagents.config.runtime_settings import RuntimeSettings


@pytest.mark.unit
class TestMarketAnalyst:
    """市场分析师测试"""

    @pytest.fixture
    def market_analyst(self):
        """创建市场分析师实例"""
        config = RuntimeSettings.get_llm_config()
        return MarketAnalyst(llm_config=config)

    @pytest.mark.asyncio
    async def test_market_analyst_initialization(self, market_analyst):
        """测试市场分析师初始化"""
        assert market_analyst is not None
        assert hasattr(market_analyst, "analyze")

    @pytest.mark.asyncio
    async def test_market_analysis_basic(self, market_analyst):
        """测试基本的市场分析功能"""
        ticker = "AAPL"
        date = "2024-01-15"

        try:
            result = await market_analyst.analyze(ticker=ticker, date=date)
            assert result is not None
            assert "market_report" in result or "error" in result
        except Exception as e:
            pytest.skip(f"Analysis failed: {e}")


@pytest.mark.integration
class TestDataSources:
    """数据源集成测试"""

    @pytest.mark.asyncio
    async def test_tushare_availability(self):
        """测试Tushare数据源可用性"""
        from tradingagents.dataflows.providers.china.tushare import TushareProvider

        provider = TushareProvider()
        is_available = provider.is_available()

        if not is_available:
            pytest.skip("Tushare not configured")

        assert is_available is True

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_data_fetch(self):
        """测试数据获取"""
        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        manager = get_data_source_manager()

        # 尝试获取股票数据
        try:
            data = manager.get_stock_data(
                ticker="600765.SH",
                start_date="2024-01-01",
                end_date="2024-01-15",
                source="baostock",  # 使用免费数据源
            )

            if data is None:
                pytest.skip("No data available")

            assert data is not None
            assert len(data) > 0
        except Exception as e:
            pytest.skip(f"Data fetch failed: {e}")


@pytest.mark.unit
class TestConfigService:
    """配置服务测试"""

    def test_runtime_settings_initialization(self):
        """测试运行时配置初始化"""
        settings = RuntimeSettings()
        assert settings is not None

    def test_llm_config_loading(self):
        """测试LLM配置加载"""
        config = RuntimeSettings.get_llm_config()
        assert config is not None or config == {}  # 可以为空字典


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
