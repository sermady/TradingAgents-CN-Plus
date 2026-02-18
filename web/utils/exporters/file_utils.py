#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
报告文件保存工具
负责将报告保存到文件系统和MongoDB
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from tradingagents.utils.logging_manager import get_logger

logger = get_logger('web.file_utils')

# 导入MongoDB报告管理器
try:
    from web.utils.mongodb_report_manager import mongodb_report_manager
    MONGODB_REPORT_AVAILABLE = True
except ImportError:
    MONGODB_REPORT_AVAILABLE = False
    mongodb_report_manager = None


def get_results_dir() -> Path:
    """获取results目录路径"""
    # 获取项目根目录
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent

    # 获取results目录配置
    results_dir_env = os.getenv("TRADINGAGENTS_RESULTS_DIR")
    if results_dir_env:
        if not os.path.isabs(results_dir_env):
            results_dir = project_root / results_dir_env
        else:
            results_dir = Path(results_dir_env)
    else:
        results_dir = project_root / "results"

    return results_dir


def format_team_decision_content(content: Dict[str, Any], module_key: str) -> str:
    """格式化团队决策内容（独立函数版本）"""
    formatted_content = ""

    if module_key == 'investment_debate_state':
        # 研究团队决策格式化
        if content.get('bull_history'):
            formatted_content += "## 📈 多头研究员分析\n\n"
            formatted_content += f"{content['bull_history']}\n\n"

        if content.get('bear_history'):
            formatted_content += "## 📉 空头研究员分析\n\n"
            formatted_content += f"{content['bear_history']}\n\n"

        if content.get('judge_decision'):
            formatted_content += "## 🎯 研究经理综合决策\n\n"
            formatted_content += f"{content['judge_decision']}\n\n"

    elif module_key == 'risk_debate_state':
        # 风险管理团队决策格式化
        if content.get('risky_history'):
            formatted_content += "## 🚀 激进分析师评估\n\n"
            formatted_content += f"{content['risky_history']}\n\n"

        if content.get('safe_history'):
            formatted_content += "## 🛡️ 保守分析师评估\n\n"
            formatted_content += f"{content['safe_history']}\n\n"

        if content.get('neutral_history'):
            formatted_content += "## ⚖️ 中性分析师评估\n\n"
            formatted_content += f"{content['neutral_history']}\n\n"

        if content.get('judge_decision'):
            formatted_content += "## 🎯 投资组合经理最终决策\n\n"
            formatted_content += f"{content['judge_decision']}\n\n"

    return formatted_content


def save_modular_reports_to_results_dir(results: Dict[str, Any], stock_symbol: str) -> Dict[str, str]:
    """保存分模块报告到results目录（CLI版本格式）"""
    try:
        results_dir = get_results_dir()

        # 创建股票专用目录
        analysis_date = datetime.now().strftime('%Y-%m-%d')
        stock_dir = results_dir / stock_symbol / analysis_date
        reports_dir = stock_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # 创建message_tool.log文件
        log_file = stock_dir / "message_tool.log"
        log_file.touch(exist_ok=True)

        state = results.get('state', {})
        saved_files = {}

        # 定义报告模块映射（与CLI版本保持一致）
        report_modules = {
            'market_report': {
                'filename': 'market_report.md',
                'title': f'{stock_symbol} 股票技术分析报告',
                'state_key': 'market_report'
            },
            'sentiment_report': {
                'filename': 'sentiment_report.md',
                'title': f'{stock_symbol} 市场情绪分析报告',
                'state_key': 'sentiment_report'
            },
            'news_report': {
                'filename': 'news_report.md',
                'title': f'{stock_symbol} 新闻事件分析报告',
                'state_key': 'news_report'
            },
            'fundamentals_report': {
                'filename': 'fundamentals_report.md',
                'title': f'{stock_symbol} 基本面分析报告',
                'state_key': 'fundamentals_report'
            },
            'investment_plan': {
                'filename': 'investment_plan.md',
                'title': f'{stock_symbol} 投资决策报告',
                'state_key': 'investment_plan'
            },
            'trader_investment_plan': {
                'filename': 'trader_investment_plan.md',
                'title': f'{stock_symbol} 交易计划报告',
                'state_key': 'trader_investment_plan'
            },
            'final_trade_decision': {
                'filename': 'final_trade_decision.md',
                'title': f'{stock_symbol} 最终投资决策',
                'state_key': 'final_trade_decision'
            },
            # 添加团队决策报告模块
            'investment_debate_state': {
                'filename': 'research_team_decision.md',
                'title': f'{stock_symbol} 研究团队决策报告',
                'state_key': 'investment_debate_state'
            },
            'risk_debate_state': {
                'filename': 'risk_management_decision.md',
                'title': f'{stock_symbol} 风险管理团队决策报告',
                'state_key': 'risk_debate_state'
            }
        }

        # 生成各个模块的报告文件
        for module_key, module_info in report_modules.items():
            content = state.get(module_info['state_key'])

            if content:
                # 生成模块报告内容
                if isinstance(content, str):
                    # 检查内容是否已经包含标题，避免重复添加
                    if content.strip().startswith('#'):
                        report_content = content
                    else:
                        report_content = f"# {module_info['title']}\n\n{content}"
                elif isinstance(content, dict):
                    report_content = f"# {module_info['title']}\n\n"
                    # 特殊处理团队决策报告的字典结构
                    if module_key in ['investment_debate_state', 'risk_debate_state']:
                        report_content += format_team_decision_content(content, module_key)
                    else:
                        for sub_key, sub_value in content.items():
                            report_content += f"## {sub_key.replace('_', ' ').title()}\n\n{sub_value}\n\n"
                else:
                    report_content = f"# {module_info['title']}\n\n{str(content)}"

                # 保存文件
                file_path = reports_dir / module_info['filename']
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)

                saved_files[module_key] = str(file_path)
                logger.info(f"✅ 保存模块报告: {file_path}")

        # 如果有决策信息，也保存最终决策报告
        decision = results.get('decision', {})
        if decision:
            decision_content = f"# {stock_symbol} 最终投资决策\n\n"

            if isinstance(decision, dict):
                decision_content += f"## 投资建议\n\n"
                decision_content += f"**行动**: {decision.get('action', 'N/A')}\n\n"
                decision_content += f"**置信度**: {decision.get('confidence', 0):.1%}\n\n"
                decision_content += f"**风险评分**: {decision.get('risk_score', 0):.1%}\n\n"
                decision_content += f"**目标价位**: {decision.get('target_price', 'N/A')}\n\n"
                decision_content += f"## 分析推理\n\n{decision.get('reasoning', '暂无分析推理')}\n\n"
            else:
                decision_content += f"{str(decision)}\n\n"

            decision_file = reports_dir / "final_trade_decision.md"
            with open(decision_file, 'w', encoding='utf-8') as f:
                f.write(decision_content)

            saved_files['final_trade_decision'] = str(decision_file)
            logger.info(f"✅ 保存最终决策: {decision_file}")

        # 保存分析元数据文件，包含研究深度等信息
        metadata = {
            'stock_symbol': stock_symbol,
            'analysis_date': analysis_date,
            'timestamp': datetime.now().isoformat(),
            'research_depth': results.get('research_depth', 1),
            'analysts': results.get('analysts', []),
            'status': 'completed',
            'reports_count': len(saved_files),
            'report_types': list(saved_files.keys())
        }

        metadata_file = reports_dir.parent / "analysis_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 保存分析元数据: {metadata_file}")
        logger.info(f"✅ 分模块报告保存完成，共保存 {len(saved_files)} 个文件")
        logger.info(f"📁 保存目录: {os.path.normpath(str(reports_dir))}")

        # 同时保存到MongoDB
        logger.info(f"🔍 [MongoDB调试] 开始MongoDB保存流程")
        logger.info(f"🔍 [MongoDB调试] MONGODB_REPORT_AVAILABLE: {MONGODB_REPORT_AVAILABLE}")
        logger.info(f"🔍 [MongoDB调试] mongodb_report_manager存在: {mongodb_report_manager is not None}")

        if MONGODB_REPORT_AVAILABLE and mongodb_report_manager:
            logger.info(f"🔍 [MongoDB调试] MongoDB管理器连接状态: {mongodb_report_manager.connected}")
            try:
                # 收集所有报告内容
                reports_content = {}

                logger.info(f"🔍 [MongoDB调试] 开始读取 {len(saved_files)} 个报告文件")
                # 读取已保存的文件内容
                for module_key, file_path in saved_files.items():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            reports_content[module_key] = content
                            logger.info(f"🔍 [MongoDB调试] 成功读取 {module_key}: {len(content)} 字符")
                    except Exception as e:
                        logger.warning(f"⚠️ 读取报告文件失败 {file_path}: {e}")

                # 保存到MongoDB
                if reports_content:
                    logger.info(f"🔍 [MongoDB调试] 准备保存到MongoDB，报告数量: {len(reports_content)}")
                    logger.info(f"🔍 [MongoDB调试] 报告类型: {list(reports_content.keys())}")

                    success = mongodb_report_manager.save_analysis_report(
                        stock_symbol=stock_symbol,
                        analysis_results=results,
                        reports=reports_content
                    )

                    if success:
                        logger.info(f"✅ 分析报告已同时保存到MongoDB")
                    else:
                        logger.warning(f"⚠️ MongoDB保存失败，但文件保存成功")
                else:
                    logger.warning(f"⚠️ 没有报告内容可保存到MongoDB")

            except Exception as e:
                logger.error(f"❌ MongoDB保存过程出错: {e}")
                import traceback
                logger.error(f"❌ MongoDB保存详细错误: {traceback.format_exc()}")
                # 不影响文件保存的成功返回
        else:
            logger.warning(f"⚠️ MongoDB保存跳过 - AVAILABLE: {MONGODB_REPORT_AVAILABLE}, Manager: {mongodb_report_manager is not None}")

        return saved_files

    except Exception as e:
        logger.error(f"❌ 保存分模块报告失败: {e}")
        import traceback
        logger.error(f"❌ 详细错误: {traceback.format_exc()}")
        return {}


def save_report_to_results_dir(content: bytes, filename: str, stock_symbol: str) -> str:
    """保存报告到results目录"""
    try:
        results_dir = get_results_dir()

        # 创建股票专用目录
        analysis_date = datetime.now().strftime('%Y-%m-%d')
        stock_dir = results_dir / stock_symbol / analysis_date / "reports"
        stock_dir.mkdir(parents=True, exist_ok=True)

        # 保存文件
        file_path = stock_dir / filename
        with open(file_path, 'wb') as f:
            f.write(content)

        logger.info(f"✅ 报告已保存到: {file_path}")
        logger.info(f"📁 Results目录: {results_dir}")
        logger.info(f"📁 环境变量TRADINGAGENTS_RESULTS_DIR: {os.getenv('TRADINGAGENTS_RESULTS_DIR', '未设置')}")

        return str(file_path)

    except Exception as e:
        logger.error(f"❌ 保存报告到results目录失败: {e}")
        import traceback
        logger.error(f"❌ 详细错误: {traceback.format_exc()}")
        return ""


def save_analysis_report(stock_symbol: str, analysis_results: Dict[str, Any],
                        report_content: str = None) -> bool:
    """
    保存分析报告到MongoDB

    Args:
        stock_symbol: 股票代码
        analysis_results: 分析结果字典
        report_content: 报告内容（可选，如果不提供则自动生成）

    Returns:
        bool: 保存是否成功
    """
    try:
        if not MONGODB_REPORT_AVAILABLE or mongodb_report_manager is None:
            logger.warning("MongoDB报告管理器不可用，无法保存报告")
            return False

        # 如果没有提供报告内容，则生成Markdown报告
        if report_content is None:
            from .markdown_exporter import MarkdownExporter
            exporter = MarkdownExporter()
            report_content = exporter.generate_report(analysis_results)

        # 调用MongoDB报告管理器保存报告
        # 将报告内容包装成字典格式
        reports_dict = {
            "markdown": report_content,
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        success = mongodb_report_manager.save_analysis_report(
            stock_symbol=stock_symbol,
            analysis_results=analysis_results,
            reports=reports_dict
        )

        if success:
            logger.info(f"✅ 分析报告已成功保存到MongoDB - 股票: {stock_symbol}")
        else:
            logger.error(f"❌ 分析报告保存到MongoDB失败 - 股票: {stock_symbol}")

        return success

    except Exception as e:
        logger.error(f"❌ 保存分析报告到MongoDB时发生异常 - 股票: {stock_symbol}, 错误: {str(e)}")
        return False
