# -*- coding: utf-8 -*-
"""
WebSocket 连接监控脚本

功能:
1. 定期查询 WebSocket 连接统计
2. 检测连接数异常增长
3. 记录连接变化趋势

运行方式:
    python scripts/monitor_websocket.py

依赖:
    - requests 库
    - FastAPI 后端运行中
"""

import requests
import time
import json
from datetime import datetime
from typing import Dict, List, Optional
import argparse

# 配置
API_BASE_URL = "http://localhost:8000"
POLL_INTERVAL = 10  # 轮询间隔（秒）
MAX_HISTORY = 100  # 历史记录最大条数


class WebSocketMonitor:
    """WebSocket 连接监控器"""

    def __init__(self, api_url: str, interval: int = 10):
        self.api_url = api_url
        self.interval = interval
        self.history: List[dict] = []
        self.prev_stats: Optional[dict] = None
        self.alert_threshold = 3  # 连接数超过此值时告警

    def get_stats(self) -> Optional[dict]:
        """获取 WebSocket 连接统计"""
        try:
            response = requests.get(f"{self.api_url}/api/ws/stats", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ 获取统计失败: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ 请求错误: {e}")
            return None

    def analyze_change(self, current: dict) -> List[str]:
        """分析连接变化，返回变化描述列表"""
        changes = []

        if self.prev_stats is None:
            return ["初始连接状态"]

        prev_users = self.prev_stats.get("users", {})
        curr_users = current.get("users", {})

        # 检查新增用户
        for user, count in curr_users.items():
            prev_count = prev_users.get(user, 0)
            if user not in prev_users:
                changes.append(f"🆕 用户 {user} 新增连接 ({count}个)")
            elif count > prev_count:
                changes.append(f"📈 用户 {user} 连接增加 ({prev_count} -> {count})")
            elif count < prev_count:
                changes.append(f"📉 用户 {user} 连接减少 ({prev_count} -> {count})")

        # 检查断开用户
        for user in prev_users:
            if user not in curr_users:
                changes.append(f"❌ 用户 {user} 已断开")

        # 检查总连接数变化
        prev_total = self.prev_stats.get("total_connections", 0)
        curr_total = current.get("total_connections", 0)
        if curr_total > prev_total:
            changes.append(f"📊 总连接数增加 ({prev_total} -> {curr_total})")
        elif curr_total < prev_total:
            changes.append(f"📊 总连接数减少 ({prev_total} -> {curr_total})")

        return changes

    def check_alerts(self, stats: dict) -> List[str]:
        """检查是否需要告警"""
        alerts = []

        total_connections = stats.get("total_connections", 0)
        users = stats.get("users", {})

        # 检查总连接数
        if total_connections > self.alert_threshold:
            alerts.append(
                f"⚠️ 总连接数({total_connections})超过阈值({self.alert_threshold})"
            )

        # 检查单个用户的连接数
        for user, count in users.items():
            if count > 3:
                alerts.append(f"⚠️ 用户 {user} 连接数({count})超过限制(3)")

        return alerts

    def log_status(self, stats: dict):
        """记录当前状态"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = stats.get("total_connections", 0)
        users = stats.get("users", {})

        # 分析变化
        changes = self.analyze_change(stats)
        alerts = self.check_alerts(stats)

        # 打印状态
        print(f"\n{'=' * 60}")
        print(f"🕐 {timestamp}")
        print(f"📊 总连接数: {total}")
        print(f"👥 用户数: {len(users)}")

        if users:
            print(f"📋 用户详情:")
            for user, count in users.items():
                status = "🔴" if count > 3 else "🟢"
                print(f"   {status} {user}: {count}个连接")

        if changes:
            print(f"\n📝 变化:")
            for change in changes:
                print(f"   {change}")

        if alerts:
            print(f"\n🚨 告警:")
            for alert in alerts:
                print(f"   {alert}")

        # 保存历史
        self.history.append(
            {
                "timestamp": timestamp,
                "stats": stats,
                "changes": changes,
                "alerts": alerts,
            }
        )

        # 保持历史记录在限制内
        if len(self.history) > MAX_HISTORY:
            self.history = self.history[-MAX_HISTORY:]

        self.prev_stats = stats

    def run(self, duration: Optional[int] = None):
        """
        运行监控

        Args:
            duration: 运行时长（秒），None 表示无限运行
        """
        print("🚀 启动 WebSocket 连接监控...")
        print(f"📡 API: {self.api_url}")
        print(f"⏱️ 轮询间隔: {self.interval}秒")
        print(f"🎯 告警阈值: {self.alert_threshold}个连接")
        print("-" * 60)

        start_time = time.time()

        try:
            while True:
                # 检查是否超时
                if duration and (time.time() - start_time) > duration:
                    print(f"\n⏹️ 监控已运行 {duration}秒，停止")
                    break

                stats = self.get_stats()
                if stats:
                    self.log_status(stats)

                time.sleep(self.interval)

        except KeyboardInterrupt:
            print("\n\n⏹️ 用户中断监控")


def main():
    parser = argparse.ArgumentParser(description="WebSocket 连接监控")
    parser.add_argument(
        "--url",
        "-u",
        default=f"{API_BASE_URL}",
        help=f"API 基础URL (默认: {API_BASE_URL})",
    )
    parser.add_argument(
        "--interval",
        "-i",
        type=int,
        default=POLL_INTERVAL,
        help=f"轮询间隔秒数 (默认: {POLL_INTERVAL})",
    )
    parser.add_argument(
        "--duration", "-d", type=int, default=None, help="运行时长（秒），默认无限运行"
    )

    args = parser.parse_args()

    monitor = WebSocketMonitor(args.url, args.interval)
    monitor.run(args.duration)


if __name__ == "__main__":
    main()
