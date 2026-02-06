# -*- coding: utf-8 -*-
"""
WebSocket 通知系统
替代 SSE + Redis PubSub，解决连接泄漏问题

安全增强 (2026-02-02):
- JWT Token 改用子协议传递，防止日志泄露
- 添加全局连接限制防止 DoS
- 添加 IP 级别连接限制
- 修复心跳任务协程泄漏
"""

import asyncio
import json
import logging
import time
from collections import defaultdict
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
from datetime import datetime

from app.services.auth_service import AuthService

router = APIRouter()
logger = logging.getLogger("webapi.websocket")


# 🔥 连接信息（用于诊断）
class ConnectionInfo:
    def __init__(self, websocket: WebSocket, user_id: str, client_ip: str = "unknown"):
        self.websocket = websocket
        self.user_id = user_id
        self.created_at = datetime.utcnow()
        self.client_info = self._get_client_info(websocket)
        self.client_ip = client_ip  # 🔒 存储客户端 IP

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
        except (KeyError, AttributeError, UnicodeDecodeError) as e:
            logger.debug(f"获取客户端信息失败: {e}")
            return "Unknown"

    def get_lifetime_seconds(self) -> float:
        return (datetime.utcnow() - self.created_at).total_seconds()


# 🔥 获取客户端 IP 地址（支持代理）
def get_client_ip(websocket: WebSocket) -> str:
    """从 WebSocket 请求中提取客户端 IP"""
    try:
        if hasattr(websocket, "scope") and websocket.scope:
            headers = dict(websocket.scope.get("headers", []))
            # 检查代理头
            for header in [b"x-forwarded-for", b"x-real-ip"]:
                if header in headers:
                    ip_list = headers[header].decode("utf-8").split(",")
                    return ip_list[0].strip() if ip_list else "unknown"
            # 回退到直接连接
            client = websocket.scope.get("client")
            if client:
                return client[0]
    except Exception as e:
        logger.warning(f"获取客户端 IP 失败: {e}")
    return "unknown"


# 🔥 全局 WebSocket 连接管理器
class ConnectionManager:
    """WebSocket 连接管理器（含 DoS 防护）"""

    def __init__(self):
        # user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # 🔥 连接信息映射（用于诊断）
        self.connection_info: Dict[WebSocket, ConnectionInfo] = {}
        self._lock = asyncio.Lock()

        # 每个用户最多允许的WebSocket连接数
        self.max_connections_per_user = 5

        # 🔒 DoS 防护配置
        self.max_total_connections = 1000  # 全局最大连接数
        self.ip_connections: Dict[str, int] = defaultdict(int)  # IP -> 连接数
        self.max_connections_per_ip = 10  # 单IP最多10个连接
        self.ip_connection_history: Dict[str, list] = defaultdict(list)  # IP连接历史

    async def connect(self, websocket: WebSocket, user_id: str, client_ip: str):
        """连接 WebSocket（含 DoS 防护）"""
        # 🔒 DoS 防护：全局连接限制
        total = sum(len(conns) for conns in self.active_connections.values())
        if total >= self.max_total_connections:
            await websocket.close(code=1013, reason="Server overload")
            logger.warning(f"🚫 [WS] 拒绝连接：服务器连接数已达上限 ({total})")
            raise HTTPException(status_code=429, detail="Too many connections")

        # 🔒 DoS 防护：IP 级别限制
        if self.ip_connections[client_ip] >= self.max_connections_per_ip:
            await websocket.close(code=1013, reason="IP limit exceeded")
            logger.warning(f"🚫 [WS] 拒绝连接：IP {client_ip} 连接数超限")
            raise HTTPException(
                status_code=429, detail="Too many connections from this IP"
            )

        # 🔒 DoS 防护：连接频率限制（防止重放攻击）
        now = time.time()
        recent = [t for t in self.ip_connection_history[client_ip] if now - t < 60]
        if len(recent) > 20:  # 1分钟内最多20次连接
            await websocket.close(code=1013, reason="Too frequent reconnections")
            logger.warning(f"🚫 [WS] 拒绝连接：IP {client_ip} 重连过于频繁")
            raise HTTPException(status_code=429, detail="Too frequent connections")

        # 记录连接
        self.ip_connections[client_ip] += 1
        self.ip_connection_history[client_ip].append(now)

        await websocket.accept()

        # 🔥 创建连接信息（包含客户端 IP）
        conn_info = ConnectionInfo(websocket, user_id)
        conn_info.client_ip = client_ip  # 存储客户端 IP

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
                f"✅ [WS] 新连接: user={user_id}, ip={client_ip}, "
                f"该用户连接数={len(self.active_connections[user_id])}, "
                f"总连接数={total_connections}, "
                f"client={conn_info.client_info[:30]}"
            )

    async def disconnect(self, websocket: WebSocket, user_id: str, client_ip: str):
        """断开 WebSocket"""
        # 🔥 获取连接存活时间
        conn_info = self.connection_info.pop(websocket, None)
        lifetime = conn_info.get_lifetime_seconds() if conn_info else 0

        # 🔒 释放 IP 计数
        if client_ip != "unknown":
            self.ip_connections[client_ip] = max(0, self.ip_connections[client_ip] - 1)

        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

            total_connections = sum(
                len(conns) for conns in self.active_connections.values()
            )
            logger.info(
                f"🔌 [WS] 断开连接: user={user_id}, ip={client_ip}, "
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
async def websocket_notifications_endpoint(websocket: WebSocket):
    """
    WebSocket 通知端点（安全增强版）

    客户端连接: new WebSocket('ws://localhost:8000/api/ws/notifications', ['auth-token', '<jwt_token>'])

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
    # 🔒 从子协议或 query string 获取 Token
    token = None

    # 方式1：从子协议获取（生产环境推荐）
    subprotocols = websocket.scope.get("subprotocols", [])
    if len(subprotocols) >= 2 and subprotocols[0] == "auth-token":
        token = subprotocols[1]
        logger.debug("[WS] 从子协议获取 Token")

    # 方式2：从 query string 获取（开发环境兼容性更好）
    if not token:
        query_string = websocket.scope.get("query_string", b"").decode("utf-8")
        if query_string:
            from urllib.parse import parse_qs

            params = parse_qs(query_string)
            if "token" in params:
                token = params["token"][0]
                logger.debug("[WS] 从 query string 获取 Token")

    if not token:
        await websocket.close(code=1008, reason="Unauthorized: No token provided")
        logger.warning("🚫 [WS] 拒绝连接：未提供 Token")
        return

    # 验证 token
    token_data = AuthService.verify_token(token)
    if not token_data:
        await websocket.close(code=1008, reason="Unauthorized: Invalid token")
        logger.warning("🚫 [WS] 拒绝连接：Token 验证失败")
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

    # 🔒 获取客户端 IP
    client_ip = get_client_ip(websocket)

    # 连接 WebSocket（含 DoS 防护）
    try:
        await manager.connect(websocket, user_id, client_ip)
    except HTTPException:
        # DoS 防护已关闭连接
        return

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

    # 🔒 显式声明心跳任务变量（修复协程泄漏）
    heartbeat_task = None

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
                if not data:
                    continue

                # 🔥 解析并处理心跳消息
                try:
                    message = json.loads(data)
                    msg_type = message.get("type")

                    if msg_type == "ping":
                        # 响应客户端心跳
                        await websocket.send_json(
                            {"type": "pong", "timestamp": time.time()}
                        )
                        logger.debug(f"📥 [WS] 收到 ping，已回复 pong: user={user_id}")
                        continue

                    # 处理其他消息类型
                    logger.debug(
                        f"📥 [WS] 收到客户端消息: user={user_id}, type={msg_type}"
                    )
                except json.JSONDecodeError:
                    # 非 JSON 消息，记录日志
                    logger.debug(
                        f"📥 [WS] 收到非JSON消息: user={user_id}, data={data[:50]}"
                    )

            except WebSocketDisconnect:
                logger.info(f"🔌 [WS] 客户端主动断开: user={user_id}")
                break
            except Exception as e:
                logger.error(f"❌ [WS] 接收消息错误: {e}")
                break

    finally:
        # 🔒 安全取消心跳任务（修复协程泄漏）
        if heartbeat_task is not None:
            heartbeat_task.cancel()
            try:
                # 添加超时防止永久挂起
                await asyncio.wait_for(heartbeat_task, timeout=2.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
            except Exception as e:
                logger.warning(f"⚠️ [WS] 心跳任务清理异常: {e}")

        # 断开连接
        await manager.disconnect(websocket, user_id, client_ip)


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
