# -*- coding: utf-8 -*-
"""
BaoStock 数据源集成测试
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
import os
import sys


@pytest.mark.integration
@pytest.mark.requires_db
class TestBaoStockIntegration:
    """BaoStock 数据源集成测试"""

    def test_baostock_adapter_available(self):
        """测试 BaoStock 适配器可用性"""
        from app.services.data_source_adapters import BaoStockAdapter

        adapter = BaoStockAdapter()
        assert adapter.is_available() == True

    def test_baostock_get_stock_list(self):
        """测试获取股票列表"""
        from app.services.data_source_adapters import BaoStockAdapter

        adapter = BaoStockAdapter()
        df = adapter.get_stock_list()

        assert df is not None
        assert not df.empty
        assert len(df) > 1000

    def test_baostock_get_daily_basic(self):
        """测试获取日线基础数据"""
        from app.services.data_source_adapters import BaoStockAdapter

        adapter = BaoStockAdapter()
        trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

        basic_df = adapter.get_daily_basic(trade_date)

        assert basic_df is not None
        assert not basic_df.empty
        assert "pe" in basic_df.columns
        assert "pb" in basic_df.columns

    def test_baostock_date_range_query(self):
        """测试带日期参数的股票查询"""
        import baostock as bs

        lg = bs.login()
        assert lg.error_code == "0"

        try:
            test_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            rs = bs.query_all_stock(day=test_date)

            assert rs.error_code == "0"

            data_list = []
            while (rs.error_code == "0") and rs.next():
                data_list.append(rs.get_row_data())

            assert len(data_list) > 0

        finally:
            bs.logout()


@pytest.mark.integration
@pytest.mark.requires_db
class TestDataSourceManagerBaoStock:
    """数据源管理器中 BaoStock 集成测试"""

    def test_data_source_manager_baostock_priority(self):
        """测试 BaoStock 在数据源管理器中的优先级"""
        from app.services.data_source_adapters import DataSourceManager

        manager = DataSourceManager()
        available_adapters = manager.get_available_adapters()

        adapter_names = [adapter.name for adapter in available_adapters]
        assert "baostock" in adapter_names

    def test_get_stock_list_with_fallback_baostock(self):
        """测试使用 BaoStock 获取股票列表的回退机制"""
        from app.services.data_source_adapters import DataSourceManager

        manager = DataSourceManager()
        stock_df, source = manager.get_stock_list_with_fallback()

        assert stock_df is not None
        assert not stock_df.empty
        assert source in ["tushare", "baostock", "akshare"]

    def test_get_daily_basic_with_fallback_baostock(self):
        """测试使用 BaoStock 获取 daily_basic 的回退机制"""
        from app.services.data_source_adapters import DataSourceManager

        manager = DataSourceManager()
        trade_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

        basic_df, source = manager.get_daily_basic_with_fallback(trade_date)

        assert basic_df is not None
        assert not basic_df.empty
        assert source in ["tushare", "baostock", "akshare"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
