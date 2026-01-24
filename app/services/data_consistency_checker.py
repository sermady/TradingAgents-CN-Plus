# -*- coding: utf-8 -*-
"""
数据一致性检查和处理服务
处理多数据源之间的数据不一致性问题
"""
import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class DataConsistencyResult:
    """数据一致性检查结果"""
    is_consistent: bool
    primary_source: str
    secondary_source: str
    differences: Dict[str, Any]
    confidence_score: float
    recommended_action: str
    details: Dict[str, Any]

@dataclass
class FinancialMetricComparison:
    """财务指标比较结果"""
    metric_name: str
    primary_value: Optional[float]
    secondary_value: Optional[float]
    difference_pct: Optional[float]
    is_significant: bool
    tolerance: float

class DataConsistencyChecker:
    """数据一致性检查器"""
    
    def __init__(self):
        # 设置各种指标的容忍度阈值
        self.tolerance_thresholds = {
            'pe': 0.05,      # PE允许5%差异
            'pb': 0.05,      # PB允许5%差异
            'total_mv': 0.02, # 市值允许2%差异
            'price': 0.01,   # 股价允许1%差异
            'volume': 0.10,  # 成交量允许10%差异
            'turnover_rate': 0.05  # 换手率允许5%差异
        }
        
        # 关键指标权重（用于计算置信度分数）
        self.metric_weights = {
            'pe': 0.25,
            'pb': 0.25,
            'total_mv': 0.20,
            'price': 0.15,
            'volume': 0.10,
            'turnover_rate': 0.05
        }
    
    def check_daily_basic_consistency(
        self, 
        primary_data: pd.DataFrame, 
        secondary_data: pd.DataFrame,
        primary_source: str,
        secondary_source: str
    ) -> DataConsistencyResult:
        """
        检查daily_basic数据的一致性
        
        Args:
            primary_data: 主数据源数据
            secondary_data: 次数据源数据
            primary_source: 主数据源名称
            secondary_source: 次数据源名称
        """
        try:
            logger.info(f"🔍 检查数据一致性: {primary_source} vs {secondary_source}")
            
            # 1. 基础检查
            if primary_data.empty or secondary_data.empty:
                return DataConsistencyResult(
                    is_consistent=False,
                    primary_source=primary_source,
                    secondary_source=secondary_source,
                    differences={'error': 'One or both datasets are empty'},
                    confidence_score=0.0,
                    recommended_action='use_primary_only',
                    details={'reason': 'Empty dataset detected'}
                )
            
            # 2. 股票代码匹配
            common_stocks = self._find_common_stocks(primary_data, secondary_data)
            if len(common_stocks) == 0:
                return DataConsistencyResult(
                    is_consistent=False,
                    primary_source=primary_source,
                    secondary_source=secondary_source,
                    differences={'error': 'No common stocks found'},
                    confidence_score=0.0,
                    recommended_action='use_primary_only',
                    details={'reason': 'No overlapping stocks'}
                )
            
            logger.info(f"📊 找到{len(common_stocks)}只共同股票进行比较")
            
            # 3. 逐指标比较
            metric_comparisons = []
            for metric in ['pe', 'pb', 'total_mv']:
                comparison = self._compare_metric(
                    primary_data, secondary_data, common_stocks, metric
                )
                if comparison:
                    metric_comparisons.append(comparison)
            
            # 4. 计算整体一致性
            consistency_result = self._calculate_overall_consistency(
                metric_comparisons, primary_source, secondary_source
            )
            
            return consistency_result
            
        except Exception as e:
            logger.error(f"❌ 数据一致性检查失败: {e}")
            return DataConsistencyResult(
                is_consistent=False,
                primary_source=primary_source,
                secondary_source=secondary_source,
                differences={'error': str(e)},
                confidence_score=0.0,
                recommended_action='use_primary_only',
                details={'exception': str(e)}
            )
    
    def _find_common_stocks(self, df1: pd.DataFrame, df2: pd.DataFrame) -> List[str]:
        """找到两个数据集中的共同股票"""
        # 尝试不同的股票代码列名
        code_cols = ['ts_code', 'symbol', 'code', 'stock_code']
        
        df1_codes = set()
        df2_codes = set()
        
        for col in code_cols:
            if col in df1.columns:
                df1_codes.update(df1[col].dropna().astype(str).tolist())
            if col in df2.columns:
                df2_codes.update(df2[col].dropna().astype(str).tolist())
        
        return list(df1_codes.intersection(df2_codes))
    
    def _compare_metric(
        self, 
        df1: pd.DataFrame, 
        df2: pd.DataFrame, 
        common_stocks: List[str], 
        metric: str
    ) -> Optional[FinancialMetricComparison]:
        """比较特定指标"""
        try:
            if metric not in df1.columns or metric not in df2.columns:
                return None
            
            # 获取共同股票的指标值
            df1_values = []
            df2_values = []
            
            for stock in common_stocks[:100]:  # 限制比较数量
                val1 = self._get_stock_metric_value(df1, stock, metric)
                val2 = self._get_stock_metric_value(df2, stock, metric)
                
                if val1 is not None and val2 is not None:
                    df1_values.append(val1)
                    df2_values.append(val2)
            
            if len(df1_values) == 0:
                return None
            
            # 计算平均值和差异
            avg1 = np.mean(df1_values)
            avg2 = np.mean(df2_values)
            
            if avg1 != 0:
                diff_pct = abs(avg2 - avg1) / abs(avg1)
            else:
                diff_pct = float('inf') if avg2 != 0 else 0
            
            tolerance = self.tolerance_thresholds.get(metric, 0.1)
            is_significant = diff_pct > tolerance
            
            return FinancialMetricComparison(
                metric_name=metric,
                primary_value=avg1,
                secondary_value=avg2,
                difference_pct=diff_pct,
                is_significant=is_significant,
                tolerance=tolerance
            )
            
        except Exception as e:
            logger.warning(f"⚠️ 比较指标{metric}失败: {e}")
            return None
    
    def _get_stock_metric_value(self, df: pd.DataFrame, stock_code: str, metric: str) -> Optional[float]:
        """获取特定股票的指标值"""
        try:
            # 尝试不同的匹配方式
            for code_col in ['ts_code', 'symbol', 'code']:
                if code_col in df.columns:
                    mask = df[code_col].astype(str) == stock_code
                    if mask.any():
                        value = df.loc[mask, metric].iloc[0]
                        if pd.notna(value) and value != 0:
                            return float(value)
            return None
        except:
            return None
    
    def _calculate_overall_consistency(
        self, 
        comparisons: List[FinancialMetricComparison],
        primary_source: str,
        secondary_source: str
    ) -> DataConsistencyResult:
        """计算整体一致性结果"""
        if not comparisons:
            return DataConsistencyResult(
                is_consistent=False,
                primary_source=primary_source,
                secondary_source=secondary_source,
                differences={'error': 'No valid metric comparisons'},
                confidence_score=0.0,
                recommended_action='use_primary_only',
                details={'reason': 'No comparable metrics'}
            )
        
        # 计算加权置信度分数
        total_weight = 0
        weighted_score = 0
        differences = {}
        
        for comp in comparisons:
            weight = self.metric_weights.get(comp.metric_name, 0.1)
            total_weight += weight
            
            # 一致性分数：差异越小分数越高
            if comp.difference_pct is not None and comp.difference_pct != float('inf'):
                consistency_score = max(0, 1 - (comp.difference_pct / comp.tolerance))
            else:
                consistency_score = 0
            
            weighted_score += weight * consistency_score
            
            # 记录差异
            differences[comp.metric_name] = {
                'primary_value': comp.primary_value,
                'secondary_value': comp.secondary_value,
                'difference_pct': comp.difference_pct,
                'is_significant': comp.is_significant,
                'tolerance': comp.tolerance
            }
        
        confidence_score = weighted_score / total_weight if total_weight > 0 else 0
        
        # 判断整体一致性
        significant_differences = sum(1 for comp in comparisons if comp.is_significant)
        is_consistent = significant_differences <= len(comparisons) * 0.3  # 允许30%的指标有显著差异
        
        # 推荐行动
        if confidence_score > 0.8:
            recommended_action = 'use_either'  # 数据高度一致，可以使用任一数据源
        elif confidence_score > 0.6:
            recommended_action = 'use_primary_with_warning'  # 使用主数据源但发出警告
        elif confidence_score > 0.3:
            recommended_action = 'use_primary_only'  # 仅使用主数据源
        else:
            recommended_action = 'investigate_sources'  # 需要调查数据源问题
        
        return DataConsistencyResult(
            is_consistent=is_consistent,
            primary_source=primary_source,
            secondary_source=secondary_source,
            differences=differences,
            confidence_score=confidence_score,
            recommended_action=recommended_action,
            details={
                'total_comparisons': len(comparisons),
                'significant_differences': significant_differences,
                'consistency_threshold': 0.3
            }
        )


    def validate_volume_consistency(
        self,
        volume_value: float,
        price: float,
        expected_amount: float = None,
        tolerance_pct: float = 0.15
    ) -> Tuple[bool, str, Dict]:
        """
        验证成交量数据的合理性
        
        由于不同数据源可能使用不同的成交量单位（手 vs 股），
        需要验证数据是否在合理范围内
        
        Args:
            volume_value: 成交量（可能是股或手）
            price: 收盘价
            expected_amount: 预期成交额（如果有）
            tolerance_pct: 允许差异百分比
        
        Returns:
            Tuple[bool, str, Dict]: (是否合理, 错误信息, 诊断信息)
        """
        try:
            diagnostic = {
                "input_volume": volume_value,
                "price": price,
                "input_unit": "unknown"
            }
            
            # A股单日成交额通常在 1000万 - 100亿 之间
            MIN_AMOUNT = 10_000_000  # 1000万
            MAX_AMOUNT = 10_000_000_000  # 100亿
            
            # 情况1：成交量单位是"手"（1手=100股）
            volume_as_hand = volume_value
            volume_in_shares = volume_as_hand * 100
            calculated_amount_hand = volume_in_shares * price
            diagnostic["volume_as_hand"] = volume_as_hand
            diagnostic["volume_in_shares"] = volume_in_shares
            diagnostic["calculated_amount_hand"] = calculated_amount_hand
            
            # 情况2：成交量单位已经是"股"
            volume_as_share = volume_value
            calculated_amount_share = volume_as_share * price
            diagnostic["volume_as_share"] = volume_as_share
            diagnostic["calculated_amount_share"] = calculated_amount_share
            
            # 判断哪个假设更合理
            hand_is_reasonable = MIN_AMOUNT <= calculated_amount_hand <= MAX_AMOUNT
            share_is_reasonable = MIN_AMOUNT <= calculated_amount_share <= MAX_AMOUNT
            
            if hand_is_reasonable and not share_is_reasonable:
                diagnostic["input_unit"] = "hand"
                diagnostic["corrected_volume"] = volume_in_shares
                diagnostic["corrected_amount"] = calculated_amount_hand
                if expected_amount:
                    diff_pct = abs(calculated_amount_hand - expected_amount) / expected_amount
                    diagnostic["amount_difference_pct"] = diff_pct
                    is_consistent = diff_pct <= tolerance_pct
                    return is_consistent, "", diagnostic
                return True, "", diagnostic
                
            elif share_is_reasonable and not hand_is_reasonable:
                diagnostic["input_unit"] = "share"
                diagnostic["corrected_volume"] = volume_as_share
                diagnostic["corrected_amount"] = calculated_amount_share
                if expected_amount:
                    diff_pct = abs(calculated_amount_share - expected_amount) / expected_amount
                    diagnostic["amount_difference_pct"] = diff_pct
                    is_consistent = diff_pct <= tolerance_pct
                    return is_consistent, "", diagnostic
                return True, "", diagnostic
                
            elif hand_is_reasonable and share_is_reasonable:
                if expected_amount:
                    hand_diff = abs(calculated_amount_hand - expected_amount)
                    share_diff = abs(calculated_amount_share - expected_amount)
                    if hand_diff < share_diff:
                        diagnostic["input_unit"] = "hand (closer to expected)"
                        diagnostic["corrected_volume"] = volume_in_shares
                        return True, "", diagnostic
                    else:
                        diagnostic["input_unit"] = "share (closer to expected)"
                        diagnostic["corrected_volume"] = volume_as_share
                        return True, "", diagnostic
                diagnostic["input_unit"] = "share (default)"
                diagnostic["corrected_volume"] = volume_as_share
                return True, "", diagnostic
                
            else:
                error_msg = f"成交量数据异常: volume={volume_value}, price={price}"
                diagnostic["input_unit"] = "invalid"
                return False, error_msg, diagnostic
                
        except Exception as e:
            return False, f"成交量验证失败: {e}", {}

    def validate_pe_calculation(
        self,
        symbol: str,
        reported_pe: float,
        current_price: float,
        total_shares: float,
        net_profit: float,
        profit_period: str = "TTM"
    ) -> Tuple[bool, str, Dict]:
        """
        验证PE计算是否正确
        
        Args:
            symbol: 股票代码
            reported_pe: 报告中的PE值
            current_price: 当前股价
            total_shares: 总股本（股）
            net_profit: 净利润（元）
            profit_period: 净利润期间
        
        Returns:
            Tuple[bool, str, Dict]: (是否正确, 错误信息, 诊断信息)
        """
        try:
            diagnostic = {
                "symbol": symbol,
                "reported_pe": reported_pe,
                "current_price": current_price,
                "total_shares": total_shares,
                "net_profit": net_profit,
                "profit_period": profit_period
            }
            
            # 计算EPS（每股收益）
            if total_shares <= 0:
                return False, f"总股本无效: {total_shares}", diagnostic
            
            eps = net_profit / total_shares
            diagnostic["calculated_eps"] = eps
            
            if eps <= 0:
                return False, f"EPS计算结果无效（净利润可能为负或零）: eps={eps}", diagnostic
            
            # 计算PE
            calculated_pe = current_price / eps
            diagnostic["calculated_pe"] = calculated_pe
            
            # 对比
            pe_diff = abs(calculated_pe - reported_pe)
            pe_diff_pct = pe_diff / reported_pe if reported_pe > 0 else float('inf')
            diagnostic["pe_difference"] = pe_diff
            diagnostic["pe_difference_pct"] = pe_diff_pct
            
            # 判断是否在合理误差范围内（5%）
            is_correct = pe_diff_pct <= 0.05
            
            if is_correct:
                return True, "", diagnostic
            else:
                error_msg = (
                    f"PE计算异常: symbol={symbol}\n"
                    f"  报告PE: {reported_pe}\n"
                    f"  计算PE: {calculated_pe:.2f}\n"
                    f"  差异: {pe_diff_pct*100:.1f}%\n"
                    f"  可能原因:\n"
                    f"    - 净利润期间不匹配（报告用{profit_period}，但计算用不同期间）\n"
                    f"    - 总股本数据过时（有增发/回购）\n"
                    f"    - 数据源返回的PE计算公式不同"
                )
                return False, error_msg, diagnostic
                
        except Exception as e:
            return False, f"PE验证失败: {e}", {}

    def resolve_data_conflicts(
        self, 
        primary_data: pd.DataFrame,
        secondary_data: pd.DataFrame,
        consistency_result: DataConsistencyResult
    ) -> Tuple[pd.DataFrame, str]:
        """
        根据一致性检查结果解决数据冲突
        
        Returns:
            Tuple[pd.DataFrame, str]: (最终数据, 解决策略说明)
        """
        action = consistency_result.recommended_action
        
        if action == 'use_either':
            logger.info("✅ 数据高度一致，使用主数据源")
            return primary_data, "数据源高度一致，使用主数据源"
        
        elif action == 'use_primary_with_warning':
            logger.warning("⚠️ 数据存在差异但在可接受范围内，使用主数据源")
            return primary_data, f"数据存在轻微差异（置信度: {consistency_result.confidence_score:.2f}），使用主数据源"
        
        elif action == 'use_primary_only':
            logger.warning("🚨 数据差异较大，仅使用主数据源")
            return primary_data, f"数据差异显著（置信度: {consistency_result.confidence_score:.2f}），仅使用主数据源"
        
        else:  # investigate_sources
            logger.error("❌ 数据源存在严重问题，需要人工调查")
            return primary_data, f"数据源存在严重不一致（置信度: {consistency_result.confidence_score:.2f}），建议检查数据源"
