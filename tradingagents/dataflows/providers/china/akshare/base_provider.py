# -*- coding: utf-8 -*-
"""
AKShare基础提供器模块

包含AKShareProvider基类，提供初始化、连接和通用工具方法
"""

import logging
from typing import Dict, Any, Optional

import pandas as pd

from ...base_provider import BaseStockDataProvider
from .cache_manager import (
    AKSHARE_CACHE_LOCK,
    AKSHARE_QUOTES_CACHE,
)
from .basic_data import BasicDataMixin
from .realtime_data import RealtimeDataMixin
from .historical_data import HistoricalDataMixin
from .financial_data import FinancialDataMixin
from .news_data import NewsDataMixin

logger = logging.getLogger(__name__)


class AKShareProvider(
    BasicDataMixin,
    RealtimeDataMixin,
    HistoricalDataMixin,
    FinancialDataMixin,
    NewsDataMixin,
    BaseStockDataProvider,
):
    """
    AKShare统一数据提供器

    提供标准化的股票数据接口，支持：
    - 股票基础信息获取
    - 历史行情数据
    - 实时行情数据
    - 财务数据
    - 港股数据支持
    """

    def __init__(self):
        super().__init__("AKShare")
        self.ak = None
        self.connected = False
        self._stock_list_cache = None  # 缓存股票列表，避免重复获取
        self._cache_time = None  # 缓存时间

        # 检查 AKSHARE_UNIFIED_ENABLED 开关
        import os

        akshare_enabled_str = os.getenv("AKSHARE_UNIFIED_ENABLED", "true").lower()
        akshare_enabled = akshare_enabled_str in ("true", "1", "yes", "on")

        if not akshare_enabled:
            logger.info(
                "⏸️ [AKShare] AKSHARE_UNIFIED_ENABLED=false，跳过 AKShare 数据源初始化"
            )
            self.connected = False
            return

        self._initialize_akshare()

    def _initialize_akshare(self):
        """初始化AKShare连接"""
        try:
            import akshare as ak
            import requests
            import time

            # 尝试导入 curl_cffi，如果可用则使用它来绕过反爬虫
            curl_requests = None  # 初始化变量以通过静态分析
            try:
                from curl_cffi import requests as curl_requests

                use_curl_cffi = True
                logger.info("🔧 检测到 curl_cffi，将使用它来模拟真实浏览器 TLS 指纹")
            except ImportError:
                use_curl_cffi = False
                logger.warning(
                    "⚠️ curl_cffi 未安装，将使用标准 requests（可能被反爬虫拦截）"
                )
                logger.warning("   建议安装: pip install curl-cffi")

            # 修复AKShare的bug：设置requests的默认headers，并添加请求延迟
            # AKShare的stock_news_em()函数没有设置必要的headers，导致API返回空响应
            if not hasattr(requests, "_akshare_headers_patched"):
                original_get = requests.get
                last_request_time = {"time": 0.0}  # 使用浮点数初始化

                def patched_get(url, **kwargs):
                    """
                    包装requests.get方法，自动添加必要的headers和请求延迟
                    修复AKShare stock_news_em()函数缺少headers的问题
                    如果可用，使用 curl_cffi 模拟真实浏览器 TLS 指纹
                    """
                    # 添加请求延迟，避免被反爬虫封禁
                    # 只对东方财富网的请求添加延迟
                    if "eastmoney.com" in url:
                        current_time = time.time()
                        time_since_last_request = (
                            current_time - last_request_time["time"]
                        )
                        if time_since_last_request < 0.5:  # 至少间隔0.5秒
                            time.sleep(0.5 - time_since_last_request)
                        last_request_time["time"] = time.time()

                    # 如果是东方财富网的请求，且 curl_cffi 可用，使用它来绕过反爬虫
                    if use_curl_cffi and "eastmoney.com" in url:
                        try:
                            # 使用 curl_cffi 模拟 Chrome 120 的 TLS 指纹
                            # 注意：使用 impersonate 时，不要传递自定义 headers，让 curl_cffi 自动设置
                            curl_kwargs = {
                                "timeout": kwargs.get("timeout", 10),
                                "impersonate": "chrome120",  # 模拟 Chrome 120
                            }

                            # 只传递非 headers 的参数
                            if "params" in kwargs:
                                curl_kwargs["params"] = kwargs["params"]
                            # 不传递 headers，让 impersonate 自动设置
                            if "data" in kwargs:
                                curl_kwargs["data"] = kwargs["data"]
                            if "json" in kwargs:
                                curl_kwargs["json"] = kwargs["json"]

                            response = curl_requests.get(url, **curl_kwargs)
                            # curl_cffi 的响应对象已经兼容 requests.Response
                            return response
                        except Exception as e:
                            # curl_cffi 失败，回退到标准 requests
                            error_msg = str(e)
                            # 忽略 TLS 库错误和 400 错误的详细日志（这是 Docker 环境的已知问题）
                            if (
                                "invalid library" not in error_msg
                                and "400" not in error_msg
                            ):
                                logger.warning(
                                    f"⚠️ curl_cffi 请求失败，回退到标准 requests: {e}"
                                )

                    # 标准 requests 请求（非东方财富网，或 curl_cffi 不可用/失败）
                    # 设置浏览器请求头
                    if "headers" not in kwargs or kwargs["headers"] is None:
                        kwargs["headers"] = {
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                            "Accept-Encoding": "gzip, deflate, br",
                            "Referer": "https://www.eastmoney.com/",
                            "Connection": "keep-alive",
                        }
                    elif isinstance(kwargs["headers"], dict):
                        # 如果已有headers，确保包含必要的字段
                        if "User-Agent" not in kwargs["headers"]:
                            kwargs["headers"]["User-Agent"] = (
                                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                            )
                        if "Referer" not in kwargs["headers"]:
                            kwargs["headers"]["Referer"] = "https://www.eastmoney.com/"
                        if "Accept" not in kwargs["headers"]:
                            kwargs["headers"]["Accept"] = (
                                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
                            )
                        if "Accept-Language" not in kwargs["headers"]:
                            kwargs["headers"]["Accept-Language"] = (
                                "zh-CN,zh;q=0.9,en;q=0.8"
                            )

                    # 添加重试机制（最多3次）
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            return original_get(url, **kwargs)
                        except Exception as e:
                            # 检查是否是SSL错误或网络错误
                            error_str = str(e)
                            is_ssl_error = (
                                "SSL" in error_str
                                or "ssl" in error_str
                                or "UNEXPECTED_EOF_WHILE_READING" in error_str
                            )

                            # FIX: 添加对 RemoteDisconnected 和其他网络错误的检测
                            is_network_error = any(
                                x in error_str.lower()
                                for x in [
                                    "remote",
                                    "connection",
                                    "aborted",
                                    "reset",
                                    "closed",
                                    "without response",
                                    "timeout",
                                    "timed out",
                                    "refused",
                                ]
                            )

                            if (
                                is_ssl_error or is_network_error
                            ) and attempt < max_retries - 1:
                                # SSL错误或网络错误，使用指数退避等待后重试
                                wait_time = min(
                                    1.0 * (2**attempt), 10.0
                                )  # 指数退避，最大10秒
                                error_type = "SSL" if is_ssl_error else "网络"
                                logger.warning(
                                    f"⚠️ [{error_type}错误] {error_str[:100]}，等待 {wait_time:.1f} 秒后重试 "
                                    f"({attempt + 1}/{max_retries})"
                                )
                                time.sleep(wait_time)
                                continue
                            else:
                                # 非SSL/网络错误或已达到最大重试次数，直接抛出
                                raise

                # 应用patch
                requests.get = patched_get
                requests._akshare_headers_patched = True  # type: ignore

                if use_curl_cffi:
                    logger.info(
                        "🔧 已修复AKShare的headers问题，使用 curl_cffi 模拟真实浏览器（Chrome 120）"
                    )
                else:
                    logger.info(
                        "🔧 已修复AKShare的headers问题，并添加请求延迟（0.5秒）"
                    )

            self.ak = ak
            self.connected = True

            # 配置超时和重试
            self._configure_timeout()

            logger.info("✅ AKShare连接成功")
        except ImportError as e:
            logger.error(f"❌ AKShare未安装: {e}")
            self.connected = False
        except Exception as e:
            logger.error(f"❌ AKShare初始化失败: {e}")
            self.connected = False

    def _configure_timeout(self):
        """配置AKShare的超时设置"""
        try:
            import socket

            socket.setdefaulttimeout(60)  # 60秒超时
            logger.info("🔧 AKShare超时配置完成: 60秒")
        except Exception as e:
            logger.warning(f"⚠️ AKShare超时配置失败: {e}")

    async def connect(self) -> bool:
        """连接到AKShare数据源"""
        return await self.test_connection()

    async def test_connection(self) -> bool:
        """测试AKShare连接"""
        if not self.connected:
            return False

        # AKShare 是基于网络爬虫的库，不需要传统的"连接"测试
        # 只要库已经导入成功，就认为可用
        # 实际的网络请求会在具体调用时进行，并有各自的错误处理
        logger.info("✅ AKShare连接测试成功（库已加载）")
        return True

    def _safe_float(self, value: Any) -> float:
        """安全转换为浮点数"""
        try:
            if pd.isna(value) or value is None:
                return 0.0
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    def _safe_int(self, value: Any) -> int:
        """安全转换为整数"""
        try:
            if pd.isna(value) or value is None:
                return 0
            return int(float(value))
        except (ValueError, TypeError):
            return 0

    def _safe_str(self, value: Any) -> str:
        """安全转换为字符串"""
        try:
            if pd.isna(value) or value is None:
                return ""
            return str(value)
        except:
            return ""

    def _get_full_symbol(self, code: str) -> str:
        """
        获取完整股票代码

        Args:
            code: 6位股票代码

        Returns:
            完整标准化代码，如果无法识别则返回原始代码（确保不为空）

        Note:
            统一使用 .SH/.SZ/.BJ 格式（与 base_provider 保持一致）
        """
        # 确保 code 不为空
        if not code:
            return ""

        # 标准化为字符串
        code = str(code).strip()

        # 根据代码前缀判断交易所 - 统一使用 .SH/.SZ/.BJ 格式
        if code.startswith(("60", "68", "90")):  # 上海证券交易所（增加90开头的B股）
            return f"{code}.SH"
        elif code.startswith(("00", "30", "20")):  # 深圳证券交易所（增加20开头的B股）
            return f"{code}.SZ"
        elif code.startswith(("8", "4")):  # 北京证券交易所（增加4开头的新三板）
            return f"{code}.BJ"
        else:
            # 无法识别的代码，返回原始代码（确保不为空）
            return code if code else ""

    def _get_market_info(self, code: str) -> Dict[str, Any]:
        """获取市场信息"""
        if code.startswith(("60", "68")):
            return {
                "market_type": "CN",
                "exchange": "SSE",
                "exchange_name": "上海证券交易所",
                "currency": "CNY",
                "timezone": "Asia/Shanghai",
            }
        elif code.startswith(("00", "30")):
            return {
                "market_type": "CN",
                "exchange": "SZSE",
                "exchange_name": "深圳证券交易所",
                "currency": "CNY",
                "timezone": "Asia/Shanghai",
            }
        elif code.startswith("8"):
            return {
                "market_type": "CN",
                "exchange": "BSE",
                "exchange_name": "北京证券交易所",
                "currency": "CNY",
                "timezone": "Asia/Shanghai",
            }
        else:
            return {
                "market_type": "CN",
                "exchange": "UNKNOWN",
                "exchange_name": "未知交易所",
                "currency": "CNY",
                "timezone": "Asia/Shanghai",
            }

    def _determine_market(self, code: str) -> str:
        """根据股票代码判断市场（调用基类通用方法）"""
        return self._get_market_info(code).get("exchange_name", "未知市场")

    def get_akshare_cache_status(self) -> Dict[str, Any]:
        """获取AKShare行情缓存状态"""
        from .cache_manager import _clean_akshare_expired_cache

        _clean_akshare_expired_cache()
        return {
            "cached_count": len(AKSHARE_QUOTES_CACHE),
            "ttl_seconds": 15,
            "codes": list(AKSHARE_QUOTES_CACHE.keys())[:20],
        }

    def invalidate_akshare_cache(self, code: Optional[str] = None) -> None:
        """使AKShare缓存失效"""
        global AKSHARE_QUOTES_CACHE
        with AKSHARE_CACHE_LOCK:
            if code:
                if code in AKSHARE_QUOTES_CACHE:
                    del AKSHARE_QUOTES_CACHE[code]
            else:
                AKSHARE_QUOTES_CACHE.clear()
