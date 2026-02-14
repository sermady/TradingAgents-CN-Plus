# -*- coding: utf-8 -*-
"""
可重试的数据源适配器基类

提取通用的重试逻辑、错误处理和网络配置，消除多个数据源适配器的重复代码。
"""

import logging
import os
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

from .base import DataSourceAdapter

logger = logging.getLogger(__name__)

# 默认重试配置
DEFAULT_RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 1.0,
    "max_delay": 10.0,
    "backoff_multiplier": 2.0,
    "jitter": 0.3,
}

F = TypeVar("F", bound=Callable[..., Any])


def get_proxy_status() -> Dict[str, str]:
    """获取当前代理配置状态"""
    return {
        "http_proxy": os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy") or "",
        "https_proxy": os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") or "",
        "no_proxy": os.environ.get("NO_PROXY") or os.environ.get("no_proxy") or "",
    }


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 10.0,
    backoff_multiplier: float = 2.0,
    jitter: float = 0.3,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    on_failure: Optional[Callable[[Exception], None]] = None,
):
    """
    装饰器：为数据源请求添加指数退避重试机制

    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        backoff_multiplier: 退避乘数
        jitter: 抖动比例（0-1）
        on_retry: 重试时的回调函数 (attempt, exception, delay)
        on_failure: 失败时的回调函数 (exception)

    Returns:
        装饰后的函数
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    delay = min(initial_delay * (backoff_multiplier**attempt), max_delay)

                    if attempt < max_retries - 1:
                        delay += (time.time() % jitter) * delay

                        if on_retry:
                            on_retry(attempt + 1, e, delay)
                        else:
                            logger.warning(
                                f"[{func.__name__}] 请求失败，{delay:.1f}秒后重试 "
                                f"({attempt + 1}/{max_retries}): {type(e).__name__}: {str(e)[:100]}"
                            )

                        time.sleep(delay)

            # 所有重试失败
            if on_failure:
                on_failure(last_exception)
            else:
                proxy_status = get_proxy_status()
                proxy_enabled = any(v for v in proxy_status.values())
                logger.error(
                    f"[{func.__name__}] 请求失败，已达最大重试次数 ({max_retries}): "
                    f"error_type={type(last_exception).__name__}, "
                    f"proxy_enabled={proxy_enabled}, "
                    f"error={str(last_exception)[:200]}"
                )

            return None

        return wrapper  # type: ignore

    return decorator


class RetryableDataSourceAdapter(DataSourceAdapter):
    """
    可重试的数据源适配器基类

    特性：
    1. 内置指数退避重试机制
    2. 统一的错误处理模式
    3. 网络代理配置检测
    4. 可配置的重试策略

    子类可以：
    - 覆盖 retry_config 自定义重试配置
    - 使用 @retry_with_backoff 装饰器包装特定方法
    - 调用 _get_retry_decorator() 获取默认重试装饰器
    """

    # 重试配置，子类可以覆盖
    retry_config: Dict[str, Any] = DEFAULT_RETRY_CONFIG.copy()

    def __init__(self):
        super().__init__()
        self._retry_decorator: Optional[Callable] = None

    def _get_retry_decorator(self, **override_config) -> Callable:
        """
        获取配置好的重试装饰器

        Args:
            **override_config: 覆盖默认配置的参数

        Returns:
            配置好的 retry_with_backoff 装饰器
        """
        config = {**self.retry_config, **override_config}

        def on_retry(attempt: int, exception: Exception, delay: float):
            logger.warning(
                f"[{self.name}] {attempt}/{config['max_retries']} 请求失败，"
                f"{delay:.1f}秒后重试: {type(exception).__name__}: {str(exception)[:100]}"
            )

        def on_failure(exception: Exception):
            proxy_status = get_proxy_status()
            proxy_enabled = any(v for v in proxy_status.values())
            logger.error(
                f"[{self.name}] 请求失败，已达最大重试次数: "
                f"error_type={type(exception).__name__}, "
                f"proxy_enabled={proxy_enabled}, "
                f"error={str(exception)[:200]}"
            )

        return retry_with_backoff(
            max_retries=config["max_retries"],
            initial_delay=config["initial_delay"],
            max_delay=config["max_delay"],
            backoff_multiplier=config["backoff_multiplier"],
            jitter=config["jitter"],
            on_retry=on_retry,
            on_failure=on_failure,
        )

    def _safe_execute(
        self,
        operation: Callable[..., Any],
        *args,
        default_return: Any = None,
        error_message: str = "",
        **kwargs,
    ) -> Any:
        """
        安全执行操作，统一错误处理

        Args:
            operation: 要执行的操作函数
            *args: 位置参数
            default_return: 失败时的默认返回值
            error_message: 错误日志消息前缀
            **kwargs: 关键字参数

        Returns:
            操作结果或默认值
        """
        try:
            return operation(*args, **kwargs)
        except Exception as e:
            msg = f"[{self.name}] {error_message}: {e}" if error_message else f"[{self.name}] 操作失败: {e}"
            logger.error(msg)
            return default_return

    def _is_network_error(self, error: Exception) -> bool:
        """
        判断是否为网络相关错误

        Args:
            error: 异常对象

        Returns:
            是否为网络错误
        """
        from .constants import NETWORK_ERROR_KEYWORDS

        error_str = str(error).lower()
        return any(keyword in error_str for keyword in NETWORK_ERROR_KEYWORDS)

    def _log_proxy_status(self):
        """记录当前代理配置状态（用于调试网络问题）"""
        status = get_proxy_status()
        proxy_enabled = any(v for v in status.values())
        if proxy_enabled:
            logger.debug(f"[{self.name}] 代理配置: http={status['http_proxy'][:20]}..., https={status['https_proxy'][:20]}...")
        else:
            logger.debug(f"[{self.name}] 未配置代理")


# 为了保持向后兼容，提供AKShare特定的配置
AKSHARE_RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 1.0,
    "max_delay": 10.0,
    "backoff_multiplier": 2.0,
    "jitter": 0.3,
}

# Tushare特定的配置
TUSHARE_RETRY_CONFIG = {
    "max_retries": 3,
    "initial_delay": 0.5,
    "max_delay": 5.0,
    "backoff_multiplier": 2.0,
    "jitter": 0.2,
}

# BaoStock特定的配置
BAOSTOCK_RETRY_CONFIG = {
    "max_retries": 2,
    "initial_delay": 1.0,
    "max_delay": 5.0,
    "backoff_multiplier": 1.5,
    "jitter": 0.3,
}
