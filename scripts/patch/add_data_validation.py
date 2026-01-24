# -*- coding: utf-8 -*-
"""
数据验证补丁 - 自动应用所有修改
运行方式: python scripts/patch/add_data_validation.py
"""

import os
import re
import sys

PROJECT_ROOT = r"E:/WorkSpace/TradingAgents-CN"
MARKET_ANALYST_FILE = os.path.join(PROJECT_ROOT, r"tradingagents/agents/analysts/market_analyst.py")

def patch_market_analyst():
    """在 market_analyst.py 中添加数据验证逻辑"""
    
    with open(MARKET_ANALYST_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已打补丁
    if "数据验证开始" in content:
        print("✅ market_analyst.py 已打过补丁，跳过")
        return True
    
    # 找到目标位置：在 "✅ 强制获取市场数据成功" 之后
    target_pattern = r'(logger\.info\(f"📊 \[市场分析师\] ✅ 强制获取市场数据成功: \{len\(str\(forced_data\)\)\} 字符"\))'
    
    replacement = r'''\1

                        # ========== 数据验证开始 ==========
                        try:
                            from tradingagents.utils.validation import validate_market_data
                            import json
                            
                            # 尝试解析返回数据
                            market_data = {}
                            if isinstance(forced_data, dict):
                                market_data = forced_data
                            elif isinstance(forced_data, str):
                                try:
                                    market_data = json.loads(forced_data)
                                except:
                                    pass
                            
                            # 执行数据验证
                            if market_data:
                                validation_report = validate_market_data(market_data)
                                
                                # 输出验证结果
                                if validation_report.get("alerts"):
                                    logger.warning(f"📊 [数据验证] 发现关键告警: {validation_report['alerts']}")
                                    
                                if validation_report.get("issues"):
                                    logger.error(f"📊 [数据验证] 数据质量问题: {validation_report['issues']}")
                                    
                                if validation_report["overall_status"] == "pass":
                                    logger.info(f"📊 [数据验证] 数据验证通过")
                                else:
                                    logger.warning(f"📊 [数据验证] 数据状态: {validation_report['overall_status']}")
                                    
                        except Exception as e:
                            logger.debug(f"📊 [数据验证] 验证过程跳过: {e}")
                        # ========== 数据验证结束 =========='''
    
    new_content = re.sub(target_pattern, replacement, content, count=1)
    
    if new_content == content:
        print("❌ 未找到目标位置，补丁失败")
        return False
    
    with open(MARKET_ANALYST_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ market_analyst.py 补丁应用成功")
    return True

def update_rsi_prompt():
    """更新RSI提示词，添加极端值警告要求"""
    
    with open(MARKET_ANALYST_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已更新
    if "连续3天≥80" in content:
        print("✅ RSI提示词已更新，跳过")
        return True
    
    # 找到RSI部分并更新
    old_rsi = r'#### 3\. RSI相对强弱指标\[从工具数据中提取并分析RSI，包括：- RSI当前数值- 超买/超卖区域判断- 背离信号\]'
    
    new_rsi = r'''#### 3. RSI相对强弱指标
[从工具数据中提取并分析RSI，包括：
- RSI当前数值
- ⚠️ **重要**：如果RSI6连续3天≥80，必须明确标注"极端超买信号"，这是3年罕见的风险信号
- 超买/超卖区域判断（70以上为超买，30以下为超卖）
- 背离信号]'''
    
    new_content = re.sub(old_rsi, new_rsi, content)
    
    if new_content == content:
        print("❌ 未找到RSI提示词位置，跳过")
        return False
    
    with open(MARKET_ANALYST_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ RSI提示词更新成功")
    return True

def main():
    print("=" * 60)
    print("数据验证补丁 - 自动应用所有修改")
    print("=" * 60)
    
    success = True
    
    # 步骤1: 添加数据验证逻辑
    print("\n[1/2] 添加数据验证逻辑...")
    if not patch_market_analyst():
        success = False
    
    # 步骤2: 更新RSI提示词
    print("\n[2/2] 更新RSI提示词...")
    if not update_rsi_prompt():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 所有补丁应用成功！")
        print("\n下一步: 运行测试验证修改")
        print("  python -m cli.main analyze 605589 2026-01-24")
    else:
        print("❌ 部分补丁应用失败，请检查错误信息")
        sys.exit(1)

if __name__ == "__main__":
    main()
