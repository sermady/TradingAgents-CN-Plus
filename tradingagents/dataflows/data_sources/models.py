# -*- coding: utf-8 -*-
"""
数据源模型定义
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List


@dataclass
class ValidatedDataResult:
    """
    带验证的数据结果 (Phase 1.1)

    包含原始数据以及数据质量评分和验证信息

    Attributes:
        data: 原始数据字典
        quality_score: 数据质量评分 (0-100)
        quality_grade: 数据质量等级 (A/B/C/D/F)
        quality_issues: 数据质量问题列表
        validation_timestamp: 验证时间戳
        data_source: 数据来源
    """

    data: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 100.0
    quality_grade: str = "A"
    quality_issues: List[str] = field(default_factory=list)
    validation_timestamp: datetime = field(default_factory=datetime.now)
    data_source: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "data": self.data,
            "quality_score": self.quality_score,
            "quality_grade": self.quality_grade,
            "quality_issues": self.quality_issues,
            "validation_timestamp": self.validation_timestamp.isoformat(),
            "data_source": self.data_source,
        }

    def is_valid(self, min_score: float = 60.0) -> bool:
        """
        检查数据是否有效

        Args:
            min_score: 最低质量评分阈值

        Returns:
            如果数据质量评分大于等于阈值，返回True
        """
        return self.quality_score >= min_score
