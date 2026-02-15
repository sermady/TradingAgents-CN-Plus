# -*- coding: utf-8 -*-
"""
AlertManager - Alert and Notification Service（优化版）

使用error_handler装饰器替代重复的try-except模式。
"""
from __future__ import annotations
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    JobExecutionEvent
)
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.error_handler import async_handle_errors_none, async_handle_errors_false
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
    告警管理器（优化版）

    使用error_handler装饰器简化错误处理，减少重复代码。
    """

    def __init__(self, scheduler: AsyncIOScheduler):
        """
        初始化服务

        Args:
            scheduler: APScheduler调度器实例
        """
        self.scheduler = scheduler
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._alerts_collection = "alerts"
        self._rules_collection = "alert_rules"
        self._history_collection = "alert_history"
        self._lock = asyncio.Lock()
        self._initialized: bool = False
        self._active_rules: Dict[str, AlertRule] = {}

    async def _get_db(self) -> AsyncIOMotorDatabase:
        """获取数据库连接"""
        if self._db is None:
            self._db = get_mongo_db()
        return self._db

    @async_handle_errors_none(error_message="获取数据库连接失败")
    async def initialize(self) -> None:
        """
        初始化告警管理器（使用装饰器简化错误处理）
        """
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            db = await self._get_db()

            # 创建索引
            await db[self._alerts_collection].create_index(
                [("status", 1), ("level", 1), ("triggered_at", -1)]
            )
            await db[self._rules_collection].create_index("name", unique=True)
            await db[self._rules_collection].create_index("enabled")
            await db[self._history_collection].create_index(
                [("alert_id", 1), ("timestamp", -1)]
            )

            # 加载启用的规则
            await self._load_active_rules()

            self._initialized = True
            logger.info("AlertManager initialized")

    @async_handle_errors_none(error_message="加载规则失败")
    async def _load_active_rules(self) -> None:
        """加载启用的告警规则"""
        db = await self._get_db()

        async for doc in db[self._rules_collection].find({"enabled": True}):
            rule = self._doc_to_rule(doc)
            if rule.id:
                self._active_rules[rule.id] = rule

    def _doc_to_rule(self, doc: Dict) -> AlertRule:
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

    @async_handle_errors_false(error_message="创建规则失败")
    async def create_rule(self, rule: AlertRule) -> Optional[str]:
        """
        创建告警规则（使用装饰器，返回False表示失败）

        装饰器自动处理异常并记录日志
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

    @async_handle_errors_none(error_message="获取规则失败")
    async def get_rules(
        self,
        enabled_only: bool = False,
        category: Optional[AlertCategory] = None
    ) -> List[AlertRule]:
        """
        获取告警规则列表（使用装饰器，返回None表示失败）
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

    @async_handle_errors_false(error_message="更新规则失败")
    async def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新告警规则（使用装饰器，返回False表示失败）

        装饰器自动处理异常并记录日志
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
            updates["channels"] = [c.value if isinstance(c, NotificationChannel) else c for c in updates["channels"]]

        updates["updated_at"] = datetime.now().isoformat()

        result = await db[self._rules_collection].update_one(
            {"_id": rule_id},
            {"$set": updates}
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

    @async_handle_errors_false(error_message="删除规则失败")
    async def delete_rule(self, rule_id: str) -> bool:
        """
        删除告警规则（使用装饰器，返回False表示失败）

        装饰器自动处理异常并记录日志
        """
        if not self._initialized:
            await self.initialize()

        db = await self._get_db()

        result = await db[self._rules_collection].delete_one({"_id": rule_id})

        if result.deleted_count > 0:
            # 从活动规则中移除
            self._active_rules.pop(rule_id, None)
            return True

        return False

    @async_handle_errors_none(error_message="触发告警失败")
    async def trigger_alert(
        self,
        rule_id: str,
        metric_value: float,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        触发告警（使用装饰器，返回None表示失败）

        装饰器自动处理异常并记录日志
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
            "message": message or rule.message_template or f"Alert triggered: {rule.condition}",
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

    @async_handle_errors_none(error_message="冷却检查失败")
    async def _is_in_cooldown(self, rule_id: str) -> bool:
        """
        检查规则是否在冷却期内（使用装饰器，返回None表示失败）
        """
        db = await self._get_db()

        recent_alert = await db[self._alerts_collection].find_one(
            {
                "rule_id": rule_id,
                "triggered_at": {
                    "$gte": datetime.now() - timedelta(seconds=300)  # 默认5分钟冷却
                }
            }
        )

        return recent_alert is not None

    @async_handle_errors_none(error_message="设置冷却时间失败")
    async def _set_cooldown(self, rule_id: str) -> None:
        """
        设置冷却时间（通过记录最近告警时间实现）

        装饰器自动处理异常
        """
        # 冷却由MongoDB查询中的时间窗口控制
        # 这里只是为了标记最近的告警
        pass

    @async_handle_errors_none
    async def _send_notifications(
        self,
        alert_data: Dict[str, Any],
        rule: AlertRule
    ) -> None:
        """
        发送告警通知（使用装饰器，返回None表示失败）

        装饰器自动处理所有异常
        """
        for channel in rule.channels:
            if channel == NotificationChannel.IN_APP:
                await self._send_in_app_notification(alert_data)
            elif channel == NotificationChannel.EMAIL:
                await self._send_email_notification(alert_data, rule)
            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook_notification(alert_data, rule)

    @async_handle_errors_none
    async def _send_in_app_notification(self, alert_data: Dict[str, Any]) -> None:
        """发送应用内通知"""
        db = await self._get_db()

        notification = {
            "type": "alert",
            "title": alert_data["title"],
            "message": alert_data["message"],
            "level": alert_data["level"],
            "alert_id": str(alert_data.get("_id", "")),
            "created_at": datetime.now().isoformat(),
            "read": False,
        }

        await db["notifications"].insert_one(notification)

    @async_handle_errors_none
    async def _send_email_notification(
        self,
        alert_data: Dict[str, Any],
        rule: AlertRule
    ) -> None:
        """
        发送邮件通知（使用装饰器，返回None表示失败）

        装饰器自动处理异常
        """
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.utils import formataddr

            config_mgr = get_config_manager()
            smtp_host = config_mgr.get("SMTP_HOST", "smtp.gmail.com")
            smtp_port = config_mgr.get("SMTP_PORT", 587)
            smtp_user = config_mgr.get("SMTP_USER", "")
            smtp_password = config_mgr.get("SMTP_PASSWORD", "")
            smtp_from = config_mgr.get("SMTP_FROM", "noreply@tradingagents.cn")
            smtp_to = config_mgr.get("SMTP_TO", "admin@tradingagents.cn")

            if not smtp_user or not smtp_password:
                logger.warning("⚠️ SMTP配置不完整，跳过邮件发送")
                return

            subject = f"[{alert_data['level']}] {alert_data['title']}"

            # 邮件正文
            body = f"""
告警详情：
━━━━━━━━━━━━━━━━━━━━━━━━
标题：{alert_data['title']}
级别：{alert_data['level']}
类别：{alert_data['category']}
时间：{alert_data.get('created_at', 'N/A')}
消息：
{alert_data.get('message', '无详细消息')}
━━━━━━━━━━━━━━━━━━━━━━━━
此邮件由TradingAgents-CN告警系统自动发送，请勿回复。
"""

            # 创建邮件对象
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = formataddr(("TradingAgents告警系统", smtp_from))
            msg["To"] = smtp_to

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

    @async_handle_errors_none
    async def _send_webhook_notification(
        self,
        alert_data: Dict[str, Any],
        rule: AlertRule
    ) -> None:
        """
        发送Webhook通知（使用装饰器，返回None表示失败）

        装饰器自动处理异常
        """
        try:
            import httpx

            config_mgr = get_config_manager()
            webhook_url = config_mgr.get("ALERT_WEBHOOK_URL", "")

            if not webhook_url:
                logger.warning("⚠️ Webhook URL未配置，跳过Webhook通知")
                return

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
                            f"(尝试 {attempt + 1}/{max_retries}), "
                            f"状态码: {response.status_code}"
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

        except ImportError:
            logger.error("❌ 缺少HTTP依赖库httpx")
        except Exception as e:
            logger.error(f"❌ 发送Webhook通知失败: {e}", exc_info=True)

    @async_handle_errors_none
    async def _add_to_history(
        self,
        alert_id: str,
        action: str,
        data: Dict[str, Any]
    ) -> None:
        """
        添加告警历史记录（使用装饰器）

        装饰器自动处理异常
        """
        db = await self._get_db()

        history_entry = {
            "alert_id": alert_id,
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }

        await db[self._history_collection].insert_one(history_entry)


# ==================== 全局实例管理 ====================

_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取AlertManager单例"""
    global _alert_manager
    if _alert_manager is None:
        # 注意：这里需要在实际使用时传入scheduler实例
        # _alert_manager = AlertManager(scheduler)
        pass
    return _alert_manager
