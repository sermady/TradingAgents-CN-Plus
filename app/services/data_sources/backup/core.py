# -*- coding: utf-8 -*-
"""
本地股票列表备用数据源核心模块
当所有网络数据源都失败时使用
"""

import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from .search import (
    get_all_areas,
    get_all_industries,
    get_stocks_by_market,
    search_by_area,
    search_by_industry,
    search_stocks,
)
from .stock_data import (
    DEFAULT_STOCKS,
    get_stock_by_code,
    get_stock_name,
    is_stock_code_valid,
)

logger = logging.getLogger(__name__)


class LocalStockListBackup:
    """本地股票列表备用数据源"""

    DEFAULT_STOCKS = DEFAULT_STOCKS

    @classmethod
    def get_default_stocks(cls) -> List[dict]:
        """获取默认股票列表

        Returns:
            默认股票列表
        """
        return DEFAULT_STOCKS.copy()

    @classmethod
    def get_stock_list(cls) -> Optional[pd.DataFrame]:
        """获取本地备用的股票列表

        Returns:
            股票列表DataFrame，失败返回None
        """
        try:
            logger.warning("[WARN] 使用本地备用股票列表（仅包含主要蓝筹股）")
            df = pd.DataFrame(DEFAULT_STOCKS)
            logger.info(f"[OK] 本地备用股票列表加载完成: {len(df)} 只股票")
            return df
        except Exception as e:
            logger.error(f"[ERROR] 加载本地备用股票列表失败: {e}")
            return None

    @classmethod
    def get_all_stocks(cls) -> pd.DataFrame:
        """获取所有股票作为DataFrame

        Returns:
            所有股票的DataFrame
        """
        return pd.DataFrame(DEFAULT_STOCKS)

    @classmethod
    def get_stock_by_code(cls, code: str) -> Optional[dict]:
        """根据股票代码查找股票信息

        Args:
            code: 股票代码（如 "000001"）

        Returns:
            股票信息字典，未找到返回None
        """
        return get_stock_by_code(code)

    @classmethod
    def get_stock_name(cls, code: str) -> Optional[str]:
        """根据股票代码获取股票名称

        Args:
            code: 股票代码（如 "000001"）

        Returns:
            股票名称，未找到返回None
        """
        return get_stock_name(code)

    @classmethod
    def is_stock_code_valid(cls, code: str) -> bool:
        """验证股票代码是否有效

        Args:
            code: 股票代码（如 "000001"）

        Returns:
            是否有效
        """
        return is_stock_code_valid(code)

    @classmethod
    def search_stocks(cls, keyword: str, limit: int = 10) -> List[dict]:
        """根据关键词搜索股票

        Args:
            keyword: 搜索关键词
            limit: 最大返回结果数

        Returns:
            匹配的股票信息列表
        """
        return search_stocks(keyword, limit)

    @classmethod
    def search_by_industry(cls, industry: str) -> List[dict]:
        """按行业搜索股票

        Args:
            industry: 行业名称

        Returns:
            该行业的所有股票
        """
        return search_by_industry(industry)

    @classmethod
    def search_by_area(cls, area: str) -> List[dict]:
        """按地区搜索股票

        Args:
            area: 地区名称

        Returns:
            该地区的所有股票
        """
        return search_by_area(area)

    @classmethod
    def get_stocks_by_market(cls, market: str) -> List[dict]:
        """按市场类型获取股票

        Args:
            market: 市场类型（如 "主板"、"创业板"）

        Returns:
            该市场的所有股票
        """
        return get_stocks_by_market(market)

    @classmethod
    def get_all_industries(cls) -> List[str]:
        """获取所有行业列表

        Returns:
            去重后的行业名称列表
        """
        return get_all_industries()

    @classmethod
    def get_all_areas(cls) -> List[str]:
        """获取所有地区列表

        Returns:
            去重后的地区名称列表
        """
        return get_all_areas()

    @classmethod
    def save_to_csv(cls, filepath: str = "data/stock_list_backup.csv"):
        """将默认股票列表保存到 CSV

        Args:
            filepath: 保存路径
        """
        try:
            df = pd.DataFrame(DEFAULT_STOCKS)
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(filepath, index=False, encoding="utf-8-sig")
            logger.info(f"[OK] 股票列表已保存到: {filepath}")
        except Exception as e:
            logger.error(f"[ERROR] 保存股票列表失败: {e}")
