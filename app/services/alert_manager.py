# -*- coding: utf-8 -*-
"""
AlertManager - Alert and Notification Service

Provides comprehensive alerting and notification management system.

Features:
- Alert rule creation and management
- Multi-level alerts (info, warning, error, critical)
- Alert history tracking
- Alert acknowledgment and resolution
- Notification channel management (in-app, email, webhook)
- Alert aggregation and suppression
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_mongo_db
from app.core.unified_config_service import get_config_manager

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别枚举"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """告警状态枚举"""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class AlertCategory(Enum):
    """告警类别枚举"""

    SYSTEM = "system"
    PERFORMANCE = "performance"
    DATA = "data"
    SECURITY = "security"
    BUSINESS = "business"
    SYNC = "sync"


class NotificationChannel(Enum):
    """通知渠道枚举"""

    IN_APP = "in_app"
    EMAIL = "email"
    WEBHOOK = "webhook"


@dataclass
class AlertRule:
    """告警规则"""

    name: str
    category: AlertCategory
    level: AlertLevel
    condition: str  # e.g., "cpu_percent > 90"
    threshold: float
    id: Optional[str] = None
    enabled: bool = True
    channels: List[NotificationChannel] = field(default_factory=list)
    message_template: str = ""
    cooldown_seconds: int = 300  # 冷却时间
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None


@dataclass
class Alert:
    """告警实例"""

    category: AlertCategory
    level: AlertLevel
    id: Optional[str] = None
    rule_id: Optional[str] = None
    rule_name: Optional[str] = None
    status: AlertStatus = AlertStatus.ACTIVE
    title: str = ""
    message: str = ""
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    triggered_at: Optional[str] = None
    acknowledged_at: Optional[str] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AlertManager:
    """
    告警管理器

    提供完整的告警创建、通知和管理功能。
    """

    def __init__(self):
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._alerts_collection = "alerts"
        self._rules_collection = "alert_rules"
        self._history_collection = "alert_history"
        self._lock = asyncio.Lock()
        self._initialized = False
        self._active_rules: Dict[str, AlertRule] = {}

    async def _get_db(self) -> AsyncIOMotorDatabase:
        """获取MongoDB连接"""
        if self._db is None:
            self._db = get_mongo_db()
        return self._db

    async def initialize(self) -> None:
        """初始化告警管理器"""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            db = await self._get_db()

            # 创建告警集合索引
            await db[self._alerts_collection].create_index(
                [("status", 1), ("level", 1), ("triggered_at", -1)]
            )
            await db[self._alerts_collection].create_index("rule_id")

            # 创建规则集合索引
            await db[self._rules_collection].create_index("name", unique=True)
            await db[self._rules_collection].create_index("enabled")

            # 创建历史记录集合索引
            await db[self._history_collection].create_index(
                [("alert_id", 1), ("timestamp", -1)]
            )

            # 加载启用的规则
            await self._load_active_rules()

            self._initialized = True
            logger.info("AlertManager initialized")

    async def _load_active_rules(self) -> None:
        """加载启用的告警规则"""
        db = await self._get_db()

        async for doc in db[self._rules_collection].find({"enabled": True}):
            rule = self._doc_to_rule(doc)
            if rule.id:
                self._active_rules[rule.id] = rule

    def _doc_to_rule(self, doc: Dict[str, Any]) -> AlertRule:
        """将文档转换为AlertRule"""
        return AlertRule(
            id=str(doc["_id"]),
            name=doc["name"],
            category=AlertCategory(doc["category"]),
            level=AlertLevel(doc["level"]),
            condition=doc["condition"],
            threshold=doc["threshold"],
            enabled=doc.get("enabled", True),
            channels=[NotificationChannel(c) for c in doc.get("channels", ["in_app"])],
            message_template=doc.get("message_template", ""),
            cooldown_seconds=doc.get("cooldown_seconds", 300),
            created_at=doc.get("created_at"),
            updated_at=doc.get("updated_at"),
            created_by=doc.get("created_by"),
        )

    # ==================== Rule Management ====================

    async def create_rule(self, rule: AlertRule) -> str:
        """
        创建告警规则

        Args:
            rule: 告警规则

        Returns:
            创建的规则ID
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        now = datetime.now().isoformat()
        rule_data = {
            "name": rule.name,
            "category": rule.category.value,
            "level": rule.level.value,
            "condition": rule.condition,
            "threshold": rule.threshold,
            "enabled": rule.enabled,
            "channels": [c.value for c in rule.channels],
            "message_template": rule.message_template,
            "cooldown_seconds": rule.cooldown_seconds,
            "created_at": now,
            "updated_at": now,
            "created_by": rule.created_by,
        }

        result = await db[self._rules_collection].insert_one(rule_data)
        rule.id = str(result.inserted_id)
        rule.created_at = now
        rule.updated_at = now

        # 如果规则已启用，添加到活动规则
        if rule.enabled and rule.id:
            self._active_rules[rule.id] = rule

        return rule.id

    async def get_rules(
        self, enabled_only: bool = False, category: Optional[AlertCategory] = None
    ) -> List[AlertRule]:
        """
        获取告警规则列表

        Args:
            enabled_only: 只返回启用的规则
            category: 按类别过滤

        Returns:
            告警规则列表
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        query = {}
        if enabled_only:
            query["enabled"] = True
        if category:
            query["category"] = category.value

        rules = []
        async for doc in db[self._rules_collection].find(query):
            rules.append(self._doc_to_rule(doc))

        return rules

    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新告警规则

        Args:
            rule_id: 规则ID
            updates: 更新内容

        Returns:
            是否更新成功
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        # 转换枚举值
        if "category" in updates and isinstance(updates["category"], AlertCategory):
            updates["category"] = updates["category"].value
        if "level" in updates and isinstance(updates["level"], AlertLevel):
            updates["level"] = updates["level"].value
        if "channels" in updates:
            updates["channels"] = [c.value for c in updates["channels"]]

        updates["updated_at"] = datetime.now().isoformat()

        result = await db[self._rules_collection].update_one(
            {"_id": rule_id}, {"$set": updates}
        )

        if result.modified_count > 0:
            # 更新缓存规则
            if rule_id in self._active_rules:
                rule = self._active_rules[rule_id]
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
            return True

        return False

    async def delete_rule(self, rule_id: str) -> bool:
        """
        删除告警规则

        Args:
            rule_id: 规则ID

        Returns:
            是否删除成功
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        result = await db[self._rules_collection].delete_one({"_id": rule_id})

        if result.deleted_count > 0:
            self._active_rules.pop(rule_id, None)
            return True

        return False

    # ==================== Alert Management ====================

    async def trigger_alert(
        self,
        rule_id: str,
        metric_value: float,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        触发告警

        Args:
            rule_id: 规则ID
            metric_value: 指标值
            message: 告警消息
            metadata: 元数据

        Returns:
            告警ID
        """
        if not self._initialized:
            await self.initialize()

        # 检查规则是否存在
        if rule_id not in self._active_rules:
            logger.warning(f"Alert rule {rule_id} not found or disabled")
            return None

        rule = self._active_rules[rule_id]

        # 检查是否在冷却期内
        if await self._is_in_cooldown(rule_id):
            logger.debug(f"Alert {rule_id} is in cooldown, skipping")
            return None

        db = await self._get_db()

        now = datetime.now().isoformat()
        alert_data = {
            "rule_id": rule_id,
            "rule_name": rule.name,
            "category": rule.category.value,
            "level": rule.level.value,
            "status": AlertStatus.ACTIVE.value,
            "title": f"[{rule.level.value.upper()}] {rule.name}",
            "message": message
            or rule.message_template
            or f"Alert triggered: {rule.condition}",
            "metric_value": metric_value,
            "threshold": rule.threshold,
            "triggered_at": now,
            "metadata": metadata or {},
        }

        result = await db[self._alerts_collection].insert_one(alert_data)
        alert_id = str(result.inserted_id)

        # 记录到历史
        await self._add_to_history(alert_id, "triggered", alert_data)

        # 设置冷却时间
        await self._set_cooldown(rule_id)

        # 发送通知
        await self._send_notifications(alert_data, rule)

        return alert_id

    async def _is_in_cooldown(self, rule_id: str) -> bool:
        """检查规则是否在冷却期内"""
        db = await self._get_db()

        recent_alert = await db[self._alerts_collection].find_one(
            {
                "rule_id": rule_id,
                "triggered_at": {
                    "$gte": datetime.now()
                    .fromtimestamp(
                        time.time() - 300  # 默认5分钟冷却
                    )
                    .isoformat()
                },
            }
        )

        return recent_alert is not None

    async def _set_cooldown(self, rule_id: str) -> None:
        """设置冷却时间（通过记录最近告警时间实现）"""
        # 冷却由MongoDB查询中的时间窗口控制
        pass

    async def _send_notifications(
        self, alert_data: Dict[str, Any], rule: AlertRule
    ) -> None:
        """发送告警通知"""
        for channel in rule.channels:
            try:
                if channel == NotificationChannel.IN_APP:
                    await self._send_in_app_notification(alert_data)
                elif channel == NotificationChannel.EMAIL:
                    await self._send_email_notification(alert_data, rule)
                elif channel == NotificationChannel.WEBHOOK:
                    await self._send_webhook_notification(alert_data, rule)
            except Exception as e:
                logger.exception(f"Failed to send notification via {channel.value}")

    async def _send_in_app_notification(self, alert_data: Dict[str, Any]) -> None:
        """发送应用内通知"""
        db = await self._get_db()

        notification = {
            "type": "alert",
            "title": alert_data["title"],
            "message": alert_data["message"],
            "level": alert_data["level"],
            "alert_id": str(alert_data["_id"]),
            "created_at": datetime.now().isoformat(),
            "read": False,
        }

        await db["notifications"].insert_one(notification)

    async def _send_email_notification(
        self, alert_data: Dict[str, Any], rule: AlertRule
    ) -> None:
        """发送邮件通知

        使用SMTP协议发送邮件告警通知
        支持重试机制和错误处理
        """
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.utils import formataddr

            # 从配置获取SMTP设置
            config_mgr = get_config_manager()
            smtp_host = config_mgr.get("SMTP_HOST", "smtp.gmail.com")
            smtp_port = config_mgr.get("SMTP_PORT", 587)
            smtp_user = config_mgr.get("SMTP_USER", "")
            smtp_password = config_mgr.get("SMTP_PASSWORD", "")
            smtp_from = config_mgr.get("SMTP_FROM", "noreply@tradingagents.cn")
            smtp_to = config_mgr.get("SMTP_TO", "admin@tradingagents.cn")

            # 检查SMTP配置
            if not smtp_user or not smtp_password:
                logger.warning("⚠️ SMTP配置不完整，跳过邮件发送")
                return

            # 构建邮件内容
            subject = f"[{str(alert_data['level']).upper()}] {alert_data['title']}"

            # 邮件正文
            body = f"""
告警详情：
━━━━━━━━━━━━━━━━━━━━━━━━

标题：{alert_data["title"]}
级别：{alert_data["level"]}
类别：{alert_data["category"]}
时间：{alert_data.get("created_at", "N/A")}

消息：
{alert_data.get("message", "无详细消息")}

━━━━━━━━━━━━━━━━━━━━━━━━
此邮件由TradingAgents-CN告警系统自动发送，请勿回复。
"""

            # 创建邮件对象
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = formataddr(("TradingAgents告警系统", smtp_from))
            msg["To"] = smtp_to

            # 添加HTML和纯文本部分
            msg.attach(MIMEText(body, "plain", "utf-8"))

            # 发送邮件（带重试）
            max_retries = 3
            retry_delay = 5  # 秒

            for attempt in range(max_retries):
                try:
                    with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                        server.starttls()
                        server.login(smtp_user, smtp_password)
                        server.send_message(msg)

                    logger.info(
                        f"✅ 邮件发送成功: {alert_data['title']} "
                        f"(尝试 {attempt + 1}/{max_retries})"
                    )
                    return

                except smtplib.SMTPException as e:
                    logger.warning(
                        f"⚠️ 邮件发送失败 (尝试 {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        raise
                except Exception as e:
                    logger.error(f"❌ 邮件发送异常: {e}")
                    raise

        except ImportError:
            logger.error("❌ 缺少邮件依赖库smtplib")
        except Exception as e:
            logger.error(f"❌ 发送邮件通知失败: {e}", exc_info=True)

    async def _send_webhook_notification(
        self, alert_data: Dict[str, Any], rule: AlertRule
    ) -> None:
        """发送Webhook通知

        使用HTTP POST发送告警通知到配置的Webhook URL
        支持重试机制、超时控制和错误处理
        """
        try:
            import httpx
            from datetime import datetime

            # 从配置获取Webhook URL
            config_mgr = get_config_manager()
            webhook_url = config_mgr.get("ALERT_WEBHOOK_URL", "")

            # 检查Webhook URL是否配置
            if not webhook_url:
                logger.warning("⚠️ Webhook URL未配置，跳过Webhook通知")
                return

            # 构建Webhook payload
            payload = {
                "alert_id": str(alert_data.get("_id", "")),
                "rule_id": str(rule.id) if rule.id else "",
                "rule_name": rule.name,
                "title": alert_data["title"],
                "level": alert_data["level"],
                "category": alert_data["category"],
                "message": alert_data.get("message", ""),
                "created_at": alert_data.get("created_at", datetime.now().isoformat()),
                "metadata": alert_data.get("metadata", {}),
                "timestamp": datetime.now().isoformat(),
            }

            # 发送Webhook请求（带重试）
            max_retries = 3
            retry_delay = 2  # 秒
            timeout = 10  # 秒

            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=timeout) as client:
                        response = await client.post(
                            webhook_url,
                            json=payload,
                            headers={
                                "Content-Type": "application/json",
                                "User-Agent": "TradingAgents-CN/AlertManager/1.0",
                            },
                        )
                        response.raise_for_status()

                    logger.info(
                        f"✅ Webhook发送成功: {alert_data['title']} "
                        f"(尝试 {attempt + 1}/{max_retries}, "
                        f"状态码: {response.status_code})"
                    )
                    return

                except httpx.HTTPStatusError as e:
                    logger.warning(
                        f"⚠️ Webhook HTTP错误 (尝试 {attempt + 1}/{max_retries}): "
                        f"状态码={e.response.status_code}, "
                        f"响应={e.response.text[:200]}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logger.error(
                            f"❌ Webhook发送失败: HTTP状态码={e.response.status_code}"
                        )
                        raise

                except httpx.TimeoutException as e:
                    logger.warning(
                        f"⚠️ Webhook超时 (尝试 {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"❌ Webhook发送失败: 超时")
                        raise

                except Exception as e:
                    logger.warning(
                        f"⚠️ Webhook发送异常 (尝试 {attempt + 1}/{max_retries}): {e}"
                    )
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)
                        continue
                    else:
                        raise

        except ImportError:
            logger.error("❌ 缺少HTTP依赖库httpx")
        except Exception as e:
            logger.error(f"❌ 发送Webhook通知失败: {e}", exc_info=True)

    async def _add_to_history(
        self, alert_id: str, action: str, data: Dict[str, Any]
    ) -> None:
        """添加告警历史记录"""
        db = await self._get_db()

        history_entry = {
            "alert_id": alert_id,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        await db[self._history_collection].insert_one(history_entry)

    async def get_active_alerts(
        self,
        level: Optional[AlertLevel] = None,
        category: Optional[AlertCategory] = None,
        limit: int = 50,
    ) -> List[Alert]:
        """
        获取活跃告警列表

        Args:
            level: 按级别过滤
            category: 按类别过滤
            limit: 返回数量限制

        Returns:
            活跃告警列表
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        query = {"status": AlertStatus.ACTIVE.value}
        if level:
            query["level"] = level.value
        if category:
            query["category"] = category.value

        alerts = []
        async for doc in (
            db[self._alerts_collection]
            .find(query)
            .sort("triggered_at", -1)
            .limit(limit)
        ):
            alerts.append(self._doc_to_alert(doc))

        return alerts

    def _doc_to_alert(self, doc: Dict[str, Any]) -> Alert:
        """将文档转换为Alert"""
        return Alert(
            id=str(doc["_id"]),
            rule_id=doc.get("rule_id"),
            rule_name=doc.get("rule_name"),
            category=AlertCategory(doc["category"]),
            level=AlertLevel(doc["level"]),
            status=AlertStatus(doc["status"]),
            title=doc.get("title", ""),
            message=doc.get("message", ""),
            metric_value=doc.get("metric_value"),
            threshold=doc.get("threshold"),
            triggered_at=doc.get("triggered_at"),
            acknowledged_at=doc.get("acknowledged_at"),
            acknowledged_by=doc.get("acknowledged_by"),
            resolved_at=doc.get("resolved_at"),
            resolved_by=doc.get("resolved_by"),
            metadata=doc.get("metadata", {}),
        )

    async def acknowledge_alert(
        self, alert_id: str, user_id: Optional[str] = None
    ) -> bool:
        """
        确认告警

        Args:
            alert_id: 告警ID
            user_id: 确认用户

        Returns:
            是否确认成功
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        result = await db[self._alerts_collection].update_one(
            {"_id": alert_id, "status": AlertStatus.ACTIVE.value},
            {
                "$set": {
                    "status": AlertStatus.ACKNOWLEDGED.value,
                    "acknowledged_at": datetime.now().isoformat(),
                    "acknowledged_by": user_id,
                }
            },
        )

        if result.modified_count > 0:
            await self._add_to_history(alert_id, "acknowledged", {"user_id": user_id})
            return True

        return False

    async def resolve_alert(
        self, alert_id: str, user_id: Optional[str] = None, notes: Optional[str] = None
    ) -> bool:
        """
        解决告警

        Args:
            alert_id: 告警ID
            user_id: 解决用户
            notes: 解决备注

        Returns:
            是否解决成功
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        result = await db[self._alerts_collection].update_one(
            {"_id": alert_id},
            {
                "$set": {
                    "status": AlertStatus.RESOLVED.value,
                    "resolved_at": datetime.now().isoformat(),
                    "resolved_by": user_id,
                }
            },
        )

        if result.modified_count > 0:
            await self._add_to_history(
                alert_id, "resolved", {"user_id": user_id, "notes": notes}
            )
            return True

        return False

    async def get_alert_history(
        self, alert_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取告警历史

        Args:
            alert_id: 告警ID
            limit: 返回数量限制

        Returns:
            历史记录列表
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        history = []
        async for doc in (
            db[self._history_collection]
            .find({"alert_id": alert_id})
            .sort("timestamp", -1)
            .limit(limit)
        ):
            doc["_id"] = str(doc["_id"])
            history.append(doc)

        return history

    async def cleanup_old_alerts(self, days: int = 30) -> int:
        """
        清理旧的已解决告警

        Args:
            days: 保留天数

        Returns:
            删除的记录数量
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        cutoff = datetime.now()

        # 只删除已解决的告警
        result = await db[self._alerts_collection].delete_many(
            {
                "status": {
                    "$in": [AlertStatus.RESOLVED.value, AlertStatus.SUPPRESSED.value]
                },
                "resolved_at": {"$lt": cutoff.isoformat()},
            }
        )

        return result.deleted_count

    async def get_statistics(self) -> Dict[str, Any]:
        """
        获取告警统计信息

        Returns:
            统计信息
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        # 统计各状态告警数量
        status_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        status_results = (
            await db[self._alerts_collection]
            .aggregate_pipeline(status_pipeline)
            .to_list(length=10)
        )

        status_counts = {r["_id"]: r["count"] for r in status_results}

        # 统计各级别告警数量
        level_pipeline = [{"$group": {"_id": "$level", "count": {"$sum": 1}}}]
        level_results = (
            await db[self._alerts_collection]
            .aggregate_pipeline(level_pipeline)
            .to_list(length=10)
        )

        level_counts = {r["_id"]: r["count"] for r in level_results}

        return {
            "total_alerts": sum(status_counts.values()),
            "active_alerts": status_counts.get("active", 0),
            "acknowledged_alerts": status_counts.get("acknowledged", 0),
            "resolved_alerts": status_counts.get("resolved", 0),
            "by_level": level_counts,
            "active_rules_count": len(self._active_rules),
        }


# 全局实例
_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取AlertManager单例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
