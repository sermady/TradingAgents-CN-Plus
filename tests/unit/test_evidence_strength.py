# -*- coding: utf-8 -*-
"""
证据强度计算器单元测试 (Phase 2.2)

测试范围:
- EvidenceStrengthCalculator.calculate_evidence_strength()
- 逻辑完整性评分
- 数据引用密度评分
- 数据质量评分影响
- 引用提取功能

测试策略:
- Happy Path: 正常论据评分
- Edge Cases: 空文本、无引用
- Error Cases: 无效输入
"""

import pytest

from tradingagents.utils.evidence_strength import (
    EvidenceStrengthCalculator,
    get_evidence_calculator,
    calculate_evidence_strength,
)


@pytest.mark.unit
class TestEvidenceStrengthCalculator:
    """证据强度计算器测试套件"""

    @pytest.fixture
    def calculator(self):
        """创建计算器实例"""
        return get_evidence_calculator()

    # ========== Happy Path Tests ==========

    def test_calculate_strong_argument(self, calculator):
        """测试: 强有力的论据应该得到高分"""
        argument = """
        根据Tushare数据显示，该公司PE为15倍，低于行业平均水平。
        因为营收增长达到30%，所以预计股价有上涨空间。
        此外，ROE达到25%，超过大多数同行企业。
        综上所述，该股票具有投资价值。
        """

        score = calculator.calculate_evidence_strength(argument)

        assert score >= 0.6  # 应该得到较高分数
        assert score <= 1.0

    def test_calculate_weak_argument(self, calculator):
        """测试: 无力论据应该得到低分"""
        argument = "这只股票可能会涨。"

        score = calculator.calculate_evidence_strength(argument)

        assert score >= 0.0
        assert score < 0.5  # 应该得到较低分数

    def test_calculate_with_citations(self, calculator):
        """测试: 带引用的论据分数更高"""
        argument = """
        [数据引用: Tushare]PE为15倍，[数据引用: AKShare]PB为2.5倍。
        根据这些数据，我们认为股票被低估。
        """

        score = calculator.calculate_evidence_strength(argument)

        assert score >= 0.4  # 有引用应该有基础分
        assert score <= 1.0

    # ========== Edge Cases ==========

    def test_empty_argument(self, calculator):
        """测试: 空论据应该返回0"""
        score = calculator.calculate_evidence_strength("")

        assert score == 0.0

    def test_whitespace_only(self, calculator):
        """测试: 只有空白字符应该返回0或接近0"""
        score = calculator.calculate_evidence_strength("   \n\t  ")

        # 空白字符串应该得到低分（虽然可能由于某些检查返回非零值）
        assert score < 0.3

    def test_very_short_argument(self, calculator):
        """测试: 非常短的论据应该返回0或接近0"""
        score = calculator.calculate_evidence_strength("买")

        # 非常短的论据应该得到0分（基础分需要20字符以上）
        assert score < 0.3

    def test_argument_without_logic_keywords(self, calculator):
        """测试: 没有逻辑连接词的论据分数较低"""
        argument = "股票价格 PE PB ROE 营收增长"

        score = calculator.calculate_evidence_strength(argument)

        assert score >= 0.0
        assert score < 0.5

    # ========== Data Quality Impact Tests ==========

    def test_low_data_quality_reduces_score(self, calculator):
        """测试: 低数据质量应该降低分数"""
        argument = """
        根据数据显示，该公司财务状况良好。
        因为营收增长，所以具有投资价值。
        """

        # 高质量数据
        score_high_quality = calculator.calculate_evidence_strength(
            argument, data_quality_score=95.0
        )

        # 低质量数据
        score_low_quality = calculator.calculate_evidence_strength(
            argument, data_quality_score=50.0
        )

        assert score_low_quality < score_high_quality

    def test_f_grade_data_quality_significant_penalty(self, calculator):
        """测试: F级数据质量应该显著降低分数"""
        argument = """
        根据数据，该公司PE为15倍，增长30%，具有投资价值。
        """

        # A级数据
        score_a = calculator.calculate_evidence_strength(
            argument, data_quality_score=95.0
        )

        # F级数据
        score_f = calculator.calculate_evidence_strength(
            argument, data_quality_score=40.0
        )

        # F级应该比A级低至少10%
        assert score_a - score_f >= 0.10

    # ========== Citation Extraction Tests ==========

    def test_extract_citations_from_text(self, calculator):
        """测试: 从文本中提取引用"""
        text = """
        根据[数据引用: Tushare]和[来源: AKShare]的数据显示，
        PE为15倍，PB为2.5倍。
        数据来源：Tushare显示ROE为25%。
        """

        citations = calculator.extract_citations(text)

        assert len(citations) >= 2
        # 检查是否有Tushare引用
        assert any("Tushare" in c["source"] for c in citations)
        # 检查是否有AKShare引用
        assert any("AKShare" in c["source"] for c in citations)

    def test_extract_citations_deduplication(self, calculator):
        """测试: 引用去重"""
        text = """
        [数据引用: Tushare]PE为15倍。
        [数据引用: Tushare]PB为2.5倍。
        """

        citations = calculator.extract_citations(text)

        # 应该去重，只有一个Tushare引用
        tushare_citations = [c for c in citations if "Tushare" in c["source"]]
        assert len(tushare_citations) <= 1

    # ========== Citation Score Tests ==========

    def test_no_citations_low_score(self, calculator):
        """测试: 没有引用应该得到低分"""
        argument = "该公司财务状况良好，具有投资价值。"

        citations = []

        score = calculator._calculate_citation_score(argument, citations)

        assert score == 0.0

    def test_few_citations_medium_score(self, calculator):
        """测试: 少量引用应该得到中等分数"""
        argument = "[数据引用: Tushare]PE为15倍。"

        citations = calculator.extract_citations(argument)

        score = calculator._calculate_citation_score(argument, citations)

        assert score >= 0.5
        assert score <= 0.8

    def test_many_citations_high_score(self, calculator):
        """测试: 大量引用应该得到高分"""
        argument = """
        [数据引用: Tushare]PE为15倍。
        [数据引用: AKShare]PB为2.5倍。
        [数据引用: BaoStock]ROE为25%。
        [数据引用: Tushare]营收增长30%。
        [数据引用: AKShare]净利润增长20%。
        [数据引用: BaoStock]毛利率40%。
        """

        citations = calculator.extract_citations(argument)

        score = calculator._calculate_citation_score(argument, citations)

        assert score >= 0.8
        assert score <= 1.0

    # ========== Logic Score Tests ==========

    def test_strong_logic_high_score(self, calculator):
        """测试: 强逻辑应该得到高分"""
        argument = """
        因为营收增长30%，所以净利润增加。
        鉴于PE低于行业平均，因此股票被低估。
        此外，ROE达到25%，超过了大多数同行。
        综上所述，该股票具有投资价值。
        """

        score = calculator._calculate_logic_score(argument)

        assert score >= 0.6
        assert score <= 1.0

    def test_weak_logic_low_score(self, calculator):
        """测试: 弱逻辑应该得到低分"""
        argument = "股票价格 营收 ROE PE"

        score = calculator._calculate_logic_score(argument)

        assert score < 0.5

    # ========== Confidence Estimation Tests ==========

    def test_estimate_confidence_tushare(self, calculator):
        """测试: Tushare应该有高可信度"""
        confidence = calculator._estimate_confidence("Tushare")

        assert confidence == 0.9

    def test_estimate_confidence_akshare(self, calculator):
        """测试: AKShare应该有中等可信度"""
        confidence = calculator._estimate_confidence("AKShare")

        assert confidence == 0.7

    def test_estimate_confidence_baostock(self, calculator):
        """测试: BaoStock应该有中等偏上可信度"""
        confidence = calculator._estimate_confidence("BaoStock")

        assert confidence == 0.75

    def test_estimate_confidence_unknown(self, calculator):
        """测试: 未知来源应该有低可信度"""
        confidence = calculator._estimate_confidence("UnknownSource")

        assert confidence == 0.5

    # ========== Module Function Tests ==========

    def test_calculate_evidence_strength_module_function(self):
        """测试: 模块函数正常工作"""
        argument = "[数据引用: Tushare]PE为15倍，增长30%。"

        score = calculate_evidence_strength(argument)

        assert score >= 0.0
        assert score <= 1.0

    def test_get_evidence_calculator_singleton(self):
        """测试: 计算器是单例"""
        calc1 = get_evidence_calculator()
        calc2 = get_evidence_calculator()

        assert calc1 is calc2

    # ========== Score Components Tests ==========

    def test_score_components_sum(self, calculator):
        """测试: 评分组件总和正确"""
        argument = """
        [数据引用: Tushare]PE为15倍。
        因为增长30%，所以具有价值。
        """

        # 各组件评分
        base_score = 0.2  # 有实质内容
        logic_score = calculator._calculate_logic_score(argument) * 0.3
        citation_score = calculator._calculate_citation_score(
            argument, calculator.extract_citations(argument)
        ) * 0.3
        quality_score = (95.0 / 100.0) * 0.2  # A级质量

        expected_range = base_score + logic_score + citation_score + quality_score
        actual_score = calculator.calculate_evidence_strength(
            argument, data_quality_score=95.0
        )

        # 应该在预期范围内（允许小误差）
        assert abs(actual_score - expected_range) < 0.01

    # ========== Integration Tests ==========

    def test_full_calculation_with_all_components(self, calculator):
        """测试: 完整计算包含所有组件"""
        argument = """
        根据[数据引用: Tushare]和[来源: AKShare]的数据显示，
        该公司PE为15倍，低于行业平均20倍。
        因为营收增长达到30%，所以预计股价有上涨空间。
        此外，ROE为25%，超过同行平均15%。
        综合以上数据，我们给予买入评级。
        """

        score = calculator.calculate_evidence_strength(
            argument,
            data_quality_score=90.0,
        )

        # 应该得到较高分数
        assert score >= 0.7
        assert score <= 1.0

    def test_calculation_with_custom_citations(self, calculator):
        """测试: 使用自定义引用列表"""
        argument = "该公司财务状况良好。"

        custom_citations = [
            {"source": "Tushare", "claim": "PE=15", "confidence": 0.9},
            {"source": "AKShare", "claim": "ROE=25", "confidence": 0.7},
        ]

        score = calculator.calculate_evidence_strength(
            argument,
            data_quality_score=80.0,
            citations=custom_citations,
        )

        # 应该使用自定义引用
        assert score > 0.0
        assert score <= 1.0


@pytest.mark.unit
class TestEvidenceStrengthUtilityFunctions:
    """证据强度工具函数测试"""

    def test_calculate_evidence_strength_with_defaults(self):
        """测试: 使用默认参数"""
        argument = "测试论据"

        score = calculate_evidence_strength(argument)

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_calculate_evidence_strength_explicit_params(self):
        """测试: 显式参数"""
        argument = "测试论据"

        score = calculate_evidence_strength(
            argument,
            data_quality_score=75.0,
            citations=[],
        )

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
