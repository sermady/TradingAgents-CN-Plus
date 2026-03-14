# -*- coding: utf-8 -*-
"""
LLM API调用缓存管理器
提供智能的LLM响应缓存功能，减少API调用成本和响应时间
"""

import os
import sys
import json
import hashlib
import time
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger

# 配置logger编码
logger.remove()
logger.add(sys.stderr, enqueue=True)

class CacheStrategy(Enum):
    """缓存策略枚举"""
    DISABLED = "disabled"      # 禁用缓存
    MEMORY_ONLY = "memory"     # 仅内存缓存
    FILE_ONLY = "file"         # 仅文件缓存
    HYBRID = "hybrid"          # 混合模式（内存+文件）
    REDIS = "redis"            # Redis缓存（如果可用）

@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    timestamp: float
    model: str
    prompt_hash: str
    ttl_seconds: int
    access_count: int = 0
    last_access: float = 0.0
    
    def is_expired(self) -> bool:
        """检查缓存是否过期"""
        return time.time() - self.timestamp > self.ttl_seconds
    
    def update_access(self):
        """更新访问信息"""
        self.access_count += 1
        self.last_access = time.time()

class LLMCacheManager:
    """LLM API调用缓存管理器"""
    
    def __init__(self, strategy: Optional[str] = None):
        self.strategy = CacheStrategy(strategy or os.getenv('LLM_CACHE_STRATEGY', 'hybrid'))
        
        # 缓存配置
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.max_memory_entries = int(os.getenv('LLM_CACHE_MAX_MEMORY_ENTRIES', '1000'))
        self.default_ttl = int(os.getenv('LLM_CACHE_TTL_SECONDS', '3600'))  # 1小时默认TTL
        
        # 文件缓存配置
        self.cache_dir = Path(os.getenv('LLM_CACHE_DIR', 'cache/llm'))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Redis配置（如果可用）
        self.redis_client = None
        if self.strategy == CacheStrategy.REDIS:
            self._init_redis()
        
        # 统计信息
        self.stats = {
            'hits': 0,
            'misses': 0,
            'saves': 0,
            'evictions': 0,
            'errors': 0
        }
        
        logger.info(f"[CACHE] LLM缓存管理器初始化完成，策略: {self.strategy.value}")
    
    def _init_redis(self):
        """初始化Redis连接"""
        try:
            import redis
            from ..config.database_config import get_database_config
            
            # 使用统一数据库配置管理器
            db_config = get_database_config()
            redis_config = db_config.get_redis_config()
            self.redis_client = redis.from_url(redis_config.url, decode_responses=True)
            self.redis_client.ping()  # 测试连接
            logger.info("[CACHE] Redis连接初始化成功")
        except ImportError:
            logger.warning("[CACHE] redis库未安装，将使用混合缓存策略")
            self.strategy = CacheStrategy.HYBRID
        except Exception as e:
            logger.warning(f"[CACHE] Redis连接失败: {e}，将使用混合缓存策略")
            self.strategy = CacheStrategy.HYBRID
            self.redis_client = None
    
    def _generate_cache_key(self, model: str, messages: List[Dict], 
                           temperature: float = 0.7, max_tokens: Optional[int] = None) -> str:
        """生成缓存键"""
        # 创建包含所有关键参数的字符串
        key_components = [
            f"model:{model}",
            f"messages:{json.dumps(messages, sort_keys=True, ensure_ascii=False)}",
            f"temp:{temperature}",
            f"max_tokens:{max_tokens}"
        ]
        
        # 生成MD5哈希
        key_string = "|".join(key_components)
        cache_key = hashlib.md5(key_string.encode('utf-8')).hexdigest()
        
        return f"llm_cache:{cache_key}"
    
    def _generate_prompt_hash(self, messages: List[Dict]) -> str:
        """生成提示词哈希（用于统计）"""
        prompt_content = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        return hashlib.md5(prompt_content.encode('utf-8')).hexdigest()[:8]
    
    def get(self, model: str, messages: List[Dict], temperature: float = 0.7, 
            max_tokens: Optional[int] = None) -> Optional[Any]:
        """从缓存获取LLM响应"""
        if self.strategy == CacheStrategy.DISABLED:
            return None
        
        cache_key = self._generate_cache_key(model, messages, temperature, max_tokens)
        
        try:
            # 尝试从内存缓存获取
            if self.strategy in [CacheStrategy.MEMORY_ONLY, CacheStrategy.HYBRID]:
                if cache_key in self.memory_cache:
                    entry = self.memory_cache[cache_key]
                    if not entry.is_expired():
                        entry.update_access()
                        self.stats['hits'] += 1
                        logger.debug(f"[CACHE] 内存缓存命中: {entry.prompt_hash}")
                        return entry.value
                    else:
                        # 缓存过期，删除
                        del self.memory_cache[cache_key]
            
            # 尝试从文件缓存获取
            if self.strategy in [CacheStrategy.FILE_ONLY, CacheStrategy.HYBRID]:
                cache_file = self.cache_dir / f"{cache_key}.json"
                if cache_file.exists():
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    if time.time() - cache_data['timestamp'] <= cache_data['ttl_seconds']:
                        # 文件缓存命中，同时加载到内存
                        if self.strategy == CacheStrategy.HYBRID:
                            self._add_to_memory_cache(cache_key, cache_data)
                        
                        self.stats['hits'] += 1
                        logger.debug(f"[CACHE] 文件缓存命中: {cache_data['prompt_hash']}")
                        return cache_data['value']
                    else:
                        # 文件过期，删除
                        cache_file.unlink(missing_ok=True)
            
            # 尝试从Redis获取
            if self.strategy == CacheStrategy.REDIS and self.redis_client:
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    cache_data = json.loads(cached_data)
                    self.stats['hits'] += 1
                    logger.debug(f"[CACHE] Redis缓存命中: {cache_data['prompt_hash']}")
                    return cache_data['value']
            
        except Exception as e:
            logger.error(f"[CACHE] 缓存读取失败: {e}")
            self.stats['errors'] += 1
        
        self.stats['misses'] += 1
        return None
    
    def set(self, model: str, messages: List[Dict], response: Any,
            temperature: float = 0.7, max_tokens: Optional[int] = None,
            ttl_seconds: Optional[int] = None) -> bool:
        """保存LLM响应到缓存"""
        if self.strategy == CacheStrategy.DISABLED:
            return False
        
        cache_key = self._generate_cache_key(model, messages, temperature, max_tokens)
        prompt_hash = self._generate_prompt_hash(messages)
        ttl = ttl_seconds or self.default_ttl
        
        try:
            cache_entry = CacheEntry(
                key=cache_key,
                value=response,
                timestamp=time.time(),
                model=model,
                prompt_hash=prompt_hash,
                ttl_seconds=ttl
            )
            
            # 保存到内存缓存
            if self.strategy in [CacheStrategy.MEMORY_ONLY, CacheStrategy.HYBRID]:
                self._add_to_memory_cache(cache_key, cache_entry)
            
            # 保存到文件缓存
            if self.strategy in [CacheStrategy.FILE_ONLY, CacheStrategy.HYBRID]:
                cache_file = self.cache_dir / f"{cache_key}.json"
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(asdict(cache_entry), f, ensure_ascii=False, indent=2, default=str)
            
            # 保存到Redis
            if self.strategy == CacheStrategy.REDIS and self.redis_client:
                self.redis_client.setex(
                    cache_key,
                    ttl,
                    json.dumps(asdict(cache_entry), ensure_ascii=False, default=str)
                )
            
            self.stats['saves'] += 1
            logger.debug(f"[CACHE] 缓存保存成功: {prompt_hash}, 模型: {model}")
            return True
            
        except Exception as e:
            logger.error(f"[CACHE] 缓存保存失败: {e}")
            self.stats['errors'] += 1
            return False
    
    def _add_to_memory_cache(self, cache_key: str, data: Union[CacheEntry, Dict]):
        """添加到内存缓存"""
        # 如果是字典数据，转换为CacheEntry
        if isinstance(data, dict):
            cache_entry = CacheEntry(**data)
        else:
            cache_entry = data
        
        # 检查内存缓存大小限制
        if len(self.memory_cache) >= self.max_memory_entries:
            self._evict_memory_cache()
        
        self.memory_cache[cache_key] = cache_entry
    
    def _evict_memory_cache(self):
        """内存缓存淘汰策略（LRU）"""
        if not self.memory_cache:
            return
        
        # 按最后访问时间排序，删除最久未访问的缓存
        sorted_entries = sorted(
            self.memory_cache.items(),
            key=lambda x: x[1].last_access or x[1].timestamp
        )
        
        # 删除25%的缓存
        evict_count = max(1, len(sorted_entries) // 4)
        for i in range(evict_count):
            key, _ = sorted_entries[i]
            del self.memory_cache[key]
            self.stats['evictions'] += 1
        
        logger.debug(f"[CACHE] 内存缓存淘汰 {evict_count} 个条目")
    
    def clear(self, model: Optional[str] = None):
        """清理缓存"""
        try:
            # 清理内存缓存
            if model:
                keys_to_remove = [key for key, entry in self.memory_cache.items() 
                                if entry.model == model]
                for key in keys_to_remove:
                    del self.memory_cache[key]
            else:
                self.memory_cache.clear()
            
            # 清理文件缓存
            if self.strategy in [CacheStrategy.FILE_ONLY, CacheStrategy.HYBRID]:
                if model:
                    # 选择性清理特定模型的缓存
                    for cache_file in self.cache_dir.glob("*.json"):
                        try:
                            with open(cache_file, 'r', encoding='utf-8') as f:
                                cache_data = json.load(f)
                            if cache_data.get('model') == model:
                                cache_file.unlink()
                        except:
                            continue
                else:
                    # 清理所有文件缓存
                    for cache_file in self.cache_dir.glob("*.json"):
                        cache_file.unlink(missing_ok=True)
            
            # 清理Redis缓存
            if self.strategy == CacheStrategy.REDIS and self.redis_client:
                if model:
                    # Redis不易实现选择性清理，暂时跳过
                    logger.warning("[CACHE] Redis不支持按模型选择性清理")
                else:
                    # 清理所有LLM缓存
                    pattern = "llm_cache:*"
                    keys = self.redis_client.keys(pattern)
                    if keys:
                        self.redis_client.delete(*keys)
            
            logger.info(f"[CACHE] 缓存清理完成{'（模型: ' + model + '）' if model else ''}")
            
        except Exception as e:
            logger.error(f"[CACHE] 缓存清理失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'strategy': self.strategy.value,
            'memory_entries': len(self.memory_cache),
            'max_memory_entries': self.max_memory_entries,
            'file_cache_dir': str(self.cache_dir),
            'redis_available': self.redis_client is not None,
            'stats': {
                **self.stats,
                'total_requests': total_requests,
                'hit_rate_percent': round(hit_rate, 2)
            }
        }
    
    def cleanup_expired(self):
        """清理过期的缓存条目"""
        current_time = time.time()
        expired_count = 0
        
        try:
            # 清理内存缓存中的过期条目
            expired_keys = [key for key, entry in self.memory_cache.items()
                           if entry.is_expired()]
            for key in expired_keys:
                del self.memory_cache[key]
                expired_count += 1
            
            # 清理文件缓存中的过期条目
            if self.strategy in [CacheStrategy.FILE_ONLY, CacheStrategy.HYBRID]:
                for cache_file in self.cache_dir.glob("*.json"):
                    try:
                        with open(cache_file, 'r', encoding='utf-8') as f:
                            cache_data = json.load(f)
                        
                        if current_time - cache_data['timestamp'] > cache_data['ttl_seconds']:
                            cache_file.unlink()
                            expired_count += 1
                    except:
                        # 无法读取的文件直接删除
                        cache_file.unlink(missing_ok=True)
                        expired_count += 1
            
            if expired_count > 0:
                logger.info(f"[CACHE] 清理过期缓存 {expired_count} 个条目")
                
        except Exception as e:
            logger.error(f"[CACHE] 清理过期缓存失败: {e}")

# 创建全局缓存管理器实例
llm_cache_manager = LLMCacheManager()

def get_llm_cache() -> LLMCacheManager:
    """获取LLM缓存管理器实例"""
    return llm_cache_manager

def cache_llm_response(model: str, messages: List[Dict], response: Any,
                      temperature: float = 0.7, max_tokens: Optional[int] = None,
                      ttl_seconds: Optional[int] = None) -> bool:
    """缓存LLM响应的便利函数"""
    return llm_cache_manager.set(model, messages, response, temperature, max_tokens, ttl_seconds)

def get_cached_llm_response(model: str, messages: List[Dict],
                          temperature: float = 0.7, max_tokens: Optional[int] = None) -> Optional[Any]:
    """获取缓存LLM响应的便利函数"""
    return llm_cache_manager.get(model, messages, temperature, max_tokens)