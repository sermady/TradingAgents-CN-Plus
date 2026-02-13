# -*- coding: utf-8 -*-
"""
模型能力管理服务

提供模型能力评估、验证和推荐功能。
"""

from typing import Tuple, Dict, Optional, List, Any
from app.constants.model_capabilities import (
    ANALYSIS_DEPTH_REQUIREMENTS,
    DEFAULT_MODEL_CAPABILITIES,
    CAPABILITY_DESCRIPTIONS,
    ModelRole,
    ModelFeature,
)
from app.core.unified_config_service import get_config_manager
import logging
import re

logger = logging.getLogger(__name__)


class ModelCapabilityService:
    """模型能力管理服务"""

    def _parse_aggregator_model_name(
        self, model_name: str
    ) -> Tuple[Optional[str], str]:
        """
        解析聚合渠道的模型名称

        Args:
            model_name: 模型名称，可能包含前缀（如 openai/gpt-4, anthropic/claude-3-sonnet）

        Returns:
            (原厂商, 原模型名) 元组
        """
        # 常见的聚合渠道模型名称格式：
        # - openai/gpt-4
        # - anthropic/claude-3-sonnet
        # - google/gemini-pro

        if "/" in model_name:
            parts = model_name.split("/", 1)
            if len(parts) == 2:
                provider_hint = parts[0].lower()
                original_model = parts[1]

                # 映射提供商提示到标准名称
                provider_map = {
                    "openai": "openai",
                    "anthropic": "anthropic",
                    "google": "google",
                    "deepseek": "deepseek",
                    "alibaba": "qwen",
                    "qwen": "qwen",
                    "zhipu": "zhipu",
                    "baidu": "baidu",
                    "moonshot": "moonshot",
                }

                provider = provider_map.get(provider_hint)
                return provider, original_model

        return None, model_name

    def _get_model_capability_with_mapping(
        self, model_name: str
    ) -> Tuple[int, Optional[str]]:
        """
        获取模型能力等级（支持聚合渠道映射）

        Returns:
            (能力等级, 映射的原模型名) 元组
        """
        # 从默认映射表读取（直接匹配字典中的配置）
        if model_name in DEFAULT_MODEL_CAPABILITIES:
            logger.info(f"✅ 从默认映射找到模型 {model_name} 的配置")
            default_config = DEFAULT_MODEL_CAPABILITIES[model_name]
            return default_config["capability_level"], None

        # 尝试解析聚合渠道模型名
        provider, original_model = self._parse_aggregator_model_name(model_name)
        if original_model and original_model != model_name:
            # 尝试用原模型名查找
            if original_model in DEFAULT_MODEL_CAPABILITIES:
                logger.info(f"🔄 聚合渠道模型映射: {model_name} -> {original_model}")
                return DEFAULT_MODEL_CAPABILITIES[original_model][
                    "capability_level"
                ], original_model

        # 返回默认值
        return 2, None

    def get_model_capability(self, model_name: str) -> int:
        """
        获取模型的能力等级（支持聚合渠道模型映射）

        Args:
            model_name: 模型名称（可能包含聚合渠道前缀，如 openai/gpt-4）

        Returns:
            能力等级 (1-5)
        """
        # 1. 优先从数据库配置读取
        try:
            llm_configs = get_config_manager().get_llm_configs()
            for config in llm_configs:
                if config.model_name == model_name:
                    return getattr(config, "capability_level", 2)
        except Exception as e:
            logger.warning(f"从配置读取模型能力失败: {e}")

        # 2. 从默认映射表读取（支持聚合渠道映射）
        capability, mapped_model = self._get_model_capability_with_mapping(model_name)
        if mapped_model:
            logger.info(f"✅ 使用映射模型 {mapped_model} 的能力等级: {capability}")

        return capability

    def get_model_config(self, model_name: str) -> Dict[str, Any]:
        """
        获取模型的完整配置信息（支持聚合渠道模型映射）

        Args:
            model_name: 模型名称（可能包含聚合渠道前缀，如 openai/gpt-4）

        Returns:
            模型配置字典
        """
        # 1. 优先从统一配置管理器读取
        try:
            config_manager = get_config_manager()
            db_config = config_manager._get_mongodb_config()

            if db_config and "llm_configs" in db_config:
                llm_configs = db_config["llm_configs"]
                logger.info(f"🔍 [MongoDB] llm_configs 数量: {len(llm_configs)}")

                for config_dict in llm_configs:
                    if config_dict.get("model_name") == model_name:
                        logger.info(f"🔍 [MongoDB] 找到模型配置: {model_name}")
                        # 🔧 将字符串列表转换为枚举列表
                        features_str = config_dict.get("features", [])
                        features_enum = []
                        for feature_str in features_str:
                            try:
                                # 将字符串转换为 ModelFeature 枚举
                                features_enum.append(ModelFeature(feature_str))
                            except ValueError:
                                logger.warning(f"⚠️ 未知的特性值: {feature_str}")

                        # 🔧 将字符串列表转换为枚举列表
                        roles_str = config_dict.get("suitable_roles", ["both"])
                        roles_enum = []
                        for role_str in roles_str:
                            try:
                                # 将字符串转换为 ModelRole 枚举
                                roles_enum.append(ModelRole(role_str))
                            except ValueError:
                                logger.warning(f"⚠️ 未知的角色值: {role_str}")

                        # 如果没有角色，默认为 both
                        if not roles_enum:
                            roles_enum = [ModelRole.BOTH]

                        # 🔧 将 enabled 属性转换为布尔值（兼容字典格式）
                        is_enabled = config_dict.get("enabled", True)
                        capability_level = config_dict.get("capability_level", 2)

                        logger.info(
                            f"📊 [MongoDB配置] {model_name}: features={features_enum}, roles={roles_enum}, enabled={is_enabled}"
                        )

                        return {
                            "model_name": config_dict.get("model_name"),
                            "capability_level": config_dict.get("capability_level", 2),
                            "suitable_roles": [str(r) for r in roles_enum],
                            "features": [
                                f.value for f in features_enum
                            ],  # 使用 .value 获取枚举值
                            "recommended_depths": config_dict.get(
                                "recommended_depths", ["快速", "基础", "标准"]
                            ),
                            "performance_metrics": config_dict.get(
                                "performance_metrics", None
                            ),
                            "enabled": is_enabled,  # 添加 enabled 属性
                        }

            logger.warning(f"未从 MongoDB 找到模型 {model_name} 的配置，尝试其他方法")
        except Exception as e:
            logger.warning(f"从 MongoDB 读取模型配置失败: {e}", exc_info=True)

            if doc and "llm_configs" in doc:
                llm_configs = doc["llm_configs"]
                logger.info(f"🔍 [MongoDB] llm_configs 数量: {len(llm_configs)}")

                for config_dict in llm_configs:
                    if config_dict.get("model_name") == model_name:
                        logger.info(f"🔍 [MongoDB] 找到模型配置: {model_name}")
                        # 🔧 将字符串列表转换为枚举列表
                        features_str = config_dict.get("features", [])
                        features_enum = []
                        for feature_str in features_str:
                            try:
                                # 将字符串转换为 ModelFeature 枚举
                                features_enum.append(ModelFeature(feature_str))
                            except ValueError:
                                logger.warning(f"⚠️ 未知的特性值: {feature_str}")

                        # 🔧 将字符串列表转换为枚举列表
                        roles_str = config_dict.get("suitable_roles", ["both"])
                        roles_enum = []
                        for role_str in roles_str:
                            try:
                                # 将字符串转换为 ModelRole 枚举
                                roles_enum.append(ModelRole(role_str))
                            except ValueError:
                                logger.warning(f"⚠️ 未知的角色值: {role_str}")

                        # 如果没有角色，默认为 both
                        if not roles_enum:
                            roles_enum = [ModelRole.BOTH]

                        logger.info(
                            f"📊 [MongoDB配置] {model_name}: features={features_enum}, roles={roles_enum}"
                        )

                        # 关闭连接
                        client.close()

                        return {
                            "model_name": config_dict.get("model_name"),
                            "capability_level": config_dict.get("capability_level", 2),
                            "suitable_roles": [
                                r.value for r in roles_enum
                            ],  # 使用 .value 获取字符串值
                            "features": [
                                f.value for f in features_enum
                            ],  # 使用 .value 获取字符串值
                            "recommended_depths": config_dict.get(
                                "recommended_depths", ["快速", "基础", "标准"]
                            ),
                            "performance_metrics": config_dict.get(
                                "performance_metrics", None
                            ),
                        }

            # 关闭连接
            client.close()

        # 2. 从默认映射表读取（直接匹配）
        if model_name in DEFAULT_MODEL_CAPABILITIES:
            return DEFAULT_MODEL_CAPABILITIES[model_name]

        # 3. 尝试聚合渠道模型映射
        provider, original_model = self._parse_aggregator_model_name(model_name)
        if original_model and original_model != model_name:
            if original_model in DEFAULT_MODEL_CAPABILITIES:
                logger.info(f"🔄 聚合渠道模型映射: {model_name} -> {original_model}")
                config = DEFAULT_MODEL_CAPABILITIES[original_model].copy()
                config["model_name"] = model_name  # 保持原始模型名
                config["_mapped_from"] = original_model  # 记录映射来源
                return config

        # 4. 返回默认配置
        logger.warning(f"未找到模型 {model_name} 的配置，使用默认配置")
        return {
            "model_name": model_name,
            "capability_level": 2,
            "suitable_roles": [ModelRole.BOTH.value],  # 使用 .value 获取字符串值
            "features": [ModelFeature.TOOL_CALLING.value],  # 使用 .value 获取字符串值
            "recommended_depths": ["快速", "基础", "标准"],
            "performance_metrics": {"speed": 3, "cost": 3, "quality": 3},
        }

    def validate_model_pair(
        self, quick_model: str, deep_model: str, research_depth: str
    ) -> Dict[str, Any]:
        """
        验证模型对是否适合当前分析深度

        Args:
            quick_model: 快速分析模型名称
            deep_model: 深度分析模型名称
            research_depth: 研究深度（快速/基础/标准/深度/全面）

        Returns:
            验证结果字典，包含 valid, warnings, recommendations
        """
        logger.info(
            f"🔍 开始验证模型对: quick={quick_model}, deep={deep_model}, depth={research_depth}"
        )

        requirements = ANALYSIS_DEPTH_REQUIREMENTS.get(
            research_depth, ANALYSIS_DEPTH_REQUIREMENTS["标准"]
        )
        logger.info(f"🔍 分析深度要求: {requirements}")

        quick_config = self.get_model_config(quick_model)
        deep_config = self.get_model_config(deep_model)

        logger.info(f"🔍 快速模型配置: {quick_config}")
        logger.info(f"🔍 深度模型配置: {deep_config}")

        result = {"valid": True, "warnings": [], "recommendations": []}

        # 检查快速模型
        quick_level = quick_config["capability_level"]
        logger.info(
            f"🔍 检查快速模型能力等级: {quick_level} >= {requirements['quick_model_min']}?"
        )
        if quick_level < requirements["quick_model_min"]:
            warning = f"⚠️ 快速模型 {quick_model} (能力等级{quick_level}) 低于 {research_depth} 分析的建议等级({requirements['quick_model_min']})"
            result["warnings"].append(warning)
            logger.warning(warning)

        # 检查快速模型角色适配
        quick_roles = quick_config.get("suitable_roles", [])
        logger.info(f"🔍 检查快速模型角色: {quick_roles}")

        # 兼容字符串和枚举格式的角色检查
        def has_role(roles, required_role):
            """检查是否包含所需角色（兼容字符串和枚举）"""
            for role in roles:
                if isinstance(role, str):
                    # 字符串格式比较
                    if role == required_role.value or role == str(required_role):
                        return True
                else:
                    # 枚举格式比较
                    if role == required_role:
                        return True
            return False

        if not has_role(quick_roles, ModelRole.QUICK_ANALYSIS) and not has_role(
            quick_roles, ModelRole.BOTH
        ):
            warning = (
                f"💡 模型 {quick_model} 不是为快速分析优化的，可能影响数据收集效率"
            )
            result["warnings"].append(warning)
            logger.warning(warning)

        # 检查快速模型是否支持工具调用
        quick_features = quick_config.get("features", [])
        logger.info(f"🔍 检查快速模型特性: {quick_features}")

        # 兼容字符串和枚举格式的特性检查
        def has_feature(features, required_feature):
            """检查是否包含所需特性（兼容字符串和枚举）"""
            required_value = required_feature.value
            required_str = str(required_feature)
            for feature in features:
                if isinstance(feature, str):
                    # 字符串格式比较：'TOOL_CALLING' 或 'ModelFeature.TOOL_CALLING'
                    if feature == required_value or feature == required_str:
                        return True
                else:
                    # 枚举格式比较
                    if feature == required_feature:
                        return True
            return False

        if not has_feature(quick_features, ModelFeature.TOOL_CALLING):
            result["valid"] = False
            warning = f"❌ 快速模型 {quick_model} 不支持工具调用，无法完成数据收集任务"
            result["warnings"].append(warning)
            logger.error(warning)

        # 检查深度模型
        deep_level = deep_config["capability_level"]
        logger.info(
            f"🔍 检查深度模型能力等级: {deep_level} >= {requirements['deep_model_min']}?"
        )
        if deep_level < requirements["deep_model_min"]:
            result["valid"] = False
            warning = f"❌ 深度模型 {deep_model} (能力等级{deep_level}) 不满足 {research_depth} 分析的最低要求(等级{requirements['deep_model_min']})"
            result["warnings"].append(warning)
            logger.error(warning)
            result["recommendations"].append(
                self._recommend_model("deep", requirements["deep_model_min"])
            )

        # 检查深度模型角色适配
        deep_roles = deep_config.get("suitable_roles", [])
        logger.info(f"🔍 检查深度模型角色: {deep_roles}")
        if not has_role(deep_roles, ModelRole.DEEP_ANALYSIS) and not has_role(
            deep_roles, ModelRole.BOTH
        ):
            warning = f"💡 模型 {deep_model} 不是为深度推理优化的，可能影响分析质量"
            result["warnings"].append(warning)
            logger.warning(warning)

        # 检查必需特性
        logger.info(f"🔍 检查必需特性: {requirements['required_features']}")
        for feature in requirements["required_features"]:
            if feature == ModelFeature.REASONING:
                deep_features = deep_config.get("features", [])
                logger.info(f"🔍 检查深度模型推理能力: {deep_features}")
                if not has_feature(deep_features, feature):
                    warning = (
                        f"💡 {research_depth} 分析建议使用具有强推理能力的深度模型"
                    )
                    result["warnings"].append(warning)
                    logger.warning(warning)

        logger.info(
            f"🔍 验证结果: valid={result['valid']}, warnings={len(result['warnings'])}条"
        )
        logger.info(f"🔍 警告详情: {result['warnings']}")

        return result

    def recommend_models_for_depth(self, research_depth: str) -> Tuple[str, str]:
        """
        根据分析深度推荐合适的模型对

        Args:
            research_depth: 研究深度（快速/基础/标准/深度/全面）

        Returns:
            (quick_model, deep_model) 元组
        """
        requirements = ANALYSIS_DEPTH_REQUIREMENTS.get(
            research_depth, ANALYSIS_DEPTH_REQUIREMENTS["标准"]
        )

        # 获取所有启用的模型
        try:
            llm_configs = get_config_manager().get_llm_configs()
            # 兼容字典格式和对象格式
            enabled_models = []
            for c in llm_configs:
                if isinstance(c, dict):
                    is_enabled = c.get("enabled", True)
                    model_name = c.get("model_name", "unknown")
                else:
                    is_enabled = getattr(c, "enabled", True)
                    model_name = getattr(c, "model_name", "unknown")

                if is_enabled:
                    enabled_models.append(c)
                    logger.debug(f"✅ 模型已启用: {model_name}")
                else:
                    logger.debug(f"⏸️ 模型已禁用: {model_name}")

        except Exception as e:
            logger.error(f"获取模型配置失败: {e}")
            # 使用默认模型
            return self._get_default_models()

        if not enabled_models:
            logger.warning("没有启用的模型，使用默认配置")
            return self._get_default_models()

        # 筛选适合快速分析的模型
        quick_candidates = []
        for m in enabled_models:
            # 兼容字典格式和对象格式
            if isinstance(m, dict):
                roles = m.get("suitable_roles", ["both"])
                level = m.get("capability_level", 2)
                features = m.get("features", [])
            else:
                roles = getattr(m, "suitable_roles", ["both"])
                level = getattr(m, "capability_level", 2)
                features = getattr(m, "features", [])

            # 将字符串角色转换为枚举
            roles_enum = []
            for role_str in roles:
                try:
                    roles_enum.append(ModelRole(role_str))
                except ValueError:
                    roles_enum.append(ModelRole.BOTH)

            # 将字符串特性转换为枚举
            features_enum = []
            for feature_str in features:
                try:
                    features_enum.append(ModelFeature(feature_str))
                except ValueError:
                    pass

            if (
                (ModelRole.QUICK_ANALYSIS in roles_enum or ModelRole.BOTH in roles_enum)
                and level >= requirements["quick_model_min"]
                and ModelFeature.TOOL_CALLING in features_enum
            ):
                quick_candidates.append(m)

        # 筛选适合深度分析的模型
        deep_candidates = []
        for m in enabled_models:
            # 兼容字典格式和对象格式
            if isinstance(m, dict):
                roles = m.get("suitable_roles", ["both"])
                level = m.get("capability_level", 2)
            else:
                roles = getattr(m, "suitable_roles", ["both"])
                level = getattr(m, "capability_level", 2)

            # 将字符串角色转换为枚举
            roles_enum = []
            for role_str in roles:
                try:
                    roles_enum.append(ModelRole(role_str))
                except ValueError:
                    roles_enum.append(ModelRole.BOTH)

            if (
                ModelRole.DEEP_ANALYSIS in roles_enum or ModelRole.BOTH in roles_enum
            ) and level >= requirements["deep_model_min"]:
                deep_candidates.append(m)

        # 按性价比排序（能力等级 vs 成本）
        def get_sort_key(x):
            if isinstance(x, dict):
                level = x.get("capability_level", 2)
                perf = x.get("performance_metrics") or {}
                cost = perf.get("cost", 3)
                quality = perf.get("quality", 3)
            else:
                level = getattr(x, "capability_level", 2)
                perf = getattr(x, "performance_metrics") or {}
                cost = perf.get("cost", 3)
                quality = perf.get("quality", 3)
            return level, cost, quality

        quick_candidates.sort(key=get_sort_key, reverse=True)
        deep_candidates.sort(key=get_sort_key, reverse=True)

        # 选择最佳模型（兼容字典和对象格式）
        if quick_candidates:
            if isinstance(quick_candidates[0], dict):
                quick_model = quick_candidates[0].get("model_name")
            else:
                quick_model = getattr(quick_candidates[0], "model_name", None)
        else:
            quick_model = None

        if deep_candidates:
            if isinstance(deep_candidates[0], dict):
                deep_model = deep_candidates[0].get("model_name")
            else:
                deep_model = getattr(deep_candidates[0], "model_name", None)
        else:
            deep_model = None

        # 如果没找到合适的，使用系统默认
        if not quick_model or not deep_model:
            return self._get_default_models()

        logger.info(
            f"🤖 为 {research_depth} 分析推荐模型: "
            f"quick={quick_model} (角色:快速分析), "
            f"deep={deep_model} (角色:深度推理)"
        )

        return quick_model, deep_model

    def _get_default_models(self) -> Tuple[str, str]:
        """获取默认模型对"""
        try:
            quick_model = get_config_manager().get_quick_analysis_model()
            deep_model = get_config_manager().get_deep_analysis_model()

            # 🔧 修复：如果返回的是整个配置对象，尝试提取 model_name
            if isinstance(quick_model, dict):
                logger.warning(
                    f"⚠️ quick_model 是配置对象，尝试提取 model_name: {quick_model.get('model_name', 'qwen-turbo')}"
                )
                quick_model = quick_model.get("model_name", "qwen-turbo")

            if isinstance(deep_model, dict):
                logger.warning(
                    f"⚠️ deep_model 是配置对象，尝试提取 model_name: {deep_model.get('model_name', 'qwen-plus')}"
                )
                deep_model = deep_model.get("model_name", "qwen-plus")

            # 确保返回的是字符串
            if not isinstance(quick_model, str):
                logger.warning(
                    f"⚠️ quick_model 类型错误: {type(quick_model)}，使用默认值"
                )
                quick_model = "qwen-turbo"

            if not isinstance(deep_model, str):
                logger.warning(f"⚠️ deep_model 类型错误: {type(deep_model)}，使用默认值")
                deep_model = "qwen-plus"

            logger.info(f"✅ 使用系统默认模型: quick={quick_model}, deep={deep_model}")
            return quick_model, deep_model
        except Exception as e:
            logger.error(f"❌ 获取默认模型失败: {e}")
            return "qwen-turbo", "qwen-plus"

    def _recommend_model(self, model_type: str, min_level: int) -> str:
        """推荐满足要求的模型"""
        try:
            llm_configs = get_config_manager().get_llm_configs()
            for config in llm_configs:
                if (
                    config.enabled
                    and getattr(config, "capability_level", 2) >= min_level
                ):
                    display_name = config.model_display_name or config.model_name
                    return f"建议使用: {display_name}"
        except Exception as e:
            logger.warning(f"推荐模型失败: {e}")

        return "建议升级模型配置"


# 单例
_model_capability_service = None


def get_model_capability_service() -> ModelCapabilityService:
    """获取模型能力服务单例"""
    global _model_capability_service
    if _model_capability_service is None:
        _model_capability_service = ModelCapabilityService()
    return _model_capability_service
