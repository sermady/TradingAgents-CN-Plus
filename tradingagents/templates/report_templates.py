# -*- coding: utf-8 -*-
"""
统一报告格式模板

定义所有分析报告的格式规范，确保：
1. 标题层级统一（# 报告标题，## 一级章节，### 二级章节）
2. 数字格式统一（金额用千分位，百分比保留2位小数）
3. 分隔线使用规范
4. 表格格式统一
"""

from datetime import datetime
from typing import Optional, Dict, Any, List


def format_number(value: float, decimals: int = 2, use_separator: bool = True) -> str:
    """
    格式化数字，支持千分位分隔符

    Args:
        value: 数值
        decimals: 小数位数
        use_separator: 是否使用千分位分隔符

    Returns:
        str: 格式化后的数字字符串
    """
    if value is None:
        return "N/A"

    try:
        if use_separator:
            return f"{value:,.{decimals}f}"
        else:
            return f"{value:.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def format_percentage(value: float, decimals: int = 2) -> str:
    """
    格式化百分比

    Args:
        value: 数值（0-1之间或0-100之间）
        decimals: 小数位数

    Returns:
        str: 格式化后的百分比字符串
    """
    if value is None:
        return "N/A"

    try:
        # 如果值在0-1之间，转换为百分比
        if -1 <= value <= 1:
            value = value * 100
        return f"{value:.{decimals}f}%"
    except (ValueError, TypeError):
        return str(value)


def format_currency(value: float, symbol: str = "¥", decimals: int = 2) -> str:
    """
    格式化货币金额

    Args:
        value: 金额
        symbol: 货币符号
        decimals: 小数位数

    Returns:
        str: 格式化后的货币字符串
    """
    if value is None:
        return "N/A"

    try:
        return f"{symbol}{value:,.{decimals}f}"
    except (ValueError, TypeError):
        return str(value)


def get_report_header(
    title: str,
    stock_code: str,
    company_name: str,
    report_date: str = None,
    analyst_type: str = None
) -> str:
    """
    生成报告头部

    Args:
        title: 报告标题
        stock_code: 股票代码
        company_name: 公司名称
        report_date: 报告日期
        analyst_type: 分析师类型

    Returns:
        str: 报告头部内容
    """
    if report_date is None:
        report_date = datetime.now().strftime("%Y-%m-%d")

    header = f"""# {title}

## 基本信息

| 项目 | 内容 |
|------|------|
| **股票代码** | {stock_code} |
| **公司名称** | {company_name} |
| **报告日期** | {report_date} |
"""

    if analyst_type:
        header += f"| **分析类型** | {analyst_type} |\n"

    header += "\n---\n\n"

    return header


def get_report_footer(
    data_sources: List[str] = None,
    disclaimer: bool = True
) -> str:
    """
    生成报告尾部

    Args:
        data_sources: 数据来源列表
        disclaimer: 是否包含免责声明

    Returns:
        str: 报告尾部内容
    """
    footer = "\n---\n\n"

    if data_sources:
        footer += "## 数据来源\n\n"
        for source in data_sources:
            footer += f"- {source}\n"
        footer += "\n"

    if disclaimer:
        footer += """## 免责声明

*本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。*
*报告中的数据和分析基于公开信息，不保证其准确性和完整性。*
*投资者应根据自身情况独立判断，自行承担投资风险。*

"""

    footer += f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

    return footer


class ReportTemplates:
    """统一报告模板类"""

    # 标题层级规范
    TITLE_LEVEL_1 = "#"      # 报告主标题
    TITLE_LEVEL_2 = "##"     # 一级章节
    TITLE_LEVEL_3 = "###"    # 二级章节
    TITLE_LEVEL_4 = "####"   # 三级章节

    # 分隔线规范
    SECTION_DIVIDER = "\n---\n\n"

    @staticmethod
    def technical_analysis_template(
        stock_code: str,
        company_name: str,
        current_price: float,
        price_change: float,
        volume: float,
        technical_indicators: Dict[str, Any],
        trend_analysis: str,
        support_resistance: Dict[str, float],
        report_date: str = None
    ) -> str:
        """
        技术分析报告模板

        Args:
            stock_code: 股票代码
            company_name: 公司名称
            current_price: 当前价格
            price_change: 涨跌幅
            volume: 成交量
            technical_indicators: 技术指标字典
            trend_analysis: 趋势分析文本
            support_resistance: 支撑位和阻力位
            report_date: 报告日期

        Returns:
            str: 格式化的技术分析报告
        """
        currency = "¥"  # 默认人民币

        header = get_report_header(
            title=f"{company_name} 技术分析报告",
            stock_code=stock_code,
            company_name=company_name,
            report_date=report_date,
            analyst_type="技术分析"
        )

        body = f"""## 价格概况

| 指标 | 数值 |
|------|------|
| **当前价格** | {format_currency(current_price, currency)} |
| **涨跌幅** | {format_percentage(price_change)} |
| **成交量** | {format_number(volume, 0)} 股 |

## 技术指标

| 指标名称 | 数值 | 信号 |
|----------|------|------|
"""

        for name, data in technical_indicators.items():
            if isinstance(data, dict):
                value = data.get("value", "N/A")
                signal = data.get("signal", "中性")
            else:
                value = data
                signal = "中性"
            body += f"| {name} | {value} | {signal} |\n"

        body += f"""
## 支撑位与阻力位

| 类型 | 价格 |
|------|------|
| **阻力位1** | {format_currency(support_resistance.get('resistance_1', 0), currency)} |
| **阻力位2** | {format_currency(support_resistance.get('resistance_2', 0), currency)} |
| **支撑位1** | {format_currency(support_resistance.get('support_1', 0), currency)} |
| **支撑位2** | {format_currency(support_resistance.get('support_2', 0), currency)} |

## 趋势分析

{trend_analysis}

"""

        footer = get_report_footer(
            data_sources=["MongoDB stock_daily_quotes", "实时行情数据"],
            disclaimer=True
        )

        return header + body + footer

    @staticmethod
    def fundamentals_template(
        stock_code: str,
        company_name: str,
        financial_metrics: Dict[str, Any],
        valuation_analysis: str,
        industry_comparison: str,
        report_date: str = None
    ) -> str:
        """
        基本面分析报告模板

        Args:
            stock_code: 股票代码
            company_name: 公司名称
            financial_metrics: 财务指标字典
            valuation_analysis: 估值分析文本
            industry_comparison: 行业对比文本
            report_date: 报告日期

        Returns:
            str: 格式化的基本面分析报告
        """
        header = get_report_header(
            title=f"{company_name} 基本面分析报告",
            stock_code=stock_code,
            company_name=company_name,
            report_date=report_date,
            analyst_type="基本面分析"
        )

        body = """## 核心财务指标

| 指标 | 数值 | 行业均值 | 评价 |
|------|------|----------|------|
"""

        for name, data in financial_metrics.items():
            if isinstance(data, dict):
                value = data.get("value", "N/A")
                industry_avg = data.get("industry_avg", "N/A")
                rating = data.get("rating", "中性")
            else:
                value = data
                industry_avg = "N/A"
                rating = "中性"

            # 格式化数值
            if isinstance(value, float):
                if "率" in name or "比" in name:
                    value = format_percentage(value)
                else:
                    value = format_number(value)

            body += f"| {name} | {value} | {industry_avg} | {rating} |\n"

        body += f"""
## 估值分析

{valuation_analysis}

## 行业对比

{industry_comparison}

"""

        footer = get_report_footer(
            data_sources=["Tushare财务数据", "行业研究报告"],
            disclaimer=True
        )

        return header + body + footer

    @staticmethod
    def sentiment_template(
        stock_code: str,
        company_name: str,
        sentiment_score: float,
        sentiment_trend: str,
        social_media_summary: str,
        news_summary: str,
        report_date: str = None
    ) -> str:
        """
        情绪分析报告模板

        Args:
            stock_code: 股票代码
            company_name: 公司名称
            sentiment_score: 情绪评分（1-10）
            sentiment_trend: 情绪趋势
            social_media_summary: 社交媒体摘要
            news_summary: 新闻摘要
            report_date: 报告日期

        Returns:
            str: 格式化的情绪分析报告
        """
        header = get_report_header(
            title=f"{company_name} 情绪分析报告",
            stock_code=stock_code,
            company_name=company_name,
            report_date=report_date,
            analyst_type="情绪分析"
        )

        # 情绪等级判断
        if sentiment_score >= 7:
            sentiment_level = "乐观"
            sentiment_emoji = "😊"
        elif sentiment_score >= 4:
            sentiment_level = "中性"
            sentiment_emoji = "😐"
        else:
            sentiment_level = "悲观"
            sentiment_emoji = "😟"

        body = f"""## 情绪概况

| 指标 | 数值 |
|------|------|
| **情绪评分** | {sentiment_score}/10 {sentiment_emoji} |
| **情绪等级** | {sentiment_level} |
| **情绪趋势** | {sentiment_trend} |

## 社交媒体分析

{social_media_summary}

## 新闻舆情分析

{news_summary}

"""

        footer = get_report_footer(
            data_sources=["雪球", "东方财富股吧", "财经新闻"],
            disclaimer=True
        )

        return header + body + footer

    @staticmethod
    def research_summary_template(
        stock_code: str,
        company_name: str,
        bull_summary: str,
        bear_summary: str,
        final_recommendation: str,
        confidence: float,
        key_points: List[str],
        report_date: str = None
    ) -> str:
        """
        研究团队决策摘要模板（精简版）

        Args:
            stock_code: 股票代码
            company_name: 公司名称
            bull_summary: 多头观点摘要
            bear_summary: 空头观点摘要
            final_recommendation: 最终建议
            confidence: 置信度
            key_points: 关键要点列表
            report_date: 报告日期

        Returns:
            str: 格式化的研究决策摘要
        """
        header = get_report_header(
            title=f"{company_name} 研究团队决策摘要",
            stock_code=stock_code,
            company_name=company_name,
            report_date=report_date,
            analyst_type="研究决策"
        )

        body = f"""## 决策结论

| 项目 | 内容 |
|------|------|
| **最终建议** | **{final_recommendation}** |
| **置信度** | {format_percentage(confidence)} |

## 多头观点摘要

{bull_summary}

## 空头观点摘要

{bear_summary}

## 关键要点

"""

        for i, point in enumerate(key_points, 1):
            body += f"{i}. {point}\n"

        body += "\n"

        footer = get_report_footer(
            data_sources=["多空研究员辩论", "风险评估团队"],
            disclaimer=True
        )

        return header + body + footer

    @staticmethod
    def risk_summary_template(
        stock_code: str,
        company_name: str,
        risk_score: float,
        risk_factors: List[Dict[str, Any]],
        risk_mitigation: List[str],
        report_date: str = None
    ) -> str:
        """
        风险管理决策摘要模板（精简版）

        Args:
            stock_code: 股票代码
            company_name: 公司名称
            risk_score: 风险评分（0-1）
            risk_factors: 风险因素列表
            risk_mitigation: 风险缓解措施
            report_date: 报告日期

        Returns:
            str: 格式化的风险管理摘要
        """
        # 风险等级判断
        if risk_score <= 0.3:
            risk_level = "低风险"
            risk_color = "🟢"
        elif risk_score <= 0.5:
            risk_level = "中低风险"
            risk_color = "🟡"
        elif risk_score <= 0.7:
            risk_level = "中高风险"
            risk_color = "🟠"
        else:
            risk_level = "高风险"
            risk_color = "🔴"

        header = get_report_header(
            title=f"{company_name} 风险管理决策摘要",
            stock_code=stock_code,
            company_name=company_name,
            report_date=report_date,
            analyst_type="风险评估"
        )

        body = f"""## 风险概况

| 项目 | 内容 |
|------|------|
| **风险评分** | {format_percentage(risk_score)} {risk_color} |
| **风险等级** | {risk_level} |

## 主要风险因素

| 风险类型 | 影响程度 | 发生概率 |
|----------|----------|----------|
"""

        for factor in risk_factors:
            risk_type = factor.get("type", "未知")
            impact = factor.get("impact", "中")
            probability = factor.get("probability", "中")
            body += f"| {risk_type} | {impact} | {probability} |\n"

        body += """
## 风险缓解建议

"""

        for i, mitigation in enumerate(risk_mitigation, 1):
            body += f"{i}. {mitigation}\n"

        body += "\n"

        footer = get_report_footer(
            data_sources=["激进/保守/中性风险评估团队"],
            disclaimer=True
        )

        return header + body + footer
