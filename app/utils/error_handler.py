# -*- coding: utf-8 -*-
"""通用错误处理装饰器和工具

该模块提供了统一的错误处理装饰器，用于替代项目中重复的错误处理模式。
支持同步和异步函数，提供灵活的日志记录和异常处理选项。

典型用法:
    # 返回 None 的错误处理
    @handle_errors_none
    def fetch_data():
        return api.get_data()

    # 返回空列表的错误处理
    @handle_errors_empty_list
    def get_items():
        return database.query_items()

    # 自定义配置
    @handle_errors(
        default_return={},
        log_level="warning",
        error_message="获取用户信息失败",
        re_raise=True
    )
    def get_user_info(user_id: str) -> dict:
        return user_service.get(user_id)
"""

import functools
import logging
import traceback
from typing import Callable, Any, Optional, TypeVar, Tuple, Union, Awaitable

logger = logging.getLogger(__name__)

T = TypeVar('T')

# 日志级别映射
_LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def handle_errors(
    default_return: T = None,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """通用错误处理装饰器（同步函数版本）

    捕获指定类型的异常，记录日志，并返回默认值或重新抛出异常。
    用于替代项目中重复 try-except 模式。

    Args:
        default_return: 发生异常时返回的默认值。默认为 None。
        log_level: 日志级别，可选值为 "debug", "info", "warning", "error", "critical"。
            默认为 "error"。
        error_message: 自定义错误消息。如果为 None，则使用函数名作为错误消息。
            默认为 None。
        re_raise: 是否在记录日志后重新抛出异常。如果为 True，则 default_return
            不会生效。默认为 False。
        exception_types: 要捕获的异常类型元组。默认为 (Exception,)，即捕获所有异常。
        include_traceback: 是否在日志中包含完整的异常堆栈跟踪。默认为 True。

    Returns:
        装饰器函数，用于包装目标函数。

    Raises:
        如果 re_raise 为 True，则会重新抛出捕获的异常。

    Example:
        >>> @handle_errors(default_return=[], log_level="warning")
        ... def get_user_list():
        ...     return database.query_users()
        ...
        >>> @handle_errors(re_raise=True, error_message="数据库连接失败")
        ... def connect_database():
        ...     return create_connection()
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            except exception_types as e:
                # 构建错误消息
                func_name = func.__name__
                msg = error_message or f"函数 {func_name} 执行失败"

                # 获取日志级别
                level = _LOG_LEVEL_MAP.get(log_level.lower(), logging.ERROR)

                # 构建日志内容
                if include_traceback:
                    exc_info = traceback.format_exc()
                    log_msg = f"{msg}: {str(e)}\n{exc_info}"
                else:
                    log_msg = f"{msg}: {str(e)}"

                # 记录日志
                logger.log(level, log_msg)

                # 重新抛出异常或返回默认值
                if re_raise:
                    raise
                return default_return

        return wrapper

    return decorator


def async_handle_errors(
    default_return: T = None,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """通用错误处理装饰器（异步函数版本）

    捕获指定类型的异常，记录日志，并返回默认值或重新抛出异常。
    专用于异步函数，功能与 handle_errors 相同。

    Args:
        default_return: 发生异常时返回的默认值。默认为 None。
        log_level: 日志级别，可选值为 "debug", "info", "warning", "error", "critical"。
            默认为 "error"。
        error_message: 自定义错误消息。如果为 None，则使用函数名作为错误消息。
            默认为 None。
        re_raise: 是否在记录日志后重新抛出异常。如果为 True，则 default_return
            不会生效。默认为 False。
        exception_types: 要捕获的异常类型元组。默认为 (Exception,)，即捕获所有异常。
        include_traceback: 是否在日志中包含完整的异常堆栈跟踪。默认为 True。

    Returns:
        装饰器函数，用于包装目标异步函数。

    Raises:
        如果 re_raise 为 True，则会重新抛出捕获的异常。

    Example:
        >>> @async_handle_errors(default_return=None, log_level="info")
        ... async def fetch_api_data():
        ...     return await api_client.get_data()
        ...
        >>> @async_handle_errors(re_raise=True)
        ... async def critical_operation():
        ...     return await perform_critical_task()
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return await func(*args, **kwargs)
            except exception_types as e:
                # 构建错误消息
                func_name = func.__name__
                msg = error_message or f"异步函数 {func_name} 执行失败"

                # 获取日志级别
                level = _LOG_LEVEL_MAP.get(log_level.lower(), logging.ERROR)

                # 构建日志内容
                if include_traceback:
                    exc_info = traceback.format_exc()
                    log_msg = f"{msg}: {str(e)}\n{exc_info}"
                else:
                    log_msg = f"{msg}: {str(e)}"

                # 记录日志
                logger.log(level, log_msg)

                # 重新抛出异常或返回默认值
                if re_raise:
                    raise
                return default_return

        return async_wrapper

    return decorator


# =============================================================================
# 便捷装饰器 - 同步版本
# =============================================================================


def handle_errors_none(
    func: Callable[..., Optional[T]] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """便捷装饰器：出错时返回 None

    Example:
        >>> @handle_errors_none
        ... def find_user(user_id: str) -> Optional[User]:
        ...     return database.get_user(user_id)
    """
    decorator = handle_errors(
        default_return=None,
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


def handle_errors_empty_list(
    func: Callable[..., list] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """便捷装饰器：出错时返回空列表

    Example:
        >>> @handle_errors_empty_list
        ... def get_active_orders() -> List[Order]:
        ...     return order_service.get_active()
    """
    decorator = handle_errors(
        default_return=[],
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


def handle_errors_empty_dict(
    func: Callable[..., dict] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """便捷装饰器：出错时返回空字典

    Example:
        >>> @handle_errors_empty_dict
        ... def load_config() -> Dict[str, Any]:
        ...     return config_loader.load()
    """
    decorator = handle_errors(
        default_return={},
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


def handle_errors_false(
    func: Callable[..., bool] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """便捷装饰器：出错时返回 False

    Example:
        >>> @handle_errors_false
        ... def validate_token(token: str) -> bool:
        ...     return auth_service.validate(token)
    """
    decorator = handle_errors(
        default_return=False,
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


def handle_errors_zero(
    func: Callable[..., int] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """便捷装饰器：出错时返回 0

    Example:
        >>> @handle_errors_zero
        ... def count_active_users() -> int:
        ...     return user_service.count_active()
    """
    decorator = handle_errors(
        default_return=0,
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


def handle_errors_empty_string(
    func: Callable[..., str] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """便捷装饰器：出错时返回空字符串

    Example:
        >>> @handle_errors_empty_string
        ... def get_user_name(user_id: str) -> str:
        ...     return user_service.get_name(user_id)
    """
    decorator = handle_errors(
        default_return="",
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


# =============================================================================
# 便捷装饰器 - 异步版本
# =============================================================================


def async_handle_errors_none(
    func: Callable[..., Awaitable[Optional[T]]] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """异步便捷装饰器：出错时返回 None

    Example:
        >>> @async_handle_errors_none
        ... async def fetch_user(user_id: str) -> Optional[User]:
        ...     return await api.get_user(user_id)
    """
    decorator = async_handle_errors(
        default_return=None,
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


def async_handle_errors_empty_list(
    func: Callable[..., Awaitable[list]] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """异步便捷装饰器：出错时返回空列表

    Example:
        >>> @async_handle_errors_empty_list
        ... async def fetch_orders() -> List[Order]:
        ...     return await api.get_orders()
    """
    decorator = async_handle_errors(
        default_return=[],
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


def async_handle_errors_empty_dict(
    func: Callable[..., Awaitable[dict]] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """异步便捷装饰器：出错时返回空字典

    Example:
        >>> @async_handle_errors_empty_dict
        ... async def fetch_settings() -> Dict[str, Any]:
        ...     return await api.get_settings()
    """
    decorator = async_handle_errors(
        default_return={},
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


def async_handle_errors_false(
    func: Callable[..., Awaitable[bool]] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """异步便捷装饰器：出错时返回 False

    Example:
        >>> @async_handle_errors_false
        ... async def check_connection() -> bool:
        ...     return await ping_service.check()
    """
    decorator = async_handle_errors(
        default_return=False,
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


def async_handle_errors_zero(
    func: Callable[..., Awaitable[int]] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """异步便捷装饰器：出错时返回 0

    Example:
        >>> @async_handle_errors_zero
        ... async def get_pending_count() -> int:
        ...     return await queue.count_pending()
    """
    decorator = async_handle_errors(
        default_return=0,
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


def async_handle_errors_empty_string(
    func: Callable[..., Awaitable[str]] = None,
    *,
    log_level: str = "error",
    error_message: Optional[str] = None,
    re_raise: bool = False,
    exception_types: Tuple[type, ...] = (Exception,),
    include_traceback: bool = True,
) -> Callable:
    """异步便捷装饰器：出错时返回空字符串

    Example:
        >>> @async_handle_errors_empty_string
        ... async def fetch_status() -> str:
        ...     return await service.get_status()
    """
    decorator = async_handle_errors(
        default_return="",
        log_level=log_level,
        error_message=error_message,
        re_raise=re_raise,
        exception_types=exception_types,
        include_traceback=include_traceback,
    )
    if func is not None:
        return decorator(func)
    return decorator


# =============================================================================
# 错误信息格式化工具
# =============================================================================

class ErrorFormatter:
    """错误信息格式化工具

    提供静态方法用于格式化异常和 API 错误信息，生成用户友好的错误描述。
    """

    @staticmethod
    def format_exception(e: Exception, context: Optional[str] = None) -> str:
        """格式化异常为可读字符串

        将异常对象转换为包含异常类型、消息和可选上下文的格式化字符串。

        Args:
            e: 异常对象
            context: 可选的上下文信息，描述发生异常的场景

        Returns:
            格式化后的错误信息字符串

        Example:
            >>> try:
            ...     risky_operation()
            ... except Exception as e:
            ...     msg = ErrorFormatter.format_exception(e, "执行数据库查询")
            ...     logger.error(msg)
        """
        exc_type = type(e).__name__
        exc_msg = str(e)

        if context:
            return f"[{context}] {exc_type}: {exc_msg}"
        return f"{exc_type}: {exc_msg}"

    @staticmethod
    def format_api_error(provider: str, status_code: int, message: str) -> str:
        """格式化 API 错误

        为 API 调用错误生成标准化的错误信息，包含服务提供商、状态码和错误消息。

        Args:
            provider: API 服务提供商名称（如 "OpenAI", "Tushare" 等）
            status_code: HTTP 状态码或错误码
            message: 错误消息

        Returns:
            格式化后的 API 错误信息字符串

        Example:
            >>> error_msg = ErrorFormatter.format_api_error(
            ...     "OpenAI", 429, "Rate limit exceeded"
            ... )
            >>> print(error_msg)
            API Error [OpenAI] Status 429: Rate limit exceeded
        """
        return f"API Error [{provider}] Status {status_code}: {message}"

    @staticmethod
    def format_validation_error(field: str, value: Any, reason: str) -> str:
        """格式化数据验证错误

        Args:
            field: 验证失败的字段名
            value: 字段的值
            reason: 验证失败的原因

        Returns:
            格式化后的验证错误信息

        Example:
            >>> msg = ErrorFormatter.format_validation_error(
            ...     "age", -5, "必须为正整数"
            ... )
            >>> print(msg)
            Validation Error: Field 'age' with value '-5' - 必须为正整数
        """
        return f"Validation Error: Field '{field}' with value '{value}' - {reason}"

    @staticmethod
    def format_timeout_error(operation: str, timeout: float) -> str:
        """格式化超时错误

        Args:
            operation: 超时的操作描述
            timeout: 超时时间（秒）

        Returns:
            格式化后的超时错误信息

        Example:
            >>> msg = ErrorFormatter.format_timeout_error("获取股票数据", 30.0)
            >>> print(msg)
            Timeout Error: 获取股票数据 操作超时 (限制: 30.0s)
        """
        return f"Timeout Error: {operation} 操作超时 (限制: {timeout}s)"


# =============================================================================
# 安全执行函数
# =============================================================================

def safe_execute(
    func: Callable[..., T],
    *args: Any,
    default_return: Optional[T] = None,
    error_message: Optional[str] = None,
    **kwargs: Any,
) -> T:
    """安全执行函数，出错返回默认值

    执行目标函数，如果发生异常则记录日志并返回默认值。
    适用于不需要装饰器语法的场景。

    Args:
        func: 要执行的函数
        *args: 传递给函数的位置参数
        default_return: 发生异常时返回的默认值。默认为 None。
        error_message: 自定义错误消息。默认为 None。
        **kwargs: 传递给函数的关键字参数

    Returns:
        函数执行结果，或发生异常时的默认值

    Example:
        >>> result = safe_execute(
        ...     risky_operation,
        ...     "arg1", "arg2",
        ...     default_return={},
        ...     error_message="操作执行失败"
        ... )
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        func_name = func.__name__ if hasattr(func, "__name__") else str(func)
        msg = error_message or f"执行 {func_name} 失败"
        logger.error(f"{msg}: {e}")
        return default_return


async def safe_execute_async(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    default_return: Optional[T] = None,
    error_message: Optional[str] = None,
    **kwargs: Any,
) -> T:
    """异步安全执行函数

    异步执行目标函数，如果发生异常则记录日志并返回默认值。
    适用于不需要装饰器语法的异步场景。

    Args:
        func: 要执行的异步函数
        *args: 传递给函数的位置参数
        default_return: 发生异常时返回的默认值。默认为 None。
        error_message: 自定义错误消息。默认为 None。
        **kwargs: 传递给函数的关键字参数

    Returns:
        函数执行结果，或发生异常时的默认值

    Example:
        >>> result = await safe_execute_async(
        ...     async_api_call,
        ...     param1, param2,
        ...     default_return=[],
        ...     error_message="API 调用失败"
        ... )
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        func_name = func.__name__ if hasattr(func, "__name__") else str(func)
        msg = error_message or f"异步执行 {func_name} 失败"
        logger.error(f"{msg}: {e}")
        return default_return


# =============================================================================
# 上下文管理器（可选）
# =============================================================================

class ErrorContext:
    """错误处理上下文管理器

    提供 with 语句形式的错误处理，适用于代码块级别的错误处理。

    Attributes:
        default_return: 发生异常时返回的默认值
        error_message: 自定义错误消息
        suppress: 是否抑制异常（不向上抛出）
        caught_exception: 捕获到的异常对象（如果有）

    Example:
        >>> with ErrorContext(default_return=[], error_message="数据处理失败"):
        ...     result = process_data()
        ...     # 如果发生异常，result 会是 []
    """

    def __init__(
        self,
        default_return: Any = None,
        error_message: Optional[str] = None,
        suppress: bool = True,
        log_level: str = "error",
    ):
        self.default_return = default_return
        self.error_message = error_message or "代码块执行失败"
        self.suppress = suppress
        self.log_level = log_level
        self.caught_exception: Optional[Exception] = None

    def __enter__(self) -> "ErrorContext":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_val is not None:
            self.caught_exception = exc_val
            level = _LOG_LEVEL_MAP.get(self.log_level.lower(), logging.ERROR)
            logger.log(level, f"{self.error_message}: {exc_val}")
            return self.suppress  # 如果 suppress 为 True，抑制异常
        return False


# =============================================================================
# 模块导出
# =============================================================================

__all__ = [
    # 核心装饰器
    "handle_errors",
    "async_handle_errors",
    # 同步便捷装饰器
    "handle_errors_none",
    "handle_errors_empty_list",
    "handle_errors_empty_dict",
    "handle_errors_false",
    "handle_errors_zero",
    "handle_errors_empty_string",
    # 异步便捷装饰器
    "async_handle_errors_none",
    "async_handle_errors_empty_list",
    "async_handle_errors_empty_dict",
    "async_handle_errors_false",
    "async_handle_errors_zero",
    "async_handle_errors_empty_string",
    # 格式化工具
    "ErrorFormatter",
    # 安全执行函数
    "safe_execute",
    "safe_execute_async",
    # 上下文管理器
    "ErrorContext",
]
