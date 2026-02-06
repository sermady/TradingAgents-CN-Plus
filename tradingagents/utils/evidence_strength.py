# -*- coding: utf-8 -*-
"""
证据强度计算工具 (Phase 2.2)

用于评估辩论中论据的证据强度，支持提前收敛决策
"""

import re
import logging
from typing import Dict, List, Tuple, Any, Optional

logger = logging.getLogger(__name__)


class EvidenceStrengthCalculator:
    """
    证据强度计算器

    评估论据的证据强度 (0-1)，基于:
    - 逻辑完整性 (40%)
    - 数据引用密度 (30%)
    - 数据质量评分 (30%)
    """

    # 数据引用模式
    CITATION_PATTERNS = [
        r'\[数据引用:\s*([^\]]+)\]',  # [数据引用: Tushare]
        r'\[来源:\s*([^\]]+)\]',         # [来源: Tushare]
        r'数据来源[:：]\s*([^\n，。]+)',   # 数据来源：Tushare
        r'根据\s+([^\n，。]+)(?:数据|显示)',  # 根据Tushare数据
    ]

    # 逻辑完整性关键词
    LOGIC_KEYWORDS = {
        'strong': ['因为', '所以', '因此', '导致', '由于', '鉴于', '基于'],
        'transition': ['然而', '但是', '另一方面', '相比之下', '相反'],
        'conclusion': ['综上所述', '总的来看', '最终', '结论'],
        'quantitative': ['增长', '下降', '上升', '超过', '低于', '达到'],
    }

    def calculate_evidence_strength(
        self,
        argument: str,
        data_quality_score: float = 100.0,
        citations: Optional[List[Dict]] = None
    ) -> float:
        """
        计算论据的证据强度

        评分构成:
        - 基础分 (20%): 有实质内容即可获得
        - 逻辑完整性 (30%): 因果关系和连接词
        - 数据引用密度 (30%): 引用数量和质量
        - 数据质量评分 (20%): 数据源可信度

        Args:
            argument: 论点文本
            data_quality_score: 数据质量评分 (0-100)
            citations: 数据引用列表（可选，如果不提供则从文本提取）

        Returns:
            float: 证据强度评分 (0-1)
        """
        if not argument:
            return 0.0

        # 如果没有提供引用列表，从文本中提取
        if citations is None:
            citations = self.extract_citations(argument)

        # 1. 基础分 (20%) - 有实质内容即可获得
        base_score = 0.2 if len(argument.strip()) > 20 else 0.0

        # 2. 逻辑完整性评分 (30%)
        logic_score = self._calculate_logic_score(argument) * 0.3

        # 3. 数据引用密度评分 (30%)
        citation_score = self._calculate_citation_score(argument, citations) * 0.3

        # 4. 数据质量评分 (20%)
        quality_score = (data_quality_score / 100.0) * 0.2

        total_score = base_score + logic_score + citation_score + quality_score

        logger.debug(
            f"证据强度计算: 基础={base_score:.2f}, 逻辑={logic_score:.2f}, "
            f"引用={citation_score:.2f}, 质量={quality_score:.2f}, 总分={total_score:.2f}"
        )

        return min(max(total_score, 0.0), 1.0)

    def _calculate_logic_score(self, argument: str) -> float:
        """
        计算逻辑完整性评分

        检查:
        - 论证结构 (因->果)
        - 逻辑连接词
        - 结论陈述
        - 数据量化程度
        """
        score = 0.2  # 基础分

        # 检查逻辑连接词 - 降低阈值使其更容易获得分数
        for keyword_group in self.LOGIC_KEYWORDS.values():
            found = sum(1 for keyword in keyword_group if keyword in argument)
            score += min(found / 2, 1.0) * 0.15  # 每组最多贡献0.15分，2个关键词即可满分

        # 检查数据量化（数字、百分比等）
        quantitative_patterns = [
            r'\d+%',  # 百分比
            r'\d+\.?\d*\s*(倍|倍|元|亿|万)',  # 数值
            r'(增长|下降|上升|超过|低于)\s*\d+',  # 变化量
        ]
        for pattern in quantitative_patterns:
            if re.search(pattern, argument):
                score += 0.1
                break

        return min(score, 1.0)

    def _calculate_citation_score(
        self,
        argument: str,
        citations: List[Dict]
    ) -> float:
        """
        计算数据引用密度评分

        评分标准:
        - 0个引用: 0分
        - 1-2个引用: 0.5分
        - 3-5个引用: 0.8分
        - 6+个引用: 1.0分
        """
        if citations is None:
            citations = self.extract_citations(argument)

        citation_count = len(citations)

        if citation_count == 0:
            return 0.0
        elif citation_count <= 2:
            return 0.5
        elif citation_count <= 5:
            return 0.8
        else:
            return 1.0

    def extract_citations(self, text: str) -> List[Dict[str, Any]]:
        """
        从文本中提取数据引用

        返回格式:
        [
            {"source": "Tushare", "claim": "PE=15", "confidence": 0.9},
            {"source": "AKShare", "claim": "MA5>MA10", "confidence": 0.8},
        ]
        """
        citations = []

        # 使用正则表达式匹配各种引用格式
        for pattern in self.CITATION_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                source = match.strip()
                # 提取引用后的声明内容
                claim = self._extract_claim_near_citation(text, source)
                citations.append({
                    "source": source,
                    "claim": claim,
                    "confidence": self._estimate_confidence(source)
                })

        # 去重
        unique_citations = []
        seen = set()
        for citation in citations:
            key = (citation["source"], citation["claim"])
            if key not in seen:
                seen.add(key)
                unique_citations.append(citation)

        logger.debug(f"从文本中提取到 {len(unique_citations)} 个数据引用")

        return unique_citations

    def _extract_claim_near_citation(self, text: str, source: str) -> str:
        """
        提取引用附近的内容作为声明

        查找引用格式前后的内容，提取简短的声明
        """
        # 在文本中查找引用位置
        pattern = rf'\[数据引用:\s*{re.escape(source)}\]'
        match = re.search(pattern, text)

        if not match:
            return ""

        # 获取引用前后各50个字符
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end]

        # 简化声明，去除引用标记本身
        claim = re.sub(r'\[数据引用[^\]]*\]', '', context).strip()

        # 截取前30个字符作为声明
        return claim[:30]

    def _estimate_confidence(self, source: str) -> float:
        """
        根据数据源估计可信度

        基于数据源可靠性:
        - MongoDB/Tushare: 0.9
        - BaoStock: 0.75
        - AKShare: 0.7
        - 其他: 0.5
        """
        source_lower = source.lower()

        if 'mongodb' in source_lower or 'tushare' in source_lower:
            return 0.9
        elif 'baostock' in source_lower:
            return 0.75
        elif 'akshare' in source_lower:
            return 0.7
        else:
            return 0.5


# 全局实例
_calculator = None


def get_evidence_calculator() -> EvidenceStrengthCalculator:
    """获取证据强度计算器实例"""
    global _calculator
    if _calculator is None:
        _calculator = EvidenceStrengthCalculator()
    return _calculator


def calculate_evidence_strength(
    argument: str,
    data_quality_score: float = 100.0,
    citations: Optional[List[Dict]] = None
) -> float:
    """
    计算论据的证据强度 (便捷函数)

    Args:
        argument: 论点文本
        data_quality_score: 数据质量评分 (0-100)
        citations: 数据引用列表（可选）

    Returns:
        float: 证据强度评分 (0-1)
    """
    calculator = get_evidence_calculator()
    return calculator.calculate_evidence_strength(argument, data_quality_score, citations)
