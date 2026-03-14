# -*- coding: utf-8 -*-
"""
AI模型智能推荐系统
根据使用场景、成本需求、性能要求自动推荐最优模型配置
"""

import os
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from .simple_config_manager import ProviderType


class AnalysisComplexity(Enum):
    """分析复杂度"""
    SIMPLE = "simple"      # 简单分析: 基本行情 + 简单指标
    STANDARD = "standard"  # 标准分析: 全面分析，平衡性能和深度
    DETAILED = "detailed"  # 详细分析: 深度分析，最高精度
    BATCH = "batch"        # 批量分析: 高并发，多股票


class CostSensitivity(Enum):
    """成本敏感度"""
    FREE_ONLY = "free_only"        # 只使用免费模型
    COST_SENSITIVE = "cost_sensitive"  # 成本敏感
    BALANCED = "balanced"          # 成本性能平衡
    PERFORMANCE_FIRST = "performance_first"  # 性能优先


class UsagePattern(Enum):
    """使用模式"""
    DEVELOPMENT = "development"    # 开发测试
    OCCASIONAL = "occasional"      # 偶尔使用
    REGULAR = "regular"           # 定期使用
    INTENSIVE = "intensive"       # 密集使用


@dataclass
class ModelProfile:
    """模型特征档案"""
    provider: ProviderType
    model_name: str
    
    # 成本特征
    cost_tier: str  # free/low/medium/high
    tokens_per_dollar: float  # 每美元token数
    daily_free_quota: int = 0  # 每日免费配额
    
    # 性能特征
    avg_response_time: float = 1000  # 平均响应时间(ms)
    max_context_length: int = 4096   # 最大上下文长度
    reasoning_quality: float = 0.8   # 推理质量评分 0-1
    chinese_performance: float = 0.8  # 中文性能评分 0-1
    
    # 能力特征
    capabilities: List[str] = field(default_factory=list)
    suitable_for: List[AnalysisComplexity] = field(default_factory=list)
    
    # 可靠性
    availability_score: float = 0.95  # 可用性评分 0-1
    rate_limit: int = 100  # 每分钟请求限制


@dataclass
class RecommendationRequest:
    """推荐请求"""
    complexity: AnalysisComplexity
    cost_sensitivity: CostSensitivity
    usage_pattern: UsagePattern
    expected_monthly_cost: Optional[float] = None
    preferred_response_time: Optional[float] = None  # ms
    chinese_priority: bool = True
    batch_size: int = 1


@dataclass
class ModelRecommendation:
    """模型推荐结果"""
    profile: ModelProfile
    score: float  # 推荐评分 0-1
    reasons: List[str]  # 推荐理由
    estimated_cost: float  # 预估成本
    cost_breakdown: Dict[str, Any]  # 成本详细分解
    performance_prediction: Dict[str, Any]  # 性能预测
    warnings: List[str] = field(default_factory=list)  # 警告信息


class SmartModelRecommender:
    """智能模型推荐器"""
    
    def __init__(self):
        # 初始化模型档案数据
        self.model_profiles: Dict[Tuple[ProviderType, str], ModelProfile] = {}
        self.usage_history: List[Dict[str, Any]] = []
        self.cost_history: List[Dict[str, Any]] = []
        
        self._initialize_model_profiles()
        self._load_historical_data()
    
    def _initialize_model_profiles(self):
        """初始化模型特征档案"""
        profiles = [
            # DeepSeek模型
            ModelProfile(
                provider=ProviderType.DEEPSEEK,
                model_name="deepseek-chat",
                cost_tier="low",
                tokens_per_dollar=500000,  # 非常高性价比
                daily_free_quota=0,
                avg_response_time=800,
                max_context_length=32768,
                reasoning_quality=0.92,
                chinese_performance=0.85,
                capabilities=["reasoning", "coding", "analysis", "chat"],
                suitable_for=[AnalysisComplexity.STANDARD, AnalysisComplexity.DETAILED],
                availability_score=0.95,
                rate_limit=60
            ),
            
            # 阿里通义千问
            ModelProfile(
                provider=ProviderType.DASHSCOPE,
                model_name="qwen-plus",
                cost_tier="medium",
                tokens_per_dollar=200000,
                daily_free_quota=1000000,
                avg_response_time=600,
                max_context_length=8192,
                reasoning_quality=0.88,
                chinese_performance=0.95,  # 中文表现最佳
                capabilities=["chinese", "reasoning", "analysis", "chat"],
                suitable_for=[AnalysisComplexity.SIMPLE, AnalysisComplexity.STANDARD],
                availability_score=0.90,
                rate_limit=100
            ),
            
            # Google Gemini
            ModelProfile(
                provider=ProviderType.GEMINI,
                model_name="gemini-2.5-flash",
                cost_tier="low",
                tokens_per_dollar=400000,
                daily_free_quota=1500000,
                avg_response_time=1000,
                max_context_length=1048576,  # 超大上下文
                reasoning_quality=0.90,
                chinese_performance=0.80,
                capabilities=["reasoning", "multimodal", "long_context"],
                suitable_for=[AnalysisComplexity.DETAILED, AnalysisComplexity.BATCH],
                availability_score=0.92,
                rate_limit=15
            ),
            
            # 硅基流动
            ModelProfile(
                provider=ProviderType.SILICONFLOW,
                model_name="deepseek-ai/DeepSeek-V3",
                cost_tier="free",
                tokens_per_dollar=float('inf'),  # 免费
                daily_free_quota=500000,
                avg_response_time=1200,
                max_context_length=8192,
                reasoning_quality=0.85,
                chinese_performance=0.82,
                capabilities=["free", "reasoning", "chat"],
                suitable_for=[AnalysisComplexity.SIMPLE, AnalysisComplexity.STANDARD],
                availability_score=0.85,
                rate_limit=30
            ),
            
            # OpenRouter (多模型聚合)
            ModelProfile(
                provider=ProviderType.OPENROUTER,
                model_name="meta-llama/llama-3.1-8b-instruct",
                cost_tier="variable",
                tokens_per_dollar=1000000,  # 价格变动
                daily_free_quota=200000,
                avg_response_time=1500,
                max_context_length=8192,
                reasoning_quality=0.75,
                chinese_performance=0.70,
                capabilities=["variety", "flexibility", "cost_effective"],
                suitable_for=[AnalysisComplexity.SIMPLE, AnalysisComplexity.BATCH],
                availability_score=0.88,
                rate_limit=50
            )
        ]
        
        for profile in profiles:
            key = (profile.provider, profile.model_name)
            self.model_profiles[key] = profile
            
        logger.info(f"[SMART_RECOMMENDER] 初始化了 {len(profiles)} 个模型档案")
    
    def _load_historical_data(self):
        """加载历史数据"""
        try:
            # 尝试从缓存加载使用历史
            cache_file = "config/model_usage_history.json"
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.usage_history = data.get('usage_history', [])
                    self.cost_history = data.get('cost_history', [])
                    
                logger.info(f"[SMART_RECOMMENDER] 加载了 {len(self.usage_history)} 条使用历史")
        except Exception as e:
            logger.debug(f"[SMART_RECOMMENDER] 历史数据加载失败: {e}")
    
    def calculate_model_score(self, profile: ModelProfile, request: RecommendationRequest) -> Tuple[float, List[str]]:
        """计算模型推荐评分"""
        score = 0.0
        reasons = []
        
        # 1. 成本评估 (权重: 35%)
        cost_score, cost_reasons = self._calculate_cost_score(profile, request)
        score += cost_score * 0.35
        reasons.extend(cost_reasons)
        
        # 2. 性能评估 (权重: 25%)
        perf_score, perf_reasons = self._calculate_performance_score(profile, request)
        score += perf_score * 0.25
        reasons.extend(perf_reasons)
        
        # 3. 功能适配 (权重: 20%)
        feature_score, feature_reasons = self._calculate_feature_score(profile, request)
        score += feature_score * 0.20
        reasons.extend(feature_reasons)
        
        # 4. 可靠性评估 (权重: 20%)
        reliability_score, reliability_reasons = self._calculate_reliability_score(profile, request)
        score += reliability_score * 0.20
        reasons.extend(reliability_reasons)
        
        return score, reasons
    
    def _calculate_cost_score(self, profile: ModelProfile, request: RecommendationRequest) -> Tuple[float, List[str]]:
        """计算成本评分"""
        score = 0.0
        reasons = []
        
        # 成本敏感度权重
        if request.cost_sensitivity == CostSensitivity.FREE_ONLY:
            if profile.cost_tier == "free":
                score = 1.0
                reasons.append("完全免费使用")
            else:
                score = 0.1
                reasons.append("需要付费，不符合免费要求")
                
        elif request.cost_sensitivity == CostSensitivity.COST_SENSITIVE:
            cost_tier_scores = {
                "free": 1.0,
                "low": 0.8,
                "medium": 0.4,
                "high": 0.1,
                "variable": 0.6
            }
            score = cost_tier_scores.get(profile.cost_tier, 0.5)
            reasons.append(f"成本等级: {profile.cost_tier}")
            
        elif request.cost_sensitivity == CostSensitivity.BALANCED:
            # 平衡成本和性能
            if profile.cost_tier in ["free", "low"]:
                score = 0.8
                reasons.append("低成本选择")
            elif profile.cost_tier == "medium":
                score = 1.0
                reasons.append("成本性能平衡")
            else:
                score = 0.6
                reasons.append("较高成本但高性能")
                
        else:  # PERFORMANCE_FIRST
            score = 0.9  # 成本不是主要考虑因素
            reasons.append("性能优先，成本次要")
        
        # 免费配额加分
        if profile.daily_free_quota > 0:
            bonus = min(0.1, profile.daily_free_quota / 1000000)
            score += bonus
            reasons.append(f"每日免费配额: {profile.daily_free_quota:,} tokens")
        
        return min(score, 1.0), reasons
    
    def _calculate_performance_score(self, profile: ModelProfile, request: RecommendationRequest) -> Tuple[float, List[str]]:
        """计算性能评分"""
        score = 0.0
        reasons = []
        
        # 响应时间评分
        if request.preferred_response_time:
            if profile.avg_response_time <= request.preferred_response_time:
                time_score = 1.0
                reasons.append(f"响应时间满足要求 ({profile.avg_response_time:.0f}ms)")
            else:
                time_score = request.preferred_response_time / profile.avg_response_time
                reasons.append(f"响应时间较慢 ({profile.avg_response_time:.0f}ms)")
        else:
            # 默认响应时间评分 (1000ms为基准)
            time_score = max(0.2, min(1.0, 1000 / profile.avg_response_time))
            reasons.append(f"响应时间: {profile.avg_response_time:.0f}ms")
        
        score += time_score * 0.4
        
        # 推理质量评分
        score += profile.reasoning_quality * 0.4
        reasons.append(f"推理质量: {profile.reasoning_quality:.2f}")
        
        # 中文性能评分
        if request.chinese_priority:
            score += profile.chinese_performance * 0.2
            reasons.append(f"中文性能: {profile.chinese_performance:.2f}")
        else:
            score += 0.2  # 不重要时给固定分数
        
        return min(score, 1.0), reasons
    
    def _calculate_feature_score(self, profile: ModelProfile, request: RecommendationRequest) -> Tuple[float, List[str]]:
        """计算功能适配评分"""
        score = 0.0
        reasons = []
        
        # 分析复杂度适配
        if request.complexity in profile.suitable_for:
            score += 0.6
            reasons.append(f"适合{request.complexity.value}分析")
        else:
            # 检查相近的复杂度
            complexity_mapping = {
                AnalysisComplexity.SIMPLE: [AnalysisComplexity.STANDARD],
                AnalysisComplexity.STANDARD: [AnalysisComplexity.SIMPLE, AnalysisComplexity.DETAILED],
                AnalysisComplexity.DETAILED: [AnalysisComplexity.STANDARD],
                AnalysisComplexity.BATCH: [AnalysisComplexity.SIMPLE, AnalysisComplexity.STANDARD]
            }
            
            related = complexity_mapping.get(request.complexity, [])
            if any(comp in profile.suitable_for for comp in related):
                score += 0.3
                reasons.append(f"可适配{request.complexity.value}分析")
            else:
                score += 0.1
                reasons.append(f"不太适合{request.complexity.value}分析")
        
        # 上下文长度评分
        required_context = {
            AnalysisComplexity.SIMPLE: 2048,
            AnalysisComplexity.STANDARD: 4096,
            AnalysisComplexity.DETAILED: 8192,
            AnalysisComplexity.BATCH: 4096
        }
        
        needed = required_context.get(request.complexity, 4096)
        if profile.max_context_length >= needed * 2:
            score += 0.3
            reasons.append(f"上下文长度充足 ({profile.max_context_length:,})")
        elif profile.max_context_length >= needed:
            score += 0.2
            reasons.append(f"上下文长度满足 ({profile.max_context_length:,})")
        else:
            score += 0.1
            reasons.append(f"上下文长度不足 ({profile.max_context_length:,})")
        
        # 特殊能力加分
        if request.chinese_priority and "chinese" in profile.capabilities:
            score += 0.1
            reasons.append("专门优化中文处理")
        
        return min(score, 1.0), reasons
    
    def _calculate_reliability_score(self, profile: ModelProfile, request: RecommendationRequest) -> Tuple[float, List[str]]:
        """计算可靠性评分"""
        score = profile.availability_score
        reasons = [f"可用性评分: {profile.availability_score:.2f}"]
        
        # 使用模式适配
        rate_requirements = {
            UsagePattern.DEVELOPMENT: 20,
            UsagePattern.OCCASIONAL: 30,
            UsagePattern.REGULAR: 60,
            UsagePattern.INTENSIVE: 100
        }
        
        required_rate = rate_requirements.get(request.usage_pattern, 60)
        
        if profile.rate_limit >= required_rate:
            rate_score = 1.0
            reasons.append(f"请求限制充足 ({profile.rate_limit}/min)")
        elif profile.rate_limit >= required_rate * 0.5:
            rate_score = 0.7
            reasons.append(f"请求限制基本满足 ({profile.rate_limit}/min)")
        else:
            rate_score = 0.3
            reasons.append(f"请求限制较低 ({profile.rate_limit}/min)")
        
        # 综合评分
        final_score = (score + rate_score) / 2
        
        return min(final_score, 1.0), reasons
    
    def estimate_usage_cost(self, profile: ModelProfile, request: RecommendationRequest) -> Dict[str, Any]:
        """估算使用成本"""
        
        # 基础参数估算
        tokens_per_analysis = {
            AnalysisComplexity.SIMPLE: 1500,
            AnalysisComplexity.STANDARD: 3000,
            AnalysisComplexity.DETAILED: 6000,
            AnalysisComplexity.BATCH: 2000  # 单股票平均
        }
        
        analyses_per_day = {
            UsagePattern.DEVELOPMENT: 5,
            UsagePattern.OCCASIONAL: 3,
            UsagePattern.REGULAR: 10,
            UsagePattern.INTENSIVE: 50
        }
        
        tokens_per_analysis_est = tokens_per_analysis.get(request.complexity, 3000)
        daily_analyses = analyses_per_day.get(request.usage_pattern, 10)
        daily_tokens = tokens_per_analysis_est * daily_analyses * request.batch_size
        monthly_tokens = daily_tokens * 30
        
        # 成本计算
        if profile.cost_tier == "free":
            if monthly_tokens <= profile.daily_free_quota * 30:
                monthly_cost = 0.0
            else:
                excess_tokens = monthly_tokens - (profile.daily_free_quota * 30)
                monthly_cost = excess_tokens / profile.tokens_per_dollar
        else:
            # 考虑免费配额
            free_tokens = profile.daily_free_quota * 30
            billable_tokens = max(0, monthly_tokens - free_tokens)
            monthly_cost = billable_tokens / profile.tokens_per_dollar
        
        return {
            "daily_tokens": daily_tokens,
            "monthly_tokens": monthly_tokens,
            "monthly_cost_usd": monthly_cost,
            "cost_per_analysis": monthly_cost / (daily_analyses * 30) if daily_analyses > 0 else 0,
            "free_quota_used_pct": min(100, (monthly_tokens / (profile.daily_free_quota * 30 or 1)) * 100),
            "breakdown": {
                "tokens_per_analysis": tokens_per_analysis_est,
                "analyses_per_day": daily_analyses,
                "batch_size": request.batch_size,
                "free_quota_monthly": profile.daily_free_quota * 30,
                "billable_tokens": max(0, monthly_tokens - (profile.daily_free_quota * 30))
            }
        }
    
    def get_recommendations(self, request: RecommendationRequest, top_k: int = 3) -> List[ModelRecommendation]:
        """获取模型推荐"""
        logger.info(f"[SMART_RECOMMENDER] 开始推荐: 复杂度={request.complexity.value}, "
                   f"成本敏感度={request.cost_sensitivity.value}, 使用模式={request.usage_pattern.value}")
        
        recommendations = []
        
        for profile in self.model_profiles.values():
            # 计算推荐评分
            score, reasons = self.calculate_model_score(profile, request)
            
            # 估算成本
            cost_breakdown = self.estimate_usage_cost(profile, request)
            
            # 生成性能预测
            performance_prediction = {
                "expected_response_time": profile.avg_response_time,
                "reasoning_quality": profile.reasoning_quality,
                "chinese_performance": profile.chinese_performance if request.chinese_priority else "不重要",
                "context_support": profile.max_context_length,
                "suitable_complexity": [c.value for c in profile.suitable_for]
            }
            
            # 生成警告
            warnings = []
            if cost_breakdown["monthly_cost_usd"] > 10.0:
                warnings.append("预估月成本较高，建议关注使用量")
            if profile.rate_limit < 60 and request.usage_pattern == UsagePattern.INTENSIVE:
                warnings.append("请求限制可能不足以支持密集使用")
            if request.chinese_priority and profile.chinese_performance < 0.8:
                warnings.append("中文处理能力一般，可能影响分析质量")
            
            recommendation = ModelRecommendation(
                profile=profile,
                score=score,
                reasons=reasons,
                estimated_cost=cost_breakdown["monthly_cost_usd"],
                cost_breakdown=cost_breakdown,
                performance_prediction=performance_prediction,
                warnings=warnings
            )
            
            recommendations.append(recommendation)
        
        # 按评分排序
        recommendations.sort(key=lambda x: x.score, reverse=True)
        
        # 记录推荐结果
        logger.info(f"[SMART_RECOMMENDER] 推荐结果Top3:")
        for i, rec in enumerate(recommendations[:3]):
            logger.info(f"  {i+1}. {rec.profile.provider.value}/{rec.profile.model_name}: "
                       f"评分={rec.score:.3f}, 预估成本=${rec.estimated_cost:.2f}/月")
        
        return recommendations[:top_k]
    
    def get_optimal_recommendation(self, request: RecommendationRequest) -> Optional[ModelRecommendation]:
        """获取最优推荐"""
        recommendations = self.get_recommendations(request, top_k=1)
        return recommendations[0] if recommendations else None
    
    def save_usage_feedback(self, provider: ProviderType, model_name: str, 
                           actual_cost: float, performance_rating: float,
                           usage_notes: str = ""):
        """保存使用反馈，用于改进推荐"""
        feedback = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider.value,
            "model_name": model_name,
            "actual_cost": actual_cost,
            "performance_rating": performance_rating,  # 0-1
            "notes": usage_notes
        }
        
        self.usage_history.append(feedback)
        
        # 保存到文件
        try:
            os.makedirs("config", exist_ok=True)
            with open("config/model_usage_history.json", 'w', encoding='utf-8') as f:
                json.dump({
                    "usage_history": self.usage_history[-100:],  # 只保存最近100条
                    "cost_history": self.cost_history
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[SMART_RECOMMENDER] 反馈保存失败: {e}")


# 全局实例
smart_model_recommender = SmartModelRecommender()


def recommend_optimal_model(complexity: str = "standard", 
                           cost_sensitivity: str = "balanced",
                           usage_pattern: str = "regular",
                           chinese_priority: bool = True) -> Optional[ModelRecommendation]:
    """便捷函数：获取最优模型推荐"""
    try:
        request = RecommendationRequest(
            complexity=AnalysisComplexity(complexity),
            cost_sensitivity=CostSensitivity(cost_sensitivity),
            usage_pattern=UsagePattern(usage_pattern),
            chinese_priority=chinese_priority
        )
        
        return smart_model_recommender.get_optimal_recommendation(request)
        
    except Exception as e:
        logger.error(f"[SMART_RECOMMENDER] 推荐失败: {e}")
        return None