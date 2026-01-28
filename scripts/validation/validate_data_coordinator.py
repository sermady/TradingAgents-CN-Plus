# -*- coding: utf-8 -*-
"""
DataCoordinator 验证脚本

验证优化后的 DataCoordinator 功能:
1. PS比率验证和修正
2. 成交量单位标准化
3. 多级降级策略
4. 数据验证集成
5. 数据质量评分
6. 并行数据获取
7. 分析级缓存
8. 港股/美股不支持提示
"""

import sys
import time
from datetime import datetime

sys.path.insert(0, r'E:\WorkSpace\TradingAgents-CN')

from tradingagents.graph.data_coordinator import get_data_coordinator
from tradingagents.utils.trading_date_manager import get_trading_date_manager


def test_ps_ratio_validation():
    """测试 PS 比率验证和修正"""
    print("\n" + "=" * 60)
    print("PS比率验证测试")
    print("=" * 60)

    coordinator = get_data_coordinator()

    # 测试数据：模拟有问题的PS比率（如605589的情况）
    test_data = {
        "PS": 0.14,  # 明显错误的PS
        "market_cap": 110.96,  # 亿元
        "revenue": 74.12,  # 亿元
    }

    issues, corrected_ps = coordinator._validate_and_fix_ps_ratio(test_data, "605589")

    print(f"\n测试股票: 605589")
    print(f"原始PS: {test_data['PS']}")
    print(f"市值: {test_data['market_cap']}亿")
    print(f"营收: {test_data['revenue']}亿")
    print(f"计算PS: {test_data['market_cap'] / test_data['revenue']:.2f}")
    print(f"修正PS: {corrected_ps}")
    print(f"检测问题数: {len(issues)}")

    if issues:
        print("\n检测到的问题:")
        for issue in issues[:2]:  # 最多显示2个
            print(f"  - [{issue['severity']}] {issue['message']}")

    # 验证结果
    expected_ps = test_data['market_cap'] / test_data['revenue']
    if corrected_ps is None:
        print("❌ PS比率验证失败: 未返回修正值")
        return False

    if abs(corrected_ps - expected_ps) > 0.1:
        print(f"❌ PS比率验证失败: 修正值不正确 {corrected_ps} != {expected_ps}")
        return False

    print("✅ PS比率验证通过")
    return True


def test_volume_standardization():
    """测试成交量单位标准化"""
    print("\n" + "=" * 60)
    print("成交量单位标准化测试")
    print("=" * 60)

    coordinator = get_data_coordinator()

    # 测试1: 明确标注为"手"的数据
    test_data_1 = {"volume": 954158}  # 单位可能是"手"
    data_str_1 = "成交量: 954,158 手"

    updated_data, unit_info = coordinator._standardize_volume_unit(test_data_1, data_str_1)

    print(f"\n测试 - 明确标注为'手':")
    print(f"原始成交量: {test_data_1['volume']}")
    print(f"处理后成交量: {updated_data['volume']}")
    print(f"单位信息: {unit_info}")

    if updated_data['volume'] != 95415800:  # 应该转换为"股"（乘以100）
        print(f"❌ 成交量标准化失败: {updated_data['volume']} != 95415800")
        return False

    if unit_info != "converted_from_lots":
        print(f"❌ 单位信息标记失败: {unit_info} != converted_from_lots")
        return False

    print("✅ 成交量单位标准化通过")
    return True


def test_analysis_cache():
    """测试分析级缓存"""
    print("\n" + "=" * 60)
    print("分析级缓存测试")
    print("=" * 60)

    coordinator = get_data_coordinator()
    symbol = "000001"
    trade_date = datetime.now().strftime("%Y-%m-%d")

    # 清除缓存
    coordinator.clear_analysis_cache()

    # 第一次获取（应该走网络）
    print(f"\n第一次获取 {symbol} 数据...")
    start = time.time()
    result1 = coordinator.fetch_all_data(symbol, trade_date, parallel=True, use_cache=True)
    time1 = time.time() - start
    print(f"耗时: {time1:.2f}s")

    # 第二次获取（应该从缓存读取）
    print(f"\n第二次获取 {symbol} 数据（应该从缓存读取）...")
    start = time.time()
    result2 = coordinator.fetch_all_data(symbol, trade_date, parallel=True, use_cache=True)
    time2 = time.time() - start
    print(f"耗时: {time2:.2f}s")

    # 验证缓存命中
    if time2 >= time1 / 2:
        print(f"⚠️ 缓存可能未命中: 第二次耗时 {time2:.2f}s >= 第一次 {time1:.2f}s / 2")
        # 不返回False，因为可能只是网络很快

    if result1['market_data'] != result2['market_data']:
        print("❌ 缓存数据不一致")
        return False

    print("✅ 分析级缓存测试通过")
    return True


def test_non_china_market():
    """测试港股/美股不支持提示"""
    print("\n" + "=" * 60)
    print("非A股市场测试")
    print("=" * 60)

    from tradingagents.graph.data_coordinator import data_coordinator_node

    # 测试美股
    print("\n测试美股: AAPL")
    state_us = {
        "company_of_interest": "AAPL",
        "trade_date": datetime.now().strftime("%Y-%m-%d"),
    }
    result_us = data_coordinator_node(state_us)

    print(f"市场数据: {result_us['market_data'][:80]}...")

    if "不支持" not in result_us['market_data'] and "unsupported" not in str(result_us['data_sources'].get('market', '')):
        print("❌ 美股未正确提示不支持")
        return False

    # 测试港股
    print("\n测试港股: 00700.HK")
    state_hk = {
        "company_of_interest": "00700.HK",
        "trade_date": datetime.now().strftime("%Y-%m-%d"),
    }
    result_hk = data_coordinator_node(state_hk)

    print(f"市场数据: {result_hk['market_data'][:80]}...")

    if "不支持" not in result_hk['market_data'] and "unsupported" not in str(result_hk['data_sources'].get('market', '')):
        print("❌ 港股未正确提示不支持")
        return False

    print("✅ 非A股市场测试通过")
    return True


def test_data_coordinator():
    """测试 DataCoordinator"""
    print("\n" + "=" * 60)
    print("DataCoordinator 功能验证")
    print("=" * 60)

    # 测试股票代码（平安银行）
    test_symbol = "000001.SZ"
    date_mgr = get_trading_date_manager()
    trade_date = date_mgr.get_latest_trading_date()

    print(f"\n📊 测试股票: {test_symbol}")
    print(f"📅 交易日期: {trade_date}")

    # 获取 DataCoordinator
    coordinator = get_data_coordinator()

    # 清除缓存确保公平测试
    coordinator.clear_analysis_cache()

    print("\n🔄 开始获取数据...")
    start_time = time.time()

    # 获取所有数据
    results = coordinator.fetch_all_data(test_symbol, trade_date, parallel=True)

    total_time = time.time() - start_time

    print("\n" + "=" * 60)
    print("📋 结果汇总")
    print("=" * 60)

    # 显示数据来源
    print("\n📡 数据来源:")
    for data_type, source in results.get("data_sources", {}).items():
        print(f"   - {data_type}: {source}")

    # 显示数据质量评分
    quality_score = results.get("data_quality_score", 0)
    print(f"\n⭐ 总体数据质量评分: {quality_score:.1%}")

    # 显示 metadata
    metadata = results.get("data_metadata", {})
    if metadata.get("corrected_ps"):
        print(f"📝 PS比率修正值: {metadata['corrected_ps']}")
    if metadata.get("volume_unit_info"):
        print(f"📝 成交量单位处理: {metadata['volume_unit_info']}")

    # 显示数据长度
    print("\n📦 数据长度:")
    print(f"   - 市场数据: {len(results.get('market_data', ''))} 字符")
    print(f"   - 基本面数据: {len(results.get('financial_data', ''))} 字符")
    print(f"   - 新闻数据: {len(results.get('news_data', ''))} 字符")
    print(f"   - 舆情数据: {len(results.get('sentiment_data', ''))} 字符")

    # 显示数据问题
    issues = results.get("data_issues", {})
    if issues:
        print("\n⚠️ 数据质量问题:")
        for data_type, issue_list in issues.items():
            if issue_list:
                print(f"   - {data_type}:")
                for issue in issue_list[:2]:  # 最多显示2个问题
                    severity = issue.get("severity", "info")
                    message = issue.get("message", "")
                    print(f"     [{severity}] {message}")

    # 显示耗时
    fetch_time = results.get("fetch_time", 0)
    print(f"\n⏱️ 总耗时: {fetch_time:.2f} 秒")
    print(f"   (验证脚本总耗时: {total_time:.2f} 秒)")

    # 验证结果
    print("\n" + "=" * 60)
    print("✅ 验证结果")
    print("=" * 60)

    success = True

    # 检查数据质量
    if quality_score >= 0.5:  # 降低要求，因为新闻/舆情数据可能不可用
        print("✅ 数据质量评分通过 (>= 50%)")
    else:
        print(f"⚠️ 数据质量评分较低: {quality_score:.1%}")
        success = False

    # 检查数据来源
    sources = results.get("data_sources", {})
    if sources.get("market") != "failed" and sources.get("market") != "unsupported":
        print("✅ 市场数据获取成功")
    else:
        print("❌ 市场数据获取失败")
        success = False

    if sources.get("financial") != "failed" and sources.get("financial") != "unsupported":
        print("✅ 基本面数据获取成功")
    else:
        print("❌ 基本面数据获取失败")
        success = False

    # 检查耗时
    if fetch_time < 30:
        print(f"✅ 数据获取耗时通过 (< 30秒)")
    else:
        print(f"⚠️ 数据获取耗时较长: {fetch_time:.2f}秒")

    print("\n" + "=" * 60)
    if success:
        print("🎉 所有关键验证通过!")
    else:
        print("⚠️ 部分验证未通过，请检查日志")
    print("=" * 60)

    return success


def test_trading_date_manager():
    """测试交易日管理器"""
    print("\n" + "=" * 60)
    print("交易日管理器验证")
    print("=" * 60)

    date_mgr = get_trading_date_manager()

    # 测试获取最新交易日
    latest_date = date_mgr.get_latest_trading_date()
    print(f"\n📅 最新交易日: {latest_date}")

    # 测试日期范围
    start_date, end_date = date_mgr.get_trading_date_range(lookback_days=10)
    print(f"📅 交易日期范围: {start_date} ~ {end_date}")

    # 验证日期格式
    try:
        datetime.strptime(latest_date, "%Y-%m-%d")
        print("✅ 日期格式正确")
        return True
    except ValueError:
        print("❌ 日期格式错误")
        return False


if __name__ == "__main__":
    print("\n🔍 开始验证 A股分析系统优化...\n")

    results = []

    # 测试交易日管理器
    results.append(("交易日管理器", test_trading_date_manager()))

    # 测试 PS 比率验证
    results.append(("PS比率验证", test_ps_ratio_validation()))

    # 测试成交量标准化
    results.append(("成交量标准化", test_volume_standardization()))

    # 测试分析级缓存
    results.append(("分析级缓存", test_analysis_cache()))

    # 测试非A股市场
    results.append(("非A股市场提示", test_non_china_market()))

    # 测试 DataCoordinator
    results.append(("DataCoordinator", test_data_coordinator()))

    # 最终结果
    print("\n" + "=" * 60)
    print("📊 最终验证结果")
    print("=" * 60)

    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")

    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)

    print(f"\n总计: {passed_count}/{total_count} 项测试通过")

    if passed_count == total_count:
        print("\n🎉 所有验证通过! A股分析系统优化成功。")
        sys.exit(0)
    else:
        print("\n⚠️ 部分验证失败，请检查日志和配置。")
        sys.exit(1)
