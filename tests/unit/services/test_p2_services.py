# -*- coding: utf-8 -*-
"""
P2 Services Unit Tests

Tests for:
- DataSyncManager (data_sync_manager.py)
- MetricsCollector (metrics_collector.py)
- AlertManager (alert_manager.py)
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class TestDataSyncManager:
    """DataSyncManager 单元测试"""

    def test_datatype_enum(self):
        """测试数据类型枚举"""
        from app.services.data_sync_manager import DataType

        assert DataType.STOCK_BASICS.value == "stock_basics"
        assert DataType.STOCK_DAILY.value == "stock_daily"
        assert DataType.FUNDAMENTALS.value == "fundamentals"
        assert DataType.NEWS.value == "news"
        assert DataType.SOCIAL_MEDIA.value == "social_media"

    def test_syncstatus_enum(self):
        """测试同步状态枚举"""
        from app.services.data_sync_manager import SyncStatus

        assert SyncStatus.IDLE.value == "idle"
        assert SyncStatus.RUNNING.value == "running"
        assert SyncStatus.COMPLETED.value == "completed"
        assert SyncStatus.FAILED.value == "failed"
        assert SyncStatus.CANCELLED.value == "cancelled"

    def test_syncjob_creation(self):
        """测试同步作业创建"""
        from app.services.data_sync_manager import SyncJob, DataType, SyncStatus

        job = SyncJob(
            id="test_job_001",
            data_type=DataType.STOCK_BASICS,
            status=SyncStatus.RUNNING,
            total_records=100,
            inserted=50,
            updated=30,
            errors=5,
        )

        assert job.id == "test_job_001"
        assert job.data_type == DataType.STOCK_BASICS
        assert job.status == SyncStatus.RUNNING
        assert job.total_records == 100
        assert job.inserted == 50
        assert job.updated == 30
        assert job.errors == 5

    def test_syncjob_default_values(self):
        """测试同步作业默认值"""
        from app.services.data_sync_manager import SyncJob, DataType, SyncStatus

        job = SyncJob(
            id="test_job", data_type=DataType.STOCK_DAILY, status=SyncStatus.IDLE
        )

        assert job.total_records == 0
        assert job.inserted == 0
        assert job.updated == 0
        assert job.errors == 0
        assert job.started_at is None
        assert job.finished_at is None

    def test_syncmanager_import(self):
        """测试同步管理器导入"""
        from app.services.data_sync_manager import get_sync_manager, DataSyncManager

        mgr = get_sync_manager()
        assert isinstance(mgr, DataSyncManager)

    @pytest.mark.asyncio
    async def test_get_sync_status_empty(self):
        """测试获取空同步状态"""
        from app.services.data_sync_manager import get_sync_manager, DataType

        mgr = get_sync_manager()
        # Mock MongoDB to avoid connection errors
        with patch.object(mgr, "_get_db", new_callable=AsyncMock) as mock_get_db:
            mock_db = MagicMock()
            mock_collection = MagicMock()
            mock_collection.find_one = AsyncMock(return_value=None)
            mock_db.__getitem__ = MagicMock(return_value=mock_collection)
            mock_get_db.return_value = mock_db

            status = await mgr.get_sync_status(DataType.STOCK_BASICS)
            assert status["status"] == "never_run"
            assert status["data_type"] == "stock_basics"

    @pytest.mark.asyncio
    async def test_trigger_sync_returns_job_id(self):
        """测试触发同步返回作业ID"""
        from app.services.data_sync_manager import get_sync_manager, DataType

        mgr = get_sync_manager()

        with patch.object(mgr, "_get_db", new_callable=AsyncMock):
            result = await mgr.trigger_sync(
                DataType.STOCK_BASICS, force=False, created_by="test_user"
            )

            assert result["success"] is True
            assert "job_id" in result
            assert result["job_id"].startswith("sync_stock_basics_")


class TestMetricsCollector:
    """MetricsCollector 单元测试"""

    def test_metrictype_enum(self):
        """测试指标类型枚举"""
        from app.services.metrics_collector import MetricType

        assert MetricType.SYSTEM_CPU.value == "system_cpu"
        assert MetricType.SYSTEM_MEMORY.value == "system_memory"
        assert MetricType.APP_REQUEST_COUNT.value == "app_request_count"
        assert MetricType.APP_REQUEST_LATENCY.value == "app_request_latency"
        assert MetricType.ANALYSIS_COUNT.value == "analysis_count"
        assert MetricType.TOKEN_USAGE.value == "token_usage"

    def test_metricpoint_creation(self):
        """测试指标点创建"""
        from app.services.metrics_collector import MetricPoint, MetricType

        point = MetricPoint(
            metric_type=MetricType.APP_REQUEST_LATENCY,
            value=0.5,
            tags={"endpoint": "/api/test"},
            source="test",
        )

        assert point.metric_type == MetricType.APP_REQUEST_LATENCY
        assert point.value == 0.5
        assert point.tags["endpoint"] == "/api/test"
        assert point.source == "test"
        assert point.timestamp is not None

    def test_metricssummary_creation(self):
        """测试指标汇总创建"""
        from app.services.metrics_collector import MetricsSummary, MetricType

        summary = MetricsSummary(
            metric_type=MetricType.APP_REQUEST_COUNT,
            count=100,
            sum=50.0,
            avg=0.5,
            min=0.1,
            max=1.0,
            last_value=0.3,
        )

        assert summary.metric_type == MetricType.APP_REQUEST_COUNT
        assert summary.count == 100
        assert summary.avg == 0.5
        assert summary.last_value == 0.3

    def test_metricscollector_import(self):
        """测试指标收集器导入"""
        from app.services.metrics_collector import (
            get_metrics_collector,
            MetricsCollector,
        )

        collector = get_metrics_collector()
        assert isinstance(collector, MetricsCollector)

    def test_record_analysis_metric_function(self):
        """测试便捷函数record_analysis_metric"""
        from app.services.metrics_collector import record_analysis_metric

        # 函数应该存在且可调用
        assert callable(record_analysis_metric)

    def test_record_request_metric_function(self):
        """测试便捷函数record_request_metric"""
        from app.services.metrics_collector import record_request_metric

        # 函数应该存在且可调用
        assert callable(record_request_metric)


class TestAlertManager:
    """AlertManager 单元测试"""

    def test_alertlevel_enum(self):
        """测试告警级别枚举"""
        from app.services.alert_manager import AlertLevel

        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.ERROR.value == "error"
        assert AlertLevel.CRITICAL.value == "critical"

    def test_alertcategory_enum(self):
        """测试告警类别枚举"""
        from app.services.alert_manager import AlertCategory

        assert AlertCategory.SYSTEM.value == "system"
        assert AlertCategory.PERFORMANCE.value == "performance"
        assert AlertCategory.DATA.value == "data"
        assert AlertCategory.SECURITY.value == "security"
        assert AlertCategory.BUSINESS.value == "business"

    def test_alertstatus_enum(self):
        """测试告警状态枚举"""
        from app.services.alert_manager import AlertStatus

        assert AlertStatus.ACTIVE.value == "active"
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.SUPPRESSED.value == "suppressed"

    def test_notificationchannel_enum(self):
        """测试通知渠道枚举"""
        from app.services.alert_manager import NotificationChannel

        assert NotificationChannel.IN_APP.value == "in_app"
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.WEBHOOK.value == "webhook"

    def testalertrule_creation(self):
        """测试告警规则创建"""
        from app.services.alert_manager import AlertRule, AlertLevel, AlertCategory

        rule = AlertRule(
            name="High CPU Usage",
            category=AlertCategory.SYSTEM,
            level=AlertLevel.WARNING,
            condition="cpu_percent > 90",
            threshold=90.0,
        )

        assert rule.name == "High CPU Usage"
        assert rule.category == AlertCategory.SYSTEM
        assert rule.level == AlertLevel.WARNING
        assert rule.condition == "cpu_percent > 90"
        assert rule.threshold == 90.0
        assert rule.enabled is True
        assert rule.cooldown_seconds == 300

    def testalertrule_with_channels(self):
        """测试告警规则（带通知渠道）"""
        from app.services.alert_manager import (
            AlertRule,
            AlertLevel,
            AlertCategory,
            NotificationChannel,
        )

        rule = AlertRule(
            name="Disk Space Low",
            category=AlertCategory.SYSTEM,
            level=AlertLevel.ERROR,
            condition="disk_percent > 95",
            threshold=95.0,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
        )

        assert len(rule.channels) == 2
        assert NotificationChannel.IN_APP in rule.channels
        assert NotificationChannel.EMAIL in rule.channels

    def testalert_creation(self):
        """测试告警创建"""
        from app.services.alert_manager import (
            Alert,
            AlertLevel,
            AlertCategory,
            AlertStatus,
        )

        alert = Alert(
            category=AlertCategory.SYSTEM,
            level=AlertLevel.WARNING,
            title="High CPU Usage",
            message="CPU usage has exceeded 90%",
            metric_value=95.0,
            threshold=90.0,
        )

        assert alert.category == AlertCategory.SYSTEM
        assert alert.level == AlertLevel.WARNING
        assert alert.title == "High CPU Usage"
        assert alert.status == AlertStatus.ACTIVE
        assert alert.metric_value == 95.0
        assert alert.threshold == 90.0

    def testalert_default_values(self):
        """测试告警默认值"""
        from app.services.alert_manager import (
            Alert,
            AlertLevel,
            AlertCategory,
            AlertStatus,
        )

        alert = Alert(category=AlertCategory.PERFORMANCE, level=AlertLevel.INFO)

        assert alert.id is None
        assert alert.rule_id is None
        assert alert.status == AlertStatus.ACTIVE
        assert alert.title == ""
        assert alert.message == ""
        assert alert.metric_value is None
        assert alert.triggered_at is None

    def testalertmanager_import(self):
        """测试告警管理器导入"""
        from app.services.alert_manager import get_alert_manager, AlertManager

        mgr = get_alert_manager()
        assert isinstance(mgr, AlertManager)


class TestP2ServicesIntegration:
    """P2服务集成测试"""

    def test_all_services_singleton(self):
        """测试所有服务都是单例"""
        from app.services.data_sync_manager import get_sync_manager
        from app.services.metrics_collector import get_metrics_collector
        from app.services.alert_manager import get_alert_manager

        # 同一实例
        sync1 = get_sync_manager()
        sync2 = get_sync_manager()
        assert sync1 is sync2

        metrics1 = get_metrics_collector()
        metrics2 = get_metrics_collector()
        assert metrics1 is metrics2

        alert1 = get_alert_manager()
        alert2 = get_alert_manager()
        assert alert1 is alert2

    def test_all_services_different_types(self):
        """测试服务类型不同"""
        from app.services.data_sync_manager import DataSyncManager
        from app.services.metrics_collector import MetricsCollector
        from app.services.alert_manager import AlertManager

        from app.services.data_sync_manager import get_sync_manager
        from app.services.metrics_collector import get_metrics_collector
        from app.services.alert_manager import get_alert_manager

        assert isinstance(get_sync_manager(), DataSyncManager)
        assert isinstance(get_metrics_collector(), MetricsCollector)
        assert isinstance(get_alert_manager(), AlertManager)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
