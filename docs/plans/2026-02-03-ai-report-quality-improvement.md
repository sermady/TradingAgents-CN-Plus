# AI 报告质量改进实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标:** 解决 AI 分析报告中存在的数据不一致、报告矛盾、缺少交叉验证等问题，提升报告质量和一致性。

**架构:** 通过增强报告生成流程的验证环节、添加报告间交叉引用机制、统一建议逻辑。

**技术栈:** Python, Pydantic (数据验证), ReportValidator (现有工具), LangGraph Agent State

---

## 问题概述

通过审查 `results/600765/2026-02-03/` 的报告，发现以下问题：

| 问题ID | 问题描述 | 严重程度 | 影响范围 |
|--------|----------|----------|----------|
| P1 | 报告间建议矛盾（技术=谨慎看多 vs 基本面=卖出） | 高 | 用户决策混乱 |
| P2 | 技术报告称"未提供单日成交量"（已修复但未同步） | 中 | 数据可信度 |
| P3 | 目标价计算权重缺乏依据 | 中 | 投资建议可靠性 |
| P4 | PE_TTM异常值未被过滤 | 中 | 数据质量 |
| P5 | 建议用词过于绝对（"坚决回避"） | 中 | 用户体验 |
| P6 | 缺少报告间交叉引用 | 低 | 信息整合度 |
| P7 | 无不确定性量化（置信度/概率） | 低 | 风险传达 |

---

## Task 1: 创建报告一致性验证器

**目标:** 在报告生成后自动检测并标记报告间的矛盾

**Files:**
- Create: `tradingagents/utils/report_consistency_checker.py`
- Modify: `tradingagents/graph/trading_graph.py` (集成验证)
- Test: `tests/unit/test_report_consistency.py`

**Step 1: 编写一致性检查器类框架**

```python
# tradingagents/utils/report_consistency_checker.py
# -*- coding: utf-8 -*-
"""
报告一致性检查器

检测 AI 生成的各分析师报告之间的矛盾和不一致
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import re

class RecommendationLevel(Enum):
    """投资建议等级"""
    STRONG_BUY = 1
    BUY = 2
    HOLD = 3
    SELL = 4
    STRONG_SELL = 5

@dataclass
class ConsistencyIssue:
    """一致性问题"""
    severity: str  # critical, warning, info
    source_reports: List[str]  # 涉及的报告
    description: str  # 问题描述
    suggestion: str  # 修复建议

class ReportConsistencyChecker:
    """报告一致性检查器"""

    # 建议等级映射
    RECOMMENDATION_MAP = {
        "强烈买入": RecommendationLevel.STRONG_BUY,
        "买入": RecommendationLevel.BUY,
        "持有": RecommendationLevel.HOLD,
        "卖出": RecommendationLevel.SELL,
        "强烈卖出": RecommendationLevel.STRONG_SELL,
        "谨慎看多": RecommendationLevel.BUY,  # 映射到买入
        "谨慎看空": RecommendationLevel.SELL,  # 映射到卖出
        "逢低买入": RecommendationLevel.BUY,
        "立即止盈": RecommendationLevel.SELL,
        "坚决回避": RecommendationLevel.STRONG_SELL,
    }

    def __init__(self):
        self.issues: List[ConsistencyIssue] = []

    def check_all_reports(self, reports: Dict[str, str]) -> List[ConsistencyIssue]:
        """
        检查所有报告的一致性

        Args:
            reports: 包含所有报告的字典，键为报告类型，值为报告内容

        Returns:
            List[ConsistencyIssue]: 发现的问题列表
        """
        self.issues = []

        # 检查1: 投资建议一致性
        self._check_recommendation_consistency(reports)

        # 检查2: 价格数据一致性
        self._check_price_consistency(reports)

        # 检查3: 成交量数据一致性
        self._check_volume_consistency(reports)

        # 检查4: 财务数据一致性
        self._check_financial_consistency(reports)

        return self.issues

    def _check_recommendation_consistency(self, reports: Dict[str, str]):
        """检查各报告的投资建议是否一致"""
        recommendations = {}

        for report_type, content in reports.items():
            if "investment_plan" in report_type or "trader" in report_type or "decision" in report_type:
                rec = self._extract_recommendation(content)
                if rec:
                    recommendations[report_type] = rec

        if len(recommendations) < 2:
            return  # 需要至少2个报告才能比较

        # 检查是否存在严重矛盾
        rec_levels = [self.RECOMMENDATION_MAP.get(r, RecommendationLevel.HOLD)
                      for r in recommendations.values()]

        if max(rec_levels) - min(rec_levels) >= 3:
            self.issues.append(ConsistencyIssue(
                severity="critical",
                source_reports=list(recommendations.keys()),
                description=f"投资建议严重不一致: {recommendations}",
                suggestion="建议在最终决策中明确说明各报告的观点差异，并给出综合判断依据"
            ))

    def _check_price_consistency(self, reports: Dict[str, str]):
        """检查各报告中的价格数据是否一致"""
        prices = {}

        for report_type, content in reports.items():
            # 提取当前价格
            price_match = re.search(r'当前价[^\d]*(¥?\d+\.?\d*)', content)
            if price_match:
                prices[report_type] = float(price_match.group(1).replace('¥', ''))

        if len(prices) < 2:
            return

        price_values = list(prices.values())
        if max(price_values) - min(price_values) > min(price_values) * 0.05:  # 5%差异阈值
            self.issues.append(ConsistencyIssue(
                severity="warning",
                source_reports=list(prices.keys()),
                description=f"价格数据不一致: {prices}",
                suggestion="统一使用数据源管理器提供的实时价格"
            ))

    def _check_volume_consistency(self, reports: Dict[str, str]):
        """检查成交量数据完整性"""
        for report_type, content in reports.items():
            if "market_report" in report_type:
                if "未提供2026-02-03单日成交量" in content:
                    self.issues.append(ConsistencyIssue(
                        severity="info",
                        source_reports=[report_type],
                        description="技术报告缺少单日成交量数据",
                        suggestion="确认数据源管理器已更新成交量增强功能"
                    ))

    def _check_financial_consistency(self, reports: Dict[str, str]):
        """检查财务数据异常值"""
        for report_type, content in reports.items():
            if "fundamentals_report" in report_type:
                # 检查 PE_TTM 异常
                pe_ttm_match = re.search(r'PE[_\(]?TTM[\)_]?\s*[：:]\s*(\d+\.?\d*)倍', content)
                if pe_ttm_match:
                    pe_ttm = float(pe_ttm_match.group(1))
                    if pe_ttm > 100:
                        self.issues.append(ConsistencyIssue(
                            severity="warning",
                            source_reports=[report_type],
                            description=f"PE_TTM值异常: {pe_ttm}倍，可能数据源错误",
                            suggestion="使用PE静态值代替，或标记数据不可用"
                        ))

    def _extract_recommendation(self, content: str) -> str:
        """从报告内容中提取投资建议"""
        # 查找包含建议的段落
        patterns = [
            r'(评级|建议|操作策略)[：:]\s*([^\n]+)',
            r'(买入|卖出|持有|回避|止盈)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(0)

        return None

    def generate_consistency_summary(self) -> str:
        """生成一致性检查摘要"""
        if not self.issues:
            return "✅ 所有报告检查通过，未发现一致性问题。"

        summary = f"⚠️ 发现 {len(self.issues)} 个一致性问题:\n\n"

        for i, issue in enumerate(self.issues, 1):
            icon = "🔴" if issue.severity == "critical" else "🟡" if issue.severity == "warning" else "ℹ️"
            summary += f"{icon} **问题{i}** ({issue.severity}): {issue.description}\n"
            summary += f"   涉及报告: {', '.join(issue.source_reports)}\n"
            summary += f"   建议: {issue.suggestion}\n\n"

        return summary
```

**Step 2: 编写测试用例**

```python
# tests/unit/test_report_consistency.py
# -*- coding: utf-8 -*-
import pytest
from tradingagents.utils.report_consistency_checker import (
    ReportConsistencyChecker,
    RecommendationLevel,
    ConsistencyIssue
)

def test_no_issues_when_consistent():
    """测试: 报告一致时不应有问题"""
    checker = ReportConsistencyChecker()

    reports = {
        "market_report": "当前价¥19.37，建议: 买入",
        "fundamentals_report": "当前价格19.37元，评级: 逢低买入",
        "trader_plan": "操作建议: 买入"
    }

    issues = checker.check_all_reports(reports)
    assert len(issues) == 0

def test_critical_recommendation_conflict():
    """测试: 检测严重的投资建议冲突"""
    checker = ReportConsistencyChecker()

    reports = {
        "market_report": "建议: 买入",
        "fundamentals_report": "评级: 卖出（Strong Sell）"
    }

    issues = checker.check_all_reports(reports)

    # 应该检测到 critical 级别问题
    critical_issues = [i for i in issues if i.severity == "critical"]
    assert len(critical_issues) > 0

def test_missing_volume_data():
    """测试: 检测缺失的成交量数据"""
    checker = ReportConsistencyChecker()

    reports = {
        "market_report": "未提供2026-02-03单日成交量，仅给出5日均量"
    }

    issues = checker.check_all_reports(reports)

    # 应该检测到 info 级别问题
    info_issues = [i for i in issues if i.severity == "info"]
    assert len(info_issues) > 0
    assert "成交量" in info_issues[0].description

def test_abnormal_pe_ttm():
    """测试: 检测异常的PE_TTM值"""
    checker = ReportConsistencyChecker()

    reports = {
        "fundamentals_report": "PE_TTM: 125.8倍（异常高）"
    }

    issues = checker.check_all_reports(reports)

    # 应该检测到 warning 级别问题
    warning_issues = [i for i in issues if i.severity == "warning"]
    assert len(warning_issues) > 0

def test_consistency_summary_generation():
    """测试: 生成一致性摘要"""
    checker = ReportConsistencyChecker()

    # 创建一个有问题的情况
    reports = {
        "market_report": "建议: 买入",
        "fundamentals_report": "评级: 强烈卖出，PE_TTM: 125.8倍"
    }

    checker.check_all_reports(reports)
    summary = checker.generate_consistency_summary()

    assert "⚠️" in summary
    assert "个一致性问题" in summary
```

**Step 3: 运行测试验证失败**

```bash
pytest tests/unit/test_report_consistency.py -v
# 预期: 测试通过（代码已实现）
```

**Step 4: 集成到报告生成流程**

修改 `tradingagents/graph/trading_graph.py`，在 `propagate` 方法的末尾添加一致性检查：

```python
# 在返回 final_state 之前
from tradingagents.utils.report_consistency_checker import ReportConsistencyChecker

# ... 现有代码 ...

# 新增: 报告一致性检查
checker = ReportConsistencyChecker()
issues = checker.check_all_reports({
    "market_report": final_state.get("market_report", ""),
    "fundamentals_report": final_state.get("fundamentals_report", ""),
    "news_report": final_state.get("news_report", ""),
    "investment_plan": final_state.get("investment_plan", ""),
    "trader_investment_plan": final_state.get("trader_investment_plan", ""),
})

if issues:
    logger.warning(f"[报告一致性] 发现 {len(issues)} 个问题")
    final_state["consistency_issues"] = issues
    final_state["consistency_summary"] = checker.generate_consistency_summary()
```

**Step 5: 提交**

```bash
git add tradingagents/utils/report_consistency_checker.py \
        tradingagents/graph/trading_graph.py \
        tests/unit/test_report_consistency.py
git commit -m "feat(report): 添加报告一致性检查器"
```

---

## Task 2: 创建投资建议标准化器

**目标:** 统一各分析师的投资建议格式和用词，避免过于绝对的表述

**Files:**
- Create: `tradingagents/utils/recommendation_standardizer.py`
- Modify: `tradingagents/agents/analysts/market_analyst.py`
- Modify: `tradingagents/agents/analysts/fundamentals_analyst.py`
- Test: `tests/unit/test_recommendation_standardizer.py`

**Step 1: 编写建议标准化器**

```python
# tradingagents/utils/recommendation_standardizer.py
# -*- coding: utf-8 -*-
"""
投资建议标准化器

统一 AI 分析师的投资建议格式和用词
"""

from typing import Dict, Optional
from enum import Enum
import re

class StandardRecommendation(Enum):
    """标准化的投资建议"""
    STRONG_BUY = "强烈买入"
    BUY = "买入"
    MODERATE_BUY = "谨慎买入"
    HOLD = "持有"
    MODERATE_SELL = "谨慎卖出"
    SELL = "卖出"
    STRONG_SELL = "强烈卖出"
    NEUTRAL = "中性观望"

class RecommendationStandardizer:
    """投资建议标准化器"""

    # 建议等级映射（从各种表述到标准等级）
    NORMALIZATION_MAP = {
        # 强烈买入
        "强烈买入": StandardRecommendation.STRONG_BUY,
        "强力买入": StandardRecommendation.STRONG_BUY,
        "重仓买入": StandardRecommendation.STRONG_BUY,

        # 买入
        "买入": StandardRecommendation.BUY,
        "逢低买入": StandardRecommendation.BUY,
        "看多": StandardRecommendation.BUY,
        "谨慎看多": StandardRecommendation.MODERATE_BUY,

        # 持有
        "持有": StandardRecommendation.HOLD,
        "观望": StandardRecommendation.NEUTRAL,
        "中性": StandardRecommendation.NEUTRAL,
        "中性观望": StandardRecommendation.NEUTRAL,

        # 卖出
        "卖出": StandardRecommendation.SELL,
        "逢高卖出": StandardRecommendation.SELL,
        "看空": StandardRecommendation.SELL,
        "谨慎看空": StandardRecommendation.MODERATE_SELL,
        "立即止盈": StandardRecommendation.SELL,
        "建议减仓": StandardRecommendation.MODERATE_SELL,

        # 强烈卖出
        "强烈卖出": StandardRecommendation.STRONG_SELL,
        "坚决回避": StandardRecommendation.STRONG_SELL,
        "清仓": StandardRecommendation.STRONG_SELL,
    }

    # 绝对化用词替换规则
    ABSOLUTE_WORD_REPLACEMENTS = {
        "坚决回避": "建议谨慎观望",
        "必须": "建议",
        "务必": "建议",
        "绝对": "倾向于",
        "一定": "大概率",
    }

    @classmethod
    def normalize(cls, text: str) -> StandardRecommendation:
        """
        将非标准建议映射到标准建议

        Args:
            text: 包含投资建议的文本

        Returns:
            StandardRecommendation: 标准化的建议
        """
        for pattern, rec in cls.NORMALIZATION_MAP.items():
            if pattern in text:
                return rec

        # 默认返回中性
        return StandardRecommendation.NEUTRAL

    @classmethod
    def soften_absolute_language(cls, text: str) -> str:
        """
        软化绝对化用词，让建议更加客观

        Args:
            text: 原始文本

        Returns:
            str: 软化后的文本
        """
        result = text
        for absolute, softer in cls.ABSOLUTE_WORD_REPLACEMENTS.items():
            result = result.replace(absolute, softer)
        return result

    @classmethod
    def extract_recommendation_with_confidence(cls, text: str) -> Dict[str, any]:
        """
        提取投资建议及其置信度

        Args:
            text: 报告文本

        Returns:
            Dict: 包含 recommendation, confidence, reasoning
        """
        recommendation = cls.normalize(text)

        # 尝试提取置信度
        confidence_match = re.search(r'(置信度|确定性|把握)[：:]\s*(\d+[%％])', text)
        confidence = confidence_match.group(2) if confidence_match else "未明确"

        # 尝试提取理由
        reasoning = ""
        reason_match = re.search(r'(理由|依据|原因)[：:]\s*([^\n]+)', text)
        if reason_match:
            reasoning = reason_match.group(2).strip()

        return {
            "recommendation": recommendation.value,
            "confidence": confidence,
            "reasoning": reasoning
        }

    @classmethod
    def format_recommendation_section(cls, report_text: str, analyst_name: str) -> str:
        """
        格式化报告中的投资建议部分

        Args:
            report_text: 原始报告文本
            analyst_name: 分析师名称

        Returns:
            str: 格式化后的建议部分
        """
        rec_info = cls.extract_recommendation_with_confidence(report_text)

        section = f"\n## {analyst_name}投资建议\n\n"
        section += f"| 维度 | 内容 |\n"
        section += f"|------|------|\n"
        section += f"| **建议等级** | {rec_info['recommendation']} |\n"
        section += f"| **置信度** | {rec_info['confidence']} |\n"
        if rec_info['reasoning']:
            section += f"| **核心理由** | {rec_info['reasoning']} |\n"

        return section
```

**Step 2: 编写测试**

```python
# tests/unit/test_recommendation_standardizer.py
# -*- coding: utf-8 -*-
import pytest
from tradingagents.utils.recommendation_standardizer import (
    RecommendationStandardizer,
    StandardRecommendation
)

class TestRecommendationStandardizer:

    def test_normalize_buy_recommendations(self):
        """测试: 标准化各种买入表述"""
        assert RecommendationStandardizer.normalize("建议买入") == StandardRecommendation.BUY
        assert RecommendationStandardizer.normalize("逢低买入") == StandardRecommendation.BUY
        assert RecommendationStandardizer.normalize("谨慎看多") == StandardRecommendation.MODERATE_BUY

    def test_normalize_sell_recommendations(self):
        """测试: 标准化各种卖出表述"""
        assert RecommendationStandardizer.normalize("建议卖出") == StandardRecommendation.SELL
        assert RecommendationStandardizer.normalize("立即止盈") == StandardRecommendation.SELL
        assert RecommendationStandardizer.normalize("坚决回避") == StandardRecommendation.STRONG_SELL

    def test_soften_absolute_language(self):
        """测试: 软化绝对化用词"""
        text = "建议坚决回避，必须立即清仓"
        softened = RecommendationStandardizer.soften_absolute_language(text)

        assert "坚决回避" not in softened
        assert "必须" not in softened
        assert "谨慎观望" in softened or "建议" in softened

    def test_extract_recommendation_with_confidence(self):
        """测试: 提取建议和置信度"""
        text = "建议: 买入，置信度: 75%，理由: 技术面改善"
        result = RecommendationStandardizer.extract_recommendation_with_confidence(text)

        assert result["recommendation"] == StandardRecommendation.BUY.value
        assert result["confidence"] == "75%"
        assert "技术面改善" in result["reasoning"]
```

**Step 3: 运行测试**

```bash
pytest tests/unit/test_recommendation_standardizer.py -v
```

**Step 4: 更新分析师提示词**

在 `market_analyst.py` 和 `fundamentals_analyst.py` 的提示词中添加标准化要求：

```python
# 在提示词中添加
**投资建议规范：**
- 建议等级：使用"强烈买入/买入/谨慎买入/持有/谨慎卖出/卖出/强烈卖出/中性观望"之一
- 避免使用绝对化词汇（如"坚决"、"必须"、"务必"）
- 必须给出置信度（如"置信度: 70%"）
- 必须给出核心理由
```

**Step 5: 提交**

```bash
git add tradingagents/utils/recommendation_standardizer.py \
        tradingagents/agents/analysts/market_analyst.py \
        tradingagents/agents/analysts/fundamentals_analyst.py \
        tests/unit/test_recommendation_standardizer.py
git commit -m "feat(report): 添加投资建议标准化器"
```

---

## Task 3: 创建报告间交叉引用生成器

**目标:** 在最终报告中添加各分析师报告的交叉引用，帮助用户理解不同观点

**Files:**
- Create: `tradingagents/utils/cross_reference_generator.py`
- Modify: `tradingagents/templates/report_templates.py`
- Test: `tests/unit/test_cross_reference_generator.py`

**Step 1: 编写交叉引用生成器**

```python
# tradingagents/utils/cross_reference_generator.py
# -*- coding: utf-8 -*-
"""
报告交叉引用生成器

在最终报告摘要中生成各分析师报告的交叉引用
"""

from typing import Dict, List

class CrossReferenceGenerator:
    """交叉引用生成器"""

    @staticmethod
    def generate_perspective_summary(reports: Dict[str, str]) -> str:
        """
        生成各分析师观点摘要

        Args:
            reports: 所有报告的字典

        Returns:
            str: 观点摘要
        """
        summary = "## 各分析师观点对比\n\n"

        # 提取各报告的核心观点
        perspectives = []

        if "market_report" in reports:
            rec = CrossReferenceGenerator._extract_key_points(reports["market_report"], "技术")
            perspectives.append(("技术分析师", rec))

        if "fundamentals_report" in reports:
            rec = CrossReferenceGenerator._extract_key_points(reports["fundamentals_report"], "基本面")
            perspectives.append(("基本面分析师", rec))

        if "news_report" in reports:
            rec = CrossReferenceGenerator._extract_key_points(reports["news_report"], "消息面")
            perspectives.append(("新闻分析师", rec))

        # 生成表格
        summary += "| 分析师 | 观点 | 建议 |\n"
        summary += "|--------|------|------|\n"

        for name, points in perspectives:
            summary += f"| {name} | {points['view']} | {points['recommendation']} |\n"

        # 添加共识与分歧说明
        summary += "\n### 共识与分歧\n\n"
        recommendations = [p["recommendation"] for p in perspectives]
        summary += CrossReferenceGenerator._analyze_agreement(recommendations)

        return summary

    @staticmethod
    def _extract_key_points(report: str, analyst_type: str) -> Dict[str, str]:
        """提取报告关键点"""
        # 简化实现：查找特定标记
        lines = report.split('\n')

        view = "中性"
        recommendation = "持有"

        for line in lines:
            if "建议" in line or "评级" in line:
                if "买入" in line:
                    recommendation = "买入/看多"
                elif "卖出" in line:
                    recommendation = "卖出/看空"
                elif "持有" in line or "观望" in line:
                    recommendation = "持有/观望"

        return {"view": analyst_type + "分析", "recommendation": recommendation}

    @staticmethod
    def _analyze_agreement(recommendations: List[str]) -> str:
        """分析建议的一致性"""
        buy_count = sum(1 for r in recommendations if "买入" in r or "看多" in r)
        sell_count = sum(1 for r in recommendations if "卖出" in r or "看空" in r)

        if buy_count == len(recommendations):
            return "- ✅ **共识**: 所有分析师均持看多观点\n"
        elif sell_count == len(recommendations):
            return "- ✅ **共识**: 所有分析师均持看空观点\n"
        elif buy_count > 0 and sell_count > 0:
            return "- ⚠️ **分歧**: 分析师观点存在分歧，请仔细阅读各报告详情\n"
        else:
            return "- ➖ **中性**: 分析师普遍持观望态度\n"
```

**Step 2: 编写测试**

```python
# tests/unit/test_cross_reference_generator.py
# -*- coding: utf-8 -*-
import pytest
from tradingagents.utils.cross_reference_generator import CrossReferenceGenerator

def test_generate_perspective_summary():
    """测试: 生成观点摘要"""
    reports = {
        "market_report": "技术分析显示上涨趋势，建议: 买入",
        "fundamentals_report": "基本面良好，建议: 买入",
        "news_report": "无重大新闻，建议: 观望"
    }

    summary = CrossReferenceGenerator.generate_perspective_summary(reports)

    assert "各分析师观点对比" in summary
    assert "技术分析师" in summary
    assert "基本面分析师" in summary
    assert "共识与分歧" in summary

def test_agreement_detection():
    """测试: 检测共识/分歧"""
    # 一致看多
    recs = ["买入", "买入", "买入"]
    analysis = CrossReferenceGenerator._analyze_agreement(recs)
    assert "共识" in analysis and "看多" in analysis

    # 分歧
    recs = ["买入", "卖出", "持有"]
    analysis = CrossReferenceGenerator._analyze_agreement(recs)
    assert "分歧" in analysis
```

**Step 3: 运行测试**

```bash
pytest tests/unit/test_cross_reference_generator.py -v
```

**Step 4: 集成到报告模板**

修改 `report_templates.py`，在生成最终报告时调用交叉引用生成器：

```python
from tradingagents.utils.cross_reference_generator import CrossReferenceGenerator

# 在 generate_final_report 方法中
perspective_section = CrossReferenceGenerator.generate_perspective_summary({
    "market_report": market_report,
    "fundamentals_report": fundamentals_report,
    "news_report": news_report
})

final_report = perspective_section + "\n\n" + final_report
```

**Step 5: 提交**

```bash
git add tradingagents/utils/cross_reference_generator.py \
        tradingagents/templates/report_templates.py \
        tests/unit/test_cross_reference_generator.py
git commit -m "feat(report): 添加报告交叉引用功能"
```

---

## Task 4: 创建数据质量过滤器

**目标:** 在基本面分析中自动过滤异常数据值（如异常的PE_TTM）

**Files:**
- Create: `tradingagents/utils/data_quality_filter.py`
- Modify: `tradingagents/agents/analysts/fundamentals_analyst.py`
- Test: `tests/unit/test_data_quality_filter.py`

**Step 1: 编写数据质量过滤器**

```python
# tradingagents/utils/data_quality_filter.py
# -*- coding: utf-8 -*-
"""
数据质量过滤器

检测和过滤财务数据中的异常值
"""

from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class DataQualityFilter:
    """数据质量过滤器"""

    # 财务指标的合理范围
    REASONABLE_RANGES = {
        "pe_ratio": (0, 100),      # PE倍数
        "pe_ttm": (0, 100),        # PE_TTM倍数
        "pb_ratio": (0, 10),       # PB倍数
        "ps_ratio": (0, 20),       # PS倍数
        "roe": (-1, 1),            # ROE (小数形式，-100%到100%)
        "roa": (-1, 1),            # ROA
        "debt_ratio": (0, 1),      # 资产负债率
        "current_ratio": (0, 10),  # 流动比率
    }

    @classmethod
    def filter_financial_data(cls, financial_data: Dict) -> Tuple[Dict, List[str]]:
        """
        过滤财务数据中的异常值

        Args:
            financial_data: 原始财务数据

        Returns:
            Tuple[Dict, List[str]]: (过滤后的数据, 警告信息列表)
        """
        filtered_data = financial_data.copy()
        warnings = []

        # 检查 PE_TTM
        if "pe_ttm" in financial_data:
            pe_ttm = financial_data["pe_ttm"]
            if pe_ttm and cls._is_out_of_range("pe_ttm", pe_ttm):
                warnings.append(f"PE_TTM值 {pe_ttm} 超出合理范围，已过滤")
                filtered_data["pe_ttm"] = None
                # 使用 PE 静态值作为替代
                if "pe_ratio" in financial_data and financial_data["pe_ratio"]:
                    filtered_data["pe_ttm_replacement"] = financial_data["pe_ratio"]

        # 检查 PE 静态值
        if "pe_ratio" in financial_data:
            pe_ratio = financial_data["pe_ratio"]
            if pe_ratio and cls._is_out_of_range("pe_ratio", pe_ratio):
                warnings.append(f"PE静态值 {pe_ratio} 异常，请确认数据源")

        # 检查 ROE
        if "roe" in financial_data:
            roe = financial_data["roe"]
            if roe is not None and cls._is_out_of_range("roe", roe):
                warnings.append(f"ROE值 {roe} 异常")

        return filtered_data, warnings

    @classmethod
    def _is_out_of_range(cls, metric: str, value: float) -> bool:
        """检查值是否在合理范围内"""
        if metric not in cls.REASONABLE_RANGES:
            return False

        min_val, max_val = cls.REASONABLE_RANGES[metric]
        return value < min_val or value > max_val

    @classmethod
    def generate_quality_summary(cls, warnings: List[str]) -> str:
        """生成数据质量摘要"""
        if not warnings:
            return ""

        summary = "\n### ⚠️ 数据质量说明\n\n"
        for warning in warnings:
            summary += f"- {warning}\n"
        summary += "\n"

        return summary
```

**Step 2: 编写测试**

```python
# tests/unit/test_data_quality_filter.py
# -*- coding: utf-8 -*-
import pytest
from tradingagents.utils.data_quality_filter import DataQualityFilter

class TestDataQualityFilter:

    def test_filter_abnormal_pe_ttm(self):
        """测试: 过滤异常PE_TTM值"""
        data = {"pe_ttm": 125.8, "pe_ratio": 49.5}
        filtered, warnings = DataQualityFilter.filter_financial_data(data)

        assert "pe_ttm" not in filtered or filtered["pe_ttm"] is None
        assert len(warnings) > 0
        assert "PE_TTM" in warnings[0]

    def test_keep_normal_pe_ttm(self):
        """测试: 保留正常PE_TTM值"""
        data = {"pe_ttm": 45.0, "pe_ratio": 49.5}
        filtered, warnings = DataQualityFilter.filter_financial_data(data)

        assert filtered.get("pe_ttm") == 45.0
        assert len(warnings) == 0

    def test_use_pe_as_replacement(self):
        """测试: 用PE静态值替代PE_TTM"""
        data = {"pe_ttm": 125.8, "pe_ratio": 49.5}
        filtered, warnings = DataQualityFilter.filter_financial_data(data)

        assert filtered.get("pe_ttm_replacement") == 49.5

    def test_generate_quality_summary(self):
        """测试: 生成质量摘要"""
        warnings = ["PE_TTM值 125.8 超出合理范围", "ROE值 异常"]
        summary = DataQualityFilter.generate_quality_summary(warnings)

        assert "数据质量说明" in summary
        assert "PE_TTM" in summary
```

**Step 3: 运行测试**

```bash
pytest tests/unit/test_data_quality_filter.py -v
```

**Step 4: 集成到基本面分析师**

在 `fundamentals_analyst.py` 中添加数据过滤：

```python
from tradingagents.utils.data_quality_filter import DataQualityFilter

# 在处理财务数据后
financial_data, quality_warnings = DataQualityFilter.filter_financial_data(raw_financial_data)
quality_summary = DataQualityFilter.generate_quality_summary(quality_warnings)

# 将质量说明添加到提示词中
if quality_summary:
    metadata_info += quality_summary
```

**Step 5: 提交**

```bash
git add tradingagents/utils/data_quality_filter.py \
        tradingagents/agents/analysts/fundamentals_analyst.py \
        tests/unit/test_data_quality_filter.py
git commit -m "feat(report): 添加财务数据质量过滤器"
```

---

## Task 5: 创建不确定性量化器

**目标:** 在投资建议中添加置信度和概率区间

**Files:**
- Create: `tradingagents/utils/uncertainty_quantifier.py`
- Modify: `tradingagents/agents/trader/trader.py`
- Test: `tests/unit/test_uncertainty_quantifier.py`

**Step 1: 编写不确定性量化器**

```python
# tradingagents/utils/uncertainty_quantifier.py
# -*- coding: utf-8 -*-
"""
不确定性量化器

为投资建议添加置信度和概率区间
"""

from typing import Dict, Optional
import re

class UncertaintyQuantifier:
    """不确定性量化器"""

    @staticmethod
    def extract_confidence_from_report(report: str) -> Optional[float]:
        """
        从报告中提取置信度

        Args:
            report: 分析报告文本

        Returns:
            Optional[float]: 置信度 (0-1)，未找到则返回None
        """
        # 查找百分比值
        patterns = [
            r'置信度[：:]\s*(\d+)%',
            r'确定性[：:]\s*(\d+)%',
            r'把握[：:]\s*(\d+)%',
        ]

        for pattern in patterns:
            match = re.search(pattern, report)
            if match:
                return int(match.group(1)) / 100.0

        # 如果没有明确说明，根据报告内容推断
        if "强烈" in report or "确定" in report:
            return 0.75
        elif "谨慎" in report or "可能" in report:
            return 0.55
        elif "观望" in report or "待定" in report:
            return 0.5

        return 0.6  # 默认中等置信度

    @staticmethod
    def calculate_probability_range(
        current_price: float,
        target_price: float,
        confidence: float
    ) -> Dict[str, float]:
        """
        计算目标价的概率区间

        Args:
            current_price: 当前价格
            target_price: 目标价格
            confidence: 置信度 (0-1)

        Returns:
            Dict: 包含 optimistic, base, pessimistic 价格
        """
        # 价格变动幅度
        change_pct = (target_price - current_price) / current_price

        # 根据置信度调整波动范围
        volatility_factor = 1.0 / (confidence + 0.1)  # 置信度越低，波动越大

        base_price = target_price
        optimistic_price = current_price * (1 + change_pct * 1.2)
        pessimistic_price = current_price * (1 + change_pct * 0.6)

        return {
            "optimistic": round(optimistic_price, 2),
            "base": round(base_price, 2),
            "pessimistic": round(pessimistic_price, 2),
        }

    @staticmethod
    def format_uncertainty_section(
        current_price: float,
        target_price: float,
        confidence: float
    ) -> str:
        """
        格式化不确定性说明部分

        Args:
            current_price: 当前价格
            target_price: 目标价格
            confidence: 置信度

        Returns:
            str: 格式化的不确定性说明
        """
        ranges = UncertaintyQuantifier.calculate_probability_range(
            current_price, target_price, confidence
        )

        section = "### 📊 概率评估\n\n"
        section += f"| 情景 | 目标价 | 概率 |\n"
        section += f"|------|--------|------|\n"
        section += f"| 乐观情景 | ¥{ranges['optimistic']} | {min(confidence * 0.4, 0.3):.0%} |\n"
        section += f"| 基准情景 | ¥{ranges['base']} | {confidence:.0%} |\n"
        section += f"| 谨慎情景 | ¥{ranges['pessimistic']} | {min((1-confidence) * 0.6, 0.4):.0%} |\n"

        section += f"\n**综合置信度**: {confidence:.0%}\n"
        section += f"**当前价格**: ¥{current_price}\n"

        return section
```

**Step 2: 编写测试**

```python
# tests/unit/test_uncertainty_quantifier.py
# -*- coding: utf-8 -*-
import pytest
from tradingagents.utils.uncertainty_quantifier import UncertaintyQuantifier

class TestUncertaintyQuantifier:

    def test_extract_confidence_from_report(self):
        """测试: 从报告中提取置信度"""
        report = "建议: 买入，置信度: 75%"
        confidence = UncertaintyQuantifier.extract_confidence_from_report(report)
        assert confidence == 0.75

    def test_calculate_probability_range(self):
        """测试: 计算概率区间"""
        ranges = UncertaintyQuantifier.calculate_probability_range(
            current_price=19.37,
            target_price=22.0,
            confidence=0.7
        )

        assert "optimistic" in ranges
        assert "base" in ranges
        assert ranges["base"] == 22.0
        assert ranges["optimistic"] > ranges["base"]

    def test_format_uncertainty_section(self):
        """测试: 格式化不确定性说明"""
        section = UncertaintyQuantifier.format_uncertainty_section(
            current_price=19.37,
            target_price=22.0,
            confidence=0.75
        )

        assert "概率评估" in section
        assert "乐观情景" in section
        assert "基准情景" in section
        assert "谨慎情景" in section
        assert "75%" in section
```

**Step 3: 运行测试**

```bash
pytest tests/unit/test_uncertainty_quantifier.py -v
```

**Step 4: 集成到交易员输出**

在 `trader.py` 中修改决策输出格式：

```python
from tradingagents.utils.uncertainty_quantifier import UncertaintyQuantifier

# 在生成最终决策时
uncertainty_section = UncertaintyQuantifier.format_uncertainty_section(
    current_price=current_price,
    target_price=target_price,
    confidence=confidence or 0.6
)

final_decision += "\n\n" + uncertainty_section
```

**Step 5: 提交**

```bash
git add tradingagents/utils/uncertainty_quantifier.py \
        tradingagents/agents/trader/trader.py \
        tests/unit/test_uncertainty_quantifier.py
git commit -m "feat(report): 添加不确定性量化功能"
```

---

## 总结

### 实施顺序

1. **Task 1**: 报告一致性验证器（最高优先级，解决核心矛盾问题）
2. **Task 2**: 投资建议标准化器（解决用词绝对化问题）
3. **Task 4**: 数据质量过滤器（解决PE_TTM等异常值问题）
4. **Task 3**: 报告交叉引用生成器（增强信息整合）
5. **Task 5**: 不确定性量化器（提升风险传达）

### 验收标准

- [ ] 所有测试用例通过
- [ ] 生成的新报告中不再出现"坚决回避"等绝对化表述
- [ ] 异常的PE_TTM值被自动过滤或标记
- [ ] 最终报告包含各分析师观点对比
- [ ] 投资建议附带概率评估

### 回滚计划

如出现问题，可通过以下命令回滚：
```bash
git revert HEAD~5..HEAD
```

---

**计划创建日期:** 2026-02-03
**预计完成时间:** 5 个任务会话
**依赖:** 现有 ReportValidator, 数据源管理器
