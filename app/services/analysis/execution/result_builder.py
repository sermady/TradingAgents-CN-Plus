# -*- coding: utf-8 -*-
"""结果构建模块

负责分析结果的构建、格式化和保存
"""

import logging
import uuid
from typing import Any, Dict, Optional

from app.services.memory_state_manager import TaskStatus
from app.utils.report_extractor import ReportExtractor

logger = logging.getLogger(__name__)


class ResultBuilderMixin:
    """结果构建混入类"""

    def _build_analysis_result(
        self, request, state, decision, execution_time: float, analysis_date: str
    ) -> Dict[str, Any]:
        """构建分析结果

        Args:
            request: 分析请求对象
            state: 分析状态
            decision: 交易决策
            execution_time: 执行时间（秒）
            analysis_date: 分析日期

        Returns:
            分析结果字典
        """
        # 提取reports
        try:
            extraction_result = ReportExtractor.extract_all_content(state)
            reports = extraction_result.get("reports", {})
        except Exception as e:
            logger.warning(f"⚠️ 提取reports时出错: {e}")
            reports = self._extract_reports_fallback(decision)

        # 格式化decision
        formatted_decision = self._format_decision(decision)

        # 生成summary和recommendation
        summary = self._generate_summary(reports, state)
        recommendation = self._generate_recommendation(formatted_decision)

        # 获取模型信息
        model_info = (
            decision.get("model_info", "Unknown")
            if isinstance(decision, dict)
            else "Unknown"
        )

        return {
            "analysis_id": str(uuid.uuid4()),
            "stock_code": request.stock_code,
            "stock_symbol": request.stock_code,
            "analysis_date": analysis_date,
            "summary": summary,
            "recommendation": recommendation,
            "confidence_score": formatted_decision.get("confidence", 0.0),
            "risk_level": "中等",
            "key_points": [],
            "detailed_analysis": decision,
            "execution_time": execution_time,
            "tokens_used": decision.get("tokens_used", 0)
            if isinstance(decision, dict)
            else 0,
            "state": state,
            "analysts": request.parameters.selected_analysts
            if request.parameters
            else [],
            "research_depth": request.parameters.research_depth
            if request.parameters
            else "快速",
            "reports": reports,
            "decision": formatted_decision,
            "model_info": model_info,
            "performance_metrics": state.get("performance_metrics", {})
            if isinstance(state, dict)
            else {},
        }

    def _extract_reports_fallback(self, decision) -> Dict[str, str]:
        """降级提取报告

        当正常提取失败时，从decision中尝试提取报告内容

        Args:
            decision: 交易决策

        Returns:
            报告字典
        """
        reports = {}
        try:
            if isinstance(decision, dict):
                for key, value in decision.items():
                    if isinstance(value, str) and len(value) > 50:
                        reports[key] = value
                logger.info(f"📊 降级：从decision中提取到 {len(reports)} 个报告")
        except Exception as e:
            logger.warning(f"⚠️ 降级提取也失败: {e}")
        return reports

    def _format_decision(self, decision) -> Dict[str, Any]:
        """格式化decision数据

        Args:
            decision: 原始决策数据

        Returns:
            格式化后的决策字典
        """
        try:
            if isinstance(decision, dict):
                # 处理目标价格
                target_price = self._parse_target_price(decision.get("target_price"))

                # 将英文投资建议转换为中文
                action_translation = {
                    "BUY": "买入",
                    "SELL": "卖出",
                    "HOLD": "持有",
                    "buy": "买入",
                    "sell": "卖出",
                    "hold": "持有",
                }
                action = decision.get("action", "持有")
                chinese_action = action_translation.get(action, action)

                return {
                    "action": chinese_action,
                    "confidence": decision.get("confidence", 0.5),
                    "risk_score": decision.get("risk_score", 0.3),
                    "target_price": target_price,
                    "reasoning": decision.get("reasoning", "暂无分析推理"),
                }
        except Exception as e:
            logger.error(f"❌ 格式化decision失败: {e}")

        return {
            "action": "持有",
            "confidence": 0.5,
            "risk_score": 0.3,
            "target_price": None,
            "reasoning": "暂无分析推理",
        }

    def _parse_target_price(self, target_price) -> Optional[float]:
        """解析目标价格

        Args:
            target_price: 目标价格（各种格式）

        Returns:
            解析后的浮点数价格，或None
        """
        if target_price is None or target_price == "N/A":
            return None

        try:
            if isinstance(target_price, str):
                clean_price = (
                    target_price.replace("$", "")
                    .replace("¥", "")
                    .replace("￥", "")
                    .strip()
                )
                return (
                    float(clean_price)
                    if clean_price and clean_price != "None"
                    else None
                )
            elif isinstance(target_price, (int, float)):
                return float(target_price)
        except (ValueError, TypeError):
            pass
        return None

    def _generate_summary(self, reports: Dict[str, str], state) -> str:
        """生成摘要

        Args:
            reports: 报告字典
            state: 分析状态

        Returns:
            摘要字符串
        """
        summary = ""

        # 1. 优先从reports中的final_trade_decision提取
        if isinstance(reports, dict) and "final_trade_decision" in reports:
            final_decision_content = reports["final_trade_decision"]
            if (
                isinstance(final_decision_content, str)
                and len(final_decision_content) > 50
            ):
                summary = (
                    final_decision_content[:200]
                    .replace("#", "")
                    .replace("*", "")
                    .strip()
                )
                if len(final_decision_content) > 200:
                    summary += "..."
                return summary

        # 2. 从state中提取
        if not summary and isinstance(state, dict):
            final_decision = state.get("final_trade_decision", "")
            if isinstance(final_decision, str) and len(final_decision) > 50:
                summary = final_decision[:200].replace("#", "").replace("*", "").strip()
                if len(final_decision) > 200:
                    summary += "..."
                return summary

        # 3. 从其他报告中提取
        if not summary and isinstance(reports, dict):
            for report_name, content in reports.items():
                if isinstance(content, str) and len(content) > 100:
                    summary = content[:200].replace("#", "").replace("*", "").strip()
                    if len(content) > 200:
                        summary += "..."
                    return summary

        # 4. 最后的备用方案
        if not summary:
            summary = "分析已完成，请查看详细报告。"

        return summary

    def _generate_recommendation(self, formatted_decision: Dict[str, Any]) -> str:
        """生成投资建议

        Args:
            formatted_decision: 格式化后的决策

        Returns:
            投资建议字符串
        """
        if not isinstance(formatted_decision, dict):
            return "请参考详细分析报告做出投资决策。"

        action = formatted_decision.get("action", "持有")
        target_price = formatted_decision.get("target_price")
        reasoning = formatted_decision.get("reasoning", "")

        recommendation = f"投资建议：{action}。"
        if target_price:
            recommendation += f"目标价格：{target_price}元。"
        if reasoning:
            recommendation += f"决策依据：{reasoning}"

        return recommendation

    async def _run_risk_validation(
        self, task_id: str, result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行风控验证

        Args:
            task_id: 任务ID
            result: 分析结果

        Returns:
            添加了风控验证信息的结果
        """
        try:
            from app.services.execution_risk_gateway import (
                get_execution_risk_gateway,
            )

            logger.info(f"🔒 开始执行风控验证: {task_id}")
            risk_gateway = get_execution_risk_gateway()
            risk_validation = risk_gateway.validate_from_analysis_result(result)

            result["risk_validation"] = risk_validation.to_dict()

            if risk_validation.blocked:
                logger.warning(f"🚫 交易决策被风控拦截: {task_id}")
                result["warnings"] = result.get("warnings", []) + [
                    f"风控拦截: {risk_validation.summary}"
                ]
            elif not risk_validation.passed:
                logger.warning(f"⚠️ 交易决策存在风险警告: {task_id}")
                result["warnings"] = result.get("warnings", []) + [
                    f"风险提示: {risk_validation.summary}"
                ]
            else:
                logger.info(f"✅ 风控验证通过: {task_id}")

        except Exception as risk_error:
            logger.error(f"❌ 风控验证失败(继续保存结果): {task_id} - {risk_error}")

        return result

    async def _save_results(self, task_id: str, result: Dict[str, Any]):
        """保存分析结果

        Args:
            task_id: 任务ID
            result: 分析结果
        """
        try:
            logger.info(f"💾 开始保存分析结果: {task_id}")
            from app.services.analysis.report_generation_service import (
                ReportGenerationService,
            )

            report_service = ReportGenerationService()
            await report_service.save_analysis_results_complete(task_id, result)
            logger.info(f"✅ 分析结果保存完成: {task_id}")
        except Exception as save_error:
            logger.error(f"❌ 保存分析结果失败: {task_id} - {save_error}")

    async def _mark_task_completed(self, task_id: str, result: Dict[str, Any]):
        """标记任务完成

        Args:
            task_id: 任务ID
            result: 分析结果
        """
        from app.models.analysis import AnalysisStatus
        from app.services.analysis.task_management_service import TaskManagementService

        await self.memory_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="分析完成",
            current_step="completed",
            result_data=result,
        )

        task_service = TaskManagementService()
        await task_service.update_task_status(task_id, AnalysisStatus.COMPLETED, 100)

    async def _create_completion_notification(
        self, user_id: str, request, result: Dict[str, Any]
    ):
        """创建分析完成通知

        Args:
            user_id: 用户ID
            request: 分析请求对象
            result: 分析结果
        """
        try:
            from app.models.notification import NotificationCreate
            from app.services.notifications_service import get_notifications_service

            svc = get_notifications_service()
            summary = str(result.get("summary", ""))[:120]
            await svc.create_and_publish(
                payload=NotificationCreate(
                    user_id=str(user_id),
                    type="analysis",
                    title=f"{request.stock_code} 分析完成",
                    content=summary,
                    link=f"/stocks/{request.stock_code}",
                    source="analysis",
                )
            )
        except Exception as notif_err:
            logger.warning(f"⚠️ 创建通知失败(忽略): {notif_err}")

    async def _handle_execution_error(
        self,
        task_id: str,
        request,
        error: Exception,
        progress_tracker=None,
    ):
        """处理执行错误

        Args:
            task_id: 任务ID
            request: 分析请求对象
            error: 异常对象
            progress_tracker: 进度跟踪器
        """
        from app.models.analysis import AnalysisStatus
        from app.services.analysis.task_management_service import TaskManagementService

        logger.error(f"❌ 后台分析任务失败: {task_id} - {error}")

        # 收集上下文信息
        error_context = {}
        if hasattr(request, "parameters") and request.parameters:
            if hasattr(request.parameters, "quick_model"):
                error_context["model"] = request.parameters.quick_model
            if hasattr(request.parameters, "deep_model"):
                error_context["model"] = request.parameters.deep_model

        # 格式化错误
        from app.utils.error_formatter import ErrorFormatter

        formatted_error = ErrorFormatter.format_error(str(error), error_context)
        user_friendly_error = (
            f"{formatted_error['title']}\n\n"
            f"{formatted_error['message']}\n\n"
            f"💡 {formatted_error['suggestion']}"
        )

        # 标记进度跟踪器失败
        if progress_tracker:
            progress_tracker.mark_failed(user_friendly_error)

        # 更新状态为失败
        await self.memory_manager.update_task_status(
            task_id=task_id,
            status=TaskStatus.FAILED,
            progress=0,
            message="分析失败",
            current_step="failed",
            error_message=user_friendly_error,
        )

        task_service = TaskManagementService()
        await task_service.update_task_status(
            task_id, AnalysisStatus.FAILED, 0, user_friendly_error
        )
