#!/usr/bin/env python
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
"""查询 600765 的分析报告"""

import sys
import io

# 设置标准输出为 UTF-8 编码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from pymongo import MongoClient
from dotenv import load_dotenv
import os
import json

# 加载环境变量
load_dotenv()

# 连接数据库
mongodb_username = os.getenv("MONGODB_USERNAME", "")
mongodb_password = os.getenv("MONGODB_PASSWORD", "")
mongodb_port = os.getenv("MONGODB_PORT", "27017")
mongodb_database = os.getenv("MONGODB_DATABASE", "tradingagents")
mongodb_auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")

# 本地环境使用 localhost
mongodb_host = "localhost"

# 如果有认证信息，使用带认证的连接
if mongodb_username and mongodb_password:
    connection_string = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_host}:{mongodb_port}/?authSource={mongodb_auth_source}"
else:
    connection_string = f"mongodb://{mongodb_host}:{mongodb_port}/"

client = MongoClient(connection_string)
db = client[mongodb_database]

print(f"📡 连接数据库: {mongodb_host}:{mongodb_port}")
print(f"📦 数据库名称: {mongodb_database}")
print("=" * 80)

# 查询 analysis_reports 集合中的 600765 分析报告
print(f"\n🔍 查找 600765 的分析报告...")
print("=" * 80)

# 方法1: 按 stock_code 查询
reports = list(
    db.analysis_reports.find({"stock_code": "600765"}).sort("created_at", -1)
)

if not reports:
    print("❌ 未找到 stock_code='600765' 的分析报告")

    # 方法2: 按 symbol 查询
    reports = list(
        db.analysis_reports.find({"symbol": "600765"}).sort("created_at", -1)
    )
    if reports:
        print(f"✅ 找到 {len(reports)} 条分析报告 (使用 symbol='600765')")
    else:
        print("❌ 未找到 symbol='600765' 的分析报告")

        # 方法3: 显示所有分析报告，让用户选择
        print(f"\n📋 显示所有分析报告:")
        all_reports = list(db.analysis_reports.find().sort("created_at", -1).limit(10))
        for i, report in enumerate(all_reports, 1):
            print(f"\n  [{i}] 分析报告")
            for key, value in report.items():
                if key in [
                    "stock_code",
                    "symbol",
                    "stock_name",
                    "status",
                    "created_at",
                    "analysis_date",
                ]:
                    print(f"      {key}: {value}")

        if all_reports:
            print(f"\n💡 提示: 请选择要查看的分析报告编号")
            # 默认查看最新的报告
            reports = [all_reports[0]]
            print(f"📌 默认显示最新的分析报告")
else:
    print(f"✅ 找到 {len(reports)} 条分析报告 (使用 stock_code='600765')")

# 显示分析报告内容
if reports:
    report = reports[0]  # 获取最新的一条

    print(f"\n" + "=" * 80)
    print(f"📊 分析报告详情")
    print("=" * 80)

    print(f"\n📋 基本信息:")
    print(f"  股票代码: {report.get('stock_code', 'N/A')}")
    print(f"  股票名称: {report.get('stock_name', 'N/A')}")
    print(f"  分析日期: {report.get('analysis_date', 'N/A')}")
    print(f"  创建时间: {report.get('created_at', 'N/A')}")
    print(f"  状态: {report.get('status', 'N/A')}")
    print(f"  分析师: {report.get('analysts', [])}")

    # 检查报告内容
    print(f"\n📄 报告内容字段:")
    for key in report.keys():
        if key not in [
            "_id",
            "stock_code",
            "stock_name",
            "analysis_date",
            "created_at",
            "status",
            "analysts",
        ]:
            print(f"  - {key}: {type(report[key]).__name__}")

    # 检查是否有 content 或 reports 字段
    if "content" in report:
        content = report["content"]
        print(f"\n📝 完整报告内容 (长度: {len(content)} 字符)")
        print("=" * 80)
        print(content)
        print("=" * 80)

    elif "reports" in report:
        reports_dict = report["reports"]
        print(f"\n📝 包含 {len(reports_dict)} 个子报告")

        for report_name, report_data in reports_dict.items():
            print(f"\n{'=' * 80}")
            print(f"🔸 {report_name.upper()} 分析报告")
            print(f"{'=' * 80}\n")

            if isinstance(report_data, dict):
                if "content" in report_data:
                    content = report_data["content"]
                    print(content)
                elif "summary" in report_data:
                    print(report_data["summary"])
                else:
                    print(json.dumps(report_data, ensure_ascii=False, indent=2))
            elif isinstance(report_data, str):
                print(report_data)

    else:
        print(f"\n⚠️  未找到标准的报告内容字段 (content 或 reports)")
        print(f"\n📄 完整数据结构:")
        print(json.dumps(report, ensure_ascii=False, indent=2, default=str))

    # 保存报告到文件
    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)
    output_file = f"{output_dir}/600765_analysis_report.txt"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("600765 (中航重机) 分析报告\n")
            f.write(f"生成时间: {report.get('created_at', 'N/A')}\n")
            f.write("=" * 80 + "\n\n")

            # 基本信息
            f.write("📋 基本信息\n")
            f.write("-" * 80 + "\n")
            f.write(f"股票代码: {report.get('stock_code', 'N/A')}\n")
            f.write(f"股票名称: {report.get('stock_name', 'N/A')}\n")
            f.write(f"分析日期: {report.get('analysis_date', 'N/A')}\n")
            f.write(f"状态: {report.get('status', 'N/A')}\n")
            f.write(f"分析师: {report.get('analysts', [])}\n\n")

            # 报告内容
            if "content" in report:
                f.write("📄 分析报告\n")
                f.write("-" * 80 + "\n")
                f.write(report["content"])
            elif "reports" in report:
                for report_name, report_data in report["reports"].items():
                    f.write(f"\n{'=' * 80}\n")
                    f.write(f"{report_name.upper()} 分析报告\n")
                    f.write(f"{'=' * 80}\n\n")

                    if isinstance(report_data, dict):
                        if "content" in report_data:
                            f.write(report_data["content"])
                        elif "summary" in report_data:
                            f.write(report_data["summary"])
                        else:
                            f.write(
                                json.dumps(report_data, ensure_ascii=False, indent=2)
                            )
                    elif isinstance(report_data, str):
                        f.write(report_data)

        print(f"\n" + "=" * 80)
        print(f"💾 报告已保存到: {output_file}")
        print("=" * 80)

    except Exception as e:
        print(f"⚠️  保存报告时出错: {e}")

else:
    print("\n💡 建议: 请确认股票代码是否正确，或检查数据库中是否有分析报告")
