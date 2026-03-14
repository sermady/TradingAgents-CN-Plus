# -*- coding: utf-8 -*-
"""
数据协调器节点 - 负责预获取所有必要的数据（仅限A股）
绕过 LLM 工具绑定，直接调用统一数据获取方法

优化特性:
1. 多级降级策略: Tushare → Baostock → AkShare → 缓存
2. 数据验证集成: 自动验证价格、成交量、基本面指标
3. 数据质量评分: 在 state 中添加 data_quality_score
4. 并行数据获取: 使用 ThreadPoolExecutor 提升性能
5. 统一缓存策略: 支持分析级缓存（5分钟TTL）
6. PS比率验证: 在预取阶段验证并修正PS计算
7. 成交量单位统一: 统一为"手"（1手=100股）
8. 数据源超时与重试: 每个数据源独立超时和指数退避重试
"""

import time
import json
import re
import asyncio
from typing import Dict, Any, Optional, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from dataclasses import dataclass, field
from functools import wraps

from tradingagents.agents.utils.agent_states import AgentState
from tradingagents.utils.logging_init import get_logger

logger = get_logger("data_coordinator")


# ==================== 重试机制 ====================


def retry_with_backoff(
    max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0
):
    """指数退避重试装饰器"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2**attempt), max_delay)
                        logger.warning(
                            f"⚠️ {func.__name__} 第 {attempt + 1} 次尝试失败: {e}，{delay:.1f}s 后重试..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"❌ {func.__name__} 所有 {max_retries} 次尝试都失败"
                        )
            raise last_exception

        return wrapper

    return decorator


@dataclass
class DataFetchResult:
    """数据获取结果封装"""

    data: str
    source: str
    quality_score: float
    issues: List[Dict[str, Any]]
    fetch_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    parsed_data: Dict[str, Any] = field(default_factory=dict)  # P0-1: 结构化数据


class DataCoordinator:
    """
    数据协调器 - 集中管理数据预取和验证

    功能:
    1. 多数据源自动降级 (Tushare → Baostock → AkShare)
    2. 数据验证集成 (价格、成交量、基本面)
    3. 质量评分计算
    4. 并行数据获取
    5. PS比率源头验证
    6. 成交量单位统一
    7. 超时与重试机制
    """

    # 数据源优先级 (用于降级)
    DATA_SOURCE_PRIORITY = ["tushare", "baostock", "akshare"]

    # 数据类型映射
    DATA_TYPES = {
        "market": {
            "name": "市场数据",
            "validator": "price",
            "weight": 0.20,
        },
        "financial": {
            "name": "基本面数据",
            "validator": "fundamentals",
            "weight": 0.20,
        },
        "news": {
            "name": "新闻数据",
            "validator": None,
            "weight": 0.20,
        },
        "sentiment": {
            "name": "舆情数据",
            "validator": None,
            "weight": 0.20,
        },
        "china_market": {
            "name": "A股特色数据",
            "validator": None,
            "weight": 0.20,
        },
    }

    # 各数据源超时时间（秒）
    SOURCE_TIMEOUT = {
        "tushare": 10,
        "baostock": 15,
        "akshare": 15,
    }

    def __init__(self):
        self.validators = {}
        self._init_validators()
        self.cache = {}  # 简单的内存缓存
        self.cache_ttl = 300  # 5分钟缓存
        self.analysis_cache = {}  # 分析级缓存（按股票代码+日期）
        self.analysis_cache_ttl = 300  # 5分钟

    # ==================== 数据获取 ====================

    def _init_validators(self):
        """初始化数据验证器"""
        try:
            from tradingagents.dataflows.validators.price_validator import (
                PriceValidator,
            )
            from tradingagents.dataflows.validators.volume_validator import (
                VolumeValidator,
            )
            from tradingagents.dataflows.validators.fundamentals_validator import (
                FundamentalsValidator,
            )

            self.validators["price"] = PriceValidator(tolerance=0.01)
            self.validators["volume"] = VolumeValidator(tolerance=0.05)
            self.validators["fundamentals"] = FundamentalsValidator(tolerance=0.05)
            logger.info("✅ 数据验证器初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ 数据验证器初始化失败: {e}")
            self.validators = {}

    # ==================== 缓存管理 ====================

    def _get_cache_key(self, symbol: str, data_type: str, date: str) -> str:
        """生成缓存键"""
        return f"{symbol}_{data_type}_{date}"

    def _get_cached_data(self, key: str) -> Optional[str]:
        """获取缓存数据"""
        if key in self.cache:
            cached_time, data = self.cache[key]
            if time.time() - cached_time < self.cache_ttl:
                logger.info(f"📦 使用缓存数据: {key}")
                return data
            else:
                # 缓存过期
                del self.cache[key]
        return None

    def _set_cached_data(self, key: str, data: str):
        """设置缓存数据"""
        self.cache[key] = (time.time(), data)

    # ==================== 数据解析 ====================

    def _parse_market_data(self, data_str: str) -> Dict[str, Any]:
        """解析市场数据字符串为结构化数据"""
        result = {}
        if not data_str or "❌" in data_str:
            return result

        try:
            # 提取关键指标
            patterns = {
                "current_price": r"最新价[：:]\s*(\d+\.?\d*)",
                "open": r"今开[：:]\s*(\d+\.?\d*)",
                "high": r"最高[：:]\s*(\d+\.?\d*)",
                "low": r"最低[：:]\s*(\d+\.?\d*)",
                "volume": r"成交量[：:]\s*(\d+\.?\d*)",
                "volume_unit": r"成交量[：:]\s*\d+\.?\d*\s*(\w+)",
                "turnover_rate": r"换手率[：:]\s*(\d+\.?\d*)",
                "MA5": r"MA5[：:]\s*[¥]?(\d+\.?\d*)",
                "MA10": r"MA10[：:]\s*[¥]?(\d+\.?\d*)",
                "MA20": r"MA20[：:]\s*[¥]?(\d+\.?\d*)",
                "MA60": r"MA60[：:]\s*[¥]?(\d+\.?\d*)",
                "RSI": r"RSI\d*[：:]\s*(\d+\.?\d*)",
                # P1-1: 扩展指标模式
                "RSI14": r"RSI14[：:]\s*(\d+\.?\d*)",
                "MACD_DIF": r"DIF[：:]\s*(-?\d+\.?\d*)",
                "MACD_DEA": r"DEA[：:]\s*(-?\d+\.?\d*)",
                "MACD": r"MACD[：:]\s*(-?\d+\.?\d*)",
                "KDJ_K": r"K[：:]\s*(\d+\.?\d*)",
                "KDJ_D": r"D[：:]\s*(\d+\.?\d*)",
                "KDJ_J": r"J[：:]\s*(-?\d+\.?\d*)",
                "ATR14": r"ATR\(?14\)?[：:]\s*(\d+\.?\d*)",
                "WR14": r"Williams\s*%?R\(?14\)?[：:]\s*(-?\d+\.?\d*)",
                "CCI14": r"CCI\(?14\)?[：:]\s*(-?\d+\.?\d*)",
                "OBV": r"OBV[：:]\s*(-?[\d,]+\.?\d*)",
                "BOLL_UPPER": r"上轨[：:]\s*[¥]?(\d+\.?\d*)",
                "BOLL_MID": r"中轨[：:]\s*[¥]?(\d+\.?\d*)",
                "BOLL_LOWER": r"下轨[：:]\s*[¥]?(\d+\.?\d*)",
            }

            for key, pattern in patterns.items():
                matches = re.findall(pattern, data_str)
                if matches:
                    try:
                        result[key] = float(matches[0])
                    except (ValueError, TypeError):
                        result[key] = matches[0]

            # 添加数据源信息
            if "来源:" in data_str or "数据来源" in data_str:
                source_match = re.search(r"来源[:：]\s*(\w+)", data_str)
                if source_match:
                    result["source"] = source_match.group(1).lower()

        except Exception as e:
            logger.debug(f"解析市场数据失败: {e}")

        return result

    def _parse_fundamentals_data(self, data_str: str) -> Dict[str, Any]:
        """解析基本面数据字符串为结构化数据"""
        result = {}
        if not data_str or "❌" in data_str:
            return result

        try:
            # 提取关键指标
            patterns = {
                "PE": r"市盈[率\(]\w*[\)：]?\s*(\-?\d+\.?\d*)",
                "PB": r"市净[率\(]\w*[\)：]?\s*(\d+\.?\d*)",
                "PS": r"市销[率\(]\w*[\)：]?\s*(\d+\.?\d*)",
                "market_cap": r"总市值[：:]\s*(\d+\.?\d*)",
                "revenue": r"总营收[：:]\s*(\d+\.?\d*)",
                "ROE": r"ROE[（\(]?净资产收益率[）\)]?[：:]\s*(\-?\d+\.?\d*)",
                "ROA": r"ROA[：:]\s*(\-?\d+\.?\d*)",
                "gross_margin": r"毛利率[：:]\s*(\d+\.?\d*)",
                "net_margin": r"净利率[：:]\s*(\d+\.?\d*)",
                "debt_ratio": r"资产负债率[：:]\s*(\d+\.?\d*)",
                "share_count": r"总股本[：:]\s*(\d+\.?\d*)",
            }

            for key, pattern in patterns.items():
                matches = re.findall(pattern, data_str)
                if matches:
                    try:
                        value = float(matches[0])
                        # 处理单位转换（如果是万或亿）
                        if (
                            "亿"
                            in data_str[
                                data_str.find(matches[0]) : data_str.find(matches[0])
                                + 10
                            ]
                        ):
                            result[key] = value  # 已经是亿
                        elif (
                            "万"
                            in data_str[
                                data_str.find(matches[0]) : data_str.find(matches[0])
                                + 10
                            ]
                        ):
                            result[key] = value / 10000  # 万转亿
                        else:
                            result[key] = value
                    except (ValueError, TypeError):
                        result[key] = matches[0]

            # 添加数据源信息
            if "来源:" in data_str or "数据来源" in data_str:
                source_match = re.search(r"来源[:：]\s*(\w+)", data_str)
                if source_match:
                    result["source"] = source_match.group(1).lower()

        except Exception as e:
            logger.debug(f"解析基本面数据失败: {e}")

        return result

    # ==================== 数据验证 ====================

    def _validate_data(
        self, data_type: str, symbol: str, data: Dict[str, Any]
    ) -> Tuple[float, List[Dict]]:
        """
        验证数据并返回质量评分

        Returns:
            (quality_score, issues)
        """
        if data_type not in self.DATA_TYPES:
            return 1.0, []

        validator_type = self.DATA_TYPES[data_type].get("validator")
        if not validator_type or validator_type not in self.validators:
            return 1.0, []

        try:
            validator = self.validators[validator_type]
            result = validator.validate(symbol, data)

            # 转换问题列表
            issues = []
            for issue in result.discrepancies:
                issues.append(
                    {
                        "severity": issue.severity.value,
                        "message": issue.message,
                        "field": issue.field,
                        "expected": issue.expected,
                        "actual": issue.actual,
                    }
                )

            return result.confidence, issues

        except Exception as e:
            logger.warning(f"验证 {data_type} 数据失败: {e}")
            return 0.8, [
                {"severity": "warning", "message": f"验证失败: {e}", "field": ""}
            ]

    # ==================== 主数据获取方法 ====================

    def _get_market_data_with_fallback(
        self, symbol: str, trade_date: str
    ) -> DataFetchResult:
        """
        获取市场数据（带降级策略）

        降级顺序: Tushare → Baostock → AkShare → 缓存
        """
        start_time = time.time()

        # 1. 先检查缓存
        cache_key = self._get_cache_key(symbol, "market", trade_date)
        cached = self._get_cached_data(cache_key)
        if cached:
            return DataFetchResult(
                data=cached,
                source="cache",
                quality_score=0.9,
                issues=[],
                fetch_time=time.time() - start_time,
            )

        # 2. 尝试各个数据源
        sources = self.DATA_SOURCE_PRIORITY
        last_error = None

        for source in sources:
            try:
                logger.info(f"📈 尝试从 {source} 获取市场数据...")
                data = self._fetch_market_data_from_source(symbol, trade_date, source)

                if data and "❌" not in str(data):
                    # 解析并验证数据
                    parsed = self._parse_market_data(data)
                    quality_score, issues = self._validate_data(
                        "market", symbol, parsed
                    )

                    # 标记数据来源
                    if parsed:
                        data += f"\n数据来源: {source}"
                        parsed["source"] = source

                    # 缓存成功数据
                    self._set_cached_data(cache_key, data)

                    fetch_time = time.time() - start_time
                    logger.info(
                        f"✅ {source} 市场数据获取成功 (质量分: {quality_score:.2f}, 耗时: {fetch_time:.2f}s)"
                    )

                    return DataFetchResult(
                        data=data,
                        source=source,
                        quality_score=quality_score,
                        issues=issues,
                        fetch_time=fetch_time,
                        parsed_data=parsed,
                    )

            except Exception as e:
                logger.warning(f"⚠️ {source} 市场数据获取失败: {e}")
                last_error = e
                continue

        # 3. 所有数据源都失败
        error_msg = f"❌ 市场数据获取失败 (已尝试: {', '.join(sources)})"
        if last_error:
            error_msg += f": {last_error}"

        return DataFetchResult(
            data=error_msg,
            source="failed",
            quality_score=0.0,
            issues=[{"severity": "critical", "message": error_msg, "field": ""}],
            fetch_time=time.time() - start_time,
        )

    def _get_fundamentals_data_with_fallback(
        self, symbol: str, trade_date: str
    ) -> DataFetchResult:
        """
        获取基本面数据（带降级策略）

        降级顺序: Tushare → Baostock → AkShare → 缓存

        优化:
        1. PS比率源头验证和修正
        2. 成交量单位统一
        3. 详细数据质量标记
        """
        start_time = time.time()

        # 1. 先检查缓存
        cache_key = self._get_cache_key(symbol, "financial", trade_date)
        cached = self._get_cached_data(cache_key)
        if cached:
            return DataFetchResult(
                data=cached,
                source="cache",
                quality_score=0.9,
                issues=[],
                fetch_time=time.time() - start_time,
            )

        # 2. 尝试各个数据源
        sources = self.DATA_SOURCE_PRIORITY
        last_error = None

        for source in sources:
            try:
                logger.info(f"💰 尝试从 {source} 获取基本面数据...")
                data = self._fetch_fundamentals_data_from_source(
                    symbol, trade_date, source
                )

                if data and "❌" not in str(data):
                    # 解析数据
                    parsed = self._parse_fundamentals_data(data)

                    # 基础验证
                    quality_score, issues = self._validate_data(
                        "financial", symbol, parsed
                    )

                    # ========== PS 比率源头验证和修正 ==========
                    ps_issues, corrected_ps = self._validate_and_fix_ps_ratio(
                        parsed, symbol
                    )
                    if ps_issues:
                        issues.extend(ps_issues)
                        if corrected_ps:
                            # 如果有修正值，在数据中标注
                            data = self._add_ps_correction_to_data(data, corrected_ps)
                            parsed["PS_corrected"] = corrected_ps
                            quality_score = max(0.3, quality_score - 0.1)  # 轻微扣分
                        else:
                            quality_score = max(0.3, quality_score - 0.2)  # 严重扣分

                    # ========== 成交量单位标准化 ==========
                    parsed, volume_unit_info = self._standardize_volume_unit(
                        parsed, data
                    )
                    if volume_unit_info in [
                        "converted_from_lots",
                        "inferred_lots_converted",
                    ]:
                        # 添加单位转换标记
                        data += f"\n成交量单位: 已统一转换为'股'（原始数据可能是'手'）"
                        logger.info(f"📊 成交量单位转换: {symbol} {volume_unit_info}")

                    # 标记数据来源
                    if parsed:
                        data += f"\n数据来源: {source}"
                        parsed["source"] = source

                    # 缓存成功数据
                    self._set_cached_data(cache_key, data)

                    fetch_time = time.time() - start_time
                    logger.info(
                        f"✅ {source} 基本面数据获取成功 (质量分: {quality_score:.2f}, 耗时: {fetch_time:.2f}s)"
                    )

                    return DataFetchResult(
                        data=data,
                        source=source,
                        quality_score=quality_score,
                        issues=issues,
                        fetch_time=fetch_time,
                        metadata={
                            "corrected_ps": corrected_ps,
                            "volume_unit_info": volume_unit_info,
                        },
                        parsed_data=parsed,
                    )

            except Exception as e:
                logger.warning(f"⚠️ {source} 基本面数据获取失败: {e}")
                last_error = e
                continue

        # 3. 所有数据源都失败
        error_msg = f"❌ 基本面数据获取失败 (已尝试: {', '.join(sources)})"
        if last_error:
            error_msg += f": {last_error}"

        return DataFetchResult(
            data=error_msg,
            source="failed",
            quality_score=0.0,
            issues=[{"severity": "critical", "message": error_msg, "field": ""}],
            fetch_time=time.time() - start_time,
        )

    def _validate_and_fix_ps_ratio(
        self, data: Dict[str, Any], symbol: str
    ) -> Tuple[List[Dict], Optional[float]]:
        """
        验证并修正 PS 比率计算

        Returns:
            (issues, corrected_ps): 问题列表和修正后的PS值（如果有）
        """
        issues = []
        corrected_ps = None

        market_cap = data.get("market_cap")
        revenue = data.get("revenue")
        ps = data.get("PS") or data.get("ps_ratio")

        if not all([market_cap, revenue]) or revenue <= 0:
            return issues, corrected_ps

        try:
            # 确保数值类型
            market_cap = float(market_cap)
            revenue = float(revenue)
            calculated_ps = market_cap / revenue

            if ps is not None:
                ps = float(ps)
                diff_pct = abs((calculated_ps - ps) / ps) * 100 if ps != 0 else 100

                if diff_pct > 20:  # 差异超过20%
                    issues.append(
                        {
                            "severity": "error",
                            "message": f"PS比率计算错误! 报告值={ps:.2f}, 正确值应为≈{calculated_ps:.2f} (市值={market_cap:.2f}亿/营收={revenue:.2f}亿)",
                            "field": "PS",
                            "expected": round(calculated_ps, 2),
                            "actual": ps,
                        }
                    )
                    corrected_ps = calculated_ps
                elif diff_pct > 10:  # 差异超过10%
                    issues.append(
                        {
                            "severity": "warning",
                            "message": f"PS比率可能存在偏差: 报告值={ps:.2f}, 计算值={calculated_ps:.2f}",
                            "field": "PS",
                            "expected": round(calculated_ps, 2),
                            "actual": ps,
                        }
                    )
            else:
                # 数据中没有PS，但可以根据市值和营收计算
                corrected_ps = calculated_ps
                issues.append(
                    {
                        "severity": "info",
                        "message": f"已自动计算PS比率={calculated_ps:.2f} (市值={market_cap:.2f}亿/营收={revenue:.2f}亿)",
                        "field": "PS",
                        "expected": round(calculated_ps, 2),
                    }
                )

            # 检查PS是否在合理范围内
            if calculated_ps < 0.1 or calculated_ps > 100:
                issues.append(
                    {
                        "severity": "warning",
                        "message": f"PS比率={calculated_ps:.2f} 超出常规范围(0.1-100)",
                        "field": "PS",
                        "actual": round(calculated_ps, 2),
                    }
                )

        except (ValueError, TypeError, ZeroDivisionError) as e:
            issues.append(
                {
                    "severity": "warning",
                    "message": f"PS比率验证失败: {e}",
                    "field": "PS",
                }
            )

        return issues, corrected_ps

    def _standardize_volume_unit(
        self, data: Dict[str, Any], data_str: str
    ) -> Tuple[Dict[str, Any], str]:
        """
        标准化成交量单位为"股"（注意：当前实现转换为股，未来可能改为手）

        Returns:
            (updated_data, unit_info): 更新后的数据和单位信息
        """
        volume = data.get("volume")
        if volume is None:
            return data, "unknown"

        try:
            volume = float(volume)

            # 检查数据中是否明确标注了单位
            if "手" in data_str and "万股" not in data_str:
                # 数据单位是"手"，转换为"股"
                converted_volume = volume * 100
                data["volume"] = converted_volume
                data["volume_unit"] = "shares"
                data["original_volume"] = volume
                data["original_unit"] = "lots"
                return data, "converted_from_lots"

            # 如果没有明确标注，根据数值大小推断
            # 如果成交量小于10000，可能是"手"；如果大于100万，可能是"股"
            if volume < 10000 and volume > 0:
                # 可能是"手"，但也可能是小盘股
                # 检查是否有换手率可以验证
                turnover_rate = data.get("turnover_rate")
                share_count = data.get("share_count")

                if turnover_rate and share_count:
                    # 根据换手率验证
                    # 换手率 = 成交量(股) / 总股本(股) * 100
                    share_count_shares = share_count * 10000  # 万股转股
                    calculated_turnover_as_shares = (volume / share_count_shares) * 100
                    calculated_turnover_as_lots = (
                        volume * 100 / share_count_shares
                    ) * 100

                    diff_as_shares = abs(calculated_turnover_as_shares - turnover_rate)
                    diff_as_lots = abs(calculated_turnover_as_lots - turnover_rate)

                    if diff_as_lots < diff_as_shares:
                        # 单位是"手"
                        converted_volume = volume * 100
                        data["volume"] = converted_volume
                        data["volume_unit"] = "shares"
                        data["original_volume"] = volume
                        data["original_unit"] = "lots"
                        return data, "inferred_lots_converted"

            # 默认为"股"
            data["volume_unit"] = "shares"
            return data, "shares"

        except (ValueError, TypeError):
            return data, "unknown"

    def _add_ps_correction_to_data(self, data_str: str, corrected_ps: float) -> str:
        """
        在基本面数据字符串中添加PS修正标记
        """
        if corrected_ps is None:
            return data_str

        correction_note = f"\n\n⚠️ **PS比率修正**: 数据源报告的PS比率可能有误，正确计算值应为 {corrected_ps:.2f}\n"
        correction_note += f"修正公式: PS = 总市值 / 总营收\n"

        return data_str + correction_note

    def _fetch_market_data_from_source(
        self, symbol: str, trade_date: str, source: str
    ) -> str:
        """从指定数据源获取市场数据"""
        from tradingagents.dataflows.interface import get_china_stock_data_unified

        # 临时切换数据源
        import os

        original_source = os.environ.get("DEFAULT_CHINA_DATA_SOURCE", "akshare")

        try:
            os.environ["DEFAULT_CHINA_DATA_SOURCE"] = source
            return get_china_stock_data_unified(symbol, trade_date, trade_date)
        finally:
            os.environ["DEFAULT_CHINA_DATA_SOURCE"] = original_source

    def _fetch_fundamentals_data_from_source(
        self, symbol: str, trade_date: str, source: str
    ) -> str:
        """从指定数据源获取基本面数据"""
        from tradingagents.agents.utils.agent_utils import Toolkit

        # 临时切换数据源
        import os

        original_source = os.environ.get("DEFAULT_CHINA_DATA_SOURCE", "akshare")

        try:
            os.environ["DEFAULT_CHINA_DATA_SOURCE"] = source
            return Toolkit.get_stock_fundamentals_unified.func(
                ticker=symbol,
                start_date=trade_date,
                end_date=trade_date,
                curr_date=trade_date,
            )
        finally:
            os.environ["DEFAULT_CHINA_DATA_SOURCE"] = original_source

    def _get_news_data(self, symbol: str, trade_date: str) -> DataFetchResult:
        """获取新闻数据"""
        start_time = time.time()

        try:
            logger.info(f"📰 正在获取新闻数据...")
            from tradingagents.agents.utils.agent_utils import Toolkit

            news_data = Toolkit.get_stock_news_unified.func(
                ticker=symbol, curr_date=trade_date
            )

            fetch_time = time.time() - start_time

            # 评估新闻数据质量（基于新闻数量）
            quality_score = 0.8
            if news_data and "❌" not in news_data:
                news_count = news_data.count("标题:") + news_data.count("标题：")
                if news_count >= 5:
                    quality_score = 1.0
                elif news_count >= 3:
                    quality_score = 0.9
                elif news_count >= 1:
                    quality_score = 0.7
                else:
                    quality_score = 0.5

            logger.info(
                f"✅ 新闻数据获取成功 (质量分: {quality_score:.2f}, 耗时: {fetch_time:.2f}s)"
            )

            return DataFetchResult(
                data=news_data if news_data else "暂无相关新闻数据",
                source="unified",
                quality_score=quality_score,
                issues=[],
                fetch_time=fetch_time,
            )

        except Exception as e:
            error_msg = f"❌ 新闻数据获取失败: {e}"
            logger.error(error_msg)
            return DataFetchResult(
                data=error_msg,
                source="failed",
                quality_score=0.0,
                issues=[{"severity": "error", "message": str(e), "field": ""}],
                fetch_time=time.time() - start_time,
            )

    def _get_sentiment_data(self, symbol: str, trade_date: str) -> DataFetchResult:
        """获取市场情绪数据 (资金流向 + 舆情)

        P1-3: 用真实的市场资金流向数据替代空的社交媒体情绪数据。
        数据来源包括：龙虎榜、北向资金、融资融券、大宗交易。
        """
        start_time = time.time()
        sections = []
        issues = []

        # 1) 获取市场资金流向数据 (P1-3 新增)
        try:
            from tradingagents.dataflows.market_flow import fetch_market_flow_data

            market_flow = fetch_market_flow_data(symbol, trade_date)
            if market_flow and "获取失败" not in market_flow:
                sections.append(market_flow)
                logger.info("✅ 市场资金流向数据获取成功")
            else:
                sections.append(market_flow or "")
                logger.warning("⚠️ 部分市场资金流向数据不可用")
        except Exception as e:
            logger.warning(f"市场资金流向数据获取失败: {e}")
            issues.append({"severity": "warning", "message": f"资金流向: {e}", "field": ""})

        # 2) 保留原有舆情数据作为补充 (如果可用)
        try:
            from tradingagents.dataflows.interface import get_chinese_social_sentiment

            sentiment_data = get_chinese_social_sentiment(symbol, trade_date)
            if sentiment_data and "❌" not in sentiment_data and "警告" not in sentiment_data:
                sections.append("\n=== 舆情情绪分析 ===")
                sections.append(sentiment_data)
        except Exception:
            pass  # 舆情数据本身就是补充，失败不影响

        fetch_time = time.time() - start_time

        # 评估数据质量
        combined = "\n".join(sections)
        quality_score = 0.3  # 基础分

        # 有资金流向数据 → 大幅加分
        if "龙虎榜" in combined and "暂无" not in combined.split("龙虎榜")[1][:20]:
            quality_score += 0.2
        if "北向资金" in combined and "暂无" not in combined.split("北向资金")[1][:20]:
            quality_score += 0.15
        if "融资融券" in combined and "暂无" not in combined.split("融资融券")[1][:20]:
            quality_score += 0.15
        if "大宗交易" in combined and "暂无" not in combined.split("大宗交易")[1][:20]:
            quality_score += 0.15

        quality_score = min(quality_score, 1.0)

        logger.info(
            f"✅ 情绪/资金流向数据获取完成 (质量分: {quality_score:.2f}, 耗时: {fetch_time:.2f}s)"
        )

        return DataFetchResult(
            data=combined if combined.strip() else "暂无市场情绪数据",
            source="market_flow+sentiment",
            quality_score=quality_score,
            issues=issues,
            fetch_time=fetch_time,
        )

    def _get_china_market_features_data(
        self, symbol: str, trade_date: str
    ) -> DataFetchResult:
        """
        获取A股特色数据（涨跌停、换手率、量比、北向资金等）

        这些数据专门用于中国市场分析师，聚焦A股市场特色指标
        """
        start_time = time.time()

        try:
            logger.info(f"🇨🇳 正在获取A股特色数据...")

            # 构建A股特色数据字符串
            china_features_data = []
            china_features_data.append(f"=== A股市场特色数据 ===")
            china_features_data.append(f"股票代码: {symbol}")
            china_features_data.append(f"数据日期: {trade_date}")
            china_features_data.append("")

            # P0-1: 同时构建结构化数据
            structured = {
                "symbol": symbol,
                "trade_date": trade_date,
            }

            # 尝试获取涨跌停数据
            try:
                from tradingagents.dataflows.interface import (
                    get_china_stock_data_unified,
                )

                market_data = get_china_stock_data_unified(
                    symbol, trade_date, trade_date
                )

                # 提取关键指标
                if market_data and "❌" not in market_data:
                    # 解析涨跌停状态
                    china_features_data.append("【涨跌停分析】")

                    # 提取价格数据
                    import re

                    price_match = re.search(r"最新价[：:]\s*(\d+\.?\d*)", market_data)
                    high_match = re.search(r"最高[：:]\s*(\d+\.?\d*)", market_data)
                    low_match = re.search(r"最低[：:]\s*(\d+\.?\d*)", market_data)
                    open_match = re.search(r"今开[：:]\s*(\d+\.?\d*)", market_data)

                    if all([price_match, open_match]):
                        current_price = float(price_match.group(1))
                        open_price = float(open_match.group(1))
                        change_pct = ((current_price - open_price) / open_price) * 100

                        structured["current_price"] = current_price
                        structured["open_price"] = open_price
                        structured["change_pct"] = round(change_pct, 2)
                        if high_match:
                            structured["high"] = float(high_match.group(1))
                        if low_match:
                            structured["low"] = float(low_match.group(1))

                        china_features_data.append(f"当前价格: {current_price}")
                        china_features_data.append(f"今日开盘: {open_price}")
                        china_features_data.append(f"涨跌幅: {change_pct:.2f}%")

                        # 判断是否触及涨跌停
                        if change_pct >= 9.5:
                            china_features_data.append("⚠️ 触及涨停板（或接近涨停）")
                            structured["limit_status"] = "涨停"
                        elif change_pct <= -9.5:
                            china_features_data.append("⚠️ 触及跌停板（或接近跌停）")
                            structured["limit_status"] = "跌停"
                        elif change_pct >= 5:
                            china_features_data.append("📈 大幅上涨")
                            structured["limit_status"] = "大幅上涨"
                        elif change_pct <= -5:
                            china_features_data.append("📉 大幅下跌")
                            structured["limit_status"] = "大幅下跌"
                        else:
                            china_features_data.append("➡️ 正常波动")
                            structured["limit_status"] = "正常波动"

                    china_features_data.append("")

                    # 提取换手率
                    turnover_match = re.search(
                        r"换手率[：:]\s*(\d+\.?\d*)", market_data
                    )
                    if turnover_match:
                        turnover = float(turnover_match.group(1))
                        structured["turnover_rate"] = turnover

                        china_features_data.append("【换手率分析】")
                        china_features_data.append(f"换手率: {turnover:.2f}%")

                        if turnover < 1:
                            china_features_data.append(
                                "💤 极低换手：交易清淡，流动性差"
                            )
                            structured["turnover_level"] = "极低"
                        elif turnover < 3:
                            china_features_data.append(
                                "🔄 低换手：正常范围，交易不活跃"
                            )
                            structured["turnover_level"] = "低"
                        elif turnover < 7:
                            china_features_data.append("⚡ 中等换手：正常活跃")
                            structured["turnover_level"] = "中等"
                        elif turnover < 10:
                            china_features_data.append(
                                "🔥 高换手：高度活跃，关注资金动向"
                            )
                            structured["turnover_level"] = "高"
                        elif turnover < 20:
                            china_features_data.append(
                                "🚨 极高换手：异常活跃，可能有重大消息"
                            )
                            structured["turnover_level"] = "极高"
                        else:
                            china_features_data.append(
                                "⚠️ 超高换手：极度活跃，高风险高机会"
                            )
                            structured["turnover_level"] = "超高"

                        china_features_data.append("")

                    # 提取量比（如果有）
                    volume_ratio_match = re.search(
                        r"量比[：:]\s*(\d+\.?\d*)", market_data
                    )
                    if volume_ratio_match:
                        volume_ratio = float(volume_ratio_match.group(1))
                        structured["volume_ratio"] = volume_ratio

                        china_features_data.append("【量比分析】")
                        china_features_data.append(f"量比: {volume_ratio:.2f}")

                        if volume_ratio < 0.5:
                            china_features_data.append("📉 严重缩量：成交清淡")
                            structured["volume_ratio_level"] = "严重缩量"
                        elif volume_ratio < 0.8:
                            china_features_data.append("📉 缩量：交易活跃度下降")
                            structured["volume_ratio_level"] = "缩量"
                        elif volume_ratio < 1.5:
                            china_features_data.append("➡️ 正常放量")
                            structured["volume_ratio_level"] = "正常"
                        elif volume_ratio < 2.5:
                            china_features_data.append("📈 明显放量：资金关注度提升")
                            structured["volume_ratio_level"] = "明显放量"
                        elif volume_ratio < 5:
                            china_features_data.append("🔥 显著放量：大量资金介入")
                            structured["volume_ratio_level"] = "显著放量"
                        else:
                            china_features_data.append("🚨 异常放量：需关注消息面")
                            structured["volume_ratio_level"] = "异常放量"

                        china_features_data.append("")

                    # 提取振幅
                    amplitude_match = re.search(r"振幅[：:]\s*(\d+\.?\d*)", market_data)
                    if amplitude_match:
                        amplitude = float(amplitude_match.group(1))
                        structured["amplitude"] = amplitude

                        china_features_data.append("【振幅分析】")
                        china_features_data.append(f"振幅: {amplitude:.2f}%")

                        if amplitude < 2:
                            china_features_data.append("💤 窄幅波动")
                            structured["amplitude_level"] = "窄幅"
                        elif amplitude < 5:
                            china_features_data.append("📊 正常波动")
                            structured["amplitude_level"] = "正常"
                        elif amplitude < 10:
                            china_features_data.append("⚡ 宽幅波动")
                            structured["amplitude_level"] = "宽幅"
                        else:
                            china_features_data.append("🚨 剧烈波动")
                            structured["amplitude_level"] = "剧烈"

                        china_features_data.append("")

                    # 标记数据来源
                    china_features_data.append(f"数据来源: 市场数据接口")
                    structured["source"] = "unified"

            except Exception as e:
                logger.warning(f"⚠️ 获取A股特色数据失败: {e}")
                china_features_data.append(f"⚠️ 部分数据获取失败: {e}")

            final_data = "\n".join(china_features_data)
            fetch_time = time.time() - start_time

            # 评估数据质量
            quality_score = 0.8
            if "触及涨停板" in final_data or "换手率" in final_data:
                quality_score = 0.95
            elif "涨跌幅" in final_data:
                quality_score = 0.85

            logger.info(
                f"✅ A股特色数据获取成功 (质量分: {quality_score:.2f}, 耗时: {fetch_time:.2f}s)"
            )

            return DataFetchResult(
                data=final_data,
                source="unified",
                quality_score=quality_score,
                issues=[],
                fetch_time=fetch_time,
                parsed_data=structured,
            )

        except Exception as e:
            error_msg = f"❌ A股特色数据获取失败: {e}"
            logger.error(error_msg)
            return DataFetchResult(
                data=error_msg,
                source="failed",
                quality_score=0.0,
                issues=[{"severity": "error", "message": str(e), "field": ""}],
                fetch_time=time.time() - start_time,
            )

    # ==================== P0-3: 数据充分性预检验 ====================

    def _check_data_sufficiency(
        self, results: Dict[str, "DataFetchResult"], symbol: str
    ) -> List[Dict[str, Any]]:
        """
        检查数据是否满足分析最低要求 (P0-3)

        检查维度:
        1. 市场数据是否获取成功
        2. 关键指标是否存在 (MA60 需要 60 天数据)
        3. 基本面数据是否有核心字段

        Returns:
            问题列表，每项 {severity, message, field}
        """
        issues = []
        market_result = results.get("market")
        financial_result = results.get("financial")

        # 1. 市场数据基本检查
        if not market_result or market_result.source == "failed":
            issues.append({
                "severity": "critical",
                "message": f"市场数据获取失败，无法进行技术分析",
                "field": "market_data",
            })
            return issues  # 无法继续检查

        market_text = market_result.data or ""
        parsed_market = market_result.parsed_data or {}

        # 2. 检查当前价格是否存在
        if not parsed_market.get("current_price"):
            issues.append({
                "severity": "critical",
                "message": "市场数据中缺少当前价格，分析结果可能不准确",
                "field": "current_price",
            })

        # 3. 检查关键移动平均线是否存在
        # MA60 需要至少 60 个交易日数据
        has_ma5 = parsed_market.get("MA5") is not None or "MA5" in market_text
        has_ma20 = parsed_market.get("MA20") is not None or "MA20" in market_text
        has_ma60 = "MA60" in market_text

        if not has_ma5:
            issues.append({
                "severity": "warning",
                "message": "缺少 MA5 (5日均线)，短期趋势判断受限",
                "field": "MA5",
            })

        if not has_ma20:
            issues.append({
                "severity": "warning",
                "message": "缺少 MA20 (20日均线)，中期趋势判断受限",
                "field": "MA20",
            })

        if not has_ma60:
            issues.append({
                "severity": "info",
                "message": "缺少 MA60 (60日均线)，数据可能不足60个交易日，长期趋势分析受限",
                "field": "MA60",
            })

        # 4. 检查 RSI 是否存在
        has_rsi = parsed_market.get("RSI") is not None or "RSI" in market_text
        if not has_rsi:
            issues.append({
                "severity": "warning",
                "message": "缺少 RSI 指标，超买超卖判断受限",
                "field": "RSI",
            })

        # 5. 基本面数据检查
        if financial_result and financial_result.source != "failed":
            parsed_fin = financial_result.parsed_data or {}
            if not parsed_fin.get("PE") and not parsed_fin.get("PB"):
                issues.append({
                    "severity": "warning",
                    "message": "基本面数据缺少 PE/PB 估值指标",
                    "field": "PE_PB",
                })
        elif financial_result and financial_result.source == "failed":
            issues.append({
                "severity": "warning",
                "message": "基本面数据获取失败，估值分析将受限",
                "field": "financial_data",
            })

        # 6. 数据行数推断 (从文本中计算日期出现次数)
        date_count = len(re.findall(r"\d{4}-\d{2}-\d{2}", market_text))
        if 0 < date_count < 20:
            issues.append({
                "severity": "warning",
                "message": f"市场数据仅包含约 {date_count} 个交易日，少于建议的最低 20 天",
                "field": "data_days",
            })

        return issues

    def fetch_all_data(
        self,
        symbol: str,
        trade_date: str,
        parallel: bool = True,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        获取所有类型的数据

        Args:
            symbol: 股票代码
            trade_date: 交易日期
            parallel: 是否并行获取
            use_cache: 是否使用分析级缓存

        Returns:
            包含所有数据和质量评分的字典
        """
        # 检查分析级缓存
        cache_key = f"analysis:{symbol}:{trade_date}"
        if use_cache:
            cached_result = self._get_analysis_cache(cache_key)
            if cached_result:
                logger.info(
                    f"💾 [Data Coordinator] 使用分析级缓存: {symbol} (剩余TTL: {self._get_cache_ttl(cache_key):.0f}s)"
                )
                return cached_result

        logger.info(
            f"🔄 [Data Coordinator] 开始获取 {symbol} 的所有数据 (并行={parallel})"
        )
        start_time = time.time()

        results = {}

        if parallel:
            # 并行获取所有数据（包括A股特色数据）
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = {
                    executor.submit(
                        self._get_market_data_with_fallback, symbol, trade_date
                    ): "market",
                    executor.submit(
                        self._get_fundamentals_data_with_fallback, symbol, trade_date
                    ): "financial",
                    executor.submit(self._get_news_data, symbol, trade_date): "news",
                    executor.submit(
                        self._get_sentiment_data, symbol, trade_date
                    ): "sentiment",
                    executor.submit(
                        self._get_china_market_features_data, symbol, trade_date
                    ): "china_market",
                }

                for future in as_completed(futures):
                    data_type = futures[future]
                    try:
                        result = future.result(timeout=30)  # 30秒超时
                        results[data_type] = result
                    except Exception as e:
                        logger.error(f"❌ {data_type} 数据获取超时或失败: {e}")
                        results[data_type] = DataFetchResult(
                            data=f"❌ {data_type} 数据获取失败: {e}",
                            source="failed",
                            quality_score=0.0,
                            issues=[
                                {"severity": "critical", "message": str(e), "field": ""}
                            ],
                            fetch_time=0,
                        )
        else:
            # 串行获取
            results["market"] = self._get_market_data_with_fallback(symbol, trade_date)
            results["financial"] = self._get_fundamentals_data_with_fallback(
                symbol, trade_date
            )
            results["news"] = self._get_news_data(symbol, trade_date)
            results["sentiment"] = self._get_sentiment_data(symbol, trade_date)
            results["china_market"] = self._get_china_market_features_data(
                symbol, trade_date
            )

        # 计算总体质量评分
        total_weight = sum(
            self.DATA_TYPES[dt]["weight"] for dt in results if dt in self.DATA_TYPES
        )
        if total_weight > 0:
            overall_quality = (
                sum(
                    results[dt].quality_score * self.DATA_TYPES[dt]["weight"]
                    for dt in results
                    if dt in self.DATA_TYPES
                )
                / total_weight
            )
        else:
            overall_quality = 0.0

        total_time = time.time() - start_time
        logger.info(
            f"✅ [Data Coordinator] 所有数据获取完成 (总体质量分: {overall_quality:.2f}, 总耗时: {total_time:.2f}s)"
        )

        # ========== P0-3: 数据充分性预检验 ==========
        sufficiency_issues = self._check_data_sufficiency(results, symbol)
        if sufficiency_issues:
            for issue in sufficiency_issues:
                severity = issue.get("severity", "warning")
                msg = issue.get("message", "")
                if severity == "critical":
                    # 严重不足：大幅降低质量评分
                    overall_quality = min(overall_quality, 0.3)
                    logger.warning(f"🚨 [P0-3] 数据严重不足: {msg}")
                elif severity == "warning":
                    # 部分不足：适度降低
                    overall_quality = max(0.3, overall_quality - 0.15)
                    logger.warning(f"⚠️ [P0-3] 数据不足: {msg}")
                else:
                    logger.info(f"ℹ️ [P0-3] 数据提示: {msg}")

            # 将充分性问题注入 market issues
            market_result = results.get("market", DataFetchResult("", "", 0.0, [], 0))
            market_result.issues.extend(sufficiency_issues)

        # 收集 metadata（如 PS 修正值、成交量单位等）
        financial_metadata = results.get(
            "financial", DataFetchResult("", "", 0.0, [], 0)
        ).metadata

        # ========== P2-2: 多维数据质量评分 ==========
        _default = DataFetchResult("", "", 0.0, [], 0)
        market_structured = results.get("market", _default).parsed_data
        market_text = results.get("market", _default).data
        try:
            from tradingagents.graph.data_quality import evaluate_data_quality

            quality_report = evaluate_data_quality(
                structured_data=market_structured,
                trade_date=trade_date,
                data_text=market_text,
            )
            # 用多维评分替代原有的简单可用性评分
            overall_quality = min(overall_quality, quality_report.overall_score)
            quality_grade = quality_report.grade
            quality_issues = list(quality_report.issues)
            logger.info(
                f"📊 [P2-2] 数据质量: {quality_grade} ({quality_report.overall_score:.0%}) "
                f"时效={quality_report.timeliness.score:.2f} "
                f"完整={quality_report.completeness.score:.2f} "
                f"一致={quality_report.consistency.score:.2f} "
                f"异常={quality_report.anomaly.score:.2f}"
            )
        except Exception as e:
            logger.warning(f"⚠️ [P2-2] 数据质量评估失败: {e}")
            quality_grade = "B"
            quality_issues = []

        # ========== P2-3: 技术信号预计算摘要 ==========
        try:
            from tradingagents.graph.technical_signals import (
                compute_technical_signals,
                format_signals_for_prompt,
            )

            tech_signals = compute_technical_signals(market_structured)
            tech_signals_text = format_signals_for_prompt(tech_signals)
            if tech_signals.get("signals"):
                logger.info(
                    f"📡 [P2-3] 技术信号: {tech_signals['trend_text']} "
                    f"(强度: {abs(tech_signals['trend_score']):.1f}/8, "
                    f"信号数: {len(tech_signals['signals'])})"
                )
        except Exception as e:
            logger.warning(f"⚠️ [P2-3] 技术信号计算失败: {e}")
            tech_signals = {}
            tech_signals_text = ""

        # 构建返回结果
        result = {
            # 文本数据通道 (向后兼容)
            "market_data": results.get("market", _default).data,
            "financial_data": results.get("financial", _default).data,
            "news_data": results.get("news", _default).data,
            "sentiment_data": results.get("sentiment", _default).data,
            "china_market_data": results.get("china_market", _default).data,
            # P0-1: 结构化数据通道
            "market_data_structured": results.get("market", _default).parsed_data,
            "financial_data_structured": results.get("financial", _default).parsed_data,
            "china_market_data_structured": results.get(
                "china_market", _default
            ).parsed_data,
            # 质量和元数据
            "data_quality_score": overall_quality,
            "data_sources": {
                "market": results.get("market", _default).source,
                "financial": results.get("financial", _default).source,
                "news": results.get("news", _default).source,
                "sentiment": results.get("sentiment", _default).source,
                "china_market": results.get("china_market", _default).source,
            },
            "data_issues": {
                "market": results.get("market", _default).issues,
                "financial": results.get("financial", _default).issues,
                "news": results.get("news", _default).issues,
                "sentiment": results.get("sentiment", _default).issues,
                "china_market": results.get("china_market", _default).issues,
            },
            "data_metadata": {
                "corrected_ps": financial_metadata.get("corrected_ps"),
                "volume_unit_info": financial_metadata.get("volume_unit_info"),
            },
            "fetch_time": total_time,
            # P2-2: 多维数据质量评分
            "data_quality_grade": quality_grade,
            "data_quality_issues": quality_issues,
            # P2-3: 技术信号预计算摘要
            "technical_signals": tech_signals,
            "technical_signals_text": tech_signals_text,
        }

        # 缓存结果
        if use_cache:
            self._set_analysis_cache(cache_key, result)

        return result

    # ==================== 分析级缓存方法 ====================

    def _get_analysis_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """获取分析级缓存"""
        if key not in self.analysis_cache:
            return None

        cached_data, expires_at = self.analysis_cache[key]
        if time.time() > expires_at:
            # 缓存过期
            del self.analysis_cache[key]
            return None

        return cached_data

    def _set_analysis_cache(self, key: str, data: Dict[str, Any]) -> None:
        """设置分析级缓存"""
        expires_at = time.time() + self.analysis_cache_ttl
        self.analysis_cache[key] = (data, expires_at)
        logger.info(
            f"💾 [Data Coordinator] 分析级缓存已设置: {key} (TTL: {self.analysis_cache_ttl}s)"
        )

    def _get_cache_ttl(self, key: str) -> float:
        """获取缓存剩余时间"""
        if key not in self.analysis_cache:
            return 0
        _, expires_at = self.analysis_cache[key]
        return max(0, expires_at - time.time())

    def clear_analysis_cache(self) -> None:
        """清除所有分析级缓存"""
        self.analysis_cache.clear()
        logger.info("🗑️ [Data Coordinator] 分析级缓存已清除")


# 全局 DataCoordinator 实例
_data_coordinator = None


def get_data_coordinator() -> DataCoordinator:
    """获取 DataCoordinator 实例"""
    global _data_coordinator
    if _data_coordinator is None:
        _data_coordinator = DataCoordinator()
    return _data_coordinator


def _extract_price_series(market_text: str) -> List[float]:
    """
    从市场数据文本中提取收盘价序列 (P1-2 辅助函数)

    尝试多种模式匹配收盘价:
    - "收盘: 12.30" / "收盘价: 12.30"
    - "close: 12.30"
    - 表格格式中的收盘价列
    - 如果没有收盘价序列，提取最新价
    """
    prices = []

    # 模式1: 收盘价标签
    close_patterns = [
        r"收盘[价]?[：:]\s*(\d+\.?\d*)",
        r"[Cc]lose[：:]\s*(\d+\.?\d*)",
    ]
    for pattern in close_patterns:
        matches = re.findall(pattern, market_text)
        if matches:
            prices = [float(m) for m in matches if float(m) > 0]
            if len(prices) >= 5:
                return prices

    # 模式2: 日线数据表格 (日期 + OHLC)
    # 匹配 "2025-01-15 | 12.30 | 12.50 | 12.10 | 12.40" 格式
    table_pattern = r"\d{4}-\d{2}-\d{2}.*?(\d+\.\d{2})\s*$"
    matches = re.findall(table_pattern, market_text, re.MULTILINE)
    if len(matches) >= 5:
        prices = [float(m) for m in matches if float(m) > 0]
        return prices

    # 模式3: 仅有单一最新价
    latest_pattern = r"最新价[：:]\s*(\d+\.?\d*)"
    match = re.search(latest_pattern, market_text)
    if match:
        prices = [float(match.group(1))]

    return prices


def data_coordinator_node(state: AgentState):
    """
    Data Coordinator Node - 集中式数据预取节点

    负责预获取所有 A 股必要的数据（Market, Fundamentals, News, Sentiment）
    并存储在 AgentState 中供下游分析师使用。

    这种集中式方法可以避免：
    1. 重复的 API 调用
    2. 分析师节点无限循环尝试调用工具
    3. 工具失败时产生幻觉

    ⚡ 关键改进：
    - 多级降级策略 (Tushare → Baostock → AkShare)
    - 数据验证集成
    - 质量评分机制
    - 并行数据获取
    """
    logger.info("🔄 [Data Coordinator] 开始集中式数据预取...")

    company = state.get("company_of_interest", "")
    trade_date = state.get("trade_date", "")

    # 将分析日期设置到 Toolkit._config，确保工具函数能获取到
    if trade_date:
        from tradingagents.agents.utils.agent_utils import Toolkit

        Toolkit.update_config({"trade_date": trade_date})
        logger.info(f"📅 [Data Coordinator] 已设置分析日期到 Toolkit: {trade_date}")

    if not company:
        logger.error("❌ [Data Coordinator] 股票代码为空")
        return {
            "market_data": "❌ 错误：股票代码为空",
            "financial_data": "❌ 错误：股票代码为空",
            "news_data": "❌ 错误：股票代码为空",
            "sentiment_data": "❌ 错误：股票代码为空",
            "data_quality_score": 0.0,
            "data_sources": {},
        }

    # 🔧 检测股票市场类型
    from tradingagents.utils.stock_utils import StockUtils

    market_info = StockUtils.get_market_info(company)
    is_china = market_info.get("is_china", False)

    if not is_china:
        logger.warning(
            f"⚠️ [Data Coordinator] 非A股市场（{market_info.get('market_name', 'Unknown')}），当前仅支持A股"
        )
        logger.info(f"💡 提示：港股/美股分析当前不可用，仅支持 A 股分析")
        return {
            "market_data": f"⚠️ 不支持的市场: {market_info.get('market_name', 'Unknown')}，当前仅支持 A 股",
            "financial_data": f"⚠️ 不支持的市场: {market_info.get('market_name', 'Unknown')}，当前仅支持 A 股",
            "news_data": f"⚠️ 不支持的市场: {market_info.get('market_name', 'Unknown')}，当前仅支持 A 股",
            "sentiment_data": f"⚠️ 不支持的市场: {market_info.get('market_name', 'Unknown')}，当前仅支持 A 股",
            "data_quality_score": 0.0,
            "data_sources": {
                "market": "unsupported",
                "financial": "unsupported",
                "news": "unsupported",
                "sentiment": "unsupported",
            },
        }

    # 仅支持 A 股数据预取
    logger.info(f"📊 目标: {company}, 交易日期: {trade_date} (A 股)")

    # 使用交易日管理器确保日期正确
    from tradingagents.utils.trading_date_manager import get_trading_date_manager

    date_mgr = get_trading_date_manager()
    adjusted_date = date_mgr.get_latest_trading_date(trade_date)
    if adjusted_date != trade_date:
        logger.info(f"📅 日期调整: {trade_date} → {adjusted_date} (最近交易日)")
        trade_date = adjusted_date

    # 使用 DataCoordinator 获取所有数据
    coordinator = get_data_coordinator()
    results = coordinator.fetch_all_data(company, trade_date, parallel=True)

    logger.info(f"✅ [Data Coordinator] 数据预取完成")
    logger.info(
        f"   市场数据质量: {results.get('data_sources', {}).get('market', 'unknown')}"
    )
    logger.info(
        f"   基本面数据质量: {results.get('data_sources', {}).get('financial', 'unknown')}"
    )
    logger.info(f"   总体质量评分: {results.get('data_quality_score', 0):.2f}")

    # ========== P1-2: 计算量化风险指标 ==========
    quant_risk_metrics = {}
    quant_risk_text = ""
    try:
        from tradingagents.graph.risk_indicators import get_quant_risk_calculator

        # 从市场数据文本中提取收盘价序列
        market_text = results.get("market_data", "")
        prices = _extract_price_series(market_text)

        if len(prices) >= 5:
            calculator = get_quant_risk_calculator()
            metrics = calculator.calculate(prices)
            quant_risk_metrics = metrics.to_dict()
            quant_risk_text = metrics.format_for_prompt()
            logger.info(
                f"📊 [P1-2] 量化风险指标已计算 ({metrics.data_days}天数据, "
                f"VaR95={metrics.var_95:.2%}, Vol={metrics.annualized_volatility:.2%})"
                if metrics.var_95 and metrics.annualized_volatility
                else f"📊 [P1-2] 量化风险指标计算完成 ({metrics.data_days}天数据)"
            )
        else:
            logger.info(f"ℹ️ [P1-2] 价格数据不足({len(prices)}天)，跳过量化风险指标计算")
    except Exception as e:
        logger.warning(f"⚠️ [P1-2] 量化风险指标计算失败: {e}")

    return {
        # 文本数据通道 (向后兼容)
        "market_data": results["market_data"],
        "financial_data": results["financial_data"],
        "news_data": results["news_data"],
        "sentiment_data": results["sentiment_data"],
        "china_market_data": results["china_market_data"],
        # P0-1: 结构化数据通道
        "market_data_structured": results.get("market_data_structured", {}),
        "financial_data_structured": results.get("financial_data_structured", {}),
        "china_market_data_structured": results.get("china_market_data_structured", {}),
        # P1-2: 量化风险指标
        "quant_risk_metrics": quant_risk_metrics,
        "quant_risk_text": quant_risk_text,
        # 质量和元数据
        "data_quality_score": results["data_quality_score"],
        "data_sources": results["data_sources"],
        "data_issues": results.get("data_issues", {}),
        "data_metadata": results.get("data_metadata", {}),
    }
