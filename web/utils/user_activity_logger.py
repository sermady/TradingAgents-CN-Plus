# -*- coding: utf-8 -*-
"""
用户操作行为记录器
记录用户在系统中的各种操作行为，并保存到独立的日志文件中
"""

import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import streamlit as st
from dataclasses import dataclass, asdict
import threading
import os

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("user_activity")


@dataclass
class UserActivity:
    """用户活动记录"""

    timestamp: float
    username: str
    user_role: str
    action_type: str
    action_name: str
    details: Dict[str, Any]
    session_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    page_url: Optional[str] = None
    duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None


class UserActivityLogger:
    """用户操作行为记录器"""

    def __init__(self):
        self.activity_dir = Path(__file__).parent.parent / "data" / "user_activities"
        self.activity_dir.mkdir(parents=True, exist_ok=True)

        # 线程锁，确保文件写入安全
        self._lock = threading.Lock()

        # 活动类型定义
        self.activity_types = {
            "auth": "认证相关",
            "analysis": "股票分析",
            "config": "配置管理",
            "navigation": "页面导航",
            "data_export": "数据导出",
            "user_management": "用户管理",
            "system": "系统操作",
        }

        logger.info(f"✅ 用户活动记录器初始化完成")
        logger.info(f"📁 活动记录目录: {self.activity_dir}")

    def _get_activity_file_path(self, date: Optional[str] = None) -> Path:
        """获取活动记录文件路径"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        return self.activity_dir / f"user_activities_{date}.jsonl"

    def _get_session_id(self) -> str:
        """获取会话ID"""
        if "session_id" not in st.session_state:
            st.session_state.session_id = (
                f"session_{int(time.time())}_{id(st.session_state)}"
            )
        return st.session_state.session_id

    def _get_user_info(self) -> Dict[str, str]:
        """获取当前用户信息"""
        user_info = st.session_state.get("user_info")
        if user_info is None:
            user_info = {}
        return {
            "username": user_info.get("username", "anonymous"),
            "role": user_info.get("role", "guest"),
        }

    def _get_request_info(self) -> Dict[str, Optional[str]]:
        """获取请求信息"""
        try:
            # 尝试获取请求信息（在Streamlit中可能有限）
            headers = st.context.headers if hasattr(st.context, "headers") else {}
            return {
                "ip_address": headers.get(
                    "x-forwarded-for", headers.get("remote-addr")
                ),
                "user_agent": headers.get("user-agent"),
                "page_url": st.session_state.get("current_page", "unknown"),
            }
        except:
            return {"ip_address": None, "user_agent": None, "page_url": None}

    def log_activity(
        self,
        action_type: str,
        action_name: str,
        details: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """
        记录用户活动

        Args:
            action_type: 活动类型 (auth, analysis, config, navigation, etc.)
            action_name: 活动名称
            details: 活动详细信息
            success: 操作是否成功
            error_message: 错误信息（如果有）
            duration_ms: 操作耗时（毫秒）
        """
        try:
            user_info = self._get_user_info()
            request_info = self._get_request_info()

            activity = UserActivity(
                timestamp=time.time(),
                username=user_info["username"],
                user_role=user_info["role"],
                action_type=action_type,
                action_name=action_name,
                details=details or {},
                session_id=self._get_session_id(),
                ip_address=request_info["ip_address"],
                user_agent=request_info["user_agent"],
                page_url=request_info["page_url"],
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
            )

            self._write_activity(activity)

        except Exception as e:
            logger.error(f"❌ 记录用户活动失败: {e}")

    def _write_activity(self, activity: UserActivity) -> None:
        """写入活动记录到文件"""
        with self._lock:
            try:
                activity_file = self._get_activity_file_path()

                # 转换为JSON格式
                activity_dict = asdict(activity)
                activity_dict["datetime"] = datetime.fromtimestamp(
                    activity.timestamp
                ).isoformat()

                # 追加写入JSONL格式
                with open(activity_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(activity_dict, ensure_ascii=False) + "\n")

            except Exception as e:
                logger.error(f"❌ 写入活动记录失败: {e}")

    def log_login(
        self, username: str, success: bool, error_message: Optional[str] = None
    ) -> None:
        """记录登录活动"""
        self.log_activity(
            action_type="auth",
            action_name="user_login",
            details={"username": username},
            success=success,
            error_message=error_message,
        )

    def log_logout(self, username: str) -> None:
        """记录登出活动"""
        self.log_activity(
            action_type="auth",
            action_name="user_logout",
            details={"username": username},
        )

    def log_analysis_request(
        self,
        stock_code: str,
        analysis_type: str,
        success: bool = True,
        duration_ms: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """记录股票分析请求"""
        self.log_activity(
            action_type="analysis",
            action_name="stock_analysis",
            details={"stock_code": stock_code, "analysis_type": analysis_type},
            success=success,
            duration_ms=duration_ms,
            error_message=error_message,
        )

    def log_page_visit(
        self, page_name: str, page_params: Optional[Dict[str, Any]] = None
    ) -> None:
        """记录页面访问"""
        self.log_activity(
            action_type="navigation",
            action_name="page_visit",
            details={"page_name": page_name, "page_params": page_params or {}},
        )

    def log_config_change(self, config_type: str, changes: Dict[str, Any]) -> None:
        """记录配置更改"""
        self.log_activity(
            action_type="config",
            action_name="config_update",
            details={"config_type": config_type, "changes": changes},
        )

    def log_data_export(
        self,
        export_type: str,
        data_info: Dict[str, Any],
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """记录数据导出"""
        self.log_activity(
            action_type="data_export",
            action_name="export_data",
            details={"export_type": export_type, "data_info": data_info},
            success=success,
            error_message=error_message,
        )

    def log_user_management(
        self,
        operation: str,
        target_user: str,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> None:
        """记录用户管理操作"""
        self.log_activity(
            action_type="user_management",
            action_name=operation,
            details={"target_user": target_user},
            success=success,
            error_message=error_message,
        )

    def get_user_activities(
        self,
        username: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取用户活动记录

        Args:
            username: 用户名过滤
            start_date: 开始日期
            end_date: 结束日期
            action_type: 活动类型过滤
            limit: 返回记录数限制

        Returns:
            活动记录列表
        """
        activities = []

        try:
            # 确定要查询的日期范围
            if start_date is None:
                start_date = datetime.now() - timedelta(days=7)  # 默认查询最近7天
            if end_date is None:
                end_date = datetime.now()

            # 遍历日期范围内的所有文件
            current_date = start_date.date()
            end_date_only = end_date.date()

            while current_date <= end_date_only:
                date_str = current_date.strftime("%Y-%m-%d")
                activity_file = self._get_activity_file_path(date_str)

                if activity_file.exists():
                    activities.extend(
                        self._read_activities_from_file(
                            activity_file, username, action_type, start_date, end_date
                        )
                    )

                current_date += timedelta(days=1)

            # 按时间戳倒序排序
            activities.sort(key=lambda x: x["timestamp"], reverse=True)

            # 应用限制
            return activities[:limit]

        except Exception as e:
            logger.error(f"❌ 获取用户活动记录失败: {e}")
            return []

    def _read_activities_from_file(
        self,
        file_path: Path,
        username: Optional[str] = None,
        action_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """从文件读取活动记录"""
        activities = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        activity = json.loads(line.strip())

                        # 应用过滤条件
                        if username and activity.get("username") != username:
                            continue

                        if action_type and activity.get("action_type") != action_type:
                            continue

                        activity_time = datetime.fromtimestamp(activity["timestamp"])
                        if start_date and activity_time < start_date:
                            continue
                        if end_date and activity_time > end_date:
                            continue

                        activities.append(activity)

        except Exception as e:
            logger.error(f"❌ 读取活动文件失败 {file_path}: {e}")

        return activities

    def get_activity_statistics(self, days: int = 7) -> Dict[str, Any]:
        """
        获取活动统计信息

        Args:
            days: 统计天数

        Returns:
            统计信息字典
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        activities = self.get_user_activities(
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # 获取更多记录用于统计
        )

        # 统计分析
        stats = {
            "total_activities": len(activities),
            "unique_users": len(set(a["username"] for a in activities)),
            "activity_types": {},
            "daily_activities": {},
            "user_activities": {},
            "success_rate": 0,
            "average_duration": 0,
        }

        # 按类型统计
        for activity in activities:
            action_type = activity.get("action_type", "unknown")
            stats["activity_types"][action_type] = (
                stats["activity_types"].get(action_type, 0) + 1
            )

            # 按用户统计
            username = activity.get("username", "unknown")
            stats["user_activities"][username] = (
                stats["user_activities"].get(username, 0) + 1
            )

            # 按日期统计
            date_str = datetime.fromtimestamp(activity["timestamp"]).strftime(
                "%Y-%m-%d"
            )
            stats["daily_activities"][date_str] = (
                stats["daily_activities"].get(date_str, 0) + 1
            )

        # 成功率统计
        successful_activities = sum(1 for a in activities if a.get("success", True))
        if activities:
            stats["success_rate"] = successful_activities / len(activities) * 100

        # 平均耗时统计
        durations = [
            a.get("duration_ms", 0) for a in activities if a.get("duration_ms")
        ]
        if durations:
            stats["average_duration"] = sum(durations) / len(durations)

        return stats

    def cleanup_old_activities(self, days_to_keep: int = 90) -> int:
        """
        清理旧的活动记录

        Args:
            days_to_keep: 保留天数

        Returns:
            删除的文件数量
        """
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        deleted_count = 0

        try:
            for activity_file in self.activity_dir.glob("user_activities_*.jsonl"):
                # 从文件名提取日期
                try:
                    date_str = activity_file.stem.replace("user_activities_", "")
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")

                    if file_date < cutoff_date:
                        activity_file.unlink()
                        deleted_count += 1
                        logger.info(f"🗑️ 删除旧活动记录: {activity_file.name}")

                except ValueError:
                    # 文件名格式不正确，跳过
                    continue

        except Exception as e:
            logger.error(f"❌ 清理旧活动记录失败: {e}")

        return deleted_count


# 全局用户活动记录器实例
user_activity_logger = UserActivityLogger()
