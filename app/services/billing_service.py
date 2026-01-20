# -*- coding: utf-8 -*-
"""
Billing Service
封装Token计费和成本计算相关的业务逻辑
"""

import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from app.models.config import LLMConfig
from app.models.usage_record import UsageRecord
from app.services.usage_statistics_service import UsageStatisticsService
from app.core.unified_config_service import get_config_manager

logger = logging.getLogger(__name__)


class BillingService:
    """
    计费服务

    负责:
    - 计算Token使用成本
    - 记录Token使用
    - 获取模型价格信息
    """

    def __init__(self):
        """初始化计费服务"""
        self.usage_service = UsageStatisticsService()
        self.config_manager = get_config_manager()

    def calculate_cost(
        self, provider: str, model_name: str, input_tokens: int, output_tokens: int
    ) -> Tuple[float, str]:
        """
        计算Token使用成本

        Args:
            provider: LLM提供商
            model_name: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数

        Returns:
            (成本, 货币单位) 元组
        """
        try:
            # 获取模型配置
            model_config = self.config_manager.get_model_config(model_name)

            # 默认价格
            input_price = 0.0
            output_price = 0.0
            currency = "CNY"

            # 从配置中获取价格
            if model_config:
                # 尝试从model_config中获取价格
                if "input_price_per_1k" in model_config:
                    input_price = model_config["input_price_per_1k"]
                if "output_price_per_1k" in model_config:
                    output_price = model_config["output_price_per_1k"]
                if "currency" in model_config:
                    currency = model_config["currency"]

            # 计算成本
            cost = (input_tokens / 1000 * input_price) + (
                output_tokens / 1000 * output_price
            )

            logger.debug(
                f"💰 计算成本: {provider}/{model_name} - "
                f"输入: {input_tokens} tokens (¥{input_price}/1k), "
                f"输出: {output_tokens} tokens (¥{output_price}/1k), "
                f"总计: {currency}{cost:.4f}"
            )

            return cost, currency

        except Exception as e:
            logger.error(f"❌ 计算成本失败: {e}")
            return 0.0, "CNY"

    def record_usage(
        self,
        provider: str,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        session_id: str,
        analysis_type: str = "stock_analysis",
        stock_code: Optional[str] = None,
    ) -> bool:
        """
        记录Token使用

        Args:
            provider: LLM提供商
            model_name: 模型名称
            input_tokens: 输入token数
            output_tokens: 输出token数
            session_id: 会话ID
            analysis_type: 分析类型
            stock_code: 股票代码(可选)

        Returns:
            是否记录成功
        """
        try:
            # 计算成本
            cost, currency = self.calculate_cost(
                provider, model_name, input_tokens, output_tokens
            )

            # 创建使用记录
            usage_record = UsageRecord(
                timestamp=datetime.now().isoformat(),
                provider=provider,
                model_name=model_name,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost=cost,
                currency=currency,
                session_id=session_id,
                analysis_type=analysis_type,
                stock_code=stock_code,
            )

            # 保存到数据库
            success = self.usage_service.add_usage_record(usage_record)

            if success:
                logger.info(
                    f"💰 记录使用成本: {provider}/{model_name} - "
                    f"输入: {input_tokens}, 输出: {output_tokens}, "
                    f"成本: {currency}{cost:.4f}"
                )
            else:
                logger.warning("⚠️ 记录使用成本失败")

            return success

        except Exception as e:
            logger.error(f"❌ 记录token使用失败: {e}")
            return False

    def get_model_pricing(self, provider: str, model_name: str) -> Dict[str, Any]:
        """
        获取模型价格信息

        Args:
            provider: LLM提供商
            model_name: 模型名称

        Returns:
            价格信息字典
        """
        try:
            model_config = self.config_manager.get_model_config(model_name)

            pricing = {
                "provider": provider,
                "model_name": model_name,
                "input_price_per_1k": 0.0,
                "output_price_per_1k": 0.0,
                "currency": "CNY",
            }

            if model_config:
                if "input_price_per_1k" in model_config:
                    pricing["input_price_per_1k"] = model_config["input_price_per_1k"]
                if "output_price_per_1k" in model_config:
                    pricing["output_price_per_1k"] = model_config["output_price_per_1k"]
                if "currency" in model_config:
                    pricing["currency"] = model_config["currency"]

            return pricing

        except Exception as e:
            logger.error(f"❌ 获取模型价格信息失败: {e}")
            return {
                "provider": provider,
                "model_name": model_name,
                "input_price_per_1k": 0.0,
                "output_price_per_1k": 0.0,
                "currency": "CNY",
                "error": str(e),
            }

    def estimate_analysis_cost(
        self,
        provider: str,
        model_name: str,
        estimated_input_tokens: int = 5000,
        estimated_output_tokens: int = 2000,
    ) -> Dict[str, Any]:
        """
        估算分析成本

        Args:
            provider: LLM提供商
            model_name: 模型名称
            estimated_input_tokens: 预估输入token数
            estimated_output_tokens: 预估输出token数

        Returns:
            估算信息字典
        """
        try:
            model_config = self.config_manager.get_model_config(model_name)

            # 默认价格
            input_price = 0.0
            output_price = 0.0
            currency = "CNY"

            if model_config:
                if "input_price_per_1k" in model_config:
                    input_price = model_config["input_price_per_1k"]
                if "output_price_per_1k" in model_config:
                    output_price = model_config["output_price_per_1k"]
                if "currency" in model_config:
                    currency = model_config["currency"]

            # 计算估算成本
            estimated_cost = (
                estimated_input_tokens / 1000 * input_price
                + estimated_output_tokens / 1000 * output_price
            )

            return {
                "provider": provider,
                "model_name": model_name,
                "estimated_input_tokens": estimated_input_tokens,
                "estimated_output_tokens": estimated_output_tokens,
                "input_price_per_1k": input_price,
                "output_price_per_1k": output_price,
                "currency": currency,
                "estimated_cost": estimated_cost,
            }

        except Exception as e:
            logger.error(f"❌ 估算分析成本失败: {e}")
            return {"error": str(e), "provider": provider, "model_name": model_name}


# 全局计费服务实例(延迟初始化)
_billing_service: Optional[BillingService] = None


def get_billing_service() -> BillingService:
    """获取全局计费服务实例"""
    global _billing_service
    if _billing_service is None:
        _billing_service = BillingService()
    return _billing_service
