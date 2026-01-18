# -*- coding: utf-8 -*-
"""
测试报告：TradingAgents-CN 数据真实性保障修复
测试日期：2025-01-17
测试人员：Sisyphus
"""


def run_validation_tests():
    """运行所有验证测试"""
    import ast
    import sys

    print("=" * 80)
    print("数据真实性保障修复验证报告")
    print("=" * 80)
    print()

    # 测试结果统计
    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    # ============ 1. 语法检查 ============
    print("1. 语法检查")
    print("-" * 80)

    files_to_check = [
        "tradingagents/agents/analysts/social_media_analyst.py",
        "tradingagents/agents/analysts/china_market_analyst.py",
        "tradingagents/agents/researchers/bull_researcher.py",
        "tradingagents/agents/researchers/bear_researcher.py",
        "tradingagents/agents/managers/research_manager.py",
        "tradingagents/agents/managers/risk_manager.py",
    ]

    for filepath in files_to_check:
        total_tests += 1
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()
            ast.parse(code)
            print(f"[PASS] {filepath} - Syntax OK")
            passed_tests += 1
        except SyntaxError as e:
            print(f"[FAIL] {filepath} - Syntax Error: {e}")
            failed_tests += 1
            sys.exit(1)

    print()

    # ============ 2. social_media_analyst.py 验证 ============
    print("2. social_media_analyst.py 关键功能验证")
    print("-" * 80)

    with open(
        "tradingagents/agents/analysts/social_media_analyst.py", "r", encoding="utf-8"
    ) as f:
        content = f.read()

    checks = [
        ("CRITICAL REQUIREMENT", "CRITICAL REQUIREMENT" in content),
        ("禁止编造数据", "绝对禁止编造投资者情绪" in content),
        ("强制调用工具", "get_stock_sentiment_unified" in content),
        ("补救机制", "启动补救机制" in content),
        ("强制获取数据", "强制调用统一情绪分析工具" in content),
        ("基于真实数据", "基于上述真实情绪数据" in content),
    ]

    for check_name, check_result in checks:
        total_tests += 1
        if check_result:
            print(f"[PASS] social_media_analyst - {check_name}")
            passed_tests += 1
        else:
            print(f"[FAIL] social_media_analyst - {check_name}")
            failed_tests += 1

    print()

    # ============ 3. china_market_analyst.py 验证 ============
    print("3. china_market_analyst.py 关键功能验证")
    print("-" * 80)

    with open(
        "tradingagents/agents/analysts/china_market_analyst.py", "r", encoding="utf-8"
    ) as f:
        content = f.read()

    checks = [
        ("CRITICAL REQUIREMENT", "CRITICAL REQUIREMENT" in content),
        ("禁止编造技术指标", "绝对禁止编造技术指标数据" in content),
        ("强制调用工具", "必须调用工具获取真实的市场数据" in content),
        ("补救机制", "启动补救机制" in content),
        ("强制获取数据", "强制调用工具获取市场数据" in content),
        ("基于真实数据", "基于上述真实市场数据" in content),
    ]

    for check_name, check_result in checks:
        total_tests += 1
        if check_result:
            print(f"[PASS] china_market_analyst - {check_name}")
            passed_tests += 1
        else:
            print(f"[FAIL] china_market_analyst - {check_name}")
            failed_tests += 1

    print()

    # ============ 4. Research Team 验证 ============
    print("4. Research Team 数据验证要求验证")
    print("-" * 80)

    research_files = [
        ("bull_researcher", "tradingagents/agents/researchers/bull_researcher.py"),
        ("bear_researcher", "tradingagents/agents/researchers/bear_researcher.py"),
        ("research_manager", "tradingagents/agents/managers/research_manager.py"),
        ("risk_manager", "tradingagents/agents/managers/risk_manager.py"),
    ]

    for agent_name, filepath in research_files:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        checks = [
            ("数据验证要求", "数据验证要求" in content),
            (
                "评估报告是否基于真实数据",
                "评估所有提供的分析报告是否基于真实数据" in content,
            ),
            ("批判性评估", "批判性地评估" in content),
            ("明确指出问题", "明确指出" in content),
        ]

        for check_name, check_result in checks:
            total_tests += 1
            if check_result:
                print(f"[PASS] {agent_name} - {check_name}")
                passed_tests += 1
            else:
                print(f"[FAIL] {agent_name} - {check_name}")
                failed_tests += 1

    print()

    # ============ 5. 测试总结 ============
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    print(f"总测试数: {total_tests}")
    print(f"通过数:   {passed_tests}")
    print(f"失败数:   {failed_tests}")
    print(f"通过率:   {(passed_tests / total_tests * 100):.1f}%")
    print()

    if failed_tests == 0:
        print("✅ 所有测试通过！修复验证成功！")
        return True
    else:
        print(f"❌ 有 {failed_tests} 个测试失败，请检查！")
        return False


if __name__ == "__main__":
    success = run_validation_tests()
    exit(0 if success else 1)
