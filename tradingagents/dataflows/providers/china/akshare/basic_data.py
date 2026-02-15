# -*- coding: utf-8 -*-
"""
AKShare基础数据模块

包含股票基础信息获取功能
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class BasicDataMixin:
    """基础数据功能混入类"""

    def get_stock_list_sync(self) -> Optional[pd.DataFrame]:
        """获取股票列表（同步版本）"""
        if not self.connected:
            return None

        try:
            logger.info("📋 获取AKShare股票列表（同步）...")
            stock_df = self.ak.stock_info_a_code_name()

            if stock_df is None or stock_df.empty:
                logger.warning("⚠️ AKShare股票列表为空")
                return None

            logger.info(f"✅ AKShare股票列表获取成功: {len(stock_df)}只股票")
            return stock_df

        except Exception as e:
            logger.error(f"❌ AKShare获取股票列表失败: {e}")
            return None

    async def get_stock_list(self) -> List[Dict[str, Any]]:
        """
        获取股票列表

        Returns:
            股票列表，包含代码和名称
        """
        if not self.connected:
            return []

        # 确保 self.ak 已初始化
        if self.ak is None:
            return []

        try:
            logger.info("📋 获取AKShare股票列表...")

            # 使用线程池异步获取股票列表，添加超时保护
            def fetch_stock_list():
                return self.ak.stock_info_a_code_name()

            stock_df = await asyncio.to_thread(fetch_stock_list)

            if stock_df is None or stock_df.empty:
                logger.warning("⚠️ AKShare股票列表为空")
                return []

            # 转换为标准格式
            stock_list = []
            for _, row in stock_df.iterrows():
                stock_list.append(
                    {
                        "code": str(row.get("code", "")),
                        "name": str(row.get("name", "")),
                        "source": "akshare",
                    }
                )

            logger.info(f"✅ AKShare股票列表获取成功: {len(stock_list)}只股票")
            return stock_list

        except Exception as e:
            logger.error(f"❌ AKShare获取股票列表失败: {e}")
            return []

    async def get_stock_basic_info(
        self, symbol: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        获取股票基础信息

        Args:
            symbol: 股票代码

        Returns:
            标准化的股票基础信息
        """
        if not self.connected:
            return None

        # 兼容旧代码：symbol 为 None 时返回 None
        if symbol is None:
            return None

        code = symbol  # 内部使用 code 保持兼容性

        try:
            stock_info = await self._get_stock_info_detail(code)

            if not stock_info:
                logger.warning(f"⚠️ 未找到{code}的基础信息")
                return None

            stock_info["code"] = code
            result = self.standardize_basic_info(stock_info)
            logger.debug(f"✅ {code}基础信息获取成功")
            return result

        except Exception as e:
            logger.error(f"❌ 获取{code}基础信息失败: {e}")
            return None

    async def _get_stock_list_cached(self):
        """获取缓存的股票列表（避免重复获取）"""
        if self.ak is None:
            return None

        # 如果缓存存在且未过期（1小时），直接返回
        if self._stock_list_cache is not None and self._cache_time is not None:
            if datetime.now() - self._cache_time < timedelta(hours=1):
                return self._stock_list_cache

        # 否则重新获取
        def fetch_stock_list():
            return self.ak.stock_info_a_code_name()

        try:
            stock_list = await asyncio.to_thread(fetch_stock_list)
            if stock_list is not None and not stock_list.empty:
                self._stock_list_cache = stock_list
                self._cache_time = datetime.now()
                logger.info(f"✅ 股票列表缓存更新: {len(stock_list)} 只股票")
                return stock_list
        except Exception as e:
            logger.error(f"❌ 获取股票列表失败: {e}")

        return None

    async def _get_stock_info_detail(self, code: str) -> Dict[str, Any]:
        """获取股票详细信息"""
        if self.ak is None:
            return {
                "code": code,
                "name": f"股票{code}",
                "industry": "未知",
                "area": "未知",
            }

        try:
            # 方法1: 尝试获取个股详细信息（包含行业、地区等详细信息）
            def fetch_individual_info():
                return self.ak.stock_individual_info_em(symbol=code)

            try:
                stock_info = await asyncio.to_thread(fetch_individual_info)

                if (
                    stock_info is not None
                    and hasattr(stock_info, "empty")
                    and not stock_info.empty
                ):
                    # 解析信息
                    info = {"code": code}

                    # 提取股票名称
                    name_row = stock_info[stock_info["item"] == "股票简称"]
                    if not name_row.empty:
                        info["name"] = str(name_row["value"].iloc[0])  # type: ignore

                    # 提取行业信息
                    industry_row = stock_info[stock_info["item"] == "所属行业"]
                    if not industry_row.empty:
                        info["industry"] = str(industry_row["value"].iloc[0])  # type: ignore

                    # 提取地区信息
                    area_row = stock_info[stock_info["item"] == "所属地区"]
                    if not area_row.empty:
                        info["area"] = str(area_row["value"].iloc[0])  # type: ignore

                    # 提取上市日期
                    list_date_row = stock_info[stock_info["item"] == "上市时间"]
                    if not list_date_row.empty:
                        info["list_date"] = str(list_date_row["value"].iloc[0])  # type: ignore

                    return info
            except Exception as e:
                logger.debug(f"获取{code}个股详细信息失败: {e}")

            # 方法2: 从缓存的股票列表中获取基本信息（只有代码和名称）
            try:
                stock_list = await self._get_stock_list_cached()
                if stock_list is not None and not stock_list.empty:
                    stock_row = stock_list[stock_list["code"] == code]
                    if not stock_row.empty:
                        return {
                            "code": code,
                            "name": str(stock_row["name"].iloc[0]),  # type: ignore
                            "industry": "未知",
                            "area": "未知",
                        }
            except Exception as e:
                logger.debug(f"从股票列表获取{code}信息失败: {e}")

            # 如果都失败，返回基本信息
            return {
                "code": code,
                "name": f"股票{code}",
                "industry": "未知",
                "area": "未知",
            }

        except Exception as e:
            logger.debug(f"获取{code}详细信息失败: {e}")
            return {
                "code": code,
                "name": f"股票{code}",
                "industry": "未知",
                "area": "未知",
            }
