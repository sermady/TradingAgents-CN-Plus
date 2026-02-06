# -*- coding: utf-8 -*-
"""
数据质量监控服务 (Phase 2.3)

实时监控数据源和数据质量，提供告警功能
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

from fastapi import HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """告警严重程度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class DataQualityMetrics:
    """数据质量指标"""
    timestamp: datetime
    # 数据源可用性
    source_availability: Dict[str, float]  # {source: availability_rate}
    # 数据延迟
    data_latency_ms: float
    # 异常值比例
    anomaly_ratio: float
    # 缺失率
    missing_rate: float
    # 交叉验证通过率
    cross_validation_pass_rate: float
    # 数据质量评分分布
    quality_score_distribution: Dict[str, int]  # {"A": count, "B": count, ...}


@dataclass
class Alert:
    """告警信息"""
    id: str
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold: float
    resolved: bool = False


class DataQualityMonitor:
    """
    数据质量监控服务

    功能:
    - 实时收集数据质量指标
    - 检查阈值并生成告警
    - 提供历史数据查询
    - 支持配置告警规则
    """

    def __init__(self):
        """初始化监控服务"""
        # 告警配置
        self.alert_thresholds = {
            # 数据源可用性告警阈值
            "source_availability": {
                "warning": 0.90,  # 90%以下告警
                "error": 0.80,    # 80%以下错误
            },
            # 数据延迟告警阈值（毫秒）
            "data_latency": {
                "warning": 2000,   # 2秒以上告警
                "error": 5000,      # 5秒以上错误
            },
            # 异常值比例告警
            "anomaly_ratio": {
                "warning": 0.05,   # 5%以上告警
                "error": 0.10,     # 10%以上错误
            },
            # 数据缺失率告警
            "missing_rate": {
                "warning": 0.10,   # 10%以上告警
                "error": 0.20,     # 20%以上错误
            },
            # 交叉验证通过率告警
            "cross_validation_pass_rate": {
                "warning": 0.90,   # 90%以下告警
                "error": 0.80,     # 80%以下错误
            },
        }

        # 历史指标存储（内存中，实际应用应使用数据库）
        self.metrics_history: List[DataQualityMetrics] = []
        self.max_history_size = 1000  # 最多保存1000条历史记录

        # 告警历史
        self.alerts: List[Alert] = []
        self.max_alerts_size = 500

    def collect_metrics(self) -> DataQualityMetrics:
        """
        收集当前数据质量指标

        Returns:
            DataQualityMetrics: 当前指标
        """
        try:
            from tradingagents.dataflows.data_source_manager import DataSourceManager

            manager = DataSourceManager()

            # 1. 收集数据源可用性
            source_availability = self._collect_source_availability(manager)

            # 2. 收集数据延迟（模拟，实际应从日志统计）
            data_latency_ms = self._estimate_data_latency()

            # 3. 收集异常值比例（从最近的数据验证结果）
            anomaly_ratio, missing_rate = self._collect_data_quality_stats(manager)

            # 4. 收集交叉验证通过率
            cross_validation_pass_rate = self._collect_cross_validation_stats()

            metrics = DataQualityMetrics(
                timestamp=datetime.now(),
                source_availability=source_availability,
                data_latency_ms=data_latency_ms,
                anomaly_ratio=anomaly_ratio,
                missing_rate=missing_rate,
                cross_validation_pass_rate=cross_validation_pass_rate,
                quality_score_distribution=self._collect_quality_distribution(manager),
            )

            # 保存到历史记录
            self.metrics_history.append(metrics)
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history.pop(0)

            return metrics

        except Exception as e:
            logger.error(f"收集数据质量指标失败: {e}")
            # 返回默认指标
            return DataQualityMetrics(
                timestamp=datetime.now(),
                source_availability={},
                data_latency_ms=0,
                anomaly_ratio=0.0,
                missing_rate=0.0,
                cross_validation_pass_rate=1.0,
                quality_score_distribution={},
            )

    def _collect_source_availability(self, manager: 'DataSourceManager') -> Dict[str, float]:
        """收集数据源可用性"""
        availability = {}

        for source in manager.available_sources:
            # 简单模拟：根据数据源类型设定可用性
            # 实际应用中应统计实际调用成功率
            if source.value.lower() == 'tushare':
                availability[source.value] = 0.95  # Tushare 通常最稳定
            elif source.value.lower() == 'baostock':
                availability[source.value] = 0.90
            elif source.value.lower() == 'akshare':
                availability[source.value] = 0.85
            else:
                availability[source.value] = 0.80

        return availability

    def _estimate_data_latency(self) -> float:
        """估算数据延迟"""
        # 实际应用中应从日志统计
        # 这里返回一个模拟值
        return 150.0  # 150ms

    def _collect_data_quality_stats(self, manager) -> tuple:
        """收集数据质量统计"""
        # 从数据源管理器获取可靠性评分
        stats = []
        for source in manager.available_sources:
            score = manager.get_source_reliability_score(source.value)
            stats.append(score)

        if not stats:
            return 0.0, 0.0

        avg_score = sum(stats) / len(stats)

        # 根据评分估算异常值比例和缺失率
        # 评分越高，异常值和缺失越少
        anomaly_ratio = max(0.0, (1.0 - avg_score / 100.0) * 0.2)
        missing_rate = max(0.0, (1.0 - avg_score / 100.0) * 0.15)

        return anomaly_ratio, missing_rate

    def _collect_cross_validation_stats(self) -> float:
        """收集交叉验证统计"""
        # 模拟交叉验证通过率
        # 实际应用中应从验证器统计
        return 0.95

    def _collect_quality_distribution(self, manager) -> Dict[str, int]:
        """收集质量评分分布"""
        # 从 Redis 获取统计数据
        distribution = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}

        if manager.cache_enabled and manager.cache_manager:
            try:
                # 获取 Redis 客户端
                redis_client = None
                if hasattr(manager.cache_manager, 'db_manager'):
                    redis_client = manager.cache_manager.db_manager.get_redis_client()
                elif hasattr(manager.cache_manager, 'redis_client'):
                    redis_client = manager.cache_manager.redis_client

                if redis_client:
                    # 扫描所有 source_stats 键
                    for source in ["tushare", "akshare", "baostock"]:
                        stats_key = f"source_stats:{source}"
                        stats = redis_client.hgetall(stats_key)

                        if stats:
                            # 根据成功率估算等级
                            success_count = int(stats.get(b"success_count", 0))
                            total = success_count + int(stats.get(b"failure_count", 0))

                            if total > 0:
                                success_rate = success_count / total
                                if success_rate >= 0.95:
                                    distribution["A"] += 1
                                elif success_rate >= 0.90:
                                    distribution["B"] += 1
                                elif success_rate >= 0.80:
                                    distribution["C"] += 1
                                elif success_rate >= 0.60:
                                    distribution["D"] += 1
                                else:
                                    distribution["F"] += 1

            except Exception as e:
                logger.debug(f"收集质量分布失败: {e}")

        return distribution

    def check_alerts(self, metrics: DataQualityMetrics) -> List[Alert]:
        """
        检查指标并生成告警

        Args:
            metrics: 数据质量指标

        Returns:
            List[Alert]: 新生成的告警列表
        """
        new_alerts = []

        # 1. 检查数据源可用性
        for source, availability in metrics.source_availability.items():
            threshold = self.alert_thresholds["source_availability"]
            if availability < threshold["error"]:
                new_alerts.append(Alert(
                    id=f"source_availability_{source}_{int(time.time())}",
                    severity=AlertSeverity.ERROR,
                    title=f"数据源 {source} 可用性过低",
                    message=f"数据源 {source} 的可用性仅为 {availability:.1%}，低于阈值 {threshold['error']:.1%}",
                    timestamp=datetime.now(),
                    metric_name="source_availability",
                    current_value=availability,
                    threshold=threshold["error"],
                ))
            elif availability < threshold["warning"]:
                new_alerts.append(Alert(
                    id=f"source_availability_{source}_{int(time.time())}",
                    severity=AlertSeverity.WARNING,
                    title=f"数据源 {source} 可用性偏低",
                    message=f"数据源 {source} 的可用性为 {availability:.1%}，低于建议值 {threshold['warning']:.1%}",
                    timestamp=datetime.now(),
                    metric_name="source_availability",
                    current_value=availability,
                    threshold=threshold["warning"],
                ))

        # 2. 检查数据延迟
        latency_threshold = self.alert_thresholds["data_latency"]
        if metrics.data_latency_ms > latency_threshold["error"]:
            new_alerts.append(Alert(
                id=f"data_latency_{int(time.time())}",
                severity=AlertSeverity.ERROR,
                title="数据延迟过高",
                message=f"数据延迟达到 {metrics.data_latency_ms:.0f}ms，超过阈值 {latency_threshold['error']}ms",
                timestamp=datetime.now(),
                metric_name="data_latency",
                current_value=metrics.data_latency_ms,
                threshold=latency_threshold["error"],
            ))
        elif metrics.data_latency_ms > latency_threshold["warning"]:
            new_alerts.append(Alert(
                id=f"data_latency_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                title="数据延迟偏高",
                message=f"数据延迟为 {metrics.data_latency_ms:.0f}ms，超过建议值 {latency_threshold['warning']}ms",
                timestamp=datetime.now(),
                metric_name="data_latency",
                current_value=metrics.data_latency_ms,
                threshold=latency_threshold["warning"],
            ))

        # 3. 检查异常值比例
        anomaly_threshold = self.alert_thresholds["anomaly_ratio"]
        if metrics.anomaly_ratio > anomaly_threshold["error"]:
            new_alerts.append(Alert(
                id=f"anomaly_ratio_{int(time.time())}",
                severity=AlertSeverity.ERROR,
                title="异常值比例过高",
                message=f"异常值比例为 {metrics.anomaly_ratio:.1%}，超过阈值 {anomaly_threshold['error']:.1%}",
                timestamp=datetime.now(),
                metric_name="anomaly_ratio",
                current_value=metrics.anomaly_ratio,
                threshold=anomaly_threshold["error"],
            ))
        elif metrics.anomaly_ratio > anomaly_threshold["warning"]:
            new_alerts.append(Alert(
                id=f"anomaly_ratio_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                title="异常值比例偏高",
                message=f"异常值比例为 {metrics.anomaly_ratio:.1%}，超过建议值 {anomaly_threshold['warning']:.1%}",
                timestamp=datetime.now(),
                metric_name="anomaly_ratio",
                current_value=metrics.anomaly_ratio,
                threshold=anomaly_threshold["warning"],
            ))

        # 4. 检查缺失率
        missing_threshold = self.alert_thresholds["missing_rate"]
        if metrics.missing_rate > missing_threshold["error"]:
            new_alerts.append(Alert(
                id=f"missing_rate_{int(time.time())}",
                severity=AlertSeverity.ERROR,
                title="数据缺失率过高",
                message=f"数据缺失率为 {metrics.missing_rate:.1%}，超过阈值 {missing_threshold['error']:.1%}",
                timestamp=datetime.now(),
                metric_name="missing_rate",
                current_value=metrics.missing_rate,
                threshold=missing_threshold["error"],
            ))
        elif metrics.missing_rate > missing_threshold["warning"]:
            new_alerts.append(Alert(
                id=f"missing_rate_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                title="数据缺失率偏高",
                message=f"数据缺失率为 {metrics.missing_rate:.1%}，超过建议值 {missing_threshold['warning']:.1%}",
                timestamp=datetime.now(),
                metric_name="missing_rate",
                current_value=metrics.missing_rate,
                threshold=missing_threshold["warning"],
            ))

        # 5. 检查交叉验证通过率
        cv_threshold = self.alert_thresholds["cross_validation_pass_rate"]
        if metrics.cross_validation_pass_rate < cv_threshold["error"]:
            new_alerts.append(Alert(
                id=f"cross_validation_{int(time.time())}",
                severity=AlertSeverity.ERROR,
                title="交叉验证通过率过低",
                message=f"交叉验证通过率为 {metrics.cross_validation_pass_rate:.1%}，低于阈值 {cv_threshold['error']:.1%}",
                timestamp=datetime.now(),
                metric_name="cross_validation_pass_rate",
                current_value=metrics.cross_validation_pass_rate,
                threshold=cv_threshold["error"],
            ))
        elif metrics.cross_validation_pass_rate < cv_threshold["warning"]:
            new_alerts.append(Alert(
                id=f"cross_validation_{int(time.time())}",
                severity=AlertSeverity.WARNING,
                title="交叉验证通过率偏低",
                message=f"交叉验证通过率为 {metrics.cross_validation_pass_rate:.1%}，低于建议值 {cv_threshold['warning']:.1%}",
                timestamp=datetime.now(),
                metric_name="cross_validation_pass_rate",
                current_value=metrics.cross_validation_pass_rate,
                threshold=cv_threshold["warning"],
            ))

        # 保存到告警历史
        self.alerts.extend(new_alerts)
        if len(self.alerts) > self.max_alerts_size:
            self.alerts = self.alerts[-self.max_alerts_size:]

        return new_alerts

    def get_current_metrics(self) -> DataQualityMetrics:
        """获取当前指标"""
        if not self.metrics_history:
            self.collect_metrics()
        return self.metrics_history[-1]

    def get_metrics_history(self, limit: int = 100) -> List[DataQualityMetrics]:
        """获取历史指标"""
        return self.metrics_history[-limit:]

    def get_alerts(self, limit: int = 50) -> List[Alert]:
        """获取告警历史"""
        return self.alerts[-limit:]

    def get_alert_summary(self) -> Dict[str, int]:
        """获取告警摘要统计"""
        summary = {
            "total": len(self.alerts),
            "unresolved": sum(1 for a in self.alerts if not a.resolved),
            "critical": sum(1 for a in self.alerts if a.severity == AlertSeverity.CRITICAL and not a.resolved),
            "error": sum(1 for a in self.alerts if a.severity == AlertSeverity.ERROR and not a.resolved),
            "warning": sum(1 for a in self.alerts if a.severity == AlertSeverity.WARNING and not a.resolved),
            "info": sum(1 for a in self.alerts if a.severity == AlertSeverity.INFO and not a.resolved),
        }
        return summary


# 全局监控实例
_monitor: Optional[DataQualityMonitor] = None


def get_data_quality_monitor() -> DataQualityMonitor:
    """获取全局监控实例"""
    global _monitor
    if _monitor is None:
        _monitor = DataQualityMonitor()
    return _monitor


# FastAPI 响应模型
class MetricsResponse(BaseModel):
    """指标响应"""
    timestamp: datetime
    source_availability: Dict[str, float]
    data_latency_ms: float
    anomaly_ratio: float
    missing_rate: float
    cross_validation_pass_rate: float
    quality_score_distribution: Dict[str, int]


class AlertResponse(BaseModel):
    """告警响应"""
    id: str
    severity: str
    title: str
    message: str
    timestamp: datetime
    metric_name: str
    current_value: float
    threshold: float
    resolved: bool
