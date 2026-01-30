# -*- coding: utf-8 -*-
"""
WebSocket 通知系统
替代 SSE + Redis PubSub，解决连接泄漏问题
"""

import asyncio
import json
import logging
from typing import Dict, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from datetime import datetime

from app.services.auth_service import AuthService

router = APIRouter()
logger = logging.getLogger("webapi.websocket")


# 🔥 连接信息（用于诊断）
class ConnectionInfo:
    def __init__(self, websocket: WebSocket, user_id: str):
        self.websocket = websocket
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.client_info = self._get_client_info(websocket)

    def _get_client_info(self, websocket: WebSocket) -> str:
        try:
            # 尝试获取客户端信息
            if hasattr(websocket, "scope") and websocket.scope:
                headers = dict(websocket.scope.get("headers", []))
                user_agent = headers.get(b"user-agent", b"Unknown").decode(
                    "utf-8", errors="ignore"
                )
                return user_agent[:50] if user_agent else "Unknown"
            return "Unknown"
        except:
            return "Unknown"

    def get_lifetime_seconds(self) -> float:
        return (datetime.utcnow() - self.created_at).total_seconds()


# 🔥 全局 WebSocket 连接管理器
class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        # user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # 🔥 连接信息映射（用于诊断）
        self.connection_info: Dict[WebSocket, ConnectionInfo] = {}
        self._lock = asyncio.Lock()
        # 每个用户最多允许的WebSocket连接数
        self.max_connections_per_user = 3

    async def connect(self, websocket: WebSocket, user_id: str):
        """连接 WebSocket"""
        await websocket.accept()

        # 🔥 创建连接信息
        conn_info = ConnectionInfo(websocket, user_id)

        async with self._lock:
            # 检查用户当前连接数
            user_connections = self.active_connections.get(user_id, set())

            # 🔥 如果连接数超过限制,关闭最旧的连接（按创建时间）
            if len(user_connections) >= self.max_connections_per_user:
                # 找到最旧的连接
                oldest_ws = None
                oldest_time = None
                for ws in user_connections:
                    info = self.connection_info.get(ws)
                    if info:
                        if oldest_time is None or info.created_at < oldest_time:
                            oldest_time = info.created_at
                            oldest_ws = ws

                if oldest_ws:
                    user_connections.discard(oldest_ws)
                    old_info = self.connection_info.pop(oldest_ws, None)
                    lifetime = old_info.get_lifetime_seconds() if old_info else 0
                    logger.warning(
                        f"⚠️ [WS] 用户 {user_id} 连接数过多 ({len(user_connections)}), "
                        f"断开最旧连接 (存活: {lifetime:.1f}s)"
                    )
                    try:
                        await oldest_ws.close(
                            code=1000, reason="Connection limit exceeded"
                        )
                        logger.info(
                            f"🔌 [WS] 断开旧连接: user={user_id}, lifetime={lifetime:.1f}s"
                        )
                    except Exception as e:
                        logger.warning(f"⚠️ [WS] 断开旧连接失败: {e}")

            # 添加新连接
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
            # 🔥 记录连接信息
            self.connection_info[websocket] = conn_info

            total_connections = sum(
                len(conns) for conns in self.active_connections.values()
            )
            logger.info(
                f"✅ [WS] 新连接: user={user_id}, "
                f"该用户连接数={len(self.active_connections[user_id])}, "
                f"总连接数={total_connections}, "
                f"client={conn_info.client_info[:30]}"
            )

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """断开 WebSocket"""
        # 🔥 获取连接存活时间
        conn_info = self.connection_info.pop(websocket, None)
        lifetime = conn_info.get_lifetime_seconds() if conn_info else 0

        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

            total_connections = sum(
                len(conns) for conns in self.active_connections.values()
            )
            logger.info(
                f"🔌 [WS] 断开连接: user={user_id}, "
                f"存活: {lifetime:.1f}s, "
                f"总连接数={total_connections}"
            )

    async def send_personal_message(self, message: dict, user_id: str):
        """发送消息给指定用户的所有连接"""
        async with self._lock:
            if user_id not in self.active_connections:
                logger.debug(f"⚠️ [WS] 用户 {user_id} 没有活跃连接")
                return

            connections = list(self.active_connections[user_id])

        # 在锁外发送消息，避免阻塞
        message_json = json.dumps(message, ensure_ascii=False)
        dead_connections = []

        for connection in connections:
            try:
                await connection.send_text(message_json)
                logger.debug(f"📤 [WS] 发送消息给 user={user_id}")
            except Exception as e:
                logger.warning(f"❌ [WS] 发送消息失败: {e}")
                dead_connections.append(connection)

        # 清理死连接
        if dead_connections:
            async with self._lock:
                if user_id in self.active_connections:
                    for conn in dead_connections:
                        self.active_connections[user_id].discard(conn)
                    if not self.active_connections[user_id]:
                        del self.active_connections[user_id]

    async def broadcast(self, message: dict):
        """广播消息给所有连接"""
        async with self._lock:
            all_connections = []
            for connections in self.active_connections.values():
                all_connections.extend(connections)

        message_json = json.dumps(message, ensure_ascii=False)

        for connection in all_connections:
            try:
                await connection.send_text(message_json)
            except Exception as e:
                logger.warning(f"❌ [WS] 广播消息失败: {e}")

    def get_stats(self) -> dict:
        """获取连接统计"""
        return {
            "total_users": len(self.active_connections),
            "total_connections": sum(
                len(conns) for conns in self.active_connections.values()
            ),
            "users": {
                user_id: len(conns)
                for user_id, conns in self.active_connections.items()
            },
        }


# 全局连接管理器实例
manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def websocket_notifications_endpoint(
    websocket: WebSocket, token: str = Query(...)
):
    """
    WebSocket 通知端点

    客户端连接: ws://localhost:8000/api/ws/notifications?token=<jwt_token>

    消息格式:
    {
        "type": "notification",  // 消息类型: notification, heartbeat, connected
        "data": {
            "id": "...",
            "title": "...",
            "content": "...",
            "type": "analysis",
            "link": "/stocks/000001",
            "source": "analysis",
            "created_at": "2025-10-23T12:00:00",
            "status": "unread"
        }
    }
    """
    # 验证 token
    token_data = AuthService.verify_token(token)
    if not token_data:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    # 🔥 安全修复：从 token 中解析用户 ID，不再硬编码
    try:
        if hasattr(token_data, "sub"):
            user_id = token_data.sub
        elif isinstance(token_data, dict):
            user_id = token_data.get("sub") or token_data.get("username")
        else:
            user_id = str(token_data)

        if not user_id:
            logger.error("❌ [WS] Token 中未找到用户标识")
            await websocket.close(code=1008, reason="Invalid token data")
            return
    except Exception as e:
        logger.error(f"❌ [WS] 解析 Token 用户 ID 失败: {e}")
        await websocket.close(code=1008, reason="Token parse error")
        return

    # 连接 WebSocket
    await manager.connect(websocket, user_id)

    # 发送连接确认
    await websocket.send_json(
        {
            "type": "connected",
            "data": {
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "WebSocket 连接成功",
            },
        }
    )

    try:
        # 心跳任务
        async def send_heartbeat():
            while True:
                try:
                    await asyncio.sleep(30)  # 每 30 秒发送一次心跳
                    await websocket.send_json(
                        {
                            "type": "heartbeat",
                            "data": {"timestamp": datetime.utcnow().isoformat()},
                        }
                    )
                except Exception as e:
                    logger.debug(f"💓 [WS] 心跳发送失败: {e}")
                    break

        # 启动心跳任务
        heartbeat_task = asyncio.create_task(send_heartbeat())

        # 接收客户端消息（主要用于保持连接）
        while True:
            try:
                data = await websocket.receive_text()
                # 可以处理客户端发送的消息（如 ping/pong）
                logger.debug(f"📥 [WS] 收到客户端消息: user={user_id}, data={data}")
            except WebSocketDisconnect:
                logger.info(f"🔌 [WS] 客户端主动断开: user={user_id}")
                break
            except Exception as e:
                logger.error(f"❌ [WS] 接收消息错误: {e}")
                break

    finally:
        # 取消心跳任务
        if "heartbeat_task" in locals():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

        # 断开连接
        await manager.disconnect(websocket, user_id)


@router.websocket("/ws/tasks/{task_id}")
async def websocket_task_progress_endpoint(
    websocket: WebSocket, task_id: str, token: str = Query(...)
):
    """
    WebSocket 任务进度端点

    客户端连接: ws://localhost:8000/api/ws/tasks/<task_id>?token=<jwt_token>

    消息格式:
    {
        "type": "progress",  // 消息类型: progress, completed, error, heartbeat
        "data": {
            "task_id": "...",
            "message": "正在分析...",
            "step": 1,
            "total_steps": 5,
            "progress": 20.0,
            "timestamp": "2025-10-23T12:00:00"
        }
    }
    """
    # 验证 token
    token_data = AuthService.verify_token(token)
    if not token_data:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    # 🔥 安全修复：从 token 中解析用户 ID，不再硬编码
    try:
        if hasattr(token_data, "sub"):
            user_id = token_data.sub
        elif isinstance(token_data, dict):
            user_id = token_data.get("sub") or token_data.get("username")
        else:
            user_id = str(token_data)

        if not user_id:
            logger.error("❌ [WS-Task] Token 中未找到用户标识")
            await websocket.close(code=1008, reason="Invalid token data")
            return
    except Exception as e:
        logger.error(f"❌ [WS-Task] 解析 Token 用户 ID 失败: {e}")
        await websocket.close(code=1008, reason="Token parse error")
        return

    channel = f"task_progress:{task_id}"

    # 连接 WebSocket
    await websocket.accept()
    logger.info(f"✅ [WS-Task] 新连接: task={task_id}, user={user_id}")

    # 发送连接确认
    await websocket.send_json(
        {
            "type": "connected",
            "data": {
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "已连接任务进度流",
            },
        }
    )

    try:
        # 这里可以从 Redis 或数据库获取任务进度
        # 暂时保持连接，等待任务完成
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(
                    f"📥 [WS-Task] 收到客户端消息: task={task_id}, data={data}"
                )
            except WebSocketDisconnect:
                logger.info(f"🔌 [WS-Task] 客户端主动断开: task={task_id}")
                break
            except Exception as e:
                logger.error(f"❌ [WS-Task] 接收消息错误: {e}")
                break

    finally:
        logger.info(f"🔌 [WS-Task] 断开连接: task={task_id}")


@router.get("/ws/stats")
async def get_websocket_stats():
    """获取 WebSocket 连接统计"""
    return manager.get_stats()


@router.websocket("/ws/task/{task_id}")
async def websocket_task_progress_endpoint_v2(
    websocket: WebSocket, task_id: str, token: str = Query(...)
):
    """
    WebSocket 任务进度端点 (统一命名空间版本)

    客户端连接: ws://localhost:8000/api/ws/task/<task_id>?token=<jwt_token>

    消息格式:
    {
        "type": "progress",  // 消息类型: progress, completed, error, heartbeat
        "data": {
            "task_id": "...",
            "message": "正在分析...",
            "step": 1,
            "total_steps": 5,
            "progress": 20.0,
            "timestamp": "2025-10-23T12:00:00"
        }
    }
    """
    # 验证 token
    token_data = AuthService.verify_token(token)
    if not token_data:
        await websocket.close(code=1008, reason="Unauthorized")
        return

    user_id = token_data.sub

    # 连接 WebSocket
    await websocket.accept()
    logger.info(f"✅ [WS-Task] 新连接: task={task_id}, user={user_id}")

    # 发送连接确认
    await websocket.send_json(
        {
            "type": "connection_established",
            "data": {
                "task_id": task_id,
                "user_id": user_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "WebSocket 连接已建立",
            },
        }
    )

    try:
        # 保持连接活跃
        while True:
            try:
                # 接收客户端的心跳消息
                data = await websocket.receive_text()
                # 可以处理客户端发送的消息
                logger.debug(
                    f"📡 [WS-Task] 收到客户端消息: task={task_id}, data={data}"
                )
            except WebSocketDisconnect:
                logger.info(f"🔌 [WS-Task] 客户端主动断开: task={task_id}")
                break
            except Exception as e:
                logger.warning(f"⚠️ [WS-Task] 消息处理错误: {e}")
                break

    except WebSocketDisconnect:
        logger.info(f"🔌 [WS-Task] 客户端断开连接: task={task_id}")
    except Exception as e:
        logger.error(f"❌ [WS-Task] 连接错误: {e}")
    finally:
        logger.info(f"🔌 [WS-Task] 断开连接: task={task_id}")


# 🔥 辅助函数：供其他模块调用，发送通知
async def send_notification_via_websocket(user_id: str, notification: dict):
    """
    通过 WebSocket 发送通知

    Args:
        user_id: 用户 ID
        notification: 通知数据
    """
    message = {"type": "notification", "data": notification}
    await manager.send_personal_message(message, user_id)


async def send_task_progress_via_websocket(task_id: str, progress_data: dict):
    """
    通过 WebSocket 发送任务进度

    Args:
        task_id: 任务 ID
        progress_data: 进度数据
    """
    # 注意：这里需要知道任务属于哪个用户
    # 可以从数据库查询或在 progress_data 中传递
    # 暂时简化处理
    message = {"type": "progress", "data": progress_data}
    # 广播给所有连接（生产环境应该只发给任务所属用户）
    await manager.broadcast(message)
