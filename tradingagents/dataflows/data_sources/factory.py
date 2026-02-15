# -*- coding: utf-8 -*-
"""
数据源管理器工厂函数
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..data_source_manager import DataSourceManager


# 单例实例缓存
_china_manager_instance = None


def get_data_source_manager() -> "DataSourceManager":
    """
    获取数据源管理器实例（单例模式）

    Returns:
        DataSourceManager: 数据源管理器实例
    """
    global _china_manager_instance
    if _china_manager_instance is None:
        from ..data_source_manager import DataSourceManager
        _china_manager_instance = DataSourceManager()
    return _china_manager_instance


def get_china_stock_data_unified(
    symbol: str,
    start_date: str = None,
    end_date: str = None,
    analysis_date: str = None,
) -> str:
    """
    统一的中国股票数据获取接口

    Args:
        symbol: 股票代码
        start_date: 开始日期
        end_date: 结束日期
        analysis_date: 分析日期

    Returns:
        str: 格式化的股票数据
    """
    manager = get_data_source_manager()
    return manager.get_stock_data(symbol, start_date, end_date, analysis_date=analysis_date)


def get_china_stock_info_unified(symbol: str) -> dict:
    """
    统一的中国股票信息获取接口

    Args:
        symbol: 股票代码

    Returns:
        dict: 股票基本信息
    """
    manager = get_data_source_manager()
    return manager.get_stock_info(symbol)


def get_stock_data_service():
    """
    获取股票数据服务实例（兼容接口）

    Returns:
        DataSourceManager: 数据源管理器实例
    """
    return get_data_source_manager()
