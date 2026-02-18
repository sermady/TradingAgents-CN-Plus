# -*- coding: utf-8 -*-
"""分析配置构建模块

负责构建分析所需的配置，包括模型选择、提供商配置等
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.services.analysis.execution.constants import DEFAULT_ANALYSTS, DEFAULT_RESEARCH_DEPTH

logger = logging.getLogger(__name__)


class ConfigBuilderMixin:
    """配置构建混入类"""

    def _build_analysis_config(self, request) -> Dict[str, Any]:
        """构建分析配置

        Args:
            request: 分析请求对象

        Returns:
            分析配置字典
        """
        from app.services.analysis.model_provider_service import (
            create_analysis_config,
            ModelProviderService,
        )
        from app.services.model_capability_service import get_model_capability_service

        capability_service = get_model_capability_service()
        research_depth = (
            request.parameters.research_depth
            if request.parameters
            else DEFAULT_RESEARCH_DEPTH
        )

        # 获取模型
        quick_model, deep_model = self._select_models(request, capability_service, research_depth)

        # 获取提供商信息
        quick_provider_info = (
            ModelProviderService.get_provider_and_url(quick_model) or {}
        )
        deep_provider_info = ModelProviderService.get_provider_and_url(deep_model) or {}

        # 创建配置
        config = create_analysis_config(
            research_depth=research_depth,
            selected_analysts=request.parameters.selected_analysts
            if request.parameters
            else DEFAULT_ANALYSTS,
            quick_model=quick_model,
            deep_model=deep_model,
            llm_provider=quick_provider_info.get("provider", "openai"),
            market_type=request.parameters.market_type if request.parameters else "A股",
        )

        # 添加混合模式配置
        config["quick_provider"] = quick_provider_info.get("provider", "openai")
        config["deep_provider"] = deep_provider_info.get("provider", "openai")
        config["quick_backend_url"] = quick_provider_info.get("backend_url", "")
        config["deep_backend_url"] = deep_provider_info.get("backend_url", "")

        return config

    def _select_models(
        self, request, capability_service, research_depth: str
    ) -> tuple[str, str]:
        """选择分析模型

        Args:
            request: 分析请求对象
            capability_service: 模型能力服务
            research_depth: 研究深度

        Returns:
            (quick_model, deep_model) 元组
        """
        if (
            request.parameters
            and hasattr(request.parameters, "quick_analysis_model")
            and hasattr(request.parameters, "deep_analysis_model")
            and request.parameters.quick_analysis_model
            and request.parameters.deep_analysis_model
        ):
            quick_model = request.parameters.quick_analysis_model
            deep_model = request.parameters.deep_analysis_model
            logger.info(
                f"📝 [分析服务] 用户指定模型: quick={quick_model}, deep={deep_model}"
            )

            # 验证模型
            validation = capability_service.validate_model_pair(
                quick_model, deep_model, research_depth
            )
            if not validation["valid"]:
                for warning in validation["warnings"]:
                    logger.warning(warning)
                quick_model, deep_model = capability_service.recommend_models_for_depth(
                    research_depth
                )
                logger.info(f"✅ 已切换: quick={quick_model}, deep={deep_model}")
        else:
            quick_model, deep_model = capability_service.recommend_models_for_depth(
                research_depth
            )
            logger.info(f"🤖 自动推荐模型: quick={quick_model}, deep={deep_model}")

        return quick_model, deep_model

    def _get_analysis_date(self, request) -> str:
        """获取分析日期

        Args:
            request: 分析请求对象

        Returns:
            格式化后的日期字符串 (YYYY-MM-DD)
        """
        if (
            request.parameters
            and hasattr(request.parameters, "analysis_date")
            and request.parameters.analysis_date
        ):
            if isinstance(request.parameters.analysis_date, datetime):
                return request.parameters.analysis_date.strftime("%Y-%m-%d")
            elif isinstance(request.parameters.analysis_date, str):
                return request.parameters.analysis_date
        return datetime.now().strftime("%Y-%m-%d")

    def _format_analysis_date(self, analysis_date) -> str:
        """格式化分析日期

        Args:
            analysis_date: 日期对象或字符串

        Returns:
            格式化后的日期字符串 (YYYY-MM-DD)
        """
        if not analysis_date:
            return datetime.now().strftime("%Y-%m-%d")

        if isinstance(analysis_date, datetime):
            return analysis_date.strftime("%Y-%m-%d")
        elif isinstance(analysis_date, str):
            try:
                parsed_date = datetime.strptime(analysis_date, "%Y-%m-%d")
                return parsed_date.strftime("%Y-%m-%d")
            except ValueError:
                return datetime.now().strftime("%Y-%m-%d")
        return datetime.now().strftime("%Y-%m-%d")
