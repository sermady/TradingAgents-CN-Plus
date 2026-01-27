# -*- coding: utf-8 -*-
"""
报告摘要生成器

将冗长的辩论报告（如 research_team_decision.md, risk_management_decision.md）
精简为易读的摘要版本，同时保留关键信息。

目标：
- 将 100KB+ 的报告压缩到 10KB 以内
- 保留结论、关键论点、数据验证结果
- 生成结构化的摘要格式
"""

import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime

# 导入日志
try:
    from tradingagents.utils.logging_init import get_logger
    logger = get_logger("report_summarizer")
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


class ReportSummarizer:
    """报告摘要生成器"""

    # 摘要目标大小（字符数）
    TARGET_SUMMARY_SIZE = 8000  # 约 8KB
    MAX_SUMMARY_SIZE = 12000    # 最大 12KB

    # 关键词权重（用于识别重要句子）
    IMPORTANCE_KEYWORDS = {
        # 结论性关键词（最高权重）
        "conclusion": ["建议", "结论", "决策", "判断", "总结", "最终", "综合", "买入", "卖出", "持有"],
        # 数据关键词（高权重）
        "data": ["市盈率", "PE", "PB", "ROE", "成交量", "涨跌", "价格", "估值", "营收", "利润"],
        # 风险关键词（中高权重）
        "risk": ["风险", "警告", "注意", "谨慎", "波动", "下跌", "亏损", "止损"],
        # 论点关键词（中权重）
        "argument": ["因为", "因此", "所以", "由于", "导致", "表明", "显示", "支撑", "反驳"],
    }

    def __init__(self):
        self.extraction_stats = {}

    def summarize_research_decision(
        self,
        full_content: str,
        stock_code: str = "",
        company_name: str = ""
    ) -> Tuple[str, str]:
        """
        生成研究团队决策报告的摘要

        Args:
            full_content: 完整报告内容
            stock_code: 股票代码
            company_name: 公司名称

        Returns:
            Tuple[str, str]: (摘要版本, 完整版本标记)
        """
        if not full_content or len(full_content) < 1000:
            # 内容太短，无需摘要
            return full_content, full_content

        logger.info(f"📝 [摘要生成] 研究决策报告原始长度: {len(full_content):,} 字符")

        # 提取关键部分
        conclusion = self._extract_conclusion(full_content)
        key_arguments = self._extract_key_arguments(full_content)
        data_points = self._extract_data_points(full_content)
        recommendation = self._extract_recommendation(full_content)

        # 构建摘要
        summary = self._build_research_summary(
            conclusion=conclusion,
            key_arguments=key_arguments,
            data_points=data_points,
            recommendation=recommendation,
            stock_code=stock_code,
            company_name=company_name,
            original_length=len(full_content)
        )

        logger.info(f"📝 [摘要生成] 研究决策报告摘要长度: {len(summary):,} 字符 (压缩率: {len(summary)/len(full_content)*100:.1f}%)")

        return summary, full_content

    def summarize_risk_decision(
        self,
        full_content: str,
        stock_code: str = "",
        company_name: str = ""
    ) -> Tuple[str, str]:
        """
        生成风险管理决策报告的摘要

        Args:
            full_content: 完整报告内容
            stock_code: 股票代码
            company_name: 公司名称

        Returns:
            Tuple[str, str]: (摘要版本, 完整版本)
        """
        if not full_content or len(full_content) < 1000:
            return full_content, full_content

        logger.info(f"📝 [摘要生成] 风险决策报告原始长度: {len(full_content):,} 字符")

        # 提取关键部分
        conclusion = self._extract_conclusion(full_content)
        risk_factors = self._extract_risk_factors(full_content)
        risk_assessment = self._extract_risk_assessment(full_content)
        recommendation = self._extract_recommendation(full_content)

        # 构建摘要
        summary = self._build_risk_summary(
            conclusion=conclusion,
            risk_factors=risk_factors,
            risk_assessment=risk_assessment,
            recommendation=recommendation,
            stock_code=stock_code,
            company_name=company_name,
            original_length=len(full_content)
        )

        logger.info(f"📝 [摘要生成] 风险决策报告摘要长度: {len(summary):,} 字符 (压缩率: {len(summary)/len(full_content)*100:.1f}%)")

        return summary, full_content

    def _extract_conclusion(self, content: str) -> str:
        """提取结论部分"""
        # 尝试多种模式匹配结论
        patterns = [
            r'(?:结论|总结|最终决策|综合评估)[：:\s]*(.{100,800}?)(?=\n\n|\n#|$)',
            r'(?:建议|决策)[：:\s]*\*{0,2}(买入|卖出|持有)\*{0,2}(.{0,500}?)(?=\n\n|\n#|$)',
            r'(?:综合来看|总体而言|综上所述)[，,](.{100,600}?)(?=\n\n|\n#|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(0).strip()[:800]

        # 如果没有匹配到，提取最后一段作为结论
        paragraphs = content.split('\n\n')
        for para in reversed(paragraphs):
            if len(para.strip()) > 100:
                return para.strip()[:800]

        return ""

    def _extract_key_arguments(self, content: str) -> List[str]:
        """提取关键论点"""
        arguments = []

        # 查找看涨/看跌论点
        bull_pattern = r'(?:看涨|多头|积极)[^：:]*[：:](.{50,300}?)(?=\n\n|\n-|\n#|$)'
        bear_pattern = r'(?:看跌|空头|消极|风险)[^：:]*[：:](.{50,300}?)(?=\n\n|\n-|\n#|$)'

        for pattern in [bull_pattern, bear_pattern]:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches[:3]:  # 每类最多3个
                clean_arg = match.strip()
                if len(clean_arg) > 50:
                    arguments.append(clean_arg[:300])

        # 如果论点不足，按重要性提取句子
        if len(arguments) < 4:
            important_sentences = self._extract_important_sentences(content, 6 - len(arguments))
            arguments.extend(important_sentences)

        return arguments[:6]  # 最多6个关键论点

    def _extract_data_points(self, content: str) -> List[str]:
        """提取关键数据点"""
        data_points = []

        # 查找包含数字的关键数据
        patterns = [
            r'(?:市盈率|PE)[：:\s]*(\d+\.?\d*)',
            r'(?:市净率|PB)[：:\s]*(\d+\.?\d*)',
            r'(?:ROE|净资产收益率)[：:\s]*(\d+\.?\d*%?)',
            r'(?:当前价|现价|股价)[：:\s]*[¥￥$]?(\d+\.?\d*)',
            r'(?:目标价)[：:\s]*[¥￥$]?(\d+\.?\d*)',
            r'(?:涨跌幅|涨幅|跌幅)[：:\s]*([+-]?\d+\.?\d*%?)',
            r'(?:成交量)[：:\s]*([\d,]+\.?\d*)\s*(?:股|万股)?',
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                # 获取完整上下文
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                context = content[start:end].strip()
                if context not in data_points:
                    data_points.append(context)

        return data_points[:8]  # 最多8个数据点

    def _extract_risk_factors(self, content: str) -> List[str]:
        """提取风险因素"""
        risk_factors = []

        # 查找风险相关内容
        patterns = [
            r'(?:风险因素|主要风险|潜在风险)[：:\s]*(.{50,300}?)(?=\n\n|\n-|\n#|$)',
            r'(?:需要注意|值得关注|警惕)[：:\s]*(.{30,200}?)(?=\n\n|\n。|$)',
            r'(?:下行风险|不利因素)[：:\s]*(.{50,300}?)(?=\n\n|\n-|\n#|$)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches[:3]:
                clean_risk = match.strip()
                if len(clean_risk) > 30:
                    risk_factors.append(clean_risk[:300])

        return risk_factors[:5]

    def _extract_risk_assessment(self, content: str) -> str:
        """提取风险评估结果"""
        patterns = [
            r'(?:风险等级|风险评级|风险评估)[：:\s]*(.{20,200}?)(?=\n|\n\n|$)',
            r'(?:激进|保守|中性)[^：:]*分析师[^：:]*[：:](.{50,300}?)(?=\n\n|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, content, re.DOTALL)
            if match:
                return match.group(0).strip()[:400]

        return ""

    def _extract_recommendation(self, content: str) -> str:
        """提取投资建议"""
        patterns = [
            r'(?:最终交易建议|投资建议|建议)[：:\s]*\*{0,2}(买入|持有|卖出)\*{0,2}',
            r'\*{2}(买入|持有|卖出)\*{2}',
        ]

        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)

        return "未明确"

    def _extract_important_sentences(self, content: str, count: int) -> List[str]:
        """按重要性提取句子"""
        sentences = re.split(r'[。！？\n]', content)
        scored_sentences = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 30 or len(sentence) > 300:
                continue

            score = 0
            for category, keywords in self.IMPORTANCE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in sentence:
                        if category == "conclusion":
                            score += 3
                        elif category == "data":
                            score += 2
                        elif category == "risk":
                            score += 2
                        else:
                            score += 1

            if score > 0:
                scored_sentences.append((score, sentence))

        # 按分数排序，取前N个
        scored_sentences.sort(key=lambda x: x[0], reverse=True)
        return [s[1] for s in scored_sentences[:count]]

    def _build_research_summary(
        self,
        conclusion: str,
        key_arguments: List[str],
        data_points: List[str],
        recommendation: str,
        stock_code: str,
        company_name: str,
        original_length: int
    ) -> str:
        """构建研究团队决策摘要"""
        display_name = company_name if company_name else stock_code

        summary = f"""# {display_name} 研究团队决策摘要

> 本摘要从 {original_length:,} 字符的完整辩论中提取关键信息
> 完整版本请查看: research_team_decision_full.md

---

## 核心结论

**投资建议**: **{recommendation}**

{conclusion if conclusion else "（结论提取中...）"}

---

## 关键论点

"""
        # 添加关键论点
        if key_arguments:
            for i, arg in enumerate(key_arguments, 1):
                summary += f"### 论点 {i}\n{arg}\n\n"
        else:
            summary += "*暂无明确论点*\n\n"

        # 添加数据验证
        summary += "---\n\n## 关键数据点\n\n"
        if data_points:
            summary += "| 指标 | 数值 |\n|------|------|\n"
            for dp in data_points:
                # 清理并格式化数据点
                clean_dp = dp.replace('\n', ' ').strip()
                summary += f"| {clean_dp} |\n"
        else:
            summary += "*暂无关键数据*\n\n"

        # 添加时间戳
        summary += f"""
---

*摘要生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*此为精简摘要，如需查看完整辩论过程，请参阅完整版报告*
"""

        return summary

    def _build_risk_summary(
        self,
        conclusion: str,
        risk_factors: List[str],
        risk_assessment: str,
        recommendation: str,
        stock_code: str,
        company_name: str,
        original_length: int
    ) -> str:
        """构建风险管理决策摘要"""
        display_name = company_name if company_name else stock_code

        summary = f"""# {display_name} 风险管理决策摘要

> 本摘要从 {original_length:,} 字符的完整风险辩论中提取关键信息
> 完整版本请查看: risk_management_decision_full.md

---

## 风险评估结论

**最终建议**: **{recommendation}**

{risk_assessment if risk_assessment else "（风险评估提取中...）"}

---

## 主要风险因素

"""
        # 添加风险因素
        if risk_factors:
            for i, risk in enumerate(risk_factors, 1):
                summary += f"### 风险 {i}\n{risk}\n\n"
        else:
            summary += "*暂无明确风险因素*\n\n"

        # 添加结论
        if conclusion:
            summary += f"---\n\n## 综合评估\n\n{conclusion}\n\n"

        # 添加时间戳
        summary += f"""
---

*摘要生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
*此为精简摘要，如需查看完整风险辩论过程，请参阅完整版报告*
"""

        return summary


def summarize_report(
    content: str,
    report_type: str,
    stock_code: str = "",
    company_name: str = ""
) -> Tuple[str, str]:
    """
    便捷函数：生成报告摘要

    Args:
        content: 报告内容
        report_type: 报告类型 ("research" 或 "risk")
        stock_code: 股票代码
        company_name: 公司名称

    Returns:
        Tuple[str, str]: (摘要版本, 完整版本)
    """
    summarizer = ReportSummarizer()

    if report_type == "research":
        return summarizer.summarize_research_decision(content, stock_code, company_name)
    elif report_type == "risk":
        return summarizer.summarize_risk_decision(content, stock_code, company_name)
    else:
        return content, content
