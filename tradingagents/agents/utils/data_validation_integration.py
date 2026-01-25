# -*- coding: utf-8 -*-
"""
分析师数据验证集成模块

在分析师工作流中集成数据验证功能
"""

from typing import Dict, Any, List, Optional
import logging
import re

logger = logging.getLogger(__name__)


def parse_data_string_to_dict(data_str: str) -> Dict[str, Any]:
    """
    将数据字符串解析为字典

    Args:
        data_str: 数据字符串（包含多行，格式: 指标: 值）

    Returns:
        Dict: 解析后的数据字典
    """
    data_dict = {'source': 'analyst_data'}

    try:
        lines = data_str.split('\n')
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('*') or line.startswith('—'):
                continue

            # 解析格式: "**指标**: 值" 或 "指标: 值"
            if ':' in line or '：' in line:
                # 使用中文冒号或英文冒号分割
                if '：' in line:
                    parts = line.split('：', 1)
                else:
                    parts = line.split(':', 1)

                if len(parts) == 2:
                    key = parts[0].strip('*').strip()
                    value_str = parts[1].strip()

                    # 移除常见的单位和符号
                    value_str = value_str.replace('¥', '').replace('$', '').replace('￥', '')
                    value_str = value_str.replace(',', '').replace(' ', '')
                    value_str = value_str.replace('亿元', '').replace('亿', '')
                    value_str = value_str.replace('万元', '').replace('万', '')
                    value_str = value_str.replace('股', '').replace('%', '')
                    value_str = value_str.replace('倍', '')

                    try:
                        # 尝试转换为数值
                        if '.' in value_str or value_str.isdigit():
                            value = float(value_str)
                        else:
                            value = value_str
                        data_dict[key] = value
                    except:
                        data_dict[key] = value_str

    except Exception as e:
        logger.debug(f"数据解析失败: {e}")

    return data_dict


def format_validation_result_to_report(
    ticker: str,
    validation_results: List[Any],
    validator_name: str
) -> str:
    """
    将验证结果格式化为报告段落

    Args:
        ticker: 股票代码
        validation_results: 验证结果列表
        validator_name: 验证器名称

    Returns:
        str: 格式化的报告段落
    """
    if not validation_results:
        return ""

    # 统计各级别问题数量
    total_issues = 0
    error_count = 0
    warning_count = 0
    info_count = 0

    for result in validation_results:
        if hasattr(result, 'discrepancies'):
            for issue in result.discrepancies:
                total_issues += 1
                if hasattr(issue, 'severity'):
                    if issue.severity.value == 'error':
                        error_count += 1
                    elif issue.severity.value == 'warning':
                        warning_count += 1
                    elif issue.severity.value == 'info':
                        info_count += 1

    if total_issues == 0:
        return f"""

---

## ✅ 数据验证通过

**验证器**: {validator_name}
**股票代码**: {ticker}
**验证时间**: 自动实时验证

**验证结果**: 未发现数据问题

---

"""

    # 构建问题报告
    report_lines = [
        "",
        "---",
        "",
        f"## ⚠️ 数据验证发现问题",
        "",
        f"**验证器**: {validator_name}",
        f"**股票代码**: {ticker}",
        f"**发现问题**: {total_issues} 个 (错误: {error_count}, 警告: {warning_count}, 提示: {info_count})",
        ""
    ]

    # 添加详细问题列表
    for result in validation_results:
        if hasattr(result, 'discrepancies') and result.discrepancies:
            for issue in result.discrepancies:
                severity_icon = {
                    'critical': '🔴',
                    'error': '❌',
                    'warning': '⚠️',
                    'info': 'ℹ️'
                }.get(issue.severity.value, '•')

                report_lines.append(f"**{severity_icon} [{issue.severity.value.upper()}] {issue.field}**")
                report_lines.append(f"- {issue.message}")

                if issue.suggested_value is not None:
                    report_lines.append(f"- **建议值**: {issue.suggested_value}")

                if issue.expected is not None:
                    report_lines.append(f"- **期望值**: {issue.expected}")

                report_lines.append("")

    report_lines.extend([
        "---",
        ""
    ])

    return "\n".join(report_lines)


def add_data_validation_to_market_report(
    ticker: str,
    raw_data: str,
    validation_enabled: bool = True
) -> str:
    """
    为市场分析报告添加数据验证信息（真实执行验证）

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

        # 解析数据
        data_dict = parse_data_string_to_dict(raw_data)

        if not data_dict:
            logger.warning(f"市场数据解析失败，跳过验证")
            return raw_data

        # 执行验证
        price_validator = PriceValidator()
        volume_validator = VolumeValidator()

        price_result = price_validator.validate(ticker, data_dict)
        volume_result = volume_validator.validate(ticker, data_dict)

        # 收集有问题的验证结果
        validation_results = []
        if not price_result.is_valid or price_result.discrepancies:
            validation_results.append(price_result)
        if not volume_result.is_valid or volume_result.discrepancies:
            validation_results.append(volume_result)

        # 生成验证报告
        if validation_results:
            validation_report = format_validation_result_to_report(
                ticker,
                validation_results,
                "市场数据验证器 (PriceValidator + VolumeValidator)"
            )
            validated_data = raw_data + validation_report

            logger.warning(f"⚠️ [市场分析] {ticker} 发现数据问题: {len(validation_results)} 个验证器报告问题")
        else:
            # 无问题，添加简短的通过说明
            validation_report = f"""

---

## ✅ 市场数据验证通过

**股票代码**: {ticker}
**验证范围**: 价格数据、技术指标、成交量
**验证结果**: 所有指标均在合理范围内

---

"""
            validated_data = raw_data + validation_report
            logger.info(f"✅ [市场分析] {ticker} 市场数据验证通过")

        return validated_data

    except Exception as e:
        logger.warning(f"⚠️ [市场分析] {ticker} 数据验证失败: {e}")
        # 验证失败时，返回原始数据
        return raw_data


def add_data_validation_to_fundamentals_report(
    ticker: str,
    raw_data: str,
    validation_enabled: bool = True
) -> str:
    """
    为基本面分析报告添加数据验证信息（真实执行验证）

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

        # 解析数据
        data_dict = parse_data_string_to_dict(raw_data)

        if not data_dict:
            logger.warning(f"基本面数据解析失败，跳过验证")
            return raw_data

        # ========== 关键修复: 自动计算并修正PS比率 ==========
        # 检查是否有市值和营收数据
        market_cap = None
        revenue = None

        # 尝试多种可能的字段名
        for key in ['总市值', 'market_cap', '市值']:
            if key in data_dict:
                market_cap = data_dict[key]
                break

        for key in ['营业总收入', '总营收', 'revenue', '营收']:
            if key in data_dict:
                revenue = data_dict[key]
                break

        # 如果有市值和营收，计算正确的PS
        calculated_ps = None
        if market_cap and revenue and revenue > 0:
            try:
                calculated_ps = market_cap / revenue
                logger.info(f"[PS修正] {ticker} 自动计算PS: {market_cap} / {revenue} = {calculated_ps:.2f}")
            except:
                pass

        # 检查数据中的PS值
        existing_ps = data_dict.get('PS') or data_dict.get('市销率') or data_dict.get('ps_ratio')

        # 如果有计算的PS，与数据中的PS比较
        ps_correction_needed = False
        corrected_ps = None

        if calculated_ps is not None:
            if existing_ps is None:
                # 数据中没有PS，使用计算的值
                corrected_ps = calculated_ps
                ps_correction_needed = True
                logger.warning(f"[PS修正] {ticker} 数据中缺少PS，使用计算值: {calculated_ps:.2f}")
            else:
                # 数据中有PS，比较是否一致
                try:
                    existing_ps_float = float(existing_ps)
                    diff_pct = abs((calculated_ps - existing_ps_float) / existing_ps_float) * 100

                    # 如果差异超过10%，认为是错误
                    if diff_pct > 10:
                        corrected_ps = calculated_ps
                        ps_correction_needed = True
                        logger.warning(f"[PS修正] {ticker} 检测到PS错误! "
                                     f"报告值={existing_ps_float:.2f}, 计算值={calculated_ps:.2f}, "
                                     f"差异={diff_pct:.1f}%")

                except:
                    pass

        # 如果需要修正PS，更新数据字典
        if ps_correction_needed and corrected_ps is not None:
            data_dict['PS'] = corrected_ps
            data_dict['市销率'] = corrected_ps
            logger.info(f"[PS修正] {ticker} PS已修正为: {corrected_ps:.2f}")

        # 执行验证
        validator = FundamentalsValidator()
        result = validator.validate(ticker, data_dict)

        # 生成验证报告
        if not result.is_valid or result.discrepancies:
            validation_report = format_validation_result_to_report(
                ticker,
                [result],
                "基本面数据验证器 (FundamentalsValidator)"
            )
            validated_data = raw_data + validation_report

            logger.warning(f"⚠️ [基本面分析] {ticker} 发现数据问题: {len(result.discrepancies)} 个")
        else:
            # 无问题，添加简短的通过说明
            validation_report = f"""

---

## ✅ 基本面数据验证通过

**股票代码**: {ticker}
**验证范围**: PE、PB、PS、ROE、市值等基本面指标
**验证结果**: 所有指标均在合理范围内
**数据置信度**: {result.confidence:.1%}

"""

            # 如果进行了PS修正，在报告中说明
            if ps_correction_needed:
                ps_note = f"""

**⚠️ 数据修正**: 报告中的PS（市销率）已根据市值和营收自动计算并修正。
- 计算公式: PS = 市值 / 营收
- 修正后PS值: {corrected_ps:.2f}
- 修正原因: 原始数据中的PS值不准确或缺失

"""
                validation_report += ps_note

            validated_data = raw_data + validation_report
            logger.info(f"✅ [基本面分析] {ticker} 基本面数据验证通过，置信度: {result.confidence:.1%}")

        return validated_data

    except Exception as e:
        logger.warning(f"⚠️ [基本面分析] {ticker} 数据验证失败: {e}")
        # 验证失败时，返回原始数据
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
        from tradingagents.dataflows.data_source_manager import get_data_source_manager

        manager = get_data_source_manager()

        # 1. 评估市场数据质量
        if market_data:
            market_quality = manager.get_data_quality_score(ticker, market_data)
            summary['validation_results']['market_data'] = {
                'quality_score': market_quality,
                'status': 'excellent' if market_quality >= 80 else 'good' if market_quality >= 60 else 'poor'
            }
            summary['overall_quality_score'] += market_quality * 0.5  # 权重50%

            # 根据质量评分添加警告
            if market_quality < 70:
                summary['warnings'].append(f'市场数据质量评分较低: {market_quality:.1f}/100')
            if market_quality < 60:
                summary['errors'].append('市场数据质量不合格，建议谨慎使用')

        # 2. 评估基本面数据质量
        if fundamentals_data:
            fundamentals_quality = manager.get_data_quality_score(ticker, fundamentals_data)
            summary['validation_results']['fundamentals_data'] = {
                'quality_score': fundamentals_quality,
                'status': 'excellent' if fundamentals_quality >= 80 else 'good' if fundamentals_quality >= 60 else 'poor'
            }
            summary['overall_quality_score'] += fundamentals_quality * 0.5  # 权重50%

            # 根据质量评分添加警告
            if fundamentals_quality < 70:
                summary['warnings'].append(f'基本面数据质量评分较低: {fundamentals_quality:.1f}/100')
            if fundamentals_quality < 60:
                summary['errors'].append('基本面数据质量不合格，建议谨慎使用')

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
