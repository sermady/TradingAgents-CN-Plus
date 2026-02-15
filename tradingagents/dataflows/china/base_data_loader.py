# -*- coding: utf-8 -*-
"""
基础数据加载器基类
提供数据加载的通用功能和接口定义
"""

import os
import time
import random
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from zoneinfo import ZoneInfo

from tradingagents.config.config_manager import config_manager
from tradingagents.config.runtime_settings import get_float, get_timezone_name
from tradingagents.dataflows.cache import get_cache
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("agents")


class DataSourceError(Exception):
    """数据源错误异常"""
    pass


class BaseDataLoader(ABC):
    """
    基础数据加载器基类

    提供以下通用功能：
    - API速率限制控制
    - 缓存管理
    - 错误处理和重试机制
    - 配置管理
    """

    def __init__(self):
        self.cache = get_cache()
        self.config = config_manager.load_settings()
        self.last_api_call = 0
        self.min_api_interval = get_float(
            "TA_CHINA_MIN_API_INTERVAL_SECONDS",
            "ta_china_min_api_interval_seconds",
            0.5,
        )
        self.max_retries = 3
        self.retry_delay = 1.0

    def _wait_for_rate_limit(self):
        """等待API限制"""
        current_time = time.time()
        time_since_last_call = current_time - self.last_api_call

        if time_since_last_call < self.min_api_interval:
            wait_time = self.min_api_interval - time_since_last_call
            time.sleep(wait_time)

        self.last_api_call = time.time()

    def _retry_with_backoff(self, func, *args, **kwargs):
        """
        带退避的重试机制

        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            函数执行结果

        Raises:
            DataSourceError: 重试次数用尽后仍失败
        """
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise DataSourceError(f"重试{self.max_retries}次后仍失败: {e}")

                delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"第{attempt + 1}次尝试失败，{delay:.1f}秒后重试: {e}")
                time.sleep(delay)

    def _check_skip_cache(self) -> bool:
        """
        检查是否跳过缓存

        Returns:
            是否跳过缓存
        """
        return os.getenv("SKIP_MONGODB_CACHE_ON_QUERY", "true").lower() == "true"

    def _get_current_time(self) -> str:
        """
        获取当前时间字符串

        Returns:
            格式化的时间字符串
        """
        tz = ZoneInfo(get_timezone_name())
        return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    def _get_analysis_date(self) -> str:
        """
        从Toolkit获取分析日期

        Returns:
            分析日期字符串或空字符串
        """
        try:
            from tradingagents.agents.utils.agent_utils import Toolkit
            date_val = Toolkit._config.get("analysis_date")
            if date_val and isinstance(date_val, str):
                return date_val
        except Exception as e:
            logger.debug(f"无法从Toolkit._config获取analysis_date: {e}")
        return ""

    def _try_get_old_cache(self, symbol: str, data_type: str = "stock_data") -> Optional[str]:
        """
        尝试获取过期的缓存数据作为备用

        Args:
            symbol: 股票代码
            data_type: 数据类型

        Returns:
            缓存数据或None
        """
        try:
            import json
            for metadata_file in self.cache.metadata_dir.glob(f"*_meta.json"):
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)

                    if (
                        metadata.get("symbol") == symbol
                        and metadata.get("data_type") == data_type
                        and metadata.get("market_type") == "china"
                    ):
                        cache_key = metadata_file.stem.replace("_meta", "")
                        cached_data = self.cache.load_stock_data(cache_key)
                        if cached_data:
                            return cached_data + "\n\n⚠️ 注意: 使用的是过期缓存数据"
                except Exception:
                    continue
        except Exception:
            pass
        return None

    def _generate_fallback_data(
        self, symbol: str, start_date: str, end_date: str, error_msg: str
    ) -> str:
        """
        生成备用数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            error_msg: 错误信息

        Returns:
            格式化的备用数据字符串
        """
        return f"""# {symbol} A股数据获取失败

## ❌ 错误信息
{error_msg}

## 📊 模拟数据（仅供演示）
- 股票代码: {symbol}
- 股票名称: 模拟公司
- 数据期间: {start_date} 至 {end_date}
- 模拟价格: ¥{random.uniform(10, 50):.2f}
- 模拟涨跌: {random.uniform(-5, 5):+.2f}%

## ⚠️ 重要提示
由于数据接口限制或网络问题，无法获取实时数据。
建议稍后重试或检查网络连接。

生成时间: {self._get_current_time()}
"""

    def _generate_fallback_fundamentals(self, symbol: str, error_msg: str) -> str:
        """
        生成备用基本面数据

        Args:
            symbol: 股票代码
            error_msg: 错误信息

        Returns:
            格式化的备用基本面数据字符串
        """
        return f"""# {symbol} A股基本面分析失败

## ❌ 错误信息
{error_msg}

## 📊 基本信息
- 股票代码: {symbol}
- 分析状态: 数据获取失败
- 建议: 稍后重试或检查网络连接

生成时间: {self._get_current_time()}
"""

    @abstractmethod
    def load(self, symbol: str, **kwargs) -> Any:
        """
        加载数据的抽象方法

        Args:
            symbol: 股票代码
            **kwargs: 其他参数

        Returns:
            加载的数据
        """
        pass

    def normalize_volume(self, volume: Any, volume_unit: str = "lots") -> str:
        """
        标准化成交量单位

        Args:
            volume: 成交量数值
            volume_unit: 单位 (lots=手, shares=股)

        Returns:
            格式化后的成交量字符串
        """
        if volume is None:
            return "N/A"

        try:
            volume_value = float(volume)
            # 如果数据源错误地返回了"股"（数值过大），则转换为"手"
            if volume_value > 1000000 and volume_unit != "shares":
                volume_value = volume_value / 100

            return f"{int(volume_value):,}手"
        except (ValueError, TypeError):
            return str(volume) + "手"
