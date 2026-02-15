# -*- coding: utf-8 -*-
"""
Alert数据模型

定义告警系统的所有数据类和枚举。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


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


def doc_to_rule(doc: Dict[str, Any]) -> AlertRule:
    """将MongoDB文档转换为AlertRule"""
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


def doc_to_alert(doc: Dict[str, Any]) -> Alert:
    """将MongoDB文档转换为Alert"""
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
