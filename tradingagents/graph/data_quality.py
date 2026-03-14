# -*- coding: utf-8 -*-
"""P2-2: 多维数据质量评分

在原有"数据可用性"评分基础上，增加 4 个量化维度:
1. 时效性 (Timeliness)      - 数据日期与请求日期的差距
2. 完整性 (Completeness)    - OHLCV 核心字段缺失率
3. 逻辑一致性 (Consistency) - OHLC 关系约束校验
4. 异常值 (Anomaly)         - 基于统计方法的离群点检测

每个维度 0.0-1.0 分, 加权合并到总体质量评分中。
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class QualityDimension:
    """单个质量维度的评估结果"""

    name: str
    score: float  # 0.0 - 1.0
    issues: tuple = ()  # 不可变, 用 tuple 而非 list


@dataclass(frozen=True)
class DataQualityReport:
    """完整的多维数据质量报告"""

    timeliness: QualityDimension
    completeness: QualityDimension
    consistency: QualityDimension
    anomaly: QualityDimension
    overall_score: float  # 0.0 - 1.0
    grade: str  # A/B/C/D/F
    issues: tuple = ()  # 所有问题汇总

    def to_dict(self) -> Dict[str, Any]:
        return {
            "overall_score": round(self.overall_score, 3),
            "grade": self.grade,
            "dimensions": {
                "timeliness": round(self.timeliness.score, 3),
                "completeness": round(self.completeness.score, 3),
                "consistency": round(self.consistency.score, 3),
                "anomaly": round(self.anomaly.score, 3),
            },
            "issues": list(self.issues),
        }

    def format_for_prompt(self) -> str:
        """格式化为可注入 prompt 的简洁文本"""
        lines = [
            f"数据质量评级: {self.grade} ({self.overall_score:.0%})",
        ]
        if self.issues:
            lines.append("质量问题:")
            for issue in self.issues[:5]:  # 最多展示 5 条
                lines.append(f"  - {issue}")
        return "\n".join(lines)


# ==================== 维度权重 ====================

DIMENSION_WEIGHTS = {
    "timeliness": 0.25,
    "completeness": 0.30,
    "consistency": 0.25,
    "anomaly": 0.20,
}


# ==================== 评分函数 ====================


def evaluate_timeliness(
    structured_data: Dict[str, Any],
    trade_date: str,
    data_text: str = "",
) -> QualityDimension:
    """评估数据时效性: 最新数据日期 vs 请求日期"""
    issues = []

    if not trade_date:
        return QualityDimension("timeliness", 0.5, ("无请求日期, 无法评估时效性",))

    # 从结构化数据或文本中提取最新数据日期
    latest_date = _extract_latest_date(structured_data, data_text)

    if not latest_date:
        return QualityDimension("timeliness", 0.6, ("无法提取数据日期",))

    try:
        from datetime import datetime

        req_dt = datetime.strptime(trade_date.replace("-", ""), "%Y%m%d")
        data_dt = datetime.strptime(latest_date.replace("-", ""), "%Y%m%d")
        gap_days = abs((req_dt - data_dt).days)

        if gap_days == 0:
            score = 1.0
        elif gap_days <= 1:
            score = 0.95  # 周末/节假日正常偏移
        elif gap_days <= 3:
            score = 0.85
        elif gap_days <= 7:
            score = 0.7
            issues.append(f"数据日期偏差 {gap_days} 天")
        elif gap_days <= 30:
            score = 0.5
            issues.append(f"数据日期偏差 {gap_days} 天, 时效性较差")
        else:
            score = 0.2
            issues.append(f"数据日期偏差 {gap_days} 天, 数据严重过时")

    except (ValueError, TypeError):
        score = 0.6
        issues.append("日期解析失败")

    return QualityDimension("timeliness", score, tuple(issues))


def evaluate_completeness(
    structured_data: Dict[str, Any],
) -> QualityDimension:
    """评估 OHLCV + 关键指标的完整性"""
    issues = []

    # 核心字段 (权重更高)
    core_fields = ["current_price", "open", "high", "low", "volume"]
    # 技术指标字段
    indicator_fields = [
        "MA5", "MA20", "MA60",
        "RSI", "MACD_DIF",
        "KDJ_K", "ATR14",
        "BOLL_UPPER", "BOLL_MID", "BOLL_LOWER",
    ]

    if not structured_data:
        return QualityDimension("completeness", 0.0, ("无结构化数据",))

    # 核心字段完整性 (占 60%)
    core_present = sum(
        1 for f in core_fields
        if structured_data.get(f) is not None
        and not (isinstance(structured_data.get(f), float) and np.isnan(structured_data.get(f)))
    )
    core_ratio = core_present / len(core_fields) if core_fields else 0

    missing_core = [
        f for f in core_fields
        if structured_data.get(f) is None
        or (isinstance(structured_data.get(f), float) and np.isnan(structured_data.get(f)))
    ]
    if missing_core:
        issues.append(f"核心字段缺失: {', '.join(missing_core)}")

    # 指标字段完整性 (占 40%)
    ind_present = sum(
        1 for f in indicator_fields
        if structured_data.get(f) is not None
        and not (isinstance(structured_data.get(f), float) and np.isnan(structured_data.get(f)))
    )
    ind_ratio = ind_present / len(indicator_fields) if indicator_fields else 0

    if ind_ratio < 0.5:
        missing_count = len(indicator_fields) - ind_present
        issues.append(f"{missing_count}/{len(indicator_fields)} 个技术指标缺失")

    score = core_ratio * 0.6 + ind_ratio * 0.4
    return QualityDimension("completeness", score, tuple(issues))


def evaluate_consistency(
    structured_data: Dict[str, Any],
) -> QualityDimension:
    """评估 OHLC 逻辑一致性"""
    issues = []
    checks_passed = 0
    checks_total = 0

    o = structured_data.get("open")
    h = structured_data.get("high")
    l = structured_data.get("low")
    c = structured_data.get("current_price") or structured_data.get("close")

    # 只有在有足够数据时才做检查
    if not all(isinstance(v, (int, float)) for v in [o, h, l, c] if v is not None):
        return QualityDimension("consistency", 0.8, ("OHLC 数据不足, 跳过一致性检查",))

    available = {k: v for k, v in {"O": o, "H": h, "L": l, "C": c}.items() if v is not None}
    if len(available) < 3:
        return QualityDimension("consistency", 0.8, ("OHLC 字段不足 3 个",))

    # Check 1: High >= Low
    if h is not None and l is not None:
        checks_total += 1
        if h >= l:
            checks_passed += 1
        else:
            issues.append(f"High({h}) < Low({l}), OHLC 逻辑异常")

    # Check 2: High >= Open
    if h is not None and o is not None:
        checks_total += 1
        if h >= o:
            checks_passed += 1
        else:
            issues.append(f"High({h}) < Open({o})")

    # Check 3: High >= Close
    if h is not None and c is not None:
        checks_total += 1
        if h >= c:
            checks_passed += 1
        else:
            issues.append(f"High({h}) < Close({c})")

    # Check 4: Low <= Open
    if l is not None and o is not None:
        checks_total += 1
        if l <= o:
            checks_passed += 1
        else:
            issues.append(f"Low({l}) > Open({o})")

    # Check 5: Low <= Close
    if l is not None and c is not None:
        checks_total += 1
        if l <= c:
            checks_passed += 1
        else:
            issues.append(f"Low({l}) > Close({c})")

    # Check 6: 价格为正
    for name, val in available.items():
        checks_total += 1
        if val > 0:
            checks_passed += 1
        else:
            issues.append(f"{name} = {val}, 价格非正数")

    # Check 7: 布林带 Upper >= Mid >= Lower
    bu = structured_data.get("BOLL_UPPER")
    bm = structured_data.get("BOLL_MID")
    bl = structured_data.get("BOLL_LOWER")
    if all(isinstance(v, (int, float)) for v in [bu, bm, bl] if v is not None):
        if bu is not None and bm is not None and bl is not None:
            checks_total += 1
            if bu >= bm >= bl:
                checks_passed += 1
            else:
                issues.append(f"布林带逻辑异常: Upper={bu}, Mid={bm}, Lower={bl}")

    # Check 8: RSI 范围 0-100
    for rsi_key in ("RSI", "RSI14"):
        rsi_val = structured_data.get(rsi_key)
        if isinstance(rsi_val, (int, float)):
            checks_total += 1
            if 0 <= rsi_val <= 100:
                checks_passed += 1
            else:
                issues.append(f"{rsi_key}={rsi_val}, 超出 0-100 范围")

    score = checks_passed / checks_total if checks_total > 0 else 0.8
    return QualityDimension("consistency", score, tuple(issues))


def evaluate_anomaly(
    structured_data: Dict[str, Any],
    data_text: str = "",
) -> QualityDimension:
    """基于统计方法检测异常值

    - 价格偏离 MA20 > 3 倍标准差 (近似)
    - 成交量突变 > 5 倍均量
    - RSI/KDJ 极端值
    """
    issues = []
    anomaly_count = 0
    check_count = 0

    price = structured_data.get("current_price")
    ma20 = structured_data.get("MA20")
    ma5 = structured_data.get("MA5")
    volume = structured_data.get("volume")

    # 检查 1: 价格偏离 MA20
    if isinstance(price, (int, float)) and isinstance(ma20, (int, float)) and ma20 > 0:
        check_count += 1
        deviation_pct = abs(price - ma20) / ma20
        if deviation_pct > 0.30:  # 偏离 30% 以上 (A股涨跌停约 10-20%)
            anomaly_count += 1
            issues.append(f"价格偏离MA20达 {deviation_pct:.0%}, 可能异常")
        elif deviation_pct > 0.15:
            anomaly_count += 0.3
            issues.append(f"价格偏离MA20达 {deviation_pct:.0%}, 波动较大")

    # 检查 2: 价格偏离 MA5 (短期异常)
    if isinstance(price, (int, float)) and isinstance(ma5, (int, float)) and ma5 > 0:
        check_count += 1
        dev5 = abs(price - ma5) / ma5
        if dev5 > 0.15:
            anomaly_count += 0.5
            issues.append(f"价格偏离MA5达 {dev5:.0%}, 短期异常波动")

    # 检查 3: 成交量突变 (通过文本提取历史均量近似)
    avg_vol = _extract_average_volume(data_text)
    if isinstance(volume, (int, float)) and avg_vol and avg_vol > 0:
        check_count += 1
        vol_ratio = volume / avg_vol
        if vol_ratio > 5.0:
            anomaly_count += 1
            issues.append(f"成交量为均量的 {vol_ratio:.1f} 倍, 严重放量")
        elif vol_ratio > 3.0:
            anomaly_count += 0.5
            issues.append(f"成交量为均量的 {vol_ratio:.1f} 倍, 显著放量")
        elif vol_ratio < 0.2:
            anomaly_count += 0.5
            issues.append(f"成交量为均量的 {vol_ratio:.1f} 倍, 显著缩量")

    # 检查 4: RSI 极端值
    for rsi_key in ("RSI", "RSI14"):
        rsi_val = structured_data.get(rsi_key)
        if isinstance(rsi_val, (int, float)):
            check_count += 1
            if rsi_val > 90 or rsi_val < 10:
                anomaly_count += 0.5
                issues.append(f"{rsi_key}={rsi_val:.1f}, 处于极端值区间")

    # 检查 5: KDJ J 值极端 (J > 100 或 J < 0 正常, 但 J > 120 或 J < -20 异常)
    kdj_j = structured_data.get("KDJ_J")
    if isinstance(kdj_j, (int, float)):
        check_count += 1
        if kdj_j > 120 or kdj_j < -20:
            anomaly_count += 0.3
            issues.append(f"KDJ-J={kdj_j:.1f}, 极端超买超卖")

    if check_count == 0:
        return QualityDimension("anomaly", 0.8, ("数据不足, 无法检测异常值",))

    # 异常比例 → 分数 (0 异常 = 1.0 分, 全异常 = 0.0 分)
    anomaly_ratio = min(anomaly_count / max(check_count, 1), 1.0)
    score = 1.0 - anomaly_ratio * 0.8  # 留底 0.2 分

    return QualityDimension("anomaly", score, tuple(issues))


# ==================== 主入口 ====================


def evaluate_data_quality(
    structured_data: Dict[str, Any],
    trade_date: str = "",
    data_text: str = "",
) -> DataQualityReport:
    """评估市场数据的多维质量

    Args:
        structured_data: _parse_market_data() 返回的结构化数据
        trade_date: 用户请求的分析日期 (YYYYMMDD 或 YYYY-MM-DD)
        data_text: 原始市场数据文本 (用于日期提取和均量估算)

    Returns:
        DataQualityReport 包含 4 个维度评分和总体评级
    """
    timeliness = evaluate_timeliness(structured_data, trade_date, data_text)
    completeness = evaluate_completeness(structured_data)
    consistency = evaluate_consistency(structured_data)
    anomaly = evaluate_anomaly(structured_data, data_text)

    # 加权总分
    overall = (
        timeliness.score * DIMENSION_WEIGHTS["timeliness"]
        + completeness.score * DIMENSION_WEIGHTS["completeness"]
        + consistency.score * DIMENSION_WEIGHTS["consistency"]
        + anomaly.score * DIMENSION_WEIGHTS["anomaly"]
    )

    # 评级
    grade = _score_to_grade(overall)

    # 汇总所有问题
    all_issues = (
        timeliness.issues + completeness.issues + consistency.issues + anomaly.issues
    )

    return DataQualityReport(
        timeliness=timeliness,
        completeness=completeness,
        consistency=consistency,
        anomaly=anomaly,
        overall_score=overall,
        grade=grade,
        issues=all_issues,
    )


# ==================== 辅助函数 ====================


def _score_to_grade(score: float) -> str:
    if score >= 0.9:
        return "A"
    elif score >= 0.75:
        return "B"
    elif score >= 0.6:
        return "C"
    elif score >= 0.4:
        return "D"
    return "F"


def _extract_latest_date(
    structured_data: Dict[str, Any], data_text: str
) -> Optional[str]:
    """从数据中提取最新日期"""
    # 优先从结构化数据
    for key in ("latest_date", "date", "trade_date"):
        val = structured_data.get(key)
        if val and isinstance(val, str):
            return val

    # 从文本提取所有日期, 取时间最近的
    if data_text:
        dates = re.findall(r"(\d{4}[-/]\d{2}[-/]\d{2})", data_text)
        if dates:
            # 统一为 - 分隔后按字典序取最大值 (YYYY-MM-DD 字典序=时间序)
            normalized = [d.replace("/", "-") for d in dates]
            return max(normalized)

    return None


def _extract_average_volume(data_text: str) -> Optional[float]:
    """从文本中估算近期平均成交量 (粗略方法)"""
    if not data_text:
        return None

    # 匹配成交量行: 成交量: 123,456 手 或 成交量: 5.23 万手
    vol_matches = re.findall(
        r"成交量[：:]\s*([\d,]+\.?\d*)\s*(万手|手)?", data_text
    )
    if len(vol_matches) >= 3:
        volumes = []
        for val_str, unit in vol_matches:
            try:
                vol = float(val_str.replace(",", ""))
                if unit == "万手":
                    vol *= 10000
                volumes.append(vol)
            except ValueError:
                continue
        if volumes:
            # 用除最后一个外的值算均值 (最后一个是"当前", 前面是历史)
            if len(volumes) > 1:
                return float(np.mean(volumes[:-1]))
            return volumes[0]

    return None
