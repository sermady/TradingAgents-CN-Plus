# -*- coding: utf-8 -*-
"""
LLM调用统一装饰器
提供统一的LLM调用接口,包含自动重试、Token统计、错误处理等功能
"""

import time
import functools
import hashlib
from typing import Optional, Callable, Any, Dict
from datetime import datetime

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("default")


class LLMCallConfig:
    """LLM调用配置"""

    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 2.0,
        validate_response: bool = True,
        min_response_length: int = 10,
        log_tokens: bool = True,
        log_performance: bool = True,
        cache_enabled: bool = True,
        cache_ttl: int = 3600,
    ):
        """
        初始化LLM调用配置

        Args:
            max_retries: 最大重试次数
            retry_delay: 重试延迟(秒)
            validate_response: 是否验证响应
            min_response_length: 最小响应长度
            log_tokens: 是否记录Token使用
            log_performance: 是否记录性能
            cache_enabled: 是否启用缓存
            cache_ttl: 缓存有效期(秒)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.validate_response = validate_response
        self.min_response_length = min_response_length
        self.log_tokens = log_tokens
        self.log_performance = log_performance
        self.cache_enabled = cache_enabled
        self.cache_ttl = cache_ttl


class LLMCallResult:
    """LLM调用结果"""

    def __init__(
        self,
        success: bool,
        content: str = "",
        error: Optional[str] = None,
        retry_count: int = 0,
        duration: float = 0.0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cached: bool = False,
    ):
        """
        初始化LLM调用结果

        Args:
            success: 是否成功
            content: 响应内容
            error: 错误信息
            retry_count: 重试次数
            duration: 耗时(秒)
            input_tokens: 输入Token数
            output_tokens: 输出Token数
            cached: 是否来自缓存
        """
        self.success = success
        self.content = content
        self.error = error
        self.retry_count = retry_count
        self.duration = duration
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cached = cached


# LLM响应缓存(简单实现)
_llm_response_cache: Dict[str, tuple] = {}


def _get_cache_key(prompt: str, llm_model: str, **kwargs) -> str:
    """
    生成缓存键

    Args:
        prompt: 提示词
        llm_model: LLM模型名称
        **kwargs: 其他参数

    Returns:
        缓存键
    """
    key_string = f"{llm_model}:{prompt}:{str(sorted(kwargs.items()))}"
    return hashlib.md5(key_string.encode("utf-8")).hexdigest()


def _get_from_cache(cache_key: str, config: LLMCallConfig) -> Optional[LLMCallResult]:
    """
    从缓存获取结果

    Args:
        cache_key: 缓存键
        config: LLM调用配置

    Returns:
        缓存结果,如果不存在或过期则返回None
    """
    global _llm_response_cache

    if not config.cache_enabled:
        return None

    if cache_key in _llm_response_cache:
        content, timestamp = _llm_response_cache[cache_key]
        age = time.time() - timestamp

        if age < config.cache_ttl:
            logger.debug(
                f"📦 [LLM缓存] 命中缓存 (TTL剩余: {config.cache_ttl - age:.1f}秒)"
            )
            return LLMCallResult(
                success=True,
                content=content,
                cached=True,
            )
        else:
            # 缓存过期,删除
            del _llm_response_cache[cache_key]
            logger.debug(f"📦 [LLM缓存] 缓存过期 (已过期{age:.1f}秒)")

    return None


def _save_to_cache(cache_key: str, content: str, config: LLMCallConfig):
    """
    保存结果到缓存

    Args:
        cache_key: 缓存键
        content: 响应内容
        config: LLM调用配置
    """
    global _llm_response_cache

    if not config.cache_enabled:
        return

    _llm_response_cache[cache_key] = (content, time.time())
    logger.debug(f"📦 [LLM缓存] 缓存结果 (TTL: {config.cache_ttl}秒)")


def llm_call(
    max_retries: int = 3,
    retry_delay: float = 2.0,
    validate_response: bool = True,
    min_response_length: int = 10,
    log_tokens: bool = True,
    log_performance: bool = True,
    cache_enabled: bool = True,
    cache_ttl: int = 3600,
    llm_name: str = "LLM",
    agent_name: str = "Agent",
):
    """
    LLM调用装饰器

    提供统一的LLM调用接口,包含:
    - 自动重试机制
    - Token统计
    - 错误处理和日志记录
    - 响应验证
    - 性能计时
    - 响应缓存

    Args:
        max_retries: 最大重试次数
        retry_delay: 重试延迟(秒)
        validate_response: 是否验证响应
        min_response_length: 最小响应长度
        log_tokens: 是否记录Token使用
        log_performance: 是否记录性能
        cache_enabled: 是否启用缓存
        cache_ttl: 缓存有效期(秒)
        llm_name: LLM名称(用于日志)
        agent_name: Agent名称(用于日志)

    Returns:
        装饰后的函数

    Examples:
        >>> @llm_call(max_retries=3, llm_name="Google", agent_name="Market Analyst")
        >>> def call_market_llm(llm, prompt):
        >>>     return llm.invoke(prompt)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(llm, *args, **kwargs) -> LLMCallResult:
            # 创建配置
            config = LLMCallConfig(
                max_retries=max_retries,
                retry_delay=retry_delay,
                validate_response=validate_response,
                min_response_length=min_response_length,
                log_tokens=log_tokens,
                log_performance=log_performance,
                cache_enabled=cache_enabled,
                cache_ttl=cache_ttl,
            )

            # 尝试从缓存获取
            # 提取prompt作为缓存键(假设第一个参数是prompt)
            prompt = args[0] if args else kwargs.get("prompt", "")
            llm_model = getattr(llm, "model", "unknown")

            cache_key = _get_cache_key(prompt, llm_model, **kwargs)
            cached_result = _get_from_cache(cache_key, config)
            if cached_result:
                return cached_result

            # 执行LLM调用
            retry_count = 0
            last_error = None
            result_content = ""
            input_tokens = 0
            output_tokens = 0
            start_time = time.time()

            while retry_count < config.max_retries:
                try:
                    retry_count += 1
                    logger.info(
                        f"🔄 [{agent_name}] 调用{llm_name} (尝试 {retry_count}/{config.max_retries})"
                    )

                    # 调用LLM
                    response = func(llm, *args, **kwargs)

                    # 提取内容
                    if hasattr(response, "content"):
                        result_content = response.content
                    elif isinstance(response, str):
                        result_content = response
                    else:
                        result_content = str(response)

                    # 验证响应
                    if config.validate_response:
                        content_length = len(result_content)
                        if content_length < config.min_response_length:
                            logger.warning(
                                f"⚠️ [{agent_name}] 响应过短: {content_length}字符 < {config.min_response_length}字符"
                            )
                            # 继续重试
                            last_error = f"响应过短: {content_length}字符"
                            continue

                    # 提取Token使用情况
                    if hasattr(response, "response_metadata"):
                        metadata = response.response_metadata
                        if isinstance(metadata, dict) and "token_usage" in metadata:
                            token_usage = metadata["token_usage"]
                            input_tokens = token_usage.get("prompt_tokens", 0)
                            output_tokens = token_usage.get("completion_tokens", 0)

                            if config.log_tokens:
                                logger.info(
                                    f"📊 [{agent_name}] Token使用: 输入={input_tokens}, "
                                    f"输出={output_tokens}, 总计={input_tokens + output_tokens}"
                                )

                    # 成功调用
                    duration = time.time() - start_time

                    if config.log_performance:
                        logger.info(f"⏱️ [{agent_name}] LLM调用耗时: {duration:.2f}秒")
                        logger.info(
                            f"📝 [{agent_name}] 响应长度: {len(result_content)}字符"
                        )

                    # 保存到缓存
                    _save_to_cache(cache_key, result_content, config)

                    return LLMCallResult(
                        success=True,
                        content=result_content,
                        retry_count=retry_count,
                        duration=duration,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cached=False,
                    )

                except Exception as e:
                    last_error = str(e)
                    logger.error(
                        f"❌ [{agent_name}] LLM调用失败 (尝试 {retry_count}): {e}"
                    )

                    if retry_count < config.max_retries:
                        logger.info(
                            f"🔄 [{agent_name}] 等待{config.retry_delay}秒后重试..."
                        )
                        time.sleep(config.retry_delay)

            # 所有重试都失败
            duration = time.time() - start_time
            logger.error(f"❌ [{agent_name}] 所有LLM调用尝试失败")

            # 生成默认响应
            default_response = f"""**默认响应**

由于技术原因,{agent_name}无法生成详细分析。

**错误信息:**
{last_error}

**建议:**
1. 检查LLM API配置
2. 检查网络连接
3. 检查API Key是否有效
4. 稍后重试分析

注意: 此为系统默认响应,建议结合人工分析做出最终决策。"""

            return LLMCallResult(
                success=False,
                content=default_response,
                error=last_error,
                retry_count=retry_count,
                duration=duration,
            )

        return wrapper

    return decorator


def clear_llm_cache():
    """清除LLM响应缓存"""
    global _llm_response_cache
    cache_size = len(_llm_response_cache)
    _llm_response_cache.clear()
    logger.info(f"🗑️ [LLM缓存] 已清除缓存 (共{cache_size}条)")


def get_cache_stats() -> Dict[str, Any]:
    """
    获取缓存统计信息

    Returns:
        缓存统计信息
    """
    global _llm_response_cache

    return {
        "cache_size": len(_llm_response_cache),
        "cache_keys": list(_llm_response_cache.keys()),
    }
