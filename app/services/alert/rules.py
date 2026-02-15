# -*- coding: utf-8 -*-
"""
Alert规则管理

处理告警规则的创建、查询、更新和删除。
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.utils.error_handler import async_handle_errors_false
from app.services.alert.models import AlertRule, AlertCategory, AlertLevel, doc_to_rule

logger = logging.getLogger(__name__)


class RuleService:
    """告警规则服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        初始化规则服务

        Args:
            db: MongoDB数据库实例
        """
        self._db = db
        self._rules_collection = "alert_rules"
        self._active_rules: Dict[str, AlertRule] = {}

    async def load_active_rules(self) -> None:
        """加载启用的告警规则"""
        try:
            async for doc in self._db[self._rules_collection].find({"enabled": True}):
                rule = doc_to_rule(doc)
                if rule.id:
                    self._active_rules[rule.id] = rule
        except Exception as e:
            logger.error(f"加载活跃规则失败: {e}", exc_info=True)

    def get_active_rule(self, rule_id: str) -> Optional[AlertRule]:
        """获取活跃规则"""
        return self._active_rules.get(rule_id)

    def is_rule_active(self, rule_id: str) -> bool:
        """检查规则是否活跃"""
        return rule_id in self._active_rules

    @property
    def active_rules_count(self) -> int:
        """获取活跃规则数量"""
        return len(self._active_rules)

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

        result = await self._db[self._rules_collection].insert_one(rule_data)
        rule.id = str(result.inserted_id)
        rule.created_at = now
        rule.updated_at = now

        # 如果规则已启用，添加到活动规则
        if rule.enabled and rule.id:
            self._active_rules[rule.id] = rule

        return rule.id

    async def get_rules(
        self,
        enabled_only: bool = False,
        category: Optional[AlertCategory] = None
    ) -> List[AlertRule]:
        """
        获取告警规则列表

        Args:
            enabled_only: 只返回启用的规则
            category: 按类别过滤

        Returns:
            告警规则列表（失败时返回空列表）
        """
        try:
            query = {}
            if enabled_only:
                query["enabled"] = True
            if category:
                query["category"] = category.value

            rules = []
            async for doc in self._db[self._rules_collection].find(query):
                rules.append(doc_to_rule(doc))

            return rules
        except Exception as e:
            logger.error(f"获取告警规则失败: {e}", exc_info=True)
            return []

    @async_handle_errors_false(error_message="更新告警规则失败")
    async def update_rule(self, rule_id: str, updates: Dict) -> bool:
        """
        更新告警规则

        Args:
            rule_id: 规则ID
            updates: 更新内容

        Returns:
            是否更新成功
        """
        # 转换枚举值
        if "category" in updates and isinstance(updates["category"], AlertCategory):
            updates["category"] = updates["category"].value
        if "level" in updates and isinstance(updates["level"], AlertLevel):
            updates["level"] = updates["level"].value
        if "channels" in updates:
            updates["channels"] = [c.value for c in updates["channels"]]

        updates["updated_at"] = datetime.now().isoformat()

        result = await self._db[self._rules_collection].update_one(
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

    @async_handle_errors_false(error_message="删除告警规则失败")
    async def delete_rule(self, rule_id: str) -> bool:
        """
        删除告警规则

        Args:
            rule_id: 规则ID

        Returns:
            是否删除成功
        """
        result = await self._db[self._rules_collection].delete_one({"_id": rule_id})

        if result.deleted_count > 0:
            self._active_rules.pop(rule_id, None)
            return True

        return False
