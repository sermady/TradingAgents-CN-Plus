# -*- coding: utf-8 -*-
"""报告生成和保存服务

提取自 simple_analysis_service.py 中的报告相关逻辑：
- _save_analysis_result
- _save_analysis_result_web_style
- _save_analysis_results_complete
- _save_modular_reports_to_data_dir
- 报告提取和格式化
"""

import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from app.core.database import get_mongo_db
from app.utils.error_handler import handle_errors, async_handle_errors, async_handle_errors_none
from app.utils.report_extractor import ReportExtractor

logger = logging.getLogger(__name__)


class ReportGenerationService:
    """报告生成和保存服务"""

    # 报告模块映射
    REPORT_MODULES = {
        "market_report": {
            "filename": "market_report.md",
            "title": "股票技术分析报告",
            "state_key": "market_report",
        },
        "sentiment_report": {
            "filename": "sentiment_report.md",
            "title": "市场情绪分析报告",
            "state_key": "sentiment_report",
        },
        "news_report": {
            "filename": "news_report.md",
            "title": "新闻事件分析报告",
            "state_key": "news_report",
        },
        "fundamentals_report": {
            "filename": "fundamentals_report.md",
            "title": "基本面分析报告",
            "state_key": "fundamentals_report",
        },
        "investment_plan": {
            "filename": "investment_plan.md",
            "title": "投资决策报告",
            "state_key": "investment_plan",
        },
        "trader_investment_plan": {
            "filename": "trader_investment_plan.md",
            "title": "交易计划报告",
            "state_key": "trader_investment_plan",
        },
        "final_trade_decision": {
            "filename": "final_trade_decision.md",
            "title": "最终投资决策",
            "state_key": "final_trade_decision",
        },
        "investment_debate_state": {
            "filename": "research_team_decision.md",
            "title": "研究团队决策报告",
            "state_key": "investment_debate_state",
        },
        "risk_debate_state": {
            "filename": "risk_management_decision.md",
            "title": "风险管理团队决策报告",
            "state_key": "risk_debate_state",
        },
    }

    @async_handle_errors_none(error_message="保存分析结果失败")
    async def save_analysis_result(self, task_id: str, result: Dict[str, Any]):
        """保存分析结果（原始方法）"""
        db = get_mongo_db()
        await db.analysis_tasks.update_one(
            {"task_id": task_id}, {"$set": {"result": result}}
        )
        logger.debug(f"💾 分析结果已保存: {task_id}")

    @async_handle_errors_none(error_message="保存分析报告失败")
    async def save_analysis_result_web_style(self, task_id: str, result: Dict[str, Any]):
        """保存分析结果 - 采用web目录的方式，保存到analysis_reports集合"""
        db = get_mongo_db()

        # 生成分析ID
        timestamp = datetime.utcnow()
        stock_symbol = result.get("stock_symbol") or result.get("stock_code", "UNKNOWN")
        analysis_id = f"{stock_symbol}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # 处理reports字段
        reports = await self._extract_reports_from_result(result)

        # 获取市场类型和股票名称
        market_type = self._infer_market_type(stock_symbol)
        stock_name = await self._get_stock_name(stock_symbol, market_type)

        # 构建文档
        document = self._build_analysis_document(
            analysis_id=analysis_id,
            task_id=task_id,
            stock_symbol=stock_symbol,
            stock_name=stock_name,
            market_type=market_type,
            timestamp=timestamp,
            result=result,
            reports=reports,
        )

        # 保存到analysis_reports集合
        result_insert = await db.analysis_reports.insert_one(document)

        if result_insert.inserted_id:
            logger.info(f"✅ 分析报告已保存到MongoDB analysis_reports: {analysis_id}")
            # 同时更新analysis_tasks集合
            await self._update_analysis_task(db, task_id, result, reports, analysis_id)

    async def _extract_reports_from_result(self, result: Dict[str, Any]) -> Dict[str, str]:
        """从结果中提取报告"""
        reports = {}
        if "state" in result:
            try:
                state = result["state"]
                extraction_result = ReportExtractor.extract_all_content(state)
                reports = extraction_result.get("reports", {})
            except Exception as e:
                logger.warning(f"⚠️ 处理state中的reports时出错: {e}")
                # 降级到从detailed_analysis提取
                reports = self._extract_reports_fallback(result)
        return reports

    def _extract_reports_fallback(self, result: Dict[str, Any]) -> Dict[str, str]:
        """降级提取报告"""
        reports = {}
        if "detailed_analysis" in result:
            try:
                detailed_analysis = result["detailed_analysis"]
                if isinstance(detailed_analysis, dict):
                    for key, value in detailed_analysis.items():
                        if isinstance(value, str) and len(value) > 50:
                            reports[key] = value
                    logger.info(f"📊 降级：从detailed_analysis中提取到 {len(reports)} 个报告")
            except Exception as e:
                logger.warning(f"⚠️ 降级提取也失败: {e}")
        return reports

    def _infer_market_type(self, stock_symbol: str) -> str:
        """根据股票代码推断市场类型"""
        from tradingagents.utils.stock_utils import StockUtils

        market_info = StockUtils.get_market_info(stock_symbol)
        market_type_map = {
            "china_a": "A股",
            "hong_kong": "港股",
            "us": "美股",
            "unknown": "A股",
        }
        market_type = market_type_map.get(market_info.get("market", "unknown"), "A股")
        logger.info(f"📊 推断市场类型: {stock_symbol} -> {market_type}")
        return market_type

    async def _get_stock_name(self, stock_symbol: str, market_type: str) -> str:
        """获取股票名称"""
        stock_name = stock_symbol
        try:
            from tradingagents.utils.stock_utils import StockUtils
            market_info = StockUtils.get_market_info(stock_symbol)

            if market_info.get("market") == "china_a":
                stock_name = await self._get_china_stock_name(stock_symbol)
            elif market_info.get("market") == "hong_kong":
                stock_name = await self._get_hk_stock_name(stock_symbol)
            elif market_info.get("market") == "us":
                stock_name = self._get_us_stock_name(stock_symbol)
        except Exception as e:
            logger.warning(f"⚠️ 获取股票名称失败: {stock_symbol} - {e}")

        return stock_name

    async def _get_china_stock_name(self, stock_symbol: str) -> str:
        """获取A股股票名称"""
        try:
            from tradingagents.dataflows.interface import get_china_stock_info_unified

            stock_info = get_china_stock_info_unified(stock_symbol)
            if stock_info and "股票名称:" in stock_info:
                return stock_info.split("股票名称:")[1].split("\n")[0].strip()
        except Exception as e:
            logger.warning(f"⚠️ 获取A股名称失败: {e}")
        return f"股票{stock_symbol}"

    async def _get_hk_stock_name(self, stock_symbol: str) -> str:
        """获取港股股票名称"""
        try:
            from tradingagents.dataflows.providers.hk.improved_hk import (
                get_hk_company_name_improved,
            )
            return get_hk_company_name_improved(stock_symbol)
        except Exception:
            clean_ticker = stock_symbol.replace(".HK", "").replace(".hk", "")
            return f"港股{clean_ticker}"

    def _get_us_stock_name(self, stock_symbol: str) -> str:
        """获取美股股票名称"""
        us_stock_names = {
            "AAPL": "苹果公司",
            "TSLA": "特斯拉",
            "NVDA": "英伟达",
            "MSFT": "微软",
            "GOOGL": "谷歌",
            "AMZN": "亚马逊",
            "META": "Meta",
            "NFLX": "奈飞",
        }
        return us_stock_names.get(stock_symbol.upper(), f"美股{stock_symbol}")

    def _build_analysis_document(
        self,
        analysis_id: str,
        task_id: str,
        stock_symbol: str,
        stock_name: str,
        market_type: str,
        timestamp: datetime,
        result: Dict[str, Any],
        reports: Dict[str, str],
    ) -> Dict[str, Any]:
        """构建分析文档"""
        return {
            "analysis_id": analysis_id,
            "stock_symbol": stock_symbol,
            "stock_name": stock_name,
            "market_type": market_type,
            "model_info": result.get("model_info", "Unknown"),
            "analysis_date": timestamp.strftime("%Y-%m-%d"),
            "timestamp": timestamp,
            "status": "completed",
            "source": "api",
            "summary": result.get("summary", ""),
            "analysts": result.get("analysts", []),
            "research_depth": result.get("research_depth", 1),
            "reports": reports,
            "decision": result.get("decision", {}),
            "created_at": timestamp,
            "updated_at": timestamp,
            "task_id": task_id,
            "recommendation": result.get("recommendation", ""),
            "confidence_score": result.get("confidence_score", 0.0),
            "risk_level": result.get("risk_level", "中等"),
            "key_points": result.get("key_points", []),
            "execution_time": result.get("execution_time", 0),
            "tokens_used": result.get("tokens_used", 0),
            "performance_metrics": result.get("performance_metrics", {}),
        }

    async def _update_analysis_task(
        self,
        db,
        task_id: str,
        result: Dict[str, Any],
        reports: Dict[str, str],
        analysis_id: str,
    ):
        """更新分析任务结果"""
        stock_symbol = result.get("stock_symbol") or result.get("stock_code", "UNKNOWN")
        await db.analysis_tasks.update_one(
            {"task_id": task_id},
            {
                "$set": {
                    "result": {
                        "analysis_id": analysis_id,
                        "stock_symbol": stock_symbol,
                        "stock_code": result.get("stock_code", stock_symbol),
                        "analysis_date": result.get("analysis_date"),
                        "summary": result.get("summary", ""),
                        "recommendation": result.get("recommendation", ""),
                        "confidence_score": result.get("confidence_score", 0.0),
                        "risk_level": result.get("risk_level", "中等"),
                        "key_points": result.get("key_points", []),
                        "detailed_analysis": result.get("detailed_analysis", {}),
                        "execution_time": result.get("execution_time", 0),
                        "tokens_used": result.get("tokens_used", 0),
                        "reports": reports,
                        "decision": result.get("decision", {}),
                    }
                }
            },
        )
        logger.info(f"💾 分析结果已保存 (web风格): {task_id}")

    @async_handle_errors_none(error_message="完整保存分析结果失败")
    async def save_analysis_results_complete(
        self, task_id: str, result: Dict[str, Any]
    ):
        """完整的分析结果保存 - 完全采用web目录的双重保存方式"""
        stock_symbol = result.get("stock_symbol") or result.get("stock_code", "UNKNOWN")
        logger.info(f"💾 开始完整保存分析结果: {stock_symbol}")

        # 1. 保存分模块报告到本地目录
        logger.info(f"📁 [本地保存] 开始保存分模块报告到本地目录")
        local_files = await self.save_modular_reports_to_data_dir(result, stock_symbol)
        if local_files:
            logger.info(f"✅ [本地保存] 已保存 {len(local_files)} 个本地报告文件")
        else:
            logger.warning(f"⚠️ [本地保存] 本地报告文件保存失败")

        # 2. 保存分析报告到数据库
        logger.info(f"🗄️ [数据库保存] 开始保存分析报告到数据库")
        await self.save_analysis_result_web_style(task_id, result)
        logger.info(f"✅ [数据库保存] 分析报告已成功保存到数据库")

    @async_handle_errors_none(error_message="保存分模块报告失败")
    async def save_modular_reports_to_data_dir(
        self, result: Dict[str, Any], stock_symbol: str
    ) -> Dict[str, str]:
        """保存分模块报告到data目录"""
        import json

        # 获取项目根目录
        project_root = Path(__file__).parent.parent.parent

        # 确定results目录路径
        results_dir_env = os.getenv("TRADINGAGENTS_RESULTS_DIR")
        if results_dir_env:
            results_dir = Path(results_dir_env) if os.path.isabs(results_dir_env) else project_root / results_dir_env
        else:
            results_dir = project_root / "data" / "analysis_results"

        # 创建股票专用目录
        analysis_date_str = self._format_analysis_date(result.get("analysis_date"))
        stock_dir = results_dir / stock_symbol / analysis_date_str
        reports_dir = stock_dir / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # 创建message_tool.log文件
        log_file = stock_dir / "message_tool.log"
        log_file.touch(exist_ok=True)

        logger.info(f"📁 创建分析结果目录: {reports_dir}")

        state = result.get("state", {})
        saved_files = {}

        # 尝试导入报告摘要生成器
        try:
            from tradingagents.utils.report_summarizer import summarize_report
            summarizer_available = True
        except ImportError:
            summarizer_available = False

        # 保存各模块报告
        for module_key, module_info in self.REPORT_MODULES.items():
            try:
                file_path = await self._save_module_report(
                    state, module_key, module_info, reports_dir, stock_symbol, summarizer_available
                )
                if file_path:
                    saved_files[module_key] = str(file_path)
            except Exception as e:
                logger.warning(f"⚠️ 保存模块 {module_key} 失败: {e}")

        # 保存最终决策报告
        decision = result.get("decision", {})
        if decision:
            decision_file = self._save_decision_report(decision, reports_dir, stock_symbol)
            if decision_file:
                saved_files["final_trade_decision"] = str(decision_file)

        # 保存分析元数据文件
        self._save_metadata(result, reports_dir.parent, stock_symbol, analysis_date_str, saved_files)

        logger.info(f"✅ 分模块报告保存完成，共保存 {len(saved_files)} 个文件")
        return saved_files

    def _format_analysis_date(self, analysis_date_raw) -> str:
        """格式化分析日期"""
        if isinstance(analysis_date_raw, datetime):
            return analysis_date_raw.strftime("%Y-%m-%d")
        elif isinstance(analysis_date_raw, str):
            try:
                datetime.strptime(analysis_date_raw, "%Y-%m-%d")
                return analysis_date_raw
            except ValueError:
                return datetime.now().strftime("%Y-%m-%d")
        else:
            return datetime.now().strftime("%Y-%m-%d")

    async def _save_module_report(
        self,
        state: Dict[str, Any],
        module_key: str,
        module_info: Dict[str, str],
        reports_dir: Path,
        stock_symbol: str,
        summarizer_available: bool,
    ) -> Optional[Path]:
        """保存单个模块报告"""
        state_key = module_info["state_key"]
        if state_key not in state:
            return None

        module_content = state[state_key]
        report_content = module_content if isinstance(module_content, str) else str(module_content)

        filename = module_info["filename"]

        # 对大型辩论报告生成摘要版本
        if summarizer_available and len(report_content) > 15000:
            report_content = await self._generate_summary_if_needed(
                module_key, report_content, reports_dir, stock_symbol
            )

        # 保存到文件
        file_path = reports_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        logger.info(f"✅ 保存模块报告: {file_path}")
        return file_path

    async def _generate_summary_if_needed(
        self, module_key: str, report_content: str, reports_dir: Path, stock_symbol: str
    ) -> str:
        """为大型报告生成摘要"""
        from tradingagents.utils.report_summarizer import summarize_report

        if module_key == "investment_debate_state":
            summary, full_content = summarize_report(report_content, "research", stock_symbol, stock_symbol)
            full_path = reports_dir / "research_team_decision_full.md"
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(full_content)
            logger.info(f"✅ 保存完整版报告: {full_path}")
            return summary

        elif module_key == "risk_debate_state":
            summary, full_content = summarize_report(report_content, "risk", stock_symbol, stock_symbol)
            full_path = reports_dir / "risk_management_decision_full.md"
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(full_content)
            logger.info(f"✅ 保存完整版报告: {full_path}")
            return summary

        return report_content

    def _save_decision_report(
        self, decision: Dict[str, Any], reports_dir: Path, stock_symbol: str
    ) -> Optional[Path]:
        """保存最终决策报告"""
        decision_content = f"# {stock_symbol} 最终投资决策\n\n"
        decision_content += "## 投资建议\n\n"

        if isinstance(decision, dict):
            decision_content += f"**行动**: {decision.get('action', 'N/A')}\n\n"
            decision_content += f"**置信度**: {decision.get('confidence', 0):.1%}\n\n"
            decision_content += f"**风险评分**: {decision.get('risk_score', 0):.1%}\n\n"
            decision_content += f"**目标价位**: {decision.get('target_price', 'N/A')}\n\n"
            decision_content += f"## 分析推理\n\n{decision.get('reasoning', '暂无分析推理')}\n\n"
        else:
            decision_content += f"{str(decision)}\n\n"

        decision_file = reports_dir / "final_trade_decision.md"
        with open(decision_file, "w", encoding="utf-8") as f:
            f.write(decision_content)

        logger.info(f"✅ 保存最终决策: {decision_file}")
        return decision_file

    def _save_metadata(
        self,
        result: Dict[str, Any],
        stock_dir: Path,
        stock_symbol: str,
        analysis_date_str: str,
        saved_files: Dict[str, str],
    ):
        """保存分析元数据"""
        metadata = {
            "stock_symbol": stock_symbol,
            "analysis_date": analysis_date_str,
            "timestamp": datetime.now().isoformat(),
            "research_depth": result.get("research_depth", 1),
            "analysts": result.get("analysts", []),
            "status": "completed",
            "reports_count": len(saved_files),
            "report_types": list(saved_files.keys()),
        }

        metadata_file = stock_dir / "analysis_metadata.json"
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 保存分析元数据: {metadata_file}")
