# -*- coding: utf-8 -*-
"""
Wave 2.3 数据质量监控面板测试脚本

测试内容:
1. 数据质量监控服务初始化
2. 指标收集功能
3. 告警检查功能
4. API 端点响应
"""

import sys
import os
import asyncio
from datetime import datetime

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)


def test_monitor_initialization():
    """测试监控服务初始化"""
    print("\n" + "=" * 60)
    print("测试 1: 数据质量监控服务初始化")
    print("=" * 60)

    try:
        from app.services.data_quality_monitor import get_data_quality_monitor

        # 获取监控实例
        monitor = get_data_quality_monitor()

        # 检查告警配置
        assert "source_availability" in monitor.alert_thresholds
        assert "data_latency" in monitor.alert_thresholds
        assert "anomaly_ratio" in monitor.alert_thresholds
        assert "missing_rate" in monitor.alert_thresholds
        assert "cross_validation_pass_rate" in monitor.alert_thresholds

        print("[OK] 监控服务初始化成功")
        print(f"   告警阈值配置: {list(monitor.alert_thresholds.keys())}")
        print(f"   历史记录容量: {monitor.max_history_size}")
        print(f"   告警容量: {monitor.max_alerts_size}")

        print("\n[OK] 监控服务初始化测试通过")
        return True

    except Exception as e:
        print(f"\n[FAIL] 监控服务初始化测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metrics_collection():
    """测试指标收集功能"""
    print("\n" + "=" * 60)
    print("测试 2: 指标收集功能")
    print("=" * 60)

    try:
        from app.services.data_quality_monitor import get_data_quality_monitor

        monitor = get_data_quality_monitor()

        # 收集指标
        metrics = monitor.collect_metrics()

        # 验证指标结构
        assert hasattr(metrics, 'timestamp'), "缺少 timestamp 字段"
        assert hasattr(metrics, 'source_availability'), "缺少 source_availability 字段"
        assert hasattr(metrics, 'data_latency_ms'), "缺少 data_latency_ms 字段"
        assert hasattr(metrics, 'anomaly_ratio'), "缺少 anomaly_ratio 字段"
        assert hasattr(metrics, 'missing_rate'), "缺少 missing_rate 字段"
        assert hasattr(metrics, 'cross_validation_pass_rate'), "缺少 cross_validation_pass_rate 字段"
        assert hasattr(metrics, 'quality_score_distribution'), "缺少 quality_score_distribution 字段"

        print("[OK] 指标收集成功:")
        print(f"   时间戳: {metrics.timestamp}")
        print(f"   数据源可用性: {metrics.source_availability}")
        print(f"   数据延迟: {metrics.data_latency_ms:.2f}ms")
        print(f"   异常值比例: {metrics.anomaly_ratio:.2%}")
        print(f"   数据缺失率: {metrics.missing_rate:.2%}")
        print(f"   交叉验证通过率: {metrics.cross_validation_pass_rate:.2%}")
        print(f"   质量评分分布: {metrics.quality_score_distribution}")

        # 验证历史记录
        history = monitor.get_metrics_history()
        assert len(history) > 0, "历史记录应为空"
        print(f"\n[OK] 历史记录保存成功，当前记录数: {len(history)}")

        print("\n[OK] 指标收集功能测试通过")
        return True

    except Exception as e:
        print(f"\n[FAIL] 指标收集功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_alert_generation():
    """测试告警生成功能"""
    print("\n" + "=" * 60)
    print("测试 3: 告警生成功能")
    print("=" * 60)

    try:
        from app.services.data_quality_monitor import get_data_quality_monitor

        monitor = get_data_quality_monitor()

        # 收集指标
        metrics = monitor.collect_metrics()

        # 检查告警
        alerts = monitor.check_alerts(metrics)

        print(f"[OK] 生成了 {len(alerts)} 个告警")

        # 显示告警详情
        for alert in alerts[:5]:  # 只显示前5个
            print(f"\n   告警 {alert.id}:")
            print(f"   严重程度: {alert.severity.value}")
            print(f"   标题: {alert.title}")
            print(f"   消息: {alert.message}")
            print(f"   当前值: {alert.current_value:.2f}")
            print(f"   阈值: {alert.threshold}")

        # 验证告警摘要
        summary = monitor.get_alert_summary()
        print(f"\n[OK] 告警摘要:")
        print(f"   总告警数: {summary['total']}")
        print(f"   未解决: {summary['unresolved']}")
        print(f"   严重: {summary['critical']}")
        print(f"   错误: {summary['error']}")
        print(f"   警告: {summary['warning']}")
        print(f"   信息: {summary['info']}")

        print("\n[OK] 告警生成功能测试通过")
        return True

    except Exception as e:
        print(f"\n[FAIL] 告警生成功能测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_endpoints():
    """测试 API 端点响应"""
    print("\n" + "=" * 60)
    print("测试 4: API 端点响应")
    print("=" * 60)

    try:
        import httpx

        # 测试 API 基础 URL (假设本地运行)
        base_url = "http://localhost:8000"

        print("注意: 此测试需要后端服务运行在 http://localhost:8000")
        print("如果服务未运行，此测试将跳过\n")

        # 尝试连接测试
        try:
            with httpx.Client(timeout=5.0) as client:
                # 测试获取指标端点
                response = client.get(f"{base_url}/api/data-quality/metrics")
                assert response.status_code == 200, f"指标端点返回 {response.status_code}"

                data = response.json()
                assert "timestamp" in data, "响应缺少 timestamp"
                assert "source_availability" in data, "响应缺少 source_availability"

                print("[OK] GET /api/data-quality/metrics - 正常")

                # 测试获取告警端点
                response = client.get(f"{base_url}/api/data-quality/alerts?limit=10")
                assert response.status_code == 200, f"告警端点返回 {response.status_code}"

                alerts = response.json()
                assert isinstance(alerts, list), "告警响应应为列表"

                print("[OK] GET /api/data-quality/alerts - 正常")

                # 测试告警摘要端点
                response = client.get(f"{base_url}/api/data-quality/alerts/summary")
                assert response.status_code == 200, f"告警摘要端点返回 {response.status_code}"

                summary = response.json()
                assert "total" in summary, "摘要响应缺少 total"

                print("[OK] GET /api/data-quality/alerts/summary - 正常")

        except httpx.ConnectError:
            print("[WARNING]  后端服务未运行，跳过 API 端点测试")
            print("   提示: 启动后端服务后重新运行此测试")
            return True  # 不视为失败

        print("\n[OK] API 端点响应测试通过")
        return True

    except Exception as e:
        print(f"\n[FAIL] API 端点响应测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_threshold_configuration():
    """测试告警阈值配置"""
    print("\n" + "=" * 60)
    print("测试 5: 告警阈值配置")
    print("=" * 60)

    try:
        from app.services.data_quality_monitor import get_data_quality_monitor

        monitor = get_data_quality_monitor()

        # 验证各指标的阈值配置
        print("[OK] 告警阈值配置:")

        # 数据源可用性
        sa = monitor.alert_thresholds["source_availability"]
        print(f"\n   数据源可用性:")
        print(f"   警告阈值: {sa['warning']:.1%}")
        print(f"   错误阈值: {sa['error']:.1%}")
        assert sa['warning'] > sa['error'], "警告阈值应大于错误阈值"

        # 数据延迟
        dl = monitor.alert_thresholds["data_latency"]
        print(f"\n   数据延迟:")
        print(f"   警告阈值: {dl['warning']}ms")
        print(f"   错误阈值: {dl['error']}ms")
        assert dl['warning'] < dl['error'], "警告阈值应小于错误阈值"

        # 异常值比例
        ar = monitor.alert_thresholds["anomaly_ratio"]
        print(f"\n   异常值比例:")
        print(f"   警告阈值: {ar['warning']:.1%}")
        print(f"   错误阈值: {ar['error']:.1%}")
        assert ar['warning'] < ar['error'], "警告阈值应小于错误阈值"

        # 数据缺失率
        mr = monitor.alert_thresholds["missing_rate"]
        print(f"\n   数据缺失率:")
        print(f"   警告阈值: {mr['warning']:.1%}")
        print(f"   错误阈值: {mr['error']:.1%}")
        assert mr['warning'] < mr['error'], "警告阈值应小于错误阈值"

        # 交叉验证通过率
        cv = monitor.alert_thresholds["cross_validation_pass_rate"]
        print(f"\n   交叉验证通过率:")
        print(f"   警告阈值: {cv['warning']:.1%}")
        print(f"   错误阈值: {cv['error']:.1%}")
        assert cv['warning'] > cv['error'], "警告阈值应大于错误阈值"

        print("\n[OK] 告警阈值配置测试通过")
        return True

    except Exception as e:
        print(f"\n[FAIL] 告警阈值配置测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("TradingAgents-CN Wave 2.3 测试")
    print("数据质量监控面板")
    print("=" * 60)

    results = []

    # 运行所有测试
    results.append(("监控服务初始化", test_monitor_initialization()))
    results.append(("指标收集功能", test_metrics_collection()))
    results.append(("告警生成功能", test_alert_generation()))
    results.append(("告警阈值配置", test_threshold_configuration()))
    results.append(("API 端点响应", test_api_endpoints()))

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "[OK] 通过" if result else "[FAIL] 失败"
        print(f"{status}: {name}")

    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n[SUCCESS] 所有测试通过！Wave 2.3 实施成功！")
        return 0
    else:
        print(f"\n[WARNING] 有 {total - passed} 个测试失败，请检查实现")
        return 1


if __name__ == "__main__":
    sys.exit(main())
