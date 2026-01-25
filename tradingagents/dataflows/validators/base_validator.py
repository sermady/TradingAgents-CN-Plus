# -*- coding: utf-8 -*-
"""
数据验证器基类

定义所有验证器的统一接口和数据结构
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """验证问题严重程度"""
    INFO = "info"           # 信息性提示
    WARNING = "warning"     # 警告,数据可用但需注意
    ERROR = "error"         # 错误,数据可能不准确
    CRITICAL = "critical"   # 严重错误,数据不可用


@dataclass
class ValidationIssue:
    """验证问题详情"""
    severity: ValidationSeverity
    message: str
    field: str              # 问题字段
    expected: Any = None    # 期望值
    actual: Any = None      # 实际值
    source: str = ""        # 数据来源

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'severity': self.severity.value,
            'message': self.message,
            'field': self.field,
            'expected': self.expected,
            'actual': self.actual,
            'source': self.source
        }


@dataclass
class ValidationResult:
    """验证结果数据类"""
    is_valid: bool                          # 是否通过验证
    confidence: float                       # 置信度 (0.0-1.0)
    source: str                             # 主要数据来源
    discrepancies: List[ValidationIssue] = field(default_factory=list)  # 发现的问题列表
    suggested_value: Any = None             # 建议值(如果数据有问题)
    alternative_sources: Dict[str, Any] = field(default_factory=dict)   # 其他数据源的值
    metadata: Dict[str, Any] = field(default_factory=dict)  # 额外元数据

    def add_issue(self, severity: ValidationSeverity, message: str,
                  field: str = "", expected: Any = None, actual: Any = None,
                  source: str = "") -> None:
        """添加验证问题"""
        issue = ValidationIssue(
            severity=severity,
            message=message,
            field=field,
            expected=expected,
            actual=actual,
            source=source
        )
        self.discrepancies.append(issue)

        # 如果有ERROR或CRITICAL级别的问题,标记为无效
        if severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.is_valid = False

    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """按严重程度获取问题"""
        return [issue for issue in self.discrepancies if issue.severity == severity]

    def has_critical_issues(self) -> bool:
        """是否有严重问题"""
        return any(issue.severity == ValidationSeverity.CRITICAL for issue in self.discrepancies)

    def has_error_issues(self) -> bool:
        """是否有错误级别问题"""
        return any(issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
                   for issue in self.discrepancies)

    def get_error_count(self) -> Dict[str, int]:
        """获取各级别问题数量统计"""
        counts = {severity.value: 0 for severity in ValidationSeverity}
        for issue in self.discrepancies:
            counts[issue.severity.value] += 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'is_valid': self.is_valid,
            'confidence': round(self.confidence, 3),
            'source': self.source,
            'discrepancies': [issue.to_dict() for issue in self.discrepancies],
            'suggested_value': self.suggested_value,
            'alternative_sources': self.alternative_sources,
            'metadata': self.metadata,
            'error_counts': self.get_error_count()
        }

    def __str__(self) -> str:
        """字符串表示"""
        status = "✅ 有效" if self.is_valid else "❌ 无效"
        error_counts = self.get_error_count()
        return (
            f"{status} | 置信度: {self.confidence:.2%} | 来源: {self.source} | "
            f"问题: {error_counts['critical']}严重, {error_counts['error']}错误, "
            f"{error_counts['warning']}警告"
        )


class BaseDataValidator(ABC):
    """
    数据验证器基类

    所有具体验证器必须继承此类并实现抽象方法
    """

    def __init__(self, tolerance: float = 0.01):
        """
        初始化验证器

        Args:
            tolerance: 允许的误差范围(百分比), 默认1%
        """
        self.tolerance = tolerance
        self.logger = logger

    @abstractmethod
    def validate(self, symbol: str, data: Dict[str, Any]) -> ValidationResult:
        """
        验证单个数据源的数据

        Args:
            symbol: 股票代码
            data: 待验证的数据字典

        Returns:
            ValidationResult: 验证结果对象
        """
        pass

    @abstractmethod
    async def cross_validate(self, symbol: str, sources: List[str],
                            metric: str) -> ValidationResult:
        """
        多源交叉验证

        Args:
            symbol: 股票代码
            sources: 数据源列表
            metric: 要验证的指标名称

        Returns:
            ValidationResult: 包含多源比较结果的验证对象
        """
        pass

    def calculate_confidence(self, values: List[Any],
                            is_numeric: bool = True) -> float:
        """
        基于数据一致性计算置信度

        Args:
            values: 多个数据源的值列表
            is_numeric: 是否为数值类型

        Returns:
            float: 置信度 (0.0-1.0)
        """
        if not values:
            return 0.0

        if len(values) == 1:
            return 0.5  # 只有一个数据源,置信度中等

        if not is_numeric:
            # 非数值类型,检查是否完全一致
            return 1.0 if len(set(values)) == 1 else 0.3

        # 数值类型,计算变异系数(CV)
        try:
            numeric_values = [float(v) for v in values if v is not None]
            if len(numeric_values) < 2:
                return 0.5

            mean_val = sum(numeric_values) / len(numeric_values)
            if mean_val == 0:
                return 1.0 if all(v == 0 for v in numeric_values) else 0.0

            std_dev = (sum((x - mean_val) ** 2 for x in numeric_values) /
                      len(numeric_values)) ** 0.5
            cv = std_dev / abs(mean_val) if mean_val != 0 else 0

            # CV越小,置信度越高
            # CV < 0.01 -> 1.0, CV > 0.1 -> 0.0
            confidence = max(0.0, min(1.0, 1.0 - cv * 10))
            return confidence

        except (ValueError, TypeError):
            self.logger.warning(f"无法计算数值置信度: {values}")
            return 0.3

    def check_value_in_range(self, value: float, min_val: float,
                            max_val: float, field_name: str) -> bool:
        """
        检查值是否在合理范围内

        Args:
            value: 待检查的值
            min_val: 最小值
            max_val: 最大值
            field_name: 字段名称

        Returns:
            bool: 是否在范围内
        """
        if value is None:
            return False

        in_range = min_val <= value <= max_val
        if not in_range:
            self.logger.warning(
                f"{field_name}={value} 超出合理范围 [{min_val}, {max_val}]"
            )
        return in_range

    def calculate_percentage_difference(self, value1: float,
                                       value2: float) -> float:
        """
        计算两个值的百分比差异

        Args:
            value1: 第一个值
            value2: 第二个值

        Returns:
            float: 百分比差异(绝对值)
        """
        if value1 is None or value2 is None:
            return float('inf')

        if value1 == 0 and value2 == 0:
            return 0.0

        if value1 == 0 or value2 == 0:
            return float('inf')

        return abs((value1 - value2) / ((value1 + value2) / 2)) * 100

    def find_median_value(self, values: List[float]) -> Optional[float]:
        """
        找出中位数(作为建议值)

        Args:
            values: 数值列表

        Returns:
            Optional[float]: 中位数
        """
        if not values:
            return None

        sorted_values = sorted([v for v in values if v is not None])
        if not sorted_values:
            return None

        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            return sorted_values[n // 2]

    def to_float(self, value: Any) -> Optional[float]:
        """
        将值转换为float类型

        能够处理各种格式的数据:
        - 数字: 直接返回
        - 字符串数字: 转换后返回
        - 带符号/单位的字符串: 移除符号后转换

        Args:
            value: 待转换的值

        Returns:
            Optional[float]: 转换后的float值,失败返回None
        """
        if value is None:
            return None

        # 如果已经是float,直接返回
        if isinstance(value, float):
            return value

        # 如果是int,转换为float
        if isinstance(value, int):
            return float(value)

        # 如果是字符串,尝试转换
        if isinstance(value, str):
            # 移除常见的符号和单位
            value = value.strip()
            value = value.replace('¥', '').replace('$', '').replace('￥', '')
            value = value.replace(',', '').replace(' ', '')
            value = value.replace('亿元', '').replace('亿', '')
            value = value.replace('万元', '').replace('万', '')
            value = value.replace('%', '')

            try:
                return float(value)
            except (ValueError, TypeError):
                self.logger.debug(f"无法将 '{value}' 转换为float")
                return None

        # 其他类型,尝试直接转换
        try:
            return float(value)
        except (ValueError, TypeError):
            self.logger.debug(f"无法将 {value} ({type(value)}) 转换为float")
            return None
