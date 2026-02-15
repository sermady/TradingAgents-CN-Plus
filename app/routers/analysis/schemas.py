# -*- coding: utf-8 -*-
"""
分析API数据模型

统一导出所有请求/响应模型，保持API兼容性。
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# 导入核心数据模型
from app.models.analysis import (
    # 枚举类型
    AnalysisStatus,
    BatchStatus,
    # 核心数据模型
    AnalysisParameters,
    AnalysisResult,
    AnalysisTask,
    AnalysisBatch,
    StockInfo,
    # 请求模型
    SingleAnalysisRequest,
    BatchAnalysisRequest,
    # 响应模型
    AnalysisTaskResponse,
    AnalysisBatchResponse,
    AnalysisHistoryQuery,
)

# ============================================================================
# 路由层特定模型（API响应格式）
# ============================================================================


class TaskStatusResponse(BaseModel):
    """任务状态响应模型（API层）

    用于 /tasks/{task_id}/status 端点
    """

    task_id: str
    status: str
    progress: float = Field(ge=0, le=100, description="任务进度百分比")
    message: Optional[str] = Field(None, description="状态消息")
    current_step: Optional[str] = Field(None, description="当前执行步骤")

    # 时间信息
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    elapsed_time: float = Field(default=0, description="已用时间（秒）")
    remaining_time: float = Field(default=0, description="预计剩余时间（秒）")
    estimated_total_time: float = Field(default=0, description="预计总时间（秒）")

    # 股票信息
    symbol: Optional[str] = Field(None, description="股票代码")
    stock_code: Optional[str] = Field(None, description="股票代码（兼容字段）")
    stock_symbol: Optional[str] = Field(None, description="股票代码（兼容字段）")

    # 分析信息
    analysts: Optional[List[str]] = Field(None, description="参与的分析师")
    research_depth: Optional[str] = Field(None, description="研究深度")

    # 数据来源标记
    source: Optional[str] = Field(None, description="数据来源（mongodb/memory）")


class TaskResultResponse(BaseModel):
    """任务结果响应模型（API层）

    用于 /tasks/{task_id}/result 端点
    """

    # 基本信息
    analysis_id: Optional[str] = Field(None, description="分析ID")
    stock_symbol: Optional[str] = Field(None, description="股票代码")
    stock_code: Optional[str] = Field(None, description="股票代码（兼容字段）")
    analysis_date: Optional[str] = Field(None, description="分析日期")

    # 分析结果
    summary: Optional[str] = Field(None, description="分析摘要")
    recommendation: Optional[str] = Field(None, description="投资建议")
    confidence_score: float = Field(default=0.0, ge=0, le=1, description="置信度分数")
    risk_level: Optional[str] = Field(None, description="风险等级")
    key_points: List[str] = Field(default_factory=list, description="关键要点")

    # 执行信息
    execution_time: float = Field(default=0.0, description="执行时间（秒）")
    tokens_used: int = Field(default=0, description="使用的Token数")

    # 分析师信息
    analysts: List[str] = Field(default_factory=list, description="参与的分析师")
    research_depth: Optional[str] = Field(None, description="研究深度")

    # 详细报告
    reports: Dict[str, str] = Field(default_factory=dict, description="详细分析报告")

    # 时间戳
    created_at: Optional[datetime] = Field(None, description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    # 状态
    status: Optional[str] = Field(None, description="任务状态")

    # 最终决策
    decision: Dict[str, Any] = Field(default_factory=dict, description="最终交易决策")

    # 数据来源标记
    source: Optional[str] = Field(None, description="数据来源")

    # 状态（可选）
    state: Optional[Dict[str, Any]] = Field(None, description="完整状态")
    detailed_analysis: Optional[Dict[str, Any]] = Field(None, description="详细分析")


class ApiResponse(BaseModel):
    """统一API响应格式

    所有端点的标准响应包装
    """

    success: bool = Field(..., description="请求是否成功")
    data: Optional[Any] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="响应消息")
    error: Optional[str] = Field(None, description="错误信息（仅在失败时）")


# ============================================================================
# 导出所有模型
# ============================================================================

__all__ = [
    # 核心枚举
    "AnalysisStatus",
    "BatchStatus",
    # 核心数据模型
    "AnalysisParameters",
    "AnalysisResult",
    "AnalysisTask",
    "AnalysisBatch",
    "StockInfo",
    # 请求模型
    "SingleAnalysisRequest",
    "BatchAnalysisRequest",
    "AnalysisHistoryQuery",
    # 响应模型
    "AnalysisTaskResponse",
    "AnalysisBatchResponse",
    # API层特定模型
    "TaskStatusResponse",
    "TaskResultResponse",
    "ApiResponse",
]
