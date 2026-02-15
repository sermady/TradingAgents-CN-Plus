# -*- coding: utf-8 -*-
"""
验证器模块测试脚本

验证 tradingagents/utils/validators 的所有验证功能
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
sys.path.insert(0, project_root)


async def test_validators():
    """测试所有验证器模块"""
    print("=" * 50)
    print("[TEST] 开始测试 validators 模块...")

    # 导入必要的模块
    try:
        from tradingagents.utils.validators.format_validator import FormatValidator, FormatValidationError
        from tradingagents.utils.validators.stock_validator import StockDataPreparer, StockDataPreparationResult
        print("[OK] 成功导入 validators 模块")
    except Exception as e:
        print(f"[ERROR] 导入失败: {e}")
        return False

    basic_tests_passed = True

    # 测试格式验证器 - 基本功能
    try:
        validator = FormatValidator()

        # 测试A股代码验证
        is_valid, error_msg, suggestion = validator.validate_stock_format("000001", "A股")
        assert is_valid == True, f"000001应该有效: {error_msg}"

        is_valid, error_msg, suggestion = validator.validate_stock_format("600000", "A股")
        assert is_valid == True, f"600000应该有效: {error_msg}"

        print("   [OK] FormatValidator - A股格式验证通过")
    except Exception as e:
        print(f"   [ERROR] FormatValidator - A股格式验证失败: {e}")
        basic_tests_passed = False

    # 测试格式验证器 - 港股
    try:
        validator = FormatValidator()

        is_valid, error_msg, suggestion = validator.validate_stock_format("00700", "港股")
        assert is_valid == True, f"00700应该有效: {error_msg}"

        print("   [OK] FormatValidator - 港股格式验证通过")
    except Exception as e:
        print(f"   [ERROR] FormatValidator - 港股格式验证失败: {e}")
        basic_tests_passed = False

    # 测试格式验证器 - 美股
    try:
        validator = FormatValidator()

        is_valid, error_msg, suggestion = validator.validate_stock_format("AAPL", "美股")
        assert is_valid == True, f"AAPL应该有效: {error_msg}"

        print("   [OK] FormatValidator - 美股格式验证通过")
    except Exception as e:
        print(f"   [ERROR] FormatValidator - 美股格式验证失败: {e}")
        basic_tests_passed = False

    # 测试格式验证器 - 无效代码
    try:
        validator = FormatValidator()

        is_valid, error_msg, suggestion = validator.validate_stock_format("INVALID", "A股")
        assert is_valid == False, f"INVALID应该无效: {error_msg}"
        assert error_msg is not None, "应该有错误消息"

        print("   [OK] FormatValidator - 无效代码验证通过")
    except Exception as e:
        print(f"   [ERROR] FormatValidator - 无效代码验证失败: {e}")
        basic_tests_passed = False

    # 测试StockDataPreparationResult
    try:
        result = StockDataPreparationResult(
            is_valid=True,
            stock_code="000001",
            market_type="A股"
        )

        assert result.is_valid == True
        assert result.stock_code == "000001"
        assert result.market_type == "A股"

        # 测试to_dict方法
        result_dict = result.to_dict()
        assert result_dict["is_valid"] == True
        assert result_dict["stock_code"] == "000001"

        print("   [OK] StockDataPreparationResult - 结果类测试通过")
    except Exception as e:
        print(f"   [ERROR] StockDataPreparationResult - 结果类测试失败: {e}")
        basic_tests_passed = False

    # 测试StockDataPreparer
    try:
        preparer = StockDataPreparer()

        # 测试实例化
        assert preparer is not None

        print("   [OK] StockDataPreparer - 数据准备器测试通过")
    except Exception as e:
        print(f"   [ERROR] StockDataPreparer - 数据准备器测试失败: {e}")
        basic_tests_passed = False

    # 测试A股专用验证器
    try:
        from tradingagents.utils.validators.market_validators.china_validator import ChinaStockValidator

        validator = ChinaStockValidator()

        # 测试实例化
        assert validator is not None

        print("   [OK] ChinaStockValidator - A股验证器导入通过")
    except Exception as e:
        print(f"   [ERROR] ChinaStockValidator - A股验证器导入失败: {e}")
        basic_tests_passed = False

    # 测试港股专用验证器
    try:
        from tradingagents.utils.validators.market_validators.hk_validator import HKStockValidator

        validator = HKStockValidator()

        # 测试实例化
        assert validator is not None

        print("   [OK] HKStockValidator - 港股验证器导入通过")
    except Exception as e:
        print(f"   [ERROR] HKStockValidator - 港股验证器导入失败: {e}")
        basic_tests_passed = False

    # 测试美股专用验证器
    try:
        from tradingagents.utils.validators.market_validators.us_validator import USStockValidator

        validator = USStockValidator()

        # 测试实例化
        assert validator is not None

        print("   [OK] USStockValidator - 美股验证器导入通过")
    except Exception as e:
        print(f"   [ERROR] USStockValidator - 美股验证器导入失败: {e}")
        basic_tests_passed = False

    # 汇总结果
    print("=" * 50)
    if basic_tests_passed:
        print("[SUCCESS] 所有验证器测试通过！")
    else:
        print("[WARNING] 部分验证器测试失败，需要修复")

    return basic_tests_passed


if __name__ == "__main__":
    asyncio.run(test_validators())
