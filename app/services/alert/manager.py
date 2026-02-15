# -*- coding: utf-8 -*-
"""
AlertManager核心管理器

协调告警系统的所有功能，提供统一的告警管理接口。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_mongo_db
from app.utils.error_handler import async_handle_errors_none
from app.services.alert.models import (
    AlertRule,
    Alert,
    AlertCategory,
    AlertLevel,
    NotificationChannel,
)
from app.services.alert.rules import RuleService
from app.services.alert.notifications import NotificationService
from app.services.alert.statistics import StatisticsService

logger = logging.getLogger(__name__)


class AlertManager:
    """
    告警管理器

    提供完整的告警创建、通知和管理功能。
    """

    def __init__(self):
        self._db: Optional[AsyncIOMotorDatabase] = None
        self._alerts_collection = "alerts"
        self._lock = asyncio.Lock()
        self._initialized: bool = False

        # 子服务
        self._rule_service: Optional[RuleService] = None
        self._notification_service: Optional[NotificationService] = None
        self._statistics_service: Optional[StatisticsService] = None

    async def _get_db(self) -> AsyncIOMotorDatabase:
        """获取MongoDB连接"""
        if self._db is None:
            self._db = get_mongo_db()
        return self._db

    @async_handle_errors_none(error_message="初始化AlertManager失败")
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
            await db["alert_rules"].create_index("name", unique=True)
            await db["alert_rules"].create_index("enabled")

            # 创建历史记录集合索引
            await db["alert_history"].create_index(
                [("alert_id", 1), ("timestamp", -1)]
            )

            # 初始化子服务
            self._rule_service = RuleService(db)
            self._notification_service = NotificationService(db)
            self._statistics_service = StatisticsService(db)

            # 加载启用的规则
            await self._rule_service.load_active_rules()

            self._initialized = True
            logger.info("AlertManager initialized")

    # ==================== 规则管理接口 ====================

    async def create_rule(self, rule: AlertRule) -> str:
        """
        创建告警规则

        Args:
            rule: 告警规则

        Returns:
            创建的规则ID

        Raises:
            Exception: 创建规则失败时抛出异常
        """
        if not self._initialized:
            await self.initialize()

        return await self._rule_service.create_rule(rule)

    async def get_rules(
        self,
        enabled_only: bool = False,
        category: Optional[AlertCategory] = None,
    ) -> List[AlertRule]:
        """
        获取告警规则列表

        Args:
            enabled_only: 只返回启用的规则
            category: 按类别过滤

        Returns:
            告警规则列表（失败时返回空列表）
        """
        if not self._initialized:
            await self.initialize()

        return await self._rule_service.get_rules(enabled_only, category)

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

        return await self._rule_service.update_rule(rule_id, updates)

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

        return await self._rule_service.delete_rule(rule_id)

    # ==================== 告警管理接口 ====================

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
            告警ID（失败时返回None）
        """
        try:
            if not self._initialized:
                await self.initialize()

            # 检查规则是否存在
            if not self._rule_service.is_rule_active(rule_id):
                logger.warning(f"Alert rule {rule_id} not found or disabled")
                return None

            rule = self._rule_service.get_active_rule(rule_id)
            if not rule:
                logger.warning(f"Alert rule {rule_id} not found in active rules")
                return None

            # 检查是否在冷却期内
            if await self._statistics_service.is_in_cooldown(rule_id):
                logger.debug(f"Alert {rule_id} is in cooldown, skipping")
                return None

            db = await self._get_db()

            now = __import__("datetime").datetime.now().isoformat()
            alert_data = {
                "rule_id": rule_id,
                "rule_name": rule.name,
                "category": rule.category.value,
                "level": rule.level.value,
                "status": "active",
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
            await self._statistics_service.add_to_history(
                alert_id, "triggered", alert_data
            )

            # 设置冷却时间
            await self._statistics_service.set_cooldown(rule_id)

            # 发送通知
            await self._notification_service.send_notifications(alert_data, rule)

            return alert_id
        except Exception as e:
            logger.error(f"触发告警失败: {e}", exc_info=True)
            return None

    # ==================== 统计和查询接口 ====================

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
            活跃告警列表（失败时返回空列表）
        """
        if not self._initialized:
            await self.initialize()

        return await self._statistics_service.get_active_alerts(
            level, category, limit
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

        return await self._statistics_service.acknowledge_alert(alert_id, user_id)

    async def resolve_alert(
        self,
        alert_id: str,
        user_id: Optional[str] = None,
        notes: Optional[str] = None,
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

        return await self._statistics_service.resolve_alert(
            alert_id, user_id, notes
        )

    async def get_alert_history(
        self, alert_id: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取告警历史

        Args:
            alert_id: 告警ID
            limit: 返回数量限制

        Returns:
            历史记录列表（失败时返回空列表）
        """
        if not self._initialized:
            await self.initialize()

        return await self._statistics_service.get_alert_history(alert_id, limit)

    async def cleanup_old_alerts(self, days: int = 30) -> int:
        """
        清理旧的已解决告警

        Args:
            days: 保留天数

        Returns:
            删除的记录数量（失败时返回0）
        """
        if not self._initialized:
            await self.initialize()

        return await self._statistics_service.cleanup_old_alerts(days)

    async def get_statistics(self) -> Dict[str, Any]:
        """
        获取告警统计信息

        Returns:
            统计信息（失败时返回空字典）
        """
        if not self._initialized:
            await self.initialize()

        stats = await self._statistics_service.get_statistics()
        stats["active_rules_count"] = self._rule_service.active_rules_count
        return stats


# ==================== 全局实例管理 ====================

_alert_manager: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """获取AlertManager单例"""
    global _alert_manager
    if _alert_manager is None:
        _alert_manager = AlertManager()
    return _alert_manager
