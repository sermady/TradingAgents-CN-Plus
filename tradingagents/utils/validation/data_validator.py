# -*- coding: utf-8 -*-
"""
数据验证器 - 确保数据质量和一致性
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging

logger = logging.getLogger("data_validation")


class DataValidator:
    """数据验证器 - 提供数据质量检查和告警功能"""
    
    # 验证阈值配置
    VALIDATION_RULES = {
        # 价格验证
        "price_change_threshold": 0.20,  # 单日涨跌幅超20%告警
        "price_min": 0.01,  # 最小有效价格
        
        # 成交量验证
        "volume_reasonability_threshold": 0.01,  # 成交量异常阈值（与市值比）
        
        # 估值指标验证
        "pe_valid_range": (1, 200),  # PE合理范围
        "pb_valid_range": (0.1, 20),  # PB合理范围
        "ps_valid_range": (0.1, 20),  # PS合理范围
        
        # RSI验证
        "rsi_valid_range": (0, 100),  # RSI必须在0-100之间
        "rsi_overbought": 80,  # RSI超买阈值
        "rsi_oversold": 20,  # RSI超卖阈值
        "rsi_extreme_consecutive_days": 3,  # RSI连续极端值告警天数
    }
    
    def __init__(self):
        """初始化数据验证器"""
        self.validation_history: List[Dict] = []
        self.alert_counters: Dict[str, int] = {}
        
    def validate_price(self, price: float, prev_close: Optional[float] = None) -> Tuple[bool, List[str]]:
        """
        验证价格数据
        
        Args:
            price: 当前价格
            prev_close: 昨收价
            
        Returns:
            (是否有效, 问题列表)
        """
        issues = []
        
        if price is None:
            issues.append("价格数据为空")
            return False, issues
            
        if price <= 0:
            issues.append(f"价格无效: {price} (必须>0)")
            return False, issues
            
        if price < self.VALIDATION_RULES["price_min"]:
            issues.append(f"价格过低: {price}")
            
        if prev_close and prev_close > 0:
            change = (price - prev_close) / prev_close
            if abs(change) > self.VALIDATION_RULES["price_change_threshold"]:
                issues.append(f"价格波动异常: {change*100:.1f}% (阈值{self.VALIDATION_RULES['price_change_threshold']*100}%)")
                
        return len(issues) == 0, issues
    
    def validate_volume(self, volume: int, market_cap: Optional[float] = None) -> Tuple[bool, List[str]]:
        """
        验证成交量数据
        
        Args:
            volume: 成交量（股）
            market_cap: 市值
            
        Returns:
            (是否有效, 问题列表)
        """
        issues = []
        
        if volume is None:
            issues.append("成交量数据为空")
            return False, issues
            
        if volume <= 0:
            issues.append(f"成交量无效: {volume} (必须>0)")
            return False, issues
            
        # 检查成交量是否过大（与市值比较）
        if market_cap and market_cap > 0:
            # 合理日成交量通常小于市值的5%
            volume_ratio = volume / market_cap
            if volume_ratio > 0.5:
                issues.append(f"成交量异常偏高: {volume_ratio*100:.1f}% 市值")
                
        return len(issues) == 0, issues
    
    def validate_pe(self, pe: Optional[float]) -> Tuple[bool, List[str]]:
        """
        验证市盈率
        
        Args:
            pe: 市盈率
            
        Returns:
            (是否有效, 问题列表)
        """
        issues = []
        
        if pe is None:
            return True, []  # PE可能为空，不算错误
            
        min_pe, max_pe = self.VALIDATION_RULES["pe_valid_range"]
        if pe < min_pe:
            issues.append(f"PE过低: {pe:.2f} (<{min_pe})")
        elif pe > max_pe:
            issues.append(f"PE过高: {pe:.2f} (>{max_pe})")
            
        return len(issues) == 0, issues
    
    def validate_ps(self, ps: Optional[float], market_cap: float, revenue: float) -> Tuple[bool, List[str]]:
        """
        验证市销率 - 包含交叉验证
        
        Args:
            ps: 市销率
            market_cap: 市值
            revenue: 营收
            
        Returns:
            (是否有效, 问题列表)
        """
        issues = []
        
        # 交叉验证：PS = 市值 / 营收
        if ps and market_cap and revenue:
            calculated_ps = market_cap / revenue
            if abs(ps - calculated_ps) / calculated_ps > 0.1:  # 10%偏差
                issues.append(f"PS交叉验证失败: 报告值={ps:.2f}, 计算值={calculated_ps:.2f}")
        
        min_ps, max_ps = self.VALIDATION_RULES["ps_valid_range"]
        if ps is not None:
            if ps < min_ps:
                issues.append(f"PS过低: {ps:.2f} (<{min_ps})，可能营收数据错误")
            elif ps > max_ps:
                issues.append(f"PS过高: {ps:.2f} (>{max_ps})")
                
        return len(issues) == 0, issues
    
    def validate_rsi_extreme(self, rsi_values: List[float], period: int = 6) -> Tuple[bool, List[str], Dict[str, Any]]:
        """
        验证RSI极端值 - 核心告警功能
        
        Args:
            rsi_values: RSI历史值列表（从新到旧）
            period: RSI周期（6=RSI6）
            
        Returns:
            (是否正常, 问题列表, 详细分析)
        """
        issues = []
        analysis = {
            "current_rsi": None,
            "consecutive_overbought_days": 0,
            "consecutive_oversold_days": 0,
            "max_rsi": max(rsi_values) if rsi_values else None,
            "min_rsi": min(rsi_values) if rsi_values else None,
            "is_extreme": False,
            "alert_level": "none"  # none, warning, critical
        }
        
        if not rsi_values:
            return True, [], analysis
            
        current_rsi = rsi_values[0]
        analysis["current_rsi"] = current_rsi
        
        # 验证RSI在有效范围内
        min_rsi, max_rsi = self.VALIDATION_RULES["rsi_valid_range"]
        if not (min_rsi <= current_rsi <= max_rsi):
            issues.append(f"RSI值异常: {current_rsi} (应在{min_rsi}-{max_rsi}之间)")
            return False, issues, analysis
        
        # 统计连续极端天数
        threshold = self.VALIDATION_RULES["rsi_overbought"]
        oversold_threshold = self.VALIDATION_RULES["rsi_oversold"]
        
        for rsi in rsi_values:
            if rsi >= threshold:
                analysis["consecutive_overbought_days"] += 1
            elif rsi <= oversold_threshold:
                analysis["consecutive_oversold_days"] += 1
            else:
                break  # 只统计连续的
        
        extreme_days = self.VALIDATION_RULES["rsi_extreme_consecutive_days"]
        
        # 生成告警
        if analysis["consecutive_overbought_days"] >= extreme_days:
            issues.append(
                f"⚠️ RSI{period} 连续超买: {analysis['consecutive_overbought_days']}天 "
                f"(当前值: {current_rsi:.2f})"
            )
            analysis["is_extreme"] = True
            analysis["alert_level"] = "critical"
        elif analysis["consecutive_oversold_days"] >= extreme_days:
            issues.append(
                f"⚠️ RSI{period} 连续超卖: {analysis['consecutive_oversold_days']}天 "
                f"(当前值: {current_rsi:.2f})"
            )
            analysis["is_extreme"] = True
            analysis["alert_level"] = "critical"
        elif current_rsi >= threshold:
            issues.append(f"RSI{period} 超买: {current_rsi:.2f} (阈值:{threshold})")
            analysis["alert_level"] = "warning"
            
        return len(issues) == 0, issues, analysis
    
    def validate_data_consistency(self, data_sources: Dict[str, Dict]) -> Tuple[bool, List[str]]:
        """
        验证多数据源数据一致性
        
        Args:
            data_sources: {数据源名称: 数据字典}
            
        Returns:
            (是否一致, 问题列表)
        """
        issues = []
        
        if len(data_sources) < 2:
            return True, []  # 单数据源无需比较
            
        # 需要一致验证的字段
        key_fields = ["close", "volume", "pe", "market_cap"]
        
        for field in key_fields:
            values = []
            for source, data in data_sources.items():
                if field in data and data[field] is not None:
                    values.append((source, data[field]))
            
            if len(values) >= 2:
                # 计算差异
                numeric_values = [v for _, v in values]
                avg = sum(numeric_values) / len(numeric_values)
                if avg > 0:
                    max_val = max(numeric_values)
                    min_val = min(numeric_values)
    


# 单例访问
_validator_instance = None

def get_data_validator() -> DataValidator:
    """获取数据验证器单例"""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = DataValidator()
    return _validator_instance


def validate_market_data(market_data: Dict, financial_data: Optional[Dict] = None) -> Dict:
    """
    便捷函数：验证市场数据
    
    Args:
        market_data: 市场数据
        financial_data: 财务数据（可选）
        
    Returns:
        验证报告
    """
    validator = get_data_validator()
    return validator.full_validation_report(
        market_data,
        financial_data or {}
    )
