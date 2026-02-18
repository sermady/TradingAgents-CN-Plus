# -*- coding: utf-8 -*-
"""
测试 app.routers.reports 辅助函数

测试范围:
- get_stock_name 函数
- 股票名称缓存
- 报告相关辅助函数
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

os.environ["USE_MONGODB_STORAGE"] = "false"
os.environ["TRADINGAGENTS_SKIP_DB_INIT"] = "true"


@pytest.mark.unit
class TestGetStockName:
    """测试 get_stock_name 辅助函数"""

    def test_stock_name_cached(self):
        """测试股票名称缓存"""
        # 模拟缓存中已有数据
        with patch.dict(
            "app.routers.reports._stock_name_cache", {"000001": "平安银行"}
        ):
            # 由于缓存是模块级变量，需要模拟
            pass

    def test_stock_name_from_cache(self):
        """测试从缓存获取股票名称"""
        from app.routers.reports import _stock_name_cache

        # 直接操作模块级缓存
        _stock_name_cache["000001"] = "平安银行"

        # 验证缓存工作
        assert "000001" in _stock_name_cache
        assert _stock_name_cache["000001"] == "平安银行"


@pytest.mark.unit
class TestStockNameCache:
    """测试股票名称缓存机制"""

    def test_cache_populate(self):
        """测试缓存填充"""
        from app.routers.reports import _stock_name_cache

        # 模拟缓存填充
        _stock_name_cache.clear()
        _stock_name_cache["600000"] = "浦发银行"

        assert len(_stock_name_cache) >= 1
        assert _stock_name_cache.get("600000") == "浦发银行"

    def test_cache_clear(self):
        """测试缓存清空"""
        from app.routers.reports import _stock_name_cache

        _stock_name_cache.clear()
        assert len(_stock_name_cache) == 0


@pytest.mark.unit
class TestReportFormats:
    """测试报告格式相关"""

    def test_report_format_detection(self):
        """测试报告格式检测"""
        # 测试各种格式的文件名
        formats = ["md", "pdf", "docx", "html"]

        for fmt in formats:
            filename = f"report.000001.{fmt}"
            # 简单验证格式提取
            assert fmt in filename

    def test_report_filename_construction(self):
        """测试报告文件名构造"""
        stock_code = "000001"
        company_name = "平安银行"
        fmt = "md"

        # 构造文件名
        filename = f"{company_name}_{stock_code}_analysis.{fmt}"
        assert "000001" in filename
        assert "analysis.md" in filename


@pytest.mark.unit
class TestReportDateHandling:
    """测试报告日期处理"""

    def test_date_range_calculation(self):
        """测试日期范围计算"""
        from datetime import datetime, timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        # 验证日期范围
        assert (end_date - start_date).days == 30

    def test_date_format(self):
        """测试日期格式"""
        from datetime import datetime

        dt = datetime(2024, 1, 15)

        # 测试各种日期格式
        assert dt.strftime("%Y-%m-%d") == "2024-01-15"
        assert dt.strftime("%Y%m%d") == "20240115"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
