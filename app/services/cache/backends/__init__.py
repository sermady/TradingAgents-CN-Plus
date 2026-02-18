# -*- coding: utf-8 -*-
"""
缓存存储后端模块

提供多级缓存后端实现：
- MemoryBackend: 内存缓存（最快）
- RedisBackend: Redis缓存（分布式）
- MongoDBBackend: MongoDB缓存（持久化）
- FileBackend: 文件缓存（本地持久化）
"""

from .memory import MemoryBackend
from .redis import RedisBackend
from .mongodb import MongoDBBackend
from .file import FileBackend

__all__ = [
    "MemoryBackend",
    "RedisBackend",
    "MongoDBBackend",
    "FileBackend",
]
