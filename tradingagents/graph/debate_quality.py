# -*- coding: utf-8 -*-
"""
辩论质量评估器

P1-4: 轻量级（无 LLM 调用）论点质量评分，
基于关键词/模式匹配评估辩论发言的证据强度。

评估维度:
- 数据引用密度 (具体数字、百分比、价格)
- 金融指标引用 (PE、ROE、MACD 等专业术语)
- 反驳质量 (对对方观点的回应)
- 论点新颖度 (避免简单重复)
"""

import re
from typing import Dict, List, Tuple

from tradingagents.utils.logging_init import get_logger

logger = get_logger("debate_quality")

# 金融专业术语集合
_FINANCIAL_TERMS = {
    # 估值指标
    "PE", "PB", "PS", "PEG", "PE_TTM", "市盈率", "市净率", "市销率",
    # 盈利指标
    "ROE", "ROA", "ROIC", "毛利率", "净利率", "净利润", "营收", "EPS",
    # 技术指标
    "MA", "MACD", "RSI", "KDJ", "ATR", "OBV", "CCI", "布林带", "BOLL",
    "支撑位", "阻力位", "金叉", "死叉", "超买", "超卖",
    # 风险指标
    "VaR", "CVaR", "波动率", "最大回撤", "夏普比率", "Beta", "Sharpe",
    # 资金面
    "北向资金", "融资融券", "龙虎榜", "大宗交易", "换手率", "量比",
    # 财务
    "现金流", "负债率", "资产负债", "分红", "股息率",
}

# 反驳/回应关键词
_REBUTTAL_KEYWORDS = [
    "然而", "但是", "不过", "相反", "反驳", "质疑", "不同意",
    "我认为", "恰恰", "事实上", "实际上", "相比之下",
    "你提到", "你的观点", "你说的", "对方", "看跌", "看涨",
    "保守", "激进", "风险",
    "however", "but", "disagree", "contrary", "actually",
]

# 数字模式
_NUMBER_PATTERN = re.compile(
    r"(?:"
    r"¥[\d,]+\.?\d*|"  # 价格 ¥12.30
    r"\d+\.?\d*%|"  # 百分比 12.3%
    r"\d+\.?\d*[亿万]|"  # 中文数量 1.5亿
    r"\d+\.?\d*倍|"  # 倍数 25.7倍
    r"[\d,]+\.?\d*元|"  # 金额 1234.56元
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"  # 日期 2024-01-15
    r")"
)


def evaluate_argument_quality(
    text: str,
    history: str = "",
    role: str = "unknown",
) -> Dict[str, float]:
    """
    评估单次辩论发言的质量

    Args:
        text: 当前发言内容
        history: 之前的辩论历史
        role: 发言者角色 (bull/bear/risky/safe/neutral)

    Returns:
        质量评分字典，包含各维度分数和总分
    """
    if not text or len(text.strip()) < 20:
        return {
            "data_citation": 0.0,
            "financial_terms": 0.0,
            "rebuttal_quality": 0.0,
            "novelty": 0.0,
            "overall": 0.0,
        }

    # 1. 数据引用密度 (0-1)
    data_score = _score_data_citations(text)

    # 2. 金融术语引用 (0-1)
    terms_score = _score_financial_terms(text)

    # 3. 反驳质量 (0-1)
    rebuttal_score = _score_rebuttal_quality(text, history)

    # 4. 论点新颖度 (0-1)
    novelty_score = _score_novelty(text, history)

    # 加权总分
    overall = (
        data_score * 0.30
        + terms_score * 0.25
        + rebuttal_score * 0.25
        + novelty_score * 0.20
    )

    scores = {
        "data_citation": round(data_score, 3),
        "financial_terms": round(terms_score, 3),
        "rebuttal_quality": round(rebuttal_score, 3),
        "novelty": round(novelty_score, 3),
        "overall": round(overall, 3),
    }

    logger.debug(
        f"[{role}] 论点质量: 数据引用={data_score:.2f}, "
        f"金融术语={terms_score:.2f}, 反驳={rebuttal_score:.2f}, "
        f"新颖度={novelty_score:.2f}, 总分={overall:.2f}"
    )

    return scores


def compute_cumulative_evidence_strength(
    current_scores: Dict[str, float],
    previous_strength: float,
    round_number: int,
) -> float:
    """
    计算累积证据强度（用于动态收敛判断）

    Args:
        current_scores: 当前发言的质量评分
        previous_strength: 之前累积的证据强度
        round_number: 当前轮次 (从1开始)

    Returns:
        更新后的证据强度 (0-1)
    """
    current_overall = current_scores.get("overall", 0.0)

    # 指数移动平均，新发言权重随轮次递减
    alpha = max(0.3, 1.0 / (round_number + 1))
    updated = (1 - alpha) * previous_strength + alpha * current_overall

    return round(min(updated, 1.0), 3)


def extract_citations(text: str) -> List[Dict[str, str]]:
    """
    从文本中提取数据引用

    Args:
        text: 发言文本

    Returns:
        引用列表，每个引用包含 source 和 value
    """
    citations = []

    # 提取数字引用
    numbers = _NUMBER_PATTERN.findall(text)
    for num in numbers[:10]:  # 限制数量
        citations.append({"source": "data", "value": num, "confidence": 0.7})

    # 提取金融术语引用
    text_upper = text.upper()
    for term in _FINANCIAL_TERMS:
        if term.upper() in text_upper or term in text:
            citations.append({"source": "indicator", "value": term, "confidence": 0.8})

    return citations[:15]  # 限制总数


def _score_data_citations(text: str) -> float:
    """评估数据引用密度"""
    matches = _NUMBER_PATTERN.findall(text)
    count = len(matches)

    # 归一化: 0个=0, 3个=0.5, 6个=0.8, 10+=1.0
    if count == 0:
        return 0.0
    if count <= 2:
        return 0.3
    if count <= 5:
        return 0.5 + (count - 3) * 0.1
    if count <= 10:
        return 0.8 + (count - 6) * 0.04
    return 1.0


def _score_financial_terms(text: str) -> float:
    """评估金融专业术语使用"""
    text_upper = text.upper()
    found = sum(
        1 for term in _FINANCIAL_TERMS
        if term.upper() in text_upper or term in text
    )

    # 归一化: 0=0, 2=0.4, 5=0.7, 8+=1.0
    if found == 0:
        return 0.0
    if found <= 2:
        return 0.2 + found * 0.1
    if found <= 5:
        return 0.4 + (found - 2) * 0.1
    if found <= 8:
        return 0.7 + (found - 5) * 0.1
    return 1.0


def _score_rebuttal_quality(text: str, history: str) -> float:
    """评估反驳质量"""
    if not history:
        # 第一轮没有反驳对象，给基础分
        return 0.4

    # 检查反驳关键词
    rebuttal_count = sum(1 for kw in _REBUTTAL_KEYWORDS if kw in text)

    # 归一化
    if rebuttal_count == 0:
        return 0.1
    if rebuttal_count <= 2:
        return 0.3 + rebuttal_count * 0.1
    if rebuttal_count <= 5:
        return 0.5 + (rebuttal_count - 2) * 0.1
    return min(0.8 + rebuttal_count * 0.02, 1.0)


def _score_novelty(text: str, history: str) -> float:
    """评估论点新颖度（与历史的差异度）"""
    if not history:
        return 0.8  # 第一轮默认较高新颖度

    # 简单的 n-gram 重叠度检测
    text_chars = set(text[:500])  # 取前500字符的字符集
    history_chars = set(history[-1000:])  # 取历史最后1000字符

    if not text_chars:
        return 0.0

    overlap = len(text_chars & history_chars) / len(text_chars)

    # 重叠度越低，新颖度越高
    # overlap 0.3 = novelty 0.9, overlap 0.7 = novelty 0.5, overlap 0.9 = novelty 0.2
    novelty = max(0.0, 1.0 - overlap * 1.2)
    return min(novelty + 0.2, 1.0)  # 加基础分，避免过低
