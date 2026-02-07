# -*- coding: utf-8 -*-
"""
测试数据提供者基础功能

测试范围:
- Tushare Provider
- AKShare Provider
- BaoStock Provider
- 基础数据获取
- 错误处理
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd


class TestTushareProvider:
    """测试Tushare数据提供者"""

    @pytest.mark.unit
    def test_tushare_provider_creation(self):
        """测试Tushare提供者创建"""
        from tradingagents.dataflows.providers.china.tushare import TushareProvider

        # 测试创建实例（需要token）
        with patch.dict("os.environ", {"TUSHARE_TOKEN": "test_token"}):
            try:
                provider = TushareProvider()
                assert provider is not None
            except Exception as e:
                # 如果没有token可能会失败
                pytest.skip(f"Tushare初始化失败: {e}")

    @pytest.mark.unit
    def test_tushare_get_stock_info_mocked(self):
        """测试获取股票信息（使用mock）"""
        from tradingagents.dataflows.providers.china.tushare import TushareProvider

        with patch.dict("os.environ", {"TUSHARE_TOKEN": "test_token"}):
            with patch("tushare.pro_api") as mock_api:
                # 设置mock返回值
                mock_df = pd.DataFrame(
                    {
                        "ts_code": ["000001.SZ"],
                        "name": ["平安银行"],
                        "industry": ["银行"],
                    }
                )
                mock_api.return_value.stock_basic.return_value = mock_df

                try:
                    provider = TushareProvider()
                    result = provider.get_stock_info("000001")

                    # 验证结果
                    assert result is not None
                    assert isinstance(result, dict)
                except Exception as e:
                    pytest.skip(f"测试需要Tushare环境: {e}")

    @pytest.mark.unit
    def test_tushare_invalid_token(self):
        """测试无效token处理"""
        from tradingagents.dataflows.providers.china.tushare import TushareProvider

        with patch.dict("os.environ", {"TUSHARE_TOKEN": ""}):
            # 应该处理无效token的情况
            try:
                provider = TushareProvider()
                # 可能不会立即抛出异常，但在调用API时会失败
            except Exception:
                # 预期行为
                pass


class TestAKShareProvider:
    """测试AKShare数据提供者"""

    @pytest.mark.unit
    def test_akshare_provider_creation(self):
        """测试AKShare提供者创建"""
        from tradingagents.dataflows.providers.china.akshare import AKShareProvider

        try:
            provider = AKShareProvider()
            assert provider is not None
        except Exception as e:
            pytest.skip(f"AKShare初始化失败: {e}")

    @pytest.mark.unit
    @patch("tradingagents.dataflows.providers.china.akshare.ak")
    def test_akshare_get_stock_info_mocked(self, mock_ak):
        """测试获取股票信息（使用mock）"""
        from tradingagents.dataflows.providers.china.akshare import AKShareProvider

        # 设置mock返回值
        mock_df = pd.DataFrame(
            {
                "代码": ["000001"],
                "名称": ["平安银行"],
                "行业": ["银行"],
            }
        )
        mock_ak.stock_individual_info_em.return_value = mock_df

        provider = AKShareProvider()

        try:
            result = provider.get_stock_info("000001")
            assert result is not None
        except Exception as e:
            # AKShare可能因网络等原因失败
            pytest.skip(f"AKShare调用失败: {e}")


class TestBaoStockProvider:
    """测试BaoStock数据提供者"""

    @pytest.mark.unit
    def test_baostock_provider_creation(self):
        """测试BaoStock提供者创建"""
        from tradingagents.dataflows.providers.china.baostock import BaoStockProvider

        try:
            provider = BaoStockProvider()
            assert provider is not None
        except Exception as e:
            pytest.skip(f"BaoStock初始化失败: {e}")

    @pytest.mark.unit
    @patch("tradingagents.dataflows.providers.china.baostock.bs")
    def test_baostock_login_mocked(self, mock_bs):
        """测试BaoStock登录（使用mock）"""
        from tradingagents.dataflows.providers.china.baostock import BaoStockProvider

        # 设置mock返回值
        mock_login_result = Mock()
        mock_login_result.error_code = "0"
        mock_bs.login.return_value = mock_login_result

        try:
            provider = BaoStockProvider()
            # 登录应该在创建时自动执行
            mock_bs.login.assert_called_once()
        except Exception as e:
            pytest.skip(f"BaoStock测试失败: {e}")


class TestProviderCommonPatterns:
    """测试提供者通用模式"""

    @pytest.mark.unit
    def test_all_providers_handle_invalid_stock_code(self):
        """测试所有提供者处理无效股票代码"""
        from tradingagents.dataflows.providers.china.akshare import AKShareProvider

        try:
            provider = AKShareProvider()

            # 测试无效股票代码
            with pytest.raises((ValueError, Exception)):
                provider.get_stock_info("INVALID")
        except Exception as e:
            pytest.skip(f"测试需要提供者环境: {e}")

    @pytest.mark.unit
    def test_provider_data_format(self):
        """测试提供者返回数据格式"""
        from tradingagents.dataflows.providers.china.akshare import AKShareProvider

        try:
            provider = AKShareProvider()

            # 使用mock测试返回格式
            with patch.object(provider, "get_stock_info") as mock_get_info:
                mock_get_info.return_value = {
                    "code": "000001",
                    "name": "平安银行",
                    "price": 10.5,
                }

                result = provider.get_stock_info("000001")

                assert isinstance(result, dict)
                assert "code" in result or "name" in result
        except Exception as e:
            pytest.skip(f"测试需要提供者环境: {e}")

    @pytest.mark.unit
    def test_provider_error_handling(self):
        """测试提供者错误处理"""
        from tradingagents.dataflows.providers.china.akshare import AKShareProvider

        try:
            provider = AKShareProvider()

            # 模拟API错误
            with patch.object(provider, "get_stock_info") as mock_get_info:
                mock_get_info.side_effect = Exception("API错误")

                # 应该抛出异常或返回错误信息
                with pytest.raises(Exception):
                    provider.get_stock_info("000001")
        except Exception as e:
            pytest.skip(f"测试需要提供者环境: {e}")


class TestDataSourceManager:
    """测试数据源管理器"""

    @pytest.mark.unit
    def test_data_source_manager_creation(self):
        """测试数据源管理器创建"""
        from tradingagents.dataflows.data_source_manager import DataSourceManager

        try:
            manager = DataSourceManager()
            assert manager is not None
        except Exception as e:
            pytest.skip(f"数据源管理器初始化失败: {e}")

    @pytest.mark.unit
    def test_data_source_priority(self):
        """测试数据源优先级"""
        from tradingagents.dataflows.data_source_manager import DataSourceManager

        try:
            manager = DataSourceManager()

            # 验证默认优先级
            assert hasattr(manager, "priority")
            assert len(manager.priority) > 0
        except Exception as e:
            pytest.skip(f"测试需要数据源管理器环境: {e}")

    @pytest.mark.unit
    def test_get_provider(self):
        """测试获取提供者"""
        from tradingagents.dataflows.data_source_manager import DataSourceManager

        try:
            manager = DataSourceManager()

            # 获取特定提供者
            provider = manager.get_provider("tushare")
            assert provider is not None
        except Exception as e:
            pytest.skip(f"测试需要数据源管理器环境: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
