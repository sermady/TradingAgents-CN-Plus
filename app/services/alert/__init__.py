# -*- coding: utf-8 -*-
"""
Alert告警管理模块

提供完整的告警创建、通知和管理功能。

示例:
    from app.services.alert import AlertManager, get_alert_manager

    # 使用单例
    manager = get_alert_manager()
    await manager.initialize()

    # 或直接实例化
    manager = AlertManager()
    await manager.initialize()
"""

from app.services.alert.manager import AlertManager, get_alert_manager
from app.services.alert.models import (
    AlertLevel,
    AlertStatus,
    AlertCategory,
    NotificationChannel,
    AlertRule,
    Alert,
)

__all__ = [
    # 核心
    "AlertManager",
    "get_alert_manager",
    # 模型
    "AlertLevel",
    "AlertStatus",
    "AlertCategory",
    "NotificationChannel",
    "AlertRule",
    "Alert",
]
