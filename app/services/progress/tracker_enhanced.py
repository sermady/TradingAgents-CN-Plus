# -*- coding: utf-8 -*-
"""
增强型进度跟踪器

改进点:
1. 更细粒度的步骤划分 (每个分析师分为: 数据获取, 分析, 报告生成)
2. 更精确的进度百分比计算
3. 支持实时调整预估时间
4. 更好的Redis回退机制
5. 添加子步骤进度更新

作者: Claude
创建日期: 2026-02-12
"""

from typing import Any, Dict, Optional, List
import json
import os
import time
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger("app.services.progress.enhanced")


class StepStatus(Enum):
    """步骤状态"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class SubStep:
    """子步骤"""

    name: str
    description: str
    status: str = "pending"
    weight: float = 0.1
    start_time: Optional[float] = None
    end_time: Optional[float] = None


@dataclass
class AnalysisStep:
    """增强型分析步骤"""

    name: str
    description: str
    status: str = "pending"
    weight: float = 0.1
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    substeps: List[SubStep] = field(default_factory=list)
    analyst_type: Optional[str] = None  # 如果是分析师步骤,记录类型


class EnhancedProgressTracker:
    """增强型进度跟踪器"""

    def __init__(
        self,
        task_id: str,
        analysts: List[str],
        research_depth: str,
        llm_provider: str,
        use_redis: bool = True,
    ):
        self.task_id = task_id
        self.analysts = analysts
        self.research_depth = research_depth
        self.llm_provider = llm_provider
        self.use_redis = use_redis

        # Redis连接
        self.redis_client = None
        if use_redis:
            self.use_redis = self._init_redis()

        # 进度数据
        self.progress_data = {
            "task_id": task_id,
            "status": "running",
            "progress_percentage": 0.0,
            "current_step": 0,
            "total_steps": 0,
            "current_step_name": "初始化",
            "current_step_description": "准备开始分析",
            "current_substep": None,
            "last_message": "分析任务已启动",
            "start_time": time.time(),
            "last_update": time.time(),
            "elapsed_time": 0.0,
            "remaining_time": 0.0,
            "estimated_total_time": 0.0,
            "steps": [],
            "agent_status": {},
        }

        # 生成分析步骤
        self.analysis_steps = self._generate_detailed_steps()
        self.progress_data["total_steps"] = len(self.analysis_steps)
        self.progress_data["steps"] = [
            self._step_to_dict(step) for step in self.analysis_steps
        ]

        # 计算预估时间
        self.progress_data["estimated_total_time"] = self._calculate_total_estimate()
        self.progress_data["remaining_time"] = self.progress_data[
            "estimated_total_time"
        ]

        # 保存初始状态
        self._save_progress()

        logger.info(
            f"📊 [增强进度] 初始化: {task_id}, 步骤数: {len(self.analysis_steps)}"
        )

    def _init_redis(self) -> bool:
        """初始化Redis连接 (带重试和回退)"""
        try:
            redis_enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true"
            if not redis_enabled:
                logger.info(f"📊 [增强进度] Redis未启用，使用文件存储")
                return False

            import redis

            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", 6379))
            redis_password = os.getenv("REDIS_PASSWORD") or None
            redis_db = int(os.getenv("REDIS_DB", 0))

            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                decode_responses=True,
                socket_connect_timeout=3,
                socket_timeout=5,
            )

            # 测试连接
            self.redis_client.ping()
            logger.info(f"📊 [增强进度] Redis连接: {redis_host}:{redis_port}")
            return True

        except Exception as e:
            logger.warning(f"📊 [增强进度] Redis失败，回退到文件: {e}")
            return False

    def _generate_detailed_steps(self) -> List[AnalysisStep]:
        """生成详细的分析步骤 (包含子步骤)"""
        steps = []

        # 1) 基础准备阶段 (10%)
        steps.extend(
            [
                AnalysisStep(
                    "📋 准备阶段", "验证股票代码，检查数据源可用性", weight=0.03
                ),
                AnalysisStep(
                    "🔧 环境检查", "检查API密钥配置，确保数据获取正常", weight=0.02
                ),
                AnalysisStep("💰 成本估算", "根据分析深度预估API调用成本", weight=0.01),
                AnalysisStep("⚙️ 参数设置", "配置分析参数和AI模型选择", weight=0.02),
                AnalysisStep(
                    "🚀 启动引擎", "初始化AI分析引擎，准备开始分析", weight=0.02
                ),
            ]
        )

        # 2) 分析师团队阶段 (35%) - 每个分析师有子步骤
        analyst_weight = 0.35 / max(len(self.analysts), 1)
        for analyst in self.analysts:
            info = self._get_analyst_step_info(analyst)
            substeps = [
                SubStep("数据获取", f"获取{info['name']}所需数据", weight=0.2),
                SubStep("数据分析", f"AI分析{info['name']}数据", weight=0.5),
                SubStep("报告生成", f"生成{info['name']}报告", weight=0.3),
            ]
            steps.append(
                AnalysisStep(
                    info["name"],
                    info["description"],
                    weight=analyst_weight,
                    substeps=substeps,
                    analyst_type=analyst,
                )
            )

        # 3) 研究团队辩论阶段 (25%)
        rounds = self._get_debate_rounds()
        debate_weight = 0.25 / (3 + rounds)
        steps.extend(
            [
                AnalysisStep(
                    "🐂 看涨研究员", "基于分析师报告构建买入论据", weight=debate_weight
                ),
                AnalysisStep(
                    "🐻 看跌研究员", "识别潜在风险和问题", weight=debate_weight
                ),
            ]
        )
        for i in range(rounds):
            steps.append(
                AnalysisStep(
                    f"🎯 研究辩论 第{i + 1}轮",
                    "多头空头研究员深度辩论",
                    weight=debate_weight,
                    substeps=[
                        SubStep("多头论证", "看涨观点论证", weight=0.5),
                        SubStep("空头反驳", "看跌观点反驳", weight=0.5),
                    ],
                )
            )
        steps.append(
            AnalysisStep(
                "👔 研究经理", "综合辩论结果，形成研究共识", weight=debate_weight
            )
        )

        # 4) 交易团队阶段 (8%)
        steps.append(
            AnalysisStep(
                "💼 交易员决策",
                "基于研究结果制定具体交易策略",
                weight=0.08,
                substeps=[
                    SubStep("策略分析", "分析入场时机和仓位", weight=0.6),
                    SubStep("报告生成", "生成交易决策报告", weight=0.4),
                ],
            )
        )

        # 5) 风险管理团队阶段 (15%)
        risk_weight = 0.15 / 4
        steps.extend(
            [
                AnalysisStep(
                    "🔥 激进风险评估", "从激进角度评估投资风险", weight=risk_weight
                ),
                AnalysisStep(
                    "🛡️ 保守风险评估", "从保守角度评估投资风险", weight=risk_weight
                ),
                AnalysisStep(
                    "⚖️ 中性风险评估", "从中性角度评估投资风险", weight=risk_weight
                ),
                AnalysisStep(
                    "🎯 风险经理", "综合风险评估，制定风险控制策略", weight=risk_weight
                ),
            ]
        )

        # 6) 最终决策阶段 (7%)
        steps.extend(
            [
                AnalysisStep(
                    "📡 信号处理", "处理所有分析结果，生成交易信号", weight=0.04
                ),
                AnalysisStep("📊 生成报告", "整理分析结果，生成完整报告", weight=0.03),
            ]
        )

        return steps

    def _get_analyst_step_info(self, analyst: str) -> Dict[str, str]:
        """获取分析师步骤信息"""
        mapping = {
            "market": {
                "name": "📊 市场分析师",
                "description": "分析股价走势、成交量、技术指标等市场表现",
            },
            "fundamentals": {
                "name": "💼 基本面分析师",
                "description": "分析公司财务状况、盈利能力、成长性等基本面",
            },
            "news": {
                "name": "📰 新闻分析师",
                "description": "分析相关新闻、公告、行业动态对股价的影响",
            },
            "social": {
                "name": "💬 社交媒体分析师",
                "description": "分析社交媒体讨论、网络热度、散户情绪等",
            },
            "china": {
                "name": "🇨🇳 A股分析师",
                "description": "分析A股特有指标和政策影响",
            },
        }
        return mapping.get(
            analyst,
            {
                "name": f"🔍 {analyst}分析师",
                "description": f"进行{analyst}相关的专业分析",
            },
        )

    def _get_debate_rounds(self) -> int:
        """根据研究深度获取辩论轮次"""
        depth_map = {"快速": 1, "基础": 2, "标准": 3, "深度": 4, "全面": 5}
        d = depth_map.get(self.research_depth, 3)
        return min(d, 3)  # 最多3轮

    def _calculate_total_estimate(self) -> float:
        """计算预估总时间 (秒)"""
        depth_map = {"快速": 1, "基础": 2, "标准": 3, "深度": 4, "全面": 5}
        d = depth_map.get(self.research_depth, 3)

        base_time_per_depth = {1: 150, 2: 180, 3: 240, 4: 330, 5: 480}.get(d, 240)

        analyst_count = len(self.analysts)
        if analyst_count == 1:
            multiplier = 1.0
        elif analyst_count == 2:
            multiplier = 1.5
        elif analyst_count == 3:
            multiplier = 2.0
        elif analyst_count == 4:
            multiplier = 2.4
        else:
            multiplier = 2.4 + (analyst_count - 4) * 0.3

        model_mult = {
            "dashscope": 1.0,
            "deepseek": 0.8,
            "google": 1.2,
            "openai": 1.0,
        }.get(self.llm_provider, 1.0)

        return base_time_per_depth * multiplier * model_mult

    def _step_to_dict(self, step: AnalysisStep) -> Dict:
        """转换步骤为字典"""
        return {
            "name": step.name,
            "description": step.description,
            "status": step.status,
            "weight": step.weight,
            "start_time": step.start_time,
            "end_time": step.end_time,
            "analyst_type": step.analyst_type,
            "substeps": [asdict(s) for s in step.substeps],
        }

    def update_step_status(
        self,
        step_name: str,
        status: str,
        substep_name: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """更新步骤状态 (支持子步骤)"""
        current_time = time.time()

        for step in self.analysis_steps:
            if step.name == step_name:
                # 更新主步骤
                if status == "in_progress" and step.status == "pending":
                    step.start_time = current_time
                elif status in ["completed", "failed"] and step.status == "in_progress":
                    step.end_time = current_time
                step.status = status

                # 更新子步骤
                if substep_name and step.substeps:
                    for substep in step.substeps:
                        if substep.name == substep_name:
                            if status == "in_progress" and substep.status == "pending":
                                substep.start_time = current_time
                            elif (
                                status == "completed"
                                and substep.status == "in_progress"
                            ):
                                substep.end_time = current_time
                            substep.status = status
                            break

                # 更新进度数据
                if message:
                    self.progress_data["last_message"] = message
                self.progress_data["current_step_name"] = step_name
                self._recalculate_progress()
                self._save_progress()
                break

    def _recalculate_progress(self):
        """重新计算进度百分比"""
        completed_weight = 0.0

        for step in self.analysis_steps:
            if step.status == "completed":
                completed_weight += step.weight
            elif step.status == "in_progress" and step.substeps:
                # 计算子步骤进度
                sub_completed = sum(
                    s.weight for s in step.substeps if s.status == "completed"
                )
                sub_total = sum(s.weight for s in step.substeps)
                if sub_total > 0:
                    sub_progress = sub_completed / sub_total
                    completed_weight += step.weight * sub_progress

        self.progress_data["progress_percentage"] = round(completed_weight * 100, 1)
        self._update_time_estimates()

    def _update_time_estimates(self):
        """更新时间估算"""
        now = time.time()
        elapsed = now - self.progress_data["start_time"]
        pct = self.progress_data["progress_percentage"]

        if pct >= 100:
            self.progress_data["remaining_time"] = 0
        elif pct > 10:
            # 基于实际进度重新估算
            estimated_total = elapsed / (pct / 100)
            self.progress_data["remaining_time"] = max(0, estimated_total - elapsed)
        else:
            # 进度太少，使用预估
            self.progress_data["remaining_time"] = max(
                0, self.progress_data["estimated_total_time"] - elapsed
            )

        self.progress_data["elapsed_time"] = elapsed
        self.progress_data["last_update"] = now

    def update_agent_status(
        self, agent_name: str, status: str, message: Optional[str] = None
    ):
        """更新代理状态"""
        if "agent_status" not in self.progress_data:
            self.progress_data["agent_status"] = {}

        self.progress_data["agent_status"][agent_name] = {
            "status": status,
            "updated_at": time.time(),
            "message": message,
        }

        # 查找对应的步骤并更新
        for step in self.analysis_steps:
            if step.analyst_type and agent_name in step.name:
                if status == "in_progress":
                    self.update_step_status(step.name, "in_progress")
                elif status == "completed":
                    self.update_step_status(step.name, "completed")
                elif status == "failed":
                    self.update_step_status(step.name, "failed")
                break

        self._save_progress()

    def _save_progress(self):
        """保存进度到存储"""
        try:
            self.progress_data["steps"] = [
                self._step_to_dict(s) for s in self.analysis_steps
            ]
            progress_copy = {
                k: v for k, v in self.progress_data.items() if k != "steps"
            }
            progress_copy["steps"] = self.progress_data["steps"]
            serialized = json.dumps(progress_copy, ensure_ascii=False)

            if self.use_redis and self.redis_client:
                try:
                    key = f"progress:{self.task_id}"
                    self.redis_client.set(key, serialized)
                    self.redis_client.expire(key, 3600)
                    return
                except Exception as e:
                    logger.debug(f"[增强进度] Redis保存失败: {e}")

            # 回退到文件存储
            os.makedirs("./data/progress", exist_ok=True)
            with open(
                f"./data/progress/{self.task_id}.json", "w", encoding="utf-8"
            ) as f:
                f.write(serialized)

        except Exception as e:
            logger.error(f"[增强进度] 保存失败: {e}")

    def mark_completed(self):
        """标记完成"""
        self.progress_data["progress_percentage"] = 100
        self.progress_data["status"] = "completed"
        self.progress_data["completed"] = True
        self.progress_data["completed_time"] = time.time()

        for step in self.analysis_steps:
            if step.status != "failed":
                step.status = "completed"
                step.end_time = step.end_time or time.time()

        self._save_progress()
        logger.info(f"✅ [增强进度] 完成: {self.task_id}")

    def mark_failed(self, reason: str = ""):
        """标记失败"""
        self.progress_data["status"] = "failed"
        self.progress_data["failed"] = True
        self.progress_data["failed_reason"] = reason
        self.progress_data["completed_time"] = time.time()
        self._save_progress()
        logger.error(f"❌ [增强进度] 失败: {self.task_id} - {reason}")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "analysts": self.analysts,
            "research_depth": self.research_depth,
            "llm_provider": self.llm_provider,
            "steps": [self._step_to_dict(s) for s in self.analysis_steps],
            "start_time": self.progress_data.get("start_time"),
            "elapsed_time": self.progress_data.get("elapsed_time", 0),
            "remaining_time": self.progress_data.get("remaining_time", 0),
            "estimated_total_time": self.progress_data.get("estimated_total_time", 0),
            "progress_percentage": self.progress_data.get("progress_percentage", 0),
            "status": self.progress_data.get("status", "pending"),
            "current_step": self.progress_data.get("current_step"),
            "agent_status": self.progress_data.get("agent_status", {}),
        }
