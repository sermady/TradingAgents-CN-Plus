# -*- coding: utf-8 -*-
"""
增强型LLM响应缓存

改进点:
1. 支持Redis后端 (原仅支持内存)
2. 添加缓存统计和命中率跟踪
3. 支持按提示词类型配置TTL
4. 添加缓存预热功能
5. 更好的序列化处理

作者: Claude
创建日期: 2026-02-12
"""

import time
import hashlib
import json
from typing import Dict, Any, Optional, Tuple, Union, List
from enum import Enum

# 导入统一日志系统
from tradingagents.utils.logging_init import get_logger

logger = get_logger("llm_cache_enhanced")


class CacheBackend(Enum):
    """缓存后端类型"""

    MEMORY = "memory"
    REDIS = "redis"
    MONGODB = "mongodb"
    FILE = "file"


class PromptType(Enum):
    """提示词类型 (用于配置不同TTL)"""

    ANALYST_REPORT = "analyst_report"  # 分析师报告 (较长TTL)
    REALTIME_DATA = "realtime_data"  # 实时数据 (短TTL)
    RESEARCH_DEBATE = "research_debate"  # 研究辩论 (中等TTL)
    RISK_ANALYSIS = "risk_analysis"  # 风险分析 (中等TTL)
    GENERAL = "general"  # 一般查询 (默认TTL)


# 不同提示词类型的默认TTL (秒)
DEFAULT_TTL_BY_TYPE = {
    PromptType.ANALYST_REPORT: 3600 * 24,  # 24小时
    PromptType.REALTIME_DATA: 300,  # 5分钟
    PromptType.RESEARCH_DEBATE: 3600 * 2,  # 2小时
    PromptType.RISK_ANALYSIS: 3600 * 4,  # 4小时
    PromptType.GENERAL: 3600,  # 1小时
}


class EnhancedLLMCache:
    """增强型LLM响应缓存"""

    def __init__(
        self,
        cache_backend: Union[CacheBackend, str] = CacheBackend.MEMORY,
        max_size: int = 10000,
        default_ttl: int = 3600,
        redis_client=None,
        mongodb_client=None,
        file_cache_dir: str = "./cache/llm",
    ):
        """
        初始化增强型LLM缓存

        Args:
            cache_backend: 缓存后端类型
            max_size: 最大缓存数量 (仅内存缓存)
            default_ttl: 默认TTL(秒)
            redis_client: Redis客户端实例
            mongodb_client: MongoDB客户端实例
            file_cache_dir: 文件缓存目录
        """
        if isinstance(cache_backend, str):
            cache_backend = CacheBackend(cache_backend)

        self.cache_backend = cache_backend
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.redis_client = redis_client
        self.mongodb_client = mongodb_client
        self.file_cache_dir = file_cache_dir

        # 内存缓存
        self._memory_cache: Dict[str, Tuple[str, float, int, Optional[PromptType]]] = {}

        # 统计信息
        self._stats = {
            "hits": 0,
            "misses": 0,
            "sets": 0,
            "evictions": 0,
            "errors": 0,
        }

        # 初始化后端
        self._init_backend()

        logger.info(
            f"🗄️ [LLM缓存] 初始化: backend={cache_backend.value}, "
            f"max_size={max_size}, default_ttl={default_ttl}s"
        )

    def _init_backend(self):
        """初始化缓存后端"""
        if self.cache_backend == CacheBackend.REDIS:
            if self.redis_client is None:
                try:
                    import redis

                    # 尝试从环境变量创建Redis连接
                    import os

                    redis_host = os.getenv("REDIS_HOST", "localhost")
                    redis_port = int(os.getenv("REDIS_PORT", 6379))
                    redis_password = os.getenv("REDIS_PASSWORD") or None
                    redis_db = int(os.getenv("REDIS_DB", 0))

                    self.redis_client = redis.Redis(
                        host=redis_host,
                        port=redis_port,
                        password=redis_password,
                        db=redis_db,
                        decode_responses=True,
                        socket_connect_timeout=5,
                        socket_timeout=5,
                    )
                    # 测试连接
                    self.redis_client.ping()
                    logger.info(
                        f"✅ [LLM缓存] Redis连接成功: {redis_host}:{redis_port}"
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [LLM缓存] Redis连接失败，回退到内存缓存: {e}")
                    self.cache_backend = CacheBackend.MEMORY
                    self.redis_client = None

        elif self.cache_backend == CacheBackend.FILE:
            import os

            os.makedirs(self.file_cache_dir, exist_ok=True)
            logger.info(f"📁 [LLM缓存] 文件缓存目录: {self.file_cache_dir}")

    def _get_cache_key(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """生成缓存键"""
        key_string = f"{model}:{temperature}:{max_tokens}:{prompt}"
        return hashlib.sha256(key_string.encode("utf-8")).hexdigest()

    def _get_ttl(
        self, prompt_type: Optional[PromptType] = None, custom_ttl: Optional[int] = None
    ) -> int:
        """获取TTL"""
        if custom_ttl is not None:
            return custom_ttl
        if prompt_type is not None:
            return DEFAULT_TTL_BY_TYPE.get(prompt_type, self.default_ttl)
        return self.default_ttl

    def get(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        prompt_type: Optional[PromptType] = None,
        ttl: Optional[int] = None,
    ) -> Optional[str]:
        """
        从缓存获取响应

        Args:
            prompt: 提示词
            model: 模型名称
            temperature: 温度
            max_tokens: 最大token数
            prompt_type: 提示词类型
            ttl: 自定义TTL(秒)

        Returns:
            缓存的响应,如果不存在或过期则返回None
        """
        cache_key = self._get_cache_key(prompt, model, temperature, max_tokens)
        actual_ttl = self._get_ttl(prompt_type, ttl)

        try:
            if self.cache_backend == CacheBackend.MEMORY:
                result = self._get_from_memory(cache_key, actual_ttl)
            elif self.cache_backend == CacheBackend.REDIS and self.redis_client:
                result = self._get_from_redis(cache_key, actual_ttl)
            elif self.cache_backend == CacheBackend.FILE:
                result = self._get_from_file(cache_key, actual_ttl)
            else:
                result = None

            if result:
                self._stats["hits"] += 1
                logger.debug(f"✅ [LLM缓存] 命中: key={cache_key[:16]}...")
            else:
                self._stats["misses"] += 1
                logger.debug(f"🔍 [LLM缓存] 未命中: key={cache_key[:16]}...")

            return result

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"❌ [LLM缓存] 获取失败: {e}")
            return None

    def set(
        self,
        prompt: str,
        response: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        prompt_type: Optional[PromptType] = None,
        ttl: Optional[int] = None,
    ):
        """
        保存响应到缓存

        Args:
            prompt: 提示词
            response: LLM响应
            model: 模型名称
            temperature: 温度
            max_tokens: 最大token数
            prompt_type: 提示词类型
            ttl: 自定义TTL(秒)
        """
        cache_key = self._get_cache_key(prompt, model, temperature, max_tokens)
        actual_ttl = self._get_ttl(prompt_type, ttl)

        try:
            if self.cache_backend == CacheBackend.MEMORY:
                self._save_to_memory(cache_key, response, actual_ttl, prompt_type)
            elif self.cache_backend == CacheBackend.REDIS and self.redis_client:
                self._save_to_redis(cache_key, response, actual_ttl)
            elif self.cache_backend == CacheBackend.FILE:
                self._save_to_file(cache_key, response, actual_ttl)

            self._stats["sets"] += 1
            logger.debug(f"💾 [LLM缓存] 保存: key={cache_key[:16]}...")

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"❌ [LLM缓存] 保存失败: {e}")

    def _get_from_memory(self, cache_key: str, ttl: int) -> Optional[str]:
        """从内存缓存获取"""
        if cache_key not in self._memory_cache:
            return None

        response, timestamp, hit_count, prompt_type = self._memory_cache[cache_key]
        age = time.time() - timestamp

        # 检查是否过期
        if age > ttl:
            del self._memory_cache[cache_key]
            logger.debug(f"⏰️ [LLM缓存] 内存缓存过期: age={age:.1f}s > {ttl}s")
            return None

        # 更新命中次数
        self._memory_cache[cache_key] = (
            response,
            timestamp,
            hit_count + 1,
            prompt_type,
        )

        return response

    def _save_to_memory(
        self,
        cache_key: str,
        response: str,
        ttl: int,
        prompt_type: Optional[PromptType] = None,
    ):
        """保存到内存缓存"""
        # 检查缓存大小,必要时清理
        if len(self._memory_cache) >= self.max_size:
            self._evict_oldest()

        self._memory_cache[cache_key] = (response, time.time(), 1, prompt_type)

    def _get_from_redis(self, cache_key: str, ttl: int) -> Optional[str]:
        """从Redis缓存获取"""
        if not self.redis_client:
            return None

        try:
            data = self.redis_client.get(f"llm_cache:{cache_key}")
            if data:
                return data.decode("utf-8") if isinstance(data, bytes) else data
            return None
        except Exception as e:
            logger.debug(f"[LLM缓存] Redis获取失败: {e}")
            return None

    def _save_to_redis(self, cache_key: str, response: str, ttl: int):
        """保存到Redis缓存"""
        if not self.redis_client:
            return

        try:
            self.redis_client.setex(f"llm_cache:{cache_key}", ttl, response)
        except Exception as e:
            logger.debug(f"[LLM缓存] Redis保存失败: {e}")

    def _get_from_file(self, cache_key: str, ttl: int) -> Optional[str]:
        """从文件缓存获取"""
        import os

        cache_file = os.path.join(self.file_cache_dir, f"{cache_key}.json")
        if not os.path.exists(cache_file):
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            timestamp = data.get("timestamp", 0)
            age = time.time() - timestamp

            if age > ttl:
                os.remove(cache_file)
                return None

            return data.get("response")
        except Exception as e:
            logger.debug(f"[LLM缓存] 文件读取失败: {e}")
            return None

    def _save_to_file(self, cache_key: str, response: str, ttl: int):
        """保存到文件缓存"""
        import os

        cache_file = os.path.join(self.file_cache_dir, f"{cache_key}.json")
        try:
            data = {
                "response": response,
                "timestamp": time.time(),
                "ttl": ttl,
            }
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception as e:
            logger.debug(f"[LLM缓存] 文件保存失败: {e}")

    def _evict_oldest(self):
        """淘汰最旧的缓存"""
        if not self._memory_cache:
            return

        # 找到最旧的缓存
        oldest_key = min(
            self._memory_cache.items(),
            key=lambda x: x[1][1],  # timestamp
        )[0]

        del self._memory_cache[oldest_key]
        self._stats["evictions"] += 1
        logger.debug(f"🗑️ [LLM缓存] 淘汰旧缓存: key={oldest_key[:16]}...")

    def clear(self):
        """清除所有缓存"""
        cache_size = len(self._memory_cache)

        if self.cache_backend == CacheBackend.MEMORY:
            self._memory_cache.clear()
        elif self.cache_backend == CacheBackend.REDIS and self.redis_client:
            try:
                # 删除所有llm_cache:*键
                for key in self.redis_client.scan_iter(match="llm_cache:*"):
                    self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"[LLM缓存] Redis清除失败: {e}")
        elif self.cache_backend == CacheBackend.FILE:
            import os
            import glob

            files = glob.glob(os.path.join(self.file_cache_dir, "*.json"))
            for f in files:
                try:
                    os.remove(f)
                except:
                    pass

        logger.info(f"🗑️ [LLM缓存] 已清除: 共{cache_size}条")

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = (
            (self._stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        )

        return {
            "backend": self.cache_backend.value,
            "size": len(self._memory_cache),
            "max_size": self.max_size,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": f"{hit_rate:.2f}%",
            "sets": self._stats["sets"],
            "evictions": self._stats["evictions"],
            "errors": self._stats["errors"],
        }

    def warm_cache(self, prompts: List[Dict[str, Any]]):
        """
        缓存预热 - 批量预加载常用提示词

        Args:
            prompts: 提示词列表,每项包含prompt, model, temperature, max_tokens, response
        """
        logger.info(f"🔥 [LLM缓存] 开始预热,共{len(prompts)}条")

        success_count = 0
        for item in prompts:
            try:
                self.set(
                    prompt=item["prompt"],
                    response=item["response"],
                    model=item.get("model", "default"),
                    temperature=item.get("temperature", 0.7),
                    max_tokens=item.get("max_tokens", 2000),
                    prompt_type=item.get("prompt_type", PromptType.GENERAL),
                    ttl=item.get("ttl"),
                )
                success_count += 1
            except Exception as e:
                logger.warning(f"[LLM缓存] 预热条目失败: {e}")

        logger.info(f"✅ [LLM缓存] 预热完成: {success_count}/{len(prompts)}")


# 全局缓存实例
_llm_cache_enhanced: Optional[EnhancedLLMCache] = None


def get_enhanced_llm_cache(
    cache_backend: Union[CacheBackend, str] = CacheBackend.MEMORY,
    max_size: int = 10000,
    default_ttl: int = 3600,
    **kwargs,
) -> EnhancedLLMCache:
    """
    获取增强型LLM缓存实例(单例模式)

    Args:
        cache_backend: 缓存后端
        max_size: 最大缓存数量
        default_ttl: 默认TTL
        **kwargs: 其他参数

    Returns:
        EnhancedLLMCache实例
    """
    global _llm_cache_enhanced

    if _llm_cache_enhanced is None:
        _llm_cache_enhanced = EnhancedLLMCache(
            cache_backend=cache_backend,
            max_size=max_size,
            default_ttl=default_ttl,
            **kwargs,
        )

    return _llm_cache_enhanced


def clear_llm_cache():
    """清除LLM缓存"""
    global _llm_cache_enhanced
    if _llm_cache_enhanced:
        _llm_cache_enhanced.clear()


def get_cache_stats() -> Dict[str, Any]:
    """获取缓存统计"""
    global _llm_cache_enhanced
    if _llm_cache_enhanced:
        return _llm_cache_enhanced.get_stats()
    return {}


# 兼容性: 保持与旧版API兼容
class LLMCache(EnhancedLLMCache):
    """旧版API兼容包装器"""

    pass


def get_llm_cache(**kwargs) -> LLMCache:
    """旧版API兼容"""
    return get_enhanced_llm_cache(**kwargs)
