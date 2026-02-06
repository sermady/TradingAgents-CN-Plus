# -*- coding: utf-8 -*-
"""
数据质量监控 API 路由 (Phase 2.3)

提供数据质量指标查询和告警功能的 API 端点
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.services.data_quality_monitor import (
    get_data_quality_monitor,
    DataQualityMonitor,
    MetricsResponse,
    AlertResponse,
)

router = APIRouter(prefix="/api/data-quality", tags=["data-quality"])


@router.get("/metrics", response_model=MetricsResponse)
async def get_current_metrics(
    monitor: DataQualityMonitor = Depends(get_data_quality_monitor)
):
    """
    获取当前数据质量指标

    返回最新的数据质量指标，包括：
    - 数据源可用性
    - 数据延迟
    - 异常值比例
    - 数据缺失率
    - 交叉验证通过率
    - 质量评分分布
    """
    try:
        # 收集最新指标
        metrics = monitor.collect_metrics()

        return MetricsResponse(
            timestamp=metrics.timestamp,
            source_availability=metrics.source_availability,
            data_latency_ms=metrics.data_latency_ms,
            anomaly_ratio=metrics.anomaly_ratio,
            missing_rate=metrics.missing_rate,
            cross_validation_pass_rate=metrics.cross_validation_pass_rate,
            quality_score_distribution=metrics.quality_score_distribution,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据质量指标失败: {e}")


@router.get("/metrics/history")
async def get_metrics_history(
    limit: int = Query(100, ge=1, le=1000, description="返回记录数量"),
    monitor: DataQualityMonitor = Depends(get_data_quality_monitor)
):
    """
    获取历史指标数据

    Args:
        limit: 返回最近N条记录，默认100条

    Returns:
        历史指标列表
    """
    try:
        history = monitor.get_metrics_history(limit)

        return [
            {
                "timestamp": m.timestamp.isoformat(),
                "source_availability": m.source_availability,
                "data_latency_ms": m.data_latency_ms,
                "anomaly_ratio": m.anomaly_ratio,
                "missing_rate": m.missing_rate,
                "cross_validation_pass_rate": m.cross_validation_pass_rate,
                "quality_score_distribution": m.quality_score_distribution,
            }
            for m in history
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史指标失败: {e}")


@router.get("/alerts", response_model=List[AlertResponse])
async def get_alerts(
    limit: int = Query(50, ge=1, le=500, description="返回告警数量"),
    resolved: Optional[bool] = Query(None, description="筛选已解决/未解决的告警"),
    severity: Optional[str] = Query(None, description="按严重程度筛选"),
    monitor: DataQualityMonitor = Depends(get_data_quality_monitor)
):
    """
    获取告警列表

    Args:
        limit: 返回最近N条告警
        resolved: 筛选已解决/未解决的告警（None返回全部）
        severity: 按严重程度筛选（info/warning/error/critical）

    Returns:
        告警列表
    """
    try:
        alerts = monitor.get_alerts(limit)

        # 筛选条件
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]

        if severity is not None:
            alerts = [a for a in alerts if a.severity.value == severity]

        return [
            AlertResponse(
                id=a.id,
                severity=a.severity.value,
                title=a.title,
                message=a.message,
                timestamp=a.timestamp,
                metric_name=a.metric_name,
                current_value=a.current_value,
                threshold=a.threshold,
                resolved=a.resolved,
            )
            for a in alerts
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取告警列表失败: {e}")


@router.get("/alerts/summary")
async def get_alert_summary(
    monitor: DataQualityMonitor = Depends(get_data_quality_monitor)
):
    """
    获取告警摘要统计

    返回各类告警的数量统计
    """
    try:
        summary = monitor.get_alert_summary()

        return summary

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取告警摘要失败: {e}")


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str,
    monitor: DataQualityMonitor = Depends(get_data_quality_monitor)
):
    """
    标记告警为已解决

    Args:
        alert_id: 告警ID

    Returns:
        操作结果
    """
    try:
        # 查找告警
        alert = None
        for a in monitor.alerts:
            if a.id == alert_id:
                alert = a
                break

        if not alert:
            raise HTTPException(status_code=404, detail=f"告警不存在: {alert_id}")

        # 标记为已解决
        alert.resolved = True

        return {
            "success": True,
            "message": f"告警 {alert_id} 已标记为已解决",
            "alert_id": alert_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解决告警失败: {e}")


@router.post("/refresh")
async def refresh_metrics(
    monitor: DataQualityMonitor = Depends(get_data_quality_monitor)
):
    """
    刷新数据质量指标

    手动触发指标收集和告警检查
    """
    try:
        # 收集新指标
        metrics = monitor.collect_metrics()

        # 检查告警
        new_alerts = monitor.check_alerts(metrics)

        return {
            "success": True,
            "message": "指标已刷新",
            "metrics": MetricsResponse(
                timestamp=metrics.timestamp,
                source_availability=metrics.source_availability,
                data_latency_ms=metrics.data_latency_ms,
                anomaly_ratio=metrics.anomaly_ratio,
                missing_rate=metrics.missing_rate,
                cross_validation_pass_rate=metrics.cross_validation_pass_rate,
                quality_score_distribution=metrics.quality_score_distribution,
            ),
            "new_alerts_count": len(new_alerts),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新指标失败: {e}")
