# -*- coding: utf-8 -*-
"""
WebSocket 连接管理器
用于实时推送分析进度更新

借鉴上游 TradingAgents 项目设计思想:
- 消息去重机制 (通过消息ID防止重复推送)
"""

import asyncio
import json
import logging
import time
from typing import Dict, Set, Any, Optional, Deque
from collections import deque
from fastapi import WebSocket, WebSocketDisconnect

from app.services.progress.constants import (
    MESSAGE_DEDUP_CACHE_SIZE,
    MESSAGE_DEDUP_WINDOW,
)

logger = logging.getLogger(__name__)


class MessageDedupCache:
    """
    消息去重缓存

    借鉴上游 TradingAgents 项目设计思想:
    - 使用 LRU 缓存存储最近消息ID
    - 时间窗口机制防止过期消息
    - 支持自定义去重字段
    """

    def __init__(self, max_size: int = MESSAGE_DEDUP_CACHE_SIZE, window: int = MESSAGE_DEDUP_WINDOW):
        self._cache: Dict[str, float] = {}  # {message_id: timestamp}
        self._order: Deque[str] = deque(maxlen=max_size)
        self._max_size = max_size
        self._window = window
        self._lock = asyncio.Lock()

    def _generate_message_id(self, message: Dict[str, Any]) -> str:
        """
        生成消息唯一ID

        基于消息内容和类型生成哈希，用于去重判断
        """
        import hashlib

        # 提取关键字段用于生成ID
        task_id = message.get('task_id', '')
        message_type = message.get('type', 'unknown')
        step_name = message.get('step_name', '')
        progress = message.get('progress', '')

        # 组合关键字段
        content = f"{task_id}:{message_type}:{step_name}:{progress}"

        # 如果有agent_status，也包含进去
        agent_status = message.get('agent_status', {})
        if agent_status:
            # 只取状态值进行哈希
            status_values = json.dumps(agent_status, sort_keys=True)
            content += f":{status_values}"

        return hashlib.md5(content.encode()).hexdigest()

    async def is_duplicate(self, message: Dict[str, Any]) -> bool:
        """
        检查消息是否是重复

        Args:
            message: 消息字典

        Returns:
            bool: True如果是重复消息，False如果不是
        """
        async with self._lock:
            message_id = self._generate_message_id(message)
            current_time = time.time()

            # 清理过期条目
            self._cleanup_expired(current_time)

            # 检查是否存在
            if message_id in self._cache:
                # 更新时间戳（LRU行为）
                self._cache[message_id] = current_time
                return True

            # 添加到缓存
            self._cache[message_id] = current_time
            self._order.append(message_id)

            # 如果超过大小限制，移除最旧的
            while len(self._cache) > self._max_size:
                oldest = self._order.popleft()
                self._cache.pop(oldest, None)

            return False

    def _cleanup_expired(self, current_time: float) -> None:
        """清理过期的缓存条目"""
        expired = [
            msg_id for msg_id, timestamp in self._cache.items()
            if current_time - timestamp > self._window
        ]
        for msg_id in expired:
            del self._cache[msg_id]
            if msg_id in self._order:
                self._order.remove(msg_id)

    async def clear(self) -> None:
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            self._order.clear()


class WebSocketManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # 存储活跃连接：{task_id: {websocket1, websocket2, ...}}
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
        # 消息去重缓存
        self._dedup_cache = MessageDedupCache()
    
    async def connect(self, websocket: WebSocket, task_id: str):
        """建立 WebSocket 连接"""
        await websocket.accept()
        
        async with self._lock:
            if task_id not in self.active_connections:
                self.active_connections[task_id] = set()
            self.active_connections[task_id].add(websocket)
        
        logger.info(f"🔌 WebSocket 连接建立: {task_id}")
    
    async def disconnect(self, websocket: WebSocket, task_id: str):
        """断开 WebSocket 连接"""
        async with self._lock:
            if task_id in self.active_connections:
                self.active_connections[task_id].discard(websocket)
                if not self.active_connections[task_id]:
                    del self.active_connections[task_id]
        
        logger.info(f"🔌 WebSocket 连接断开: {task_id}")
    
    async def send_progress_update(self, task_id: str, message: Dict[str, Any]):
        """
        发送进度更新到指定任务的所有连接

        借鉴上游 TradingAgents 项目设计思想:
        - 检查消息ID防止重复推送
        - 支持消息去重机制
        """
        if task_id not in self.active_connections:
            return

        # 添加 task_id 到消息（用于去重）
        message['task_id'] = task_id

        # 检查消息是否重复
        is_dup = await self._dedup_cache.is_duplicate(message)
        if is_dup:
            logger.debug(f"🔄 WebSocket 消息去重: {task_id}")
            return

        # 复制连接集合以避免在迭代时修改
        connections = self.active_connections[task_id].copy()
        failed_connections = []

        for connection in connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.warning(f"⚠️ 发送 WebSocket 消息失败: {e}")
                failed_connections.append(connection)

        # 移除失效的连接
        if failed_connections:
            async with self._lock:
                if task_id in self.active_connections:
                    for conn in failed_connections:
                        self.active_connections[task_id].discard(conn)
    
    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]):
        """向用户的所有连接广播消息"""
        # 这里可以扩展为按用户ID管理连接
        # 目前简化实现，只按任务ID管理
        pass
    
    async def get_connection_count(self, task_id: str) -> int:
        """获取指定任务的连接数"""
        async with self._lock:
            return len(self.active_connections.get(task_id, set()))
    
    async def get_total_connections(self) -> int:
        """获取总连接数"""
        async with self._lock:
            total = 0
            for connections in self.active_connections.values():
                total += len(connections)
            return total

# 全局实例
_websocket_manager = None

def get_websocket_manager() -> WebSocketManager:
    """获取 WebSocket 管理器实例"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
