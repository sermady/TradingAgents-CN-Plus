# -*- coding: utf-8 -*-
"""
股票基础信息标准化器

将各数据源（Tushare/Baostock/AkShare）的原始数据转换为统一格式
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime

from tradingagents.dataflows.schemas.stock_basic_schema import (
    StockBasicData,
    get_full_symbol,
    get_market_info,
    normalize_date,
    convert_to_float,
    validate_stock_basic_data,
)

logger = logging.getLogger("dataflows.standardizer")


class StockBasicStandardizer(ABC):
    """股票基础信息标准化器基类"""

    PROVIDER_NAME = "base"

    def standardize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        标准化单条数据

        Args:
            raw_data: 原始数据字典

        Returns:
            标准化后的数据字典
        """
        if not raw_data:
            return {}

        try:
            basic_data = self._transform(raw_data)
            return self._post_process(basic_data)
        except Exception as e:
            logger.error(f"[{self.PROVIDER_NAME}] 标准化失败: {e}, data={raw_data}")
            return {}

    def standardize_list(self, raw_list: list) -> list:
        """
        标准化数据列表

        Args:
            raw_list: 原始数据列表

        Returns:
            标准化后的数据列表
        """
        return [self.standardize(item) for item in raw_list if item]

    @abstractmethod
    def _transform(self, raw_data: Dict[str, Any]) -> StockBasicData:
        """
        转换原始数据为核心格式

        Args:
            raw_data: 原始数据字典

        Returns:
            StockBasicData实例
        """
        pass

    def _post_process(self, data: StockBasicData) -> Dict[str, Any]:
        """
        后处理：补全字段、验证数据

        Args:
            data: StockBasicData实例

        Returns:
            标准化后的字典
        """
        result = data.to_dict()

        code = result.get("code", "")
        if code and not result.get("symbol"):
            result["symbol"] = code

        if code:
            market_info = get_market_info(code)
            if not result.get("market"):
                result["market"] = market_info["market"]
            if not result.get("exchange"):
                result["exchange"] = market_info["exchange"]
            if not result.get("exchange_name"):
                result["exchange_name"] = market_info["exchange_name"]

        if code and not result.get("full_symbol"):
            result["full_symbol"] = get_full_symbol(code, result.get("exchange"))

        if not result.get("last_sync"):
            result["last_sync"] = datetime.now().isoformat()

        if not result.get("data_version"):
            result["data_version"] = 1

        # Validate the standardized data
        validation_result = validate_stock_basic_data(result)
        if not validation_result["valid"]:
            logger.warning(
                f"[{self.PROVIDER_NAME}] 数据验证失败: {validation_result['errors']}, code={result.get('code')}"
            )
            # Add warnings to the result for debugging
            result["_validation_warnings"] = validation_result.get("warnings", [])
            result["_validation_errors"] = validation_result.get("errors", [])

        return result


class TushareBasicStandardizer(StockBasicStandardizer):
    """Tushare数据源标准化器"""

    PROVIDER_NAME = "tushare"

    def _transform(self, raw_data: Dict[str, Any]) -> StockBasicData:
        code = (
            raw_data.get("ts_code", "").split(".")[0] if raw_data.get("ts_code") else ""
        )
        if not code:
            code = raw_data.get("symbol", "")

        market_info = get_market_info(code)

        ts_code = raw_data.get("ts_code", "")
        full_symbol = raw_data.get("full_symbol") or get_full_symbol(
            code, raw_data.get("exchange") or market_info["exchange"]
        )

        return StockBasicData(
            code=code,
            symbol=raw_data.get("symbol", code),
            ts_code=ts_code,
            full_symbol=full_symbol,
            name=raw_data.get("name", f"股票{code}"),
            market=raw_data.get("market") or market_info["market"],
            exchange=raw_data.get("exchange") or market_info["exchange"],
            exchange_name=raw_data.get("exchange_name") or market_info["exchange_name"],
            list_status=raw_data.get("list_status", "L"),
            area=raw_data.get("area", ""),
            industry=raw_data.get("industry", ""),
            industry_sw=raw_data.get("industry_sw", ""),
            industry_gn=raw_data.get("industry_gn", ""),
            list_date=normalize_date(raw_data.get("list_date")) or "",
            delist_date=normalize_date(raw_data.get("delist_date")),
            is_hs=raw_data.get("is_hs", "N"),
            act_name=raw_data.get("act_name", ""),
            act_ent_type=raw_data.get("act_ent_type", ""),
            pe=convert_to_float(raw_data.get("pe")),
            pe_ttm=convert_to_float(raw_data.get("pe_ttm")),
            pb=convert_to_float(raw_data.get("pb")),
            ps=convert_to_float(raw_data.get("ps")),
            pcf=convert_to_float(raw_data.get("pcf")),
            total_mv=convert_to_float(raw_data.get("total_mv")),
            circ_mv=convert_to_float(raw_data.get("circ_mv")),
            turnover_rate=convert_to_float(raw_data.get("turnover_rate")),
            volume_ratio=convert_to_float(raw_data.get("volume_ratio")),
            data_source=self.PROVIDER_NAME,
            data_version=1,
        )


class BaostockBasicStandardizer(StockBasicStandardizer):
    """BaoStock数据源标准化器"""

    PROVIDER_NAME = "baostock"

    def _transform(self, raw_data: Dict[str, Any]) -> StockBasicData:
        code = raw_data.get("code", "")
        if not code:
            code = raw_data.get("symbol", "")

        market_info = get_market_info(code)

        full_symbol = raw_data.get("full_symbol") or get_full_symbol(
            code, raw_data.get("exchange") or market_info["exchange"]
        )

        ts_code = raw_data.get("ts_code") or full_symbol

        return StockBasicData(
            code=code,
            symbol=raw_data.get("symbol", code),
            ts_code=ts_code,
            full_symbol=full_symbol,
            name=raw_data.get("name", f"股票{code}"),
            market=raw_data.get("market") or market_info["market"],
            exchange=raw_data.get("exchange") or market_info["exchange"],
            exchange_name=raw_data.get("exchange_name") or market_info["exchange_name"],
            list_status=raw_data.get("list_status", "L"),
            area=raw_data.get("area", ""),
            industry=raw_data.get("industry", ""),
            industry_sw=raw_data.get("industry_sw", ""),
            industry_gn=raw_data.get("industry_gn", ""),
            list_date=normalize_date(raw_data.get("list_date")) or "",
            delist_date=normalize_date(raw_data.get("delist_date")),
            is_hs=raw_data.get("is_hs", "N"),
            act_name=raw_data.get("act_name", ""),
            act_ent_type=raw_data.get("act_ent_type", ""),
            pe=convert_to_float(raw_data.get("pe")),
            pe_ttm=convert_to_float(raw_data.get("pe_ttm")),
            pb=convert_to_float(raw_data.get("pb")),
            ps=convert_to_float(raw_data.get("ps")),
            pcf=convert_to_float(raw_data.get("pcf")),
            total_mv=convert_to_float(raw_data.get("total_mv")),
            circ_mv=convert_to_float(raw_data.get("circ_mv")),
            turnover_rate=convert_to_float(raw_data.get("turnover_rate")),
            volume_ratio=convert_to_float(raw_data.get("volume_ratio")),
            data_source=self.PROVIDER_NAME,
            data_version=1,
        )


class AkShareBasicStandardizer(StockBasicStandardizer):
    """AkShare数据源标准化器"""

    PROVIDER_NAME = "akshare"

    def _transform(self, raw_data: Dict[str, Any]) -> StockBasicData:
        code = raw_data.get("code", "")
        if not code:
            code = raw_data.get("symbol", "")

        market_info = get_market_info(code)

        full_symbol = raw_data.get("full_symbol") or get_full_symbol(
            code, raw_data.get("exchange") or market_info["exchange"]
        )

        ts_code = raw_data.get("ts_code") or full_symbol

        return StockBasicData(
            code=code,
            symbol=raw_data.get("symbol", code),
            ts_code=ts_code,
            full_symbol=full_symbol,
            name=raw_data.get("name", f"股票{code}"),
            market=raw_data.get("market") or market_info["market"],
            exchange=raw_data.get("exchange") or market_info["exchange"],
            exchange_name=raw_data.get("exchange_name") or market_info["exchange_name"],
            list_status=raw_data.get("list_status", "L"),
            area=raw_data.get("area", ""),
            industry=raw_data.get("industry", ""),
            industry_sw=raw_data.get("industry_sw", ""),
            industry_gn=raw_data.get("industry_gn", ""),
            list_date=normalize_date(raw_data.get("list_date")) or "",
            delist_date=normalize_date(raw_data.get("delist_date")),
            is_hs=raw_data.get("is_hs", "N"),
            act_name=raw_data.get("act_name", ""),
            act_ent_type=raw_data.get("act_ent_type", ""),
            pe=convert_to_float(raw_data.get("pe")),
            pe_ttm=convert_to_float(raw_data.get("pe_ttm")),
            pb=convert_to_float(raw_data.get("pb")),
            ps=convert_to_float(raw_data.get("ps")),
            pcf=convert_to_float(raw_data.get("pcf")),
            total_mv=convert_to_float(raw_data.get("total_mv")),
            circ_mv=convert_to_float(raw_data.get("circ_mv")),
            turnover_rate=convert_to_float(raw_data.get("turnover_rate")),
            volume_ratio=convert_to_float(raw_data.get("volume_ratio")),
            data_source=self.PROVIDER_NAME,
            data_version=1,
        )


STANDARDIZER_MAP = {
    "tushare": TushareBasicStandardizer(),
    "baostock": BaostockBasicStandardizer(),
    "akshare": AkShareBasicStandardizer(),
}


def standardize_stock_basic(
    raw_data: Dict[str, Any], provider: str = "tushare"
) -> Dict[str, Any]:
    """
    标准化股票基础信息（便捷函数）

    Args:
        raw_data: 原始数据字典
        provider: 数据源标识

    Returns:
        标准化后的数据字典
    """
    standardizer = STANDARDIZER_MAP.get(provider.lower())
    if standardizer:
        return standardizer.standardize(raw_data)

    logger.warning(
        f"[standardize_stock_basic] 未知数据源: {provider}，使用tushare标准化器"
    )
    return TushareBasicStandardizer().standardize(raw_data)


def get_standardizer(provider: str) -> StockBasicStandardizer:
    """
    获取指定数据源的标准化器

    Args:
        provider: 数据源标识

    Returns:
        标准化器实例
    """
    return STANDARDIZER_MAP.get(provider.lower(), TushareBasicStandardizer())
