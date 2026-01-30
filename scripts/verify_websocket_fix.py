# -*- coding: utf-8 -*-
"""
WebSocket 修复验证脚本

功能:
1. 查询当前 WebSocket 连接状态
2. 生成验证报告
3. 检查前后端日志

运行方式:
    python scripts/verify_websocket_fix.py
"""

import requests
import json
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_URL = "http://localhost:8000"


def check_websocket_stats():
    """检查 WebSocket 连接统计"""
    print("=" * 70)
    print("🔍 WebSocket 连接状态检查")
    print("=" * 70)

    try:
        response = requests.get(f"{API_URL}/api/ws/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()

            print(f"\n📊 统计信息:")
            print(f"  总用户数: {stats.get('total_users', 0)}")
            print(f"  总连接数: {stats.get('total_connections', 0)}")

            users = stats.get("users", {})
            if users:
                print(f"\n👥 用户连接详情:")
                for user_id, count in users.items():
                    status = "✅ 正常" if count <= 3 else f"⚠️ 超标 (限制: 3)"
                    print(f"  - {user_id}: {count} 个连接 {status}")
            else:
                print(f"\n  暂无用户连接")

            return stats
        else:
            print(f"❌ 查询失败: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 请求错误: {e}")
        print(f"💡 请确保后端服务已启动: {API_URL}")
        return None


def check_logs_for_websocket():
    """检查日志中的 WebSocket 相关记录"""
    print("\n" + "=" * 70)
    print("📋 日志检查 (最近20条 WebSocket 相关)")
    print("=" * 70)

    log_file = "error.log"
    if not os.path.exists(log_file):
        print(f"⚠️ 未找到日志文件: {log_file}")
        return

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # 查找 WebSocket 相关日志
        ws_logs = []
        for line in lines:
            if "[WS]" in line or "websocket" in line.lower():
                try:
                    log_entry = json.loads(line.strip())
                    ws_logs.append(log_entry)
                except:
                    pass

        # 显示最近20条
        recent_logs = ws_logs[-20:] if len(ws_logs) > 20 else ws_logs

        if recent_logs:
            print(f"\n找到 {len(recent_logs)} 条 WebSocket 日志:\n")
            for log in recent_logs:
                time = log.get("time", "N/A")
                level = log.get("level", "INFO")
                message = log.get("message", "")
                print(f"[{time}] {level}: {message}")
        else:
            print("\n  未找到 WebSocket 相关日志")
            print("  💡 请刷新前端页面触发 WebSocket 连接")

    except Exception as e:
        print(f"❌ 读取日志失败: {e}")


def verify_fix():
    """验证修复效果"""
    print("\n" + "=" * 70)
    print("✅ 修复验证报告")
    print("=" * 70)

    stats = check_websocket_stats()

    if stats is None:
        print("\n❌ 无法获取 WebSocket 状态，请确保后端服务已启动")
        return False

    total_connections = stats.get("total_connections", 0)
    users = stats.get("users", {})

    issues = []

    # 检查每个用户的连接数
    for user_id, count in users.items():
        if count > 3:
            issues.append(f"用户 {user_id} 连接数超标: {count} > 3")

    # 检查总体情况
    if total_connections > 10:
        issues.append(f"总连接数过多: {total_connections}")

    print(f"\n📊 验证结果:")
    print(f"  当前总连接数: {total_connections}")
    print(f"  当前用户数: {len(users)}")

    if issues:
        print(f"\n⚠️ 发现问题 ({len(issues)} 个):")
        for issue in issues:
            print(f"  - {issue}")
        print(f"\n💡 建议:")
        print(f"  1. 刷新前端页面查看新的日志格式")
        print(f"  2. 检查浏览器控制台是否有 [WS] 日志")
        print(f"  3. 运行监控脚本: python scripts/monitor_websocket.py")
        return False
    else:
        print(f"\n✅ 当前状态正常!")
        if total_connections == 0:
            print(f"\n💡 提示: 当前没有活跃连接")
            print(f"  请刷新前端页面并查看日志")
        return True


def print_manual_test_guide():
    """打印手动测试指南"""
    print("\n" + "=" * 70)
    print("🧪 手动测试指南")
    print("=" * 70)

    print("""
测试 1: 正常连接
  1. 打开浏览器开发者工具 (F12)
  2. 切换到 Console 标签
  3. 刷新页面 (Ctrl+R)
  4. 预期看到:
     [WS] 页面生命周期监听已添加
     [WS] 🔌 创建新连接 #1
     [WS] ✅ 连接成功 #1 (耗时: xxms)

测试 2: 页面刷新
  1. 在控制台看到连接成功后，刷新页面
  2. 预期看到:
     [WS] ❌ 连接关闭 #1: ... 手动断开: false
     [WS] 🔌 创建新连接 #2
  3. 后端日志应显示旧连接断开，新连接创建

测试 3: 手动断开
  1. 在浏览器控制台执行:
     notificationsStore.disconnect()
  2. 预期看到:
     [WS] 🔌 手动断开连接...
     [WS] 手动断开连接，停止重连
  3. 不应再看到重连日志

测试 4: 长时间运行
  1. 保持页面打开 10 分钟
  2. 观察连接数是否保持稳定
  3. 运行监控脚本:
     python scripts/monitor_websocket.py --interval 10
    """)


def main():
    print("\n" + "=" * 70)
    print("🔍 WebSocket 修复验证工具")
    print(f"🕐 当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 检查 WebSocket 状态
    success = verify_fix()

    # 检查日志
    check_logs_for_websocket()

    # 打印手动测试指南
    print_manual_test_guide()

    print("\n" + "=" * 70)
    if success:
        print("✅ 验证完成 - 当前状态正常")
    else:
        print("⚠️ 验证完成 - 请按照手动测试指南进一步检查")
    print("=" * 70)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
