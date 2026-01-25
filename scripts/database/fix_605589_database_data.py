# -*- coding: utf-8 -*-
"""
数据库数据修正脚本 - 独立版本

从源头修正605589的PS比率错误数据
直接连接MongoDB，避免导入链中的emoji编码问题
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# 读取.env文件
def load_env():
    """读取.env文件"""
    env_path = Path(__file__).parent.parent.parent / '.env'
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # 移除行内注释（#后面的内容）
                    if ' #' in value:
                        value = value.split(' #')[0].strip()
                    env_vars[key] = value
    return env_vars

def main():
    symbol = "605589"

    print("=" * 80)
    print(f"数据库数据修正 - {symbol}")
    print("=" * 80)
    print()

    try:
        # 加载环境变量
        env = load_env()

        # MongoDB配置
        mongodb_host = env.get('MONGODB_HOST', 'localhost')
        mongodb_port = int(env.get('MONGODB_PORT', '27017'))
        mongodb_username = env.get('MONGODB_USERNAME')
        mongodb_password = env.get('MONGODB_PASSWORD')
        mongodb_database = env.get('MONGODB_DATABASE', 'tradingagents')
        mongodb_auth_source = env.get('MONGODB_AUTH_SOURCE', 'admin')

        print(f"连接MongoDB: {mongodb_host}:{mongodb_port}/{mongodb_database}")

        # 连接MongoDB
        import pymongo
        from pymongo import MongoClient

        # 构建连接参数
        connect_kwargs = {
            "host": mongodb_host,
            "port": mongodb_port,
            "serverSelectionTimeoutMS": 5000
        }

        # 如果有用户名和密码，添加认证
        if mongodb_username and mongodb_password:
            connect_kwargs.update({
                "username": mongodb_username,
                "password": mongodb_password,
                "authSource": mongodb_auth_source
            })

        mongo_client = MongoClient(**connect_kwargs)
        db = mongo_client[mongodb_database]

        print("数据库连接成功!")
        print()

        # ========== 第一步: 查看当前数据 ==========
        print("【第一步】查看数据库中的当前数据")
        print("-" * 80)

        # 查询基本面数据
        fundamentals_collection = db['china_stocks_fundamentals']
        doc = fundamentals_collection.find_one({'symbol': symbol})

        if not doc:
            print(f"未找到 {symbol} 的基本面数据")
            return

        print(f"找到数据文档，报告期: {doc.get('report_date')}")
        print()

        # 显示当前估值指标
        print("当前估值指标:")
        if 'valuation_metrics' in doc:
            metrics = doc['valuation_metrics']
            print(f"  PE: {metrics.get('pe_ratio')}")
            print(f"  PB: {metrics.get('pb_ratio')}")
            print(f"  PS: {metrics.get('ps_ratio')}")
        else:
            print("  (无估值指标字段)")
        print()

        # 显示财务数据
        print("当前财务数据:")
        if 'financial_data' in doc:
            financial = doc['financial_data']
            print(f"  总市值: {financial.get('market_cap')}")
            print(f"  营业总收入: {financial.get('revenue')}")
            print(f"  净利润: {financial.get('net_profit')}")
        print()

        # ========== 第二步: 计算正确的PS ==========
        print("【第二步】计算正确的PS比率")
        print("-" * 80)

        # 尝试从不同位置获取数据
        market_cap = None
        revenue = None
        existing_ps = None

        # 从valuation_metrics获取
        if 'valuation_metrics' in doc:
            vm = doc['valuation_metrics']
            market_cap = vm.get('market_cap')
            # PS可能存在但错误
            existing_ps = vm.get('ps_ratio')

        # 从financial_data获取
        if 'financial_data' in doc:
            fd = doc['financial_data']
            if market_cap is None:
                market_cap = fd.get('market_cap')
            revenue = fd.get('revenue')

        print(f"提取的数据:")
        print(f"  市值: {market_cap}")
        print(f"  营收: {revenue}")
        print(f"  现有PS: {existing_ps}")
        print()

        # 计算正确的PS
        if market_cap and revenue and revenue > 0:
            correct_ps = market_cap / revenue
            print(f"计算结果:")
            print(f"  PS = {market_cap} / {revenue} = {correct_ps:.2f}倍")
            print()

            # 检查是否需要修正
            if existing_ps is None:
                print(f"[OK] 数据库中没有PS值，需要添加")
                action = "add"
            elif existing_ps == 0:
                print(f"[ERROR] 数据库中PS值为0，明显错误，需要修正")
                action = "update"
            elif abs(existing_ps - correct_ps) / max(existing_ps, 0.01) > 0.1:
                print(f"[ERROR] 数据库中PS值错误 ({existing_ps} vs {correct_ps:.2f})，需要修正")
                action = "update"
            else:
                print(f"[OK] 数据库中PS值正确 ({existing_ps})，无需修正")
                action = None
        else:
            print("[ERROR] 缺少必要数据（市值或营收），无法计算PS")
            action = None

        print()

        # ========== 第三步: 执行修正 ==========
        if action:
            print("【第三步】执行数据库修正")
            print("-" * 80)

            update_data = {}
            timestamp = datetime.now().isoformat()

            if action == "add":
                # 添加PS字段
                if 'valuation_metrics' in doc:
                    update_data['valuation_metrics.ps_ratio'] = correct_ps
                    update_data['valuation_metrics.ps_data_source'] = 'auto_calculated'
                    update_data['valuation_metrics.ps_last_updated'] = timestamp

                    # 计算日志
                    calc_note = f"""PS计算:
- 公式: PS = 总市值 / 营业总收入
- 数据: 市值={market_cap}, 营收={revenue}
- 结果: PS={correct_ps:.2f}
- 计算时间: {timestamp}
- 原因: 原数据缺失，自动计算并添加
"""
                    update_data['valuation_metrics.ps_calculation_note'] = calc_note

                    print(f"[执行] 添加PS值: {correct_ps:.2f}")
                else:
                    print("[警告] valuation_metrics字段不存在，无法添加")

            elif action == "update":
                # 修正PS字段
                if 'valuation_metrics' in doc:
                    # 保存原始值
                    original_ps = doc['valuation_metrics'].get('ps_ratio')
                    update_data['valuation_metrics.ps_ratio_original'] = original_ps
                    update_data['valuation_metrics.ps_ratio_error'] = True
                    update_data['valuation_metrics.ps_ratio'] = correct_ps
                    update_data['valuation_metrics.ps_data_source'] = 'corrected'
                    update_data['valuation_metrics.ps_last_updated'] = timestamp

                    # 修正日志
                    correction_note = f"""PS修正记录:
- 原始值: {original_ps}
- 修正值: {correct_ps:.2f}
- 差异: {abs(correct_ps - original_ps):.2f}
- 修正时间: {timestamp}
- 修正原因: 数据验证发现错误
"""
                    update_data['valuation_metrics.ps_correction_note'] = correction_note

                    print(f"[执行] 修正PS值: {original_ps} -> {correct_ps:.2f}")
                else:
                    print("[警告] valuation_metrics字段不存在，无法修正")

            # 执行数据库更新
            if update_data:
                result = fundamentals_collection.update_one(
                    {'symbol': symbol},
                    {'$set': update_data}
                )

                if result.modified_count > 0:
                    print(f"[成功] 数据库更新成功! 修改了 {result.modified_count} 个文档")
                    print(f"        修改的字段数: {len(update_data)}")
                else:
                    print("[失败] 数据库更新失败（未找到匹配的文档）")

        else:
            print("【第三步】无需修正")
            print("-" * 80)
            print("数据库中的PS数据正确，无需修改")

        print()
        print("=" * 80)
        print("数据库修正完成")
        print("=" * 80)

        # 关闭连接
        mongo_client.close()

    except Exception as e:
        print(f"[错误] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
