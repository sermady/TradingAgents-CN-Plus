# -*- coding: utf-8 -*-
"""
文件缓存后端

提供本地文件系统持久化缓存实现
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional, Tuple

if TYPE_CHECKING:
    from ..stats import CacheStats

logger = logging.getLogger(__name__)


class FileBackend:
    """文件缓存后端"""

    def __init__(
        self,
        stats: "CacheStats",
        cache_dir: str = "data/cache",
    ):
        """
        初始化文件缓存后端

        Args:
            stats: 缓存统计管理器
            cache_dir: 缓存目录路径
        """
        self._stats = stats
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Tuple[Optional[Any], str]:
        """
        从文件获取缓存

        Args:
            key: 缓存键

        Returns:
            (值, 来源)
        """
        try:
            file_path = self._cache_dir / f"{key}.json"

            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 检查过期
                expires_at = datetime.fromisoformat(
                    data.get("expires_at", "2099-12-31")
                )
                if expires_at > datetime.now(timezone.utc):
                    self._stats.increment("hits")
                    logger.debug(f"📦 File缓存命中: {key}")
                    return data.get("value"), "file"
                else:
                    file_path.unlink()  # 删除过期文件
                    self._stats.increment("expires")

            self._stats.increment("misses")
            return None, "file"

        except Exception as e:
            logger.warning(f"⚠️ File读取失败: {e}")
            return None, "file"

    def set(self, key: str, value: Any, ttl: int = 3600, category: str = "general"):
        """
        设置文件缓存

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            category: 缓存类别
        """
        try:
            file_path = self._cache_dir / f"{key}.json"
            file_path.parent.mkdir(parents=True, exist_ok=True)

            expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)

            data = {
                "key": key,
                "value": value,
                "category": category,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": expires_at.isoformat(),
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self._stats.increment("sets")
            logger.debug(f"💾 设置File缓存: {key} (TTL: {ttl}s)")

        except Exception as e:
            logger.warning(f"⚠️ File写入失败: {e}")

    def delete(self, key: str) -> bool:
        """
        删除文件缓存

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        try:
            file_path = self._cache_dir / f"{key}.json"
            if file_path.exists():
                file_path.unlink()
                self._stats.increment("deletes")
                return True
            return False

        except Exception as e:
            logger.warning(f"⚠️ File删除失败: {e}")
            return False

    def clear_category(self, category: str) -> int:
        """
        清除指定类别的缓存

        Args:
            category: 缓存类别

        Returns:
            清除的缓存数量
        """
        # 文件缓存不支持按类别清除（需要读取每个文件检查category）
        # 简化处理：直接返回0，如需清除请手动删除缓存目录
        logger.warning("文件缓存不支持按类别清除，请手动删除缓存目录")
        return 0
