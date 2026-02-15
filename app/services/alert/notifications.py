# -*- coding: utf-8 -*-
"""
Alert通知系统

处理告警通知的发送，包括应用内通知、邮件和Webhook。
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.unified_config_service import get_config_manager
from app.utils.error_handler import async_handle_errors_none
from app.services.alert.models import AlertRule, NotificationChannel

logger = logging.getLogger(__name__)


class NotificationService:
    """告警通知服务"""

    def __init__(self, db: AsyncIOMotorDatabase):
        """
        初始化通知服务

        Args:
            db: MongoDB数据库实例
        """
        self._db = db
        self._alerts_collection = "alerts"
        self._notifications_collection = "notifications"

    @async_handle_errors_none(error_message="发送通知失败")
    async def send_notifications(
        self, alert_data: Dict[str, Any], rule: AlertRule
    ) -> None:
        """发送告警通知"""
        for channel in rule.channels:
            if channel == NotificationChannel.IN_APP:
                await self._send_in_app_notification(alert_data)
            elif channel == NotificationChannel.EMAIL:
                await self._send_email_notification(alert_data, rule)
            elif channel == NotificationChannel.WEBHOOK:
                await self._send_webhook_notification(alert_data, rule)

    @async_handle_errors_none(error_message="发送应用内通知失败")
    async def _send_in_app_notification(self, alert_data: Dict[str, Any]) -> None:
        """发送应用内通知"""
        notification = {
            "type": "alert",
            "title": alert_data["title"],
            "message": alert_data["message"],
            "level": alert_data["level"],
            "alert_id": str(alert_data.get("_id", "")),
            "created_at": datetime.now().isoformat(),
            "read": False,
        }

        await self._db[self._notifications_collection].insert_one(notification)

    @async_handle_errors_none(error_message="发送邮件通知失败")
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

    @async_handle_errors_none(error_message="发送Webhook通知失败")
    async def _send_webhook_notification(
        self, alert_data: Dict[str, Any], rule: AlertRule
    ) -> None:
        """发送Webhook通知

        使用HTTP POST发送告警通知到配置的Webhook URL
        支持重试机制、超时控制和错误处理
        """
        try:
            import httpx

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
