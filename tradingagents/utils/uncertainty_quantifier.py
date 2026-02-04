# -*- coding: utf-8 -*-
"""
不确定性量化器

为投资建议添加置信度和概率区间
"""

from typing import Dict, Optional
import re


class UncertaintyQuantifier:
    """不确定性量化器"""

    @staticmethod
    def extract_confidence_from_report(report: str) -> float:
        """
        从报告中提取置信度

        Args:
            report: 分析报告文本

        Returns:
            float: 置信度 (0-1)，未找到则返回默认值
        """
        # 查找百分比值
        patterns = [
            r'置信度[：:]\s*(\d+)%',
            r'确定性[：:]\s*(\d+)%',
            r'把握[：:]\s*(\d+)%',
        ]

        for pattern in patterns:
            match = re.search(pattern, report)
            if match:
                return int(match.group(1)) / 100.0

        # 如果没有明确说明，根据报告内容推断
        if "强烈" in report or "确定" in report:
            return 0.75
        elif "谨慎" in report or "可能" in report:
            return 0.55
        elif "观望" in report or "待定" in report:
            return 0.5

        return 0.6  # 默认中等置信度

    @staticmethod
    def calculate_probability_range(
        current_price: float,
        target_price: float,
        confidence: float
    ) -> Dict[str, float]:
        """
        计算目标价的概率区间

        Args:
            current_price: 当前价格
            target_price: 目标价格
            confidence: 置信度 (0-1)

        Returns:
            Dict: 包含 optimistic, base, pessimistic 价格
        """
        # 价格变动幅度
        change_pct = (target_price - current_price) / current_price

        # 根据置信度调整波动范围
        # 置信度越低，波动越大
        volatility_factor = 1.0 / (confidence + 0.1)

        base_price = target_price
        optimistic_price = current_price * (1 + change_pct * 1.2)
        pessimistic_price = current_price * (1 + change_pct * 0.6)

        return {
            "optimistic": round(optimistic_price, 2),
            "base": round(base_price, 2),
            "pessimistic": round(pessimistic_price, 2),
        }

    @staticmethod
    def format_uncertainty_section(
        current_price: float,
        target_price: float,
        confidence: float
    ) -> str:
        """
        格式化不确定性说明部分

        Args:
            current_price: 当前价格
            target_price: 目标价格
            confidence: 置信度

        Returns:
            str: 格式化的不确定性说明
        """
        ranges = UncertaintyQuantifier.calculate_probability_range(
            current_price, target_price, confidence
        )

        # 计算各情景概率
        optimistic_prob = min(confidence * 0.3, 0.25)
        pessimistic_prob = min((1 - confidence) * 0.5, 0.35)
        base_prob = max(1 - optimistic_prob - pessimistic_prob, 0.4)

        section = "### 📊 概率评估\n\n"
        section += "| 情景 | 目标价 | 概率 |\n"
        section += "|------|--------|------|\n"
        section += f"| 乐观情景 | ¥{ranges['optimistic']:.2f} | {optimistic_prob:.0%} |\n"
        section += f"| 基准情景 | ¥{ranges['base']:.2f} | {base_prob:.0%} |\n"
        section += f"| 谨慎情景 | ¥{ranges['pessimistic']:.2f} | {pessimistic_prob:.0%} |\n"

        section += f"\n**综合置信度**: {confidence:.0%}\n"
        section += f"**当前价格**: ¥{current_price:.2f}\n"

        return section

    @staticmethod
    def format_recommendation_with_risk(
        recommendation: str,
        current_price: float,
        target_price: Optional[float],
        confidence: float,
        stop_loss: Optional[float] = None
    ) -> str:
        """
        格式化带风险提示的投资建议

        Args:
            recommendation: 投资建议（买入/持有/卖出）
            current_price: 当前价格
            target_price: 目标价格
            confidence: 置信度
            stop_loss: 止损价

        Returns:
            str: 格式化的建议
        """
        section = f"## 投资建议\n\n"
        section += f"| 维度 | 内容 |\n"
        section += f"|------|------|\n"
        section += f"| **建议等级** | {recommendation} |\n"
        section += f"| **当前价格** | ¥{current_price:.2f} |\n"

        if target_price:
            change_pct = (target_price - current_price) / current_price * 100
            section += f"| **目标价格** | ¥{target_price:.2f} ({change_pct:+.1f}%) |\n"

        section += f"| **置信度** | {confidence:.0%} |\n"

        if stop_loss:
            stop_loss_pct = (stop_loss - current_price) / current_price * 100
            section += f"| **止损价位** | ¥{stop_loss:.2f} ({stop_loss_pct:+.1f}%) |\n"

        # 添加不确定性说明
        if target_price and confidence:
            section += "\n"
            section += UncertaintyQuantifier.format_uncertainty_section(
                current_price, target_price, confidence
            )

        return section
