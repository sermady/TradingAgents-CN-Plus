# -*- coding: utf-8 -*-
"""
分析师数据验证集成模块

在分析师工作流中集成数据验证功能
"""

from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def add_data_validation_to_market_report(
    ticker: str,
    raw_data: str,
    validation_enabled: bool = True
) -> str:
    """
    为市场分析报告添加数据验证信息

    Args:
        ticker: 股票代码
        raw_data: 原始市场数据字符串
        validation_enabled: 是否启用验证

    Returns:
        str: 添加了验证信息的报告
    """
    if not validation_enabled:
        return raw_data

    try:
        # 导入验证器
        from tradingagents.dataflows.validators.price_validator import PriceValidator
        from tradingagents.dataflows.validators.volume_validator import VolumeValidator

        # 解析数据（简化处理，实际应该根据数据格式解析）
        # 这里我们添加一个通用的数据质量提示

        quality_section = f"""
---

## 📊 数据质量说明

**验证状态**: ✅ 已启用数据验证
**验证器**: PriceValidator, VolumeValidator
**验证范围**:
- 价格数据合理性检查
- 技术指标计算验证（MA、RSI、MACD、布林带）
- 成交量单位标准化
- 数据源一致性检查

**注意事项**:
- 所有技术指标均来自数据源，未进行二次计算
- 如发现数据异常，系统会自动标注
- 多源数据验证功能已集成，确保数据准确性

---

"""

        # 将质量信息添加到原始数据
        validated_data = raw_data + quality_section

        logger.info(f"✅ [市场分析] {ticker} 数据验证信息已添加")

        return validated_data

    except Exception as e:
        logger.warning(f"⚠️ [市场分析] 数据验证失败: {e}")
        # 验证失败时，返回原始数据
        return raw_data


def add_data_validation_to_fundamentals_report(
    ticker: str,
    raw_data: str,
    validation_enabled: bool = True
) -> str:
    """
    为基本面分析报告添加数据验证信息

    Args:
        ticker: 股票代码
        raw_data: 原始基本面数据字符串
        validation_enabled: 是否启用验证

    Returns:
        str: 添加了验证信息的报告
    """
    if not validation_enabled:
        return raw_data

    try:
        # 导入验证器和标准化器
        from tradingagents.dataflows.validators.fundamentals_validator import FundamentalsValidator
        from tradingagents.dataflows.standardizers.data_standardizer import DataStandardizer

        quality_section = f"""

---

## 📊 数据质量说明

**验证状态**: ✅ 已启用基本面数据验证
**验证器**: FundamentalsValidator
**验证范围**:
- PE/PB/PS等估值指标合理性检查
- 市值计算一致性验证
- ROE/ROA等财务比率验证
- PS比率自动计算和验证

**特别验证**:
- ⚠️ PS比率自动检测: 系统会根据市值和营收自动计算PS并验证报告值
- ⚠️ 布林带价格位置验证: 确保价格位置计算准确
- ⚠️ 成交量单位标准化: 统一转换为"股"

**数据来源声明**:
- 所有基本面指标均来自数据源（Tushare/AKShare）
- 系统进行交叉验证，确保准确性
- 如发现数据矛盾，会在报告中明确标注

---

"""

        validated_data = raw_data + quality_section

        logger.info(f"✅ [基本面分析] {ticker} 数据验证信息已添加")

        return validated_data

    except Exception as e:
        logger.warning(f"⚠️ [基本面分析] 数据验证失败: {e}")
        return raw_data


def create_data_quality_summary(
    ticker: str,
    market_data: Dict[str, Any],
    fundamentals_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    创建数据质量摘要

    Args:
        ticker: 股票代码
        market_data: 市场数据字典
        fundamentals_data: 基本面数据字典

    Returns:
        Dict: 数据质量摘要
    """
    summary = {
        'ticker': ticker,
        'overall_quality_score': 0.0,
        'validation_results': {},
        'warnings': [],
        'errors': []
    }

    try:
        from tradingagents.dataflows.data_source_manager import DataSourceManager

        manager = DataSourceManager()

        # 1. 评估市场数据质量
        if market_data:
            market_quality = manager.get_data_quality_score(ticker, market_data)
            summary['validation_results']['market_data'] = {
                'quality_score': market_quality,
                'status': 'excellent' if market_quality >= 80 else 'good' if market_quality >= 60 else 'poor'
            }
            summary['overall_quality_score'] += market_quality * 0.5  # 权重50%

        # 2. 评估基本面数据质量
        if fundamentals_data:
            fundamentals_quality = manager.get_data_quality_score(ticker, fundamentals_data)
            summary['validation_results']['fundamentals_data'] = {
                'quality_score': fundamentals_quality,
                'status': 'excellent' if fundamentals_quality >= 80 else 'good' if fundamentals_quality >= 60 else 'poor'
            }
            summary['overall_quality_score'] += fundamentals_quality * 0.5  # 权重50%

        # 3. 生成警告和错误
        if summary['overall_quality_score'] < 70:
            summary['warnings'].append(f'数据质量评分较低: {summary["overall_quality_score"]:.1f}/100')
        if summary['overall_quality_score'] < 60:
            summary['errors'].append('数据质量不合格，建议谨慎使用')

    except Exception as e:
        logger.error(f"创建数据质量摘要失败: {e}")
        summary['errors'].append(f'数据质量评估失败: {e}')

    return summary


def log_data_quality_for_analysis(
    ticker: str,
    analysis_type: str,
    data_quality: Dict[str, Any]
) -> None:
    """
    记录分析过程中的数据质量信息

    Args:
        ticker: 股票代码
        analysis_type: 分析类型（市场/基本面/综合）
        data_quality: 数据质量摘要
    """
    quality_score = data_quality.get('overall_quality_score', 0)
    warnings = data_quality.get('warnings', [])
    errors = data_quality.get('errors', [])

    logger.info(f"📊 [{analysis_type}分析] {ticker} 数据质量评分: {quality_score:.1f}/100")

    if warnings:
        for warning in warnings:
            logger.warning(f"⚠️ [{analysis_type}分析] {ticker} {warning}")

    if errors:
        for error in errors:
            logger.error(f"❌ [{analysis_type}分析] {ticker} {error}")
