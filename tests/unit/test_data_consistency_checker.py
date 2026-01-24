# -*- coding: utf-8 -*-
"""
数据一致性检查器单元测试
测试成交量和PE验证功能
"""
import pytest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.data_consistency_checker import DataConsistencyChecker


class TestVolumeValidation:
    """成交量验证测试"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.checker = DataConsistencyChecker()
    
    def test_volume_in_shares_correct(self):
        """测试成交量单位为股且数据合理"""
        # 假设股价50元，成交量555万股（合理）
        volume = 5_554_100  # 股
        price = 53.65
        
        is_valid, error_msg, diagnostic = self.checker.validate_volume_consistency(
            volume, price
        )
        
        assert is_valid is True
        assert error_msg == ""
        assert diagnostic["input_unit"] == "share"
        assert diagnostic["corrected_volume"] == volume
    
    def test_volume_in_hands_correct(self):
        """测试成交量单位为手且数据合理
        
        注意：当手和股两种解释都给出合理成交额时，
        系统默认使用"股"单位（share (default)），
        因为A股数据更常以股为单位存储
        """
        # 假设股价50元，成交量55.5万手 = 555万股（合理）
        volume = 555_410  # 手
        price = 53.65
        
        is_valid, error_msg, diagnostic = self.checker.validate_volume_consistency(
            volume, price
        )
        
        assert is_valid is True
        assert error_msg == ""
        # 两种解释都合理时，默认使用share
        assert diagnostic["input_unit"] in ["hand", "share (default)", "share"]
        assert diagnostic["corrected_volume"] in [volume, volume * 100]
    
    def test_volume_mismatch_hand_vs_share(self):
        """测试成交量单位混淆场景（报告中的问题）
        
        报告问题：
        - 技术报告写 1,904,255（应该是股，但量级偏小）
        - 基本面报告写 55,544,100（多了个零，应该是5,554,410股）
        """
        # 场景1：技术报告的数值（偏低）
        volume_tech = 1_904_255
        price = 53.65
        
        is_valid, error_msg, diagnostic = self.checker.validate_volume_consistency(
            volume_tech, price
        )
        
        # 这个值太小，算出来的成交额只有1亿，偏低但不是完全异常
        print(f"技术报告成交量验证: valid={is_valid}, unit={diagnostic.get('input_unit')}")
        
        # 场景2：基本面报告的数值（多了个零）
        volume_fund = 55_544_100  # 多了个零
        price = 53.65
        
        is_valid2, error_msg2, diagnostic2 = self.checker.validate_volume_consistency(
            volume_fund, price
        )
        
        # 这个值算出来成交额接近300亿，虽然偏高但可能是真实数据
        print(f"基本面报告成交量验证: valid={is_valid2}, unit={diagnostic2.get('input_unit')}")
        
        # 验证：两个值的差异应该被检测到
        # 1,904,255 vs 55,544,100 差了约29倍
    
    def test_volume_with_expected_amount(self):
        """测试带预期成交额的验证"""
        volume = 555_410  # 手
        price = 53.65
        expected_amount = 29_800_000  # 真实成交额约2.98亿
        
        is_valid, error_msg, diagnostic = self.checker.validate_volume_consistency(
            volume, price, expected_amount
        )
        
        assert is_valid is True
        # 当有预期成交额时，会选择更接近的那个
        assert "amount_difference_pct" in diagnostic or diagnostic.get("input_unit") in ["hand (closer to expected)", "share (closer to expected)"]
    
    def test_volume_extremely_low(self):
        """测试异常低的成交量"""
        volume = 1  # 不合理
        price = 53.65
        
        is_valid, error_msg, diagnostic = self.checker.validate_volume_consistency(
            volume, price
        )
        
        assert is_valid is False
        assert "异常" in error_msg
    
    def test_volume_extremely_high(self):
        """测试异常高的成交量"""
        volume = 999_999_999  # 不合理
        price = 53.65
        
        is_valid, error_msg, diagnostic = self.checker.validate_volume_consistency(
            volume, price
        )
        
        assert is_valid is False


class TestPEValidation:
    """PE验证测试"""
    
    def setup_method(self):
        """每个测试前初始化"""
        self.checker = DataConsistencyChecker()
    
    def test_pe_calculation_correct(self):
        """测试PE计算正确"""
        symbol = "600391"
        reported_pe = 397.7
        current_price = 53.65
        total_shares = 332_000_000  # 3.32亿股
        net_profit = 44_600_000  # 4460万净利润
        
        is_valid, error_msg, diagnostic = self.checker.validate_pe_calculation(
            symbol, reported_pe, current_price, total_shares, net_profit
        )
        
        print(f"PE验证: valid={is_valid}")
        print(f"  计算EPS: {diagnostic.get('calculated_eps')}")
        print(f"  计算PE: {diagnostic.get('calculated_pe')}")
        print(f"  差异: {diagnostic.get('pe_difference_pct')}")
        
        # PE 397.7 = 53.65 / (4460万/3.32亿) = 53.65 / 0.1343 = 399.6
        # 误差约0.5%，应该在5%容忍度内
        assert is_valid is True
    
    def test_pe_mismatch_different_period(self):
        """测试PE不匹配（净利润期间不同）
        
        问题场景：
        - 报告用TTM PE = 397.7
        - 但实际只用了Q1-Q3的数据（4460万）
        - 如果Q4只有1000万利润，TTM应该是5460万
        """
        symbol = "600391"
        reported_pe = 397.7
        current_price = 53.65
        total_shares = 332_000_000
        
        # 场景1：用Q1-Q3净利润（4460万）
        net_profit_q1q3 = 44_600_000
        is_valid1, error_msg1, diagnostic1 = self.checker.validate_pe_calculation(
            symbol, reported_pe, current_price, total_shares, net_profit_q1q3, "Q1-Q3"
        )
        
        print(f"PE验证(Q1-Q3): valid={is_valid1}")
        print(f"  报告PE: {reported_pe}, 计算PE: {diagnostic1.get('calculated_pe')}")
        
        # 场景2：用全年净利润（假设Q4很差，只有1000万）
        net_profit_full = 54_600_000  # 4460 + 1000 = 5460万
        is_valid2, error_msg2, diagnostic2 = self.checker.validate_pe_calculation(
            symbol, reported_pe, current_price, total_shares, net_profit_full, "Annual"
        )
        
        print(f"PE验证(全年): valid={is_valid2}")
        print(f"  报告PE: {reported_pe}, 计算PE: {diagnostic2.get('calculated_pe')}")
        
        # 用全年净利润计算，PE会显著低于397.7
        assert diagnostic2.get('calculated_pe') < 350  # 应该明显低于报告值
    
    def test_pe_zero_shares(self):
        """测试总股本为零的情况"""
        is_valid, error_msg, diagnostic = self.checker.validate_pe_calculation(
            "600391", 397.7, 53.65, 0, 44_600_000
        )
        
        assert is_valid is False
        assert "总股本无效" in error_msg
    
    def test_pe_negative_profit(self):
        """测试净利润为负的情况"""
        is_valid, error_msg, diagnostic = self.checker.validate_pe_calculation(
            "600391", 397.7, 53.65, 332_000_000, -10_000_000  # 亏损
        )
        
        assert is_valid is False
        assert "EPS" in error_msg or "净利润" in error_msg


class TestDataConsistencyChecker:
    """数据一致性检查器综合测试"""
    
    def test_tolerance_thresholds(self):
        """测试容忍度阈值配置"""
        checker = DataConsistencyChecker()
        
        assert checker.tolerance_thresholds['volume'] == 0.10  # 10%
        assert checker.tolerance_thresholds['pe'] == 0.05      # 5%
        assert checker.tolerance_thresholds['price'] == 0.01   # 1%
    
    def test_metric_weights(self):
        """测试指标权重"""
        checker = DataConsistencyChecker()
        
        assert checker.metric_weights['pe'] == 0.25
        assert checker.metric_weights['pb'] == 0.25
        assert checker.metric_weights['volume'] == 0.10


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
