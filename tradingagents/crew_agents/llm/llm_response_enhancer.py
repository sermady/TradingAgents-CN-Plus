# -*- coding: utf-8 -*-
"""
LLM响应增强器
解决"Invalid response from LLM call - None or empty"问题
增强LLM调用的稳定性和可靠性
"""

import time
import random
import logging
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from loguru import logger

@dataclass
class ResponseEnhancementConfig:
    """响应增强配置"""
    max_retries: int = 3                    # 最大重试次数
    base_delay: float = 0.5                 # 基础延迟时间
    max_delay: float = 5.0                  # 最大延迟时间
    exponential_base: float = 2.0           # 指数退避基数
    jitter_ratio: float = 0.1              # 随机抖动比例

    # 响应验证配置
    min_response_length: int = 1            # 最小响应长度
    require_non_empty: bool = True          # 要求非空响应
    require_meaningful_content: bool = True # 要求有意义的内容

    # 降级策略配置
    enable_prompt_simplification: bool = True    # 启用提示简化
    enable_model_fallback: bool = True          # 启用模型降级
    enable_response_reconstruction: bool = True  # 启用响应重构


class LLMResponseEnhancer:
    """LLM响应增强器"""

    def __init__(self, config: Optional[ResponseEnhancementConfig] = None):
        self.config = config or ResponseEnhancementConfig()
        self.call_statistics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'empty_responses': 0,
            'retries_used': 0,
            'average_response_time': 0.0,
            'last_reset': time.time()
        }

    def enhance_llm_call(self, llm_call_func: Callable,
                        messages: Union[List[Dict], str],
                        **kwargs) -> Any:
        """
        增强的LLM调用方法

        Args:
            llm_call_func: LLM调用函数
            messages: 消息内容
            **kwargs: 其他参数

        Returns:
            LLM响应结果
        """
        self.call_statistics['total_calls'] += 1
        start_time = time.time()

        original_messages = messages
        attempt = 0

        while attempt <= self.config.max_retries:
            try:
                # 执行LLM调用
                response = self._execute_llm_call(
                    llm_call_func, messages, attempt, **kwargs
                )

                # 验证响应
                if self._validate_response(response, attempt):
                    # 成功响应
                    elapsed_time = time.time() - start_time
                    self._update_success_stats(elapsed_time)

                    logger.debug(f"[ENHANCE] LLM调用成功，耗时 {elapsed_time:.2f}s，尝试 {attempt + 1}")
                    return response

                # 响应无效，准备重试
                logger.warning(f"[ENHANCE] LLM响应无效，准备重试 (尝试 {attempt + 1}/{self.config.max_retries + 1})")
                self.call_statistics['empty_responses'] += 1

            except Exception as e:
                logger.error(f"[ENHANCE] LLM调用异常 (尝试 {attempt + 1}): {e}")

                # 检查是否应该重试
                if not self._should_retry_on_exception(e, attempt):
                    raise

            # 准备下一次重试
            attempt += 1
            if attempt <= self.config.max_retries:
                # 应用恢复策略
                messages = self._apply_recovery_strategies(
                    original_messages, attempt, **kwargs
                )

                # 计算延迟时间并等待
                delay = self._calculate_retry_delay(attempt)
                logger.info(f"[ENHANCE] 等待 {delay:.2f}s 后重试...")
                time.sleep(delay)

                self.call_statistics['retries_used'] += 1

        # 所有重试都失败了
        elapsed_time = time.time() - start_time
        self.call_statistics['failed_calls'] += 1

        logger.error(f"[ENHANCE] LLM调用最终失败，耗时 {elapsed_time:.2f}s，总尝试 {attempt} 次")
        raise ValueError("Invalid response from LLM call - None or empty after all retries")

    def _execute_llm_call(self, llm_call_func: Callable,
                         messages: Union[List[Dict], str],
                         attempt: int, **kwargs) -> Any:
        """执行LLM调用"""
        try:
            return llm_call_func(messages, **kwargs)
        except Exception as e:
            # 记录调用异常
            logger.debug(f"[ENHANCE] LLM调用函数异常 (尝试 {attempt + 1}): {e}")
            raise

    def _validate_response(self, response: Any, attempt: int) -> bool:
        """验证LLM响应是否有效"""
        if response is None:
            logger.debug(f"[ENHANCE] 响应为None (尝试 {attempt + 1})")
            return False

        # 转换为字符串进行检查
        response_str = str(response).strip()

        if not response_str:
            logger.debug(f"[ENHANCE] 响应为空字符串 (尝试 {attempt + 1})")
            return False

        if self.config.require_non_empty and len(response_str) < self.config.min_response_length:
            logger.debug(f"[ENHANCE] 响应长度不足 {len(response_str)} < {self.config.min_response_length} (尝试 {attempt + 1})")
            return False

        if self.config.require_meaningful_content:
            # 检查是否包含有意义的内容
            meaningful_chars = sum(1 for c in response_str if c.isalnum() or c.isspace())
            if meaningful_chars < 3:  # 至少包含3个字母数字字符
                logger.debug(f"[ENHANCE] 响应缺乏有意义内容 (尝试 {attempt + 1})")
                return False

        return True

    def _should_retry_on_exception(self, exception: Exception, attempt: int) -> bool:
        """判断是否应该在异常时重试"""
        # 对于特定类型的异常，决定是否重试
        retryable_exceptions = [
            'ConnectionError',
            'TimeoutError',
            'HTTPError',
            'RequestException',
            'RemoteDisconnected',
            'ChunkedEncodingError'
        ]

        exception_name = type(exception).__name__
        is_retryable = any(retry_type in exception_name for retry_type in retryable_exceptions)

        if is_retryable and attempt < self.config.max_retries:
            logger.info(f"[ENHANCE] 检测到可重试异常 {exception_name}，将重试")
            return True

        return False

    def _apply_recovery_strategies(self, original_messages: Union[List[Dict], str],
                                 attempt: int, **kwargs) -> Union[List[Dict], str]:
        """应用恢复策略"""
        messages = original_messages

        # 策略1: 提示简化
        if self.config.enable_prompt_simplification and attempt >= 2:
            messages = self._simplify_prompt(messages)
            logger.info(f"[ENHANCE] 应用提示简化策略 (尝试 {attempt + 1})")

        # 策略2: 消息格式优化
        if isinstance(messages, list) and attempt >= 1:
            messages = self._optimize_message_format(messages)
            logger.debug(f"[ENHANCE] 应用消息格式优化 (尝试 {attempt + 1})")

        return messages

    def _simplify_prompt(self, messages: Union[List[Dict], str]) -> Union[List[Dict], str]:
        """简化提示内容"""
        if isinstance(messages, str):
            # 简化字符串提示
            if len(messages) > 200:
                return messages[:200] + "..."
            return messages

        elif isinstance(messages, list):
            # 简化消息列表
            simplified_messages = []
            for msg in messages:
                if isinstance(msg, dict):
                    content = msg.get('content', '')
                    if len(content) > 150:
                        simplified_msg = msg.copy()
                        simplified_msg['content'] = content[:150] + "..."
                        simplified_messages.append(simplified_msg)
                    else:
                        simplified_messages.append(msg)
                else:
                    simplified_messages.append(msg)
            return simplified_messages

        return messages

    def _optimize_message_format(self, messages: List[Dict]) -> List[Dict]:
        """优化消息格式"""
        optimized_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                # 确保必要字段存在
                optimized_msg = {
                    'role': msg.get('role', 'user'),
                    'content': str(msg.get('content', ''))
                }
                optimized_messages.append(optimized_msg)
        return optimized_messages

    def _calculate_retry_delay(self, attempt: int) -> float:
        """计算重试延迟时间"""
        # 指数退避
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
        delay = min(delay, self.config.max_delay)

        # 添加随机抖动
        jitter = delay * self.config.jitter_ratio * random.random()
        delay += jitter

        return delay

    def _update_success_stats(self, response_time: float):
        """更新成功统计信息"""
        self.call_statistics['successful_calls'] += 1

        # 更新平均响应时间
        total_successful = self.call_statistics['successful_calls']
        current_avg = self.call_statistics['average_response_time']
        self.call_statistics['average_response_time'] = (
            (current_avg * (total_successful - 1) + response_time) / total_successful
        )

    def get_statistics(self) -> Dict[str, Any]:
        """获取调用统计信息"""
        stats = self.call_statistics.copy()

        # 计算成功率
        total_calls = stats['total_calls']
        if total_calls > 0:
            stats['success_rate'] = stats['successful_calls'] / total_calls
            stats['failure_rate'] = stats['failed_calls'] / total_calls
            stats['empty_response_rate'] = stats['empty_responses'] / total_calls
            stats['retry_usage_rate'] = stats['retries_used'] / total_calls
        else:
            stats['success_rate'] = 0.0
            stats['failure_rate'] = 0.0
            stats['empty_response_rate'] = 0.0
            stats['retry_usage_rate'] = 0.0

        stats['uptime'] = time.time() - stats['last_reset']

        return stats

    def reset_statistics(self):
        """重置统计信息"""
        self.call_statistics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'empty_responses': 0,
            'retries_used': 0,
            'average_response_time': 0.0,
            'last_reset': time.time()
        }


# 全局增强器实例
_global_enhancer: Optional[LLMResponseEnhancer] = None


def get_llm_response_enhancer(config: Optional[ResponseEnhancementConfig] = None) -> LLMResponseEnhancer:
    """获取全局LLM响应增强器实例"""
    global _global_enhancer

    if _global_enhancer is None:
        _global_enhancer = LLMResponseEnhancer(config)
        logger.info("[ENHANCE] LLM响应增强器已初始化")

    return _global_enhancer


def enhanced_llm_call(llm_call_func: Callable,
                     messages: Union[List[Dict], str],
                     **kwargs) -> Any:
    """
    便捷函数：增强的LLM调用

    Args:
        llm_call_func: LLM调用函数
        messages: 消息内容
        **kwargs: 其他参数

    Returns:
        增强后的LLM响应
    """
    enhancer = get_llm_response_enhancer()
    return enhancer.enhance_llm_call(llm_call_func, messages, **kwargs)


if __name__ == "__main__":
    # 测试代码
    print("=== LLM响应增强器测试 ===")

    enhancer = LLMResponseEnhancer()

    # 模拟一个有时返回空响应的LLM函数
    call_count = 0
    def mock_llm_call(messages):
        global call_count
        call_count += 1
        if call_count <= 2:  # 前两次调用返回空
            return None
        return f"成功响应，调用次数: {call_count}"

    try:
        # 测试增强调用
        result = enhancer.enhance_llm_call(mock_llm_call, "测试消息")
        print(f"调用结果: {result}")

        # 显示统计信息
        stats = enhancer.get_statistics()
        print(f"\n统计信息:")
        print(f"  总调用次数: {stats['total_calls']}")
        print(f"  成功次数: {stats['successful_calls']}")
        print(f"  重试次数: {stats['retries_used']}")
        print(f"  成功率: {stats['success_rate']:.1%}")

    except Exception as e:
        print(f"测试失败: {e}")