#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""检查 600765 (中航重机) 的完整分析结果"""

import sys
import io

# 设置标准输出为 UTF-8 编码
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from pymongo import MongoClient
from datetime import datetime
import json


def format_report(report):
    """格式化报告内容，使其更易读"""
    if isinstance(report, dict):
        if "content" in report:
            return report["content"]
        elif "summary" in report:
            return report["summary"]
        else:
            return json.dumps(report, ensure_ascii=False, indent=2)
    elif isinstance(report, str):
        return report
    else:
        return str(report)


def check_analysis_results():
    """查询并显示分析结果"""
    # 连接数据库
    try:
        import os
        from dotenv import load_dotenv

        # 加载环境变量
        load_dotenv()

        # 本地环境直接使用 localhost，Docker 环境会通过环境变量使用 mongodb 服务名
        # 先尝试带认证的连接（Docker环境）
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
            print(f"📡 连接数据库 (带认证): {mongodb_host}:{mongodb_port}")
        else:
            connection_string = f"mongodb://{mongodb_host}:{mongodb_port}/"
            print(f"📡 连接数据库 (无认证): {mongodb_host}:{mongodb_port}")

        client = MongoClient(connection_string)
        db = client[mongodb_database]

        # 查询任务 ID
        task_id = "befa202e-ed38-4de7-8649-5a487cbe7061"
        stock_code = "600765"

        print(f"🔍 正在查询分析结果...")
        print(f"📌 任务 ID: {task_id}")
        print(f"📌 股票代码: {stock_code}")
        print("=" * 80)

        # 从 analysis_results 集合查询
        result = db.analysis_results.find_one({"analysis_id": task_id})

        if result:
            print(f"\n✅ 找到分析结果\n")

            # 基本信息
            print(f"📋 基本信息")
            print(f"  股票代码: {result.get('stock_code')}")
            print(f"  股票名称: {result.get('stock_name', 'N/A')}")
            print(f"  分析日期: {result.get('analysis_date', 'N/A')}")
            print(f"  分析时间: {result.get('created_at', 'N/A')}")
            print(f"  分析师: {result.get('analysts', [])}")
            print(f"  状态: {result.get('status', 'N/A')}")

            # 检查报告数量
            reports = result.get("reports", {})
            print(f"\n📊 报告概览")
            print(f"  报告总数: {len(reports)}")
            print(f"  报告类型: {', '.join(reports.keys())}")

            # 详细报告内容
            print(f"\n" + "=" * 80)
            print(f"📄 详细报告内容")
            print("=" * 80)

            for report_name, report_data in reports.items():
                print(f"\n{'=' * 80}")
                print(f"🔸 {report_name.upper()} 分析报告")
                print(f"{'=' * 80}\n")

                content = format_report(report_data)

                # 如果内容太长，分页显示
                if len(content) > 2000:
                    lines = content.split("\n")
                    print(f"  (报告长度: {len(lines)} 行)")
                    print("\n前 50 行内容:\n")
                    for i, line in enumerate(lines[:50], 1):
                        print(f"{i:3d}. {line}")

                    if len(lines) > 50:
                        print(f"\n... (还有 {len(lines) - 50} 行)")
                        print("\n后 20 行内容:\n")
                        for i, line in enumerate(lines[-20:], len(lines) - 19):
                            print(f"{i:3d}. {line}")
                else:
                    print(content)

                print("\n")

            # 保存完整报告到文件
            output_file = "reports/600765_full_analysis.txt"
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write("=" * 80 + "\n")
                    f.write("600765 (中航重机) 完整分析报告\n")
                    f.write(f"任务 ID: {task_id}\n")
                    f.write(f"生成时间: {result.get('created_at', 'N/A')}\n")
                    f.write("=" * 80 + "\n\n")

                    for report_name, report_data in reports.items():
                        f.write("=" * 80 + "\n")
                        f.write(f"{report_name.upper()} 分析报告\n")
                        f.write("=" * 80 + "\n\n")
                        f.write(format_report(report_data))
                        f.write("\n\n")

                print("=" * 80)
                print(f"💾 完整报告已保存到: {output_file}")
                print("=" * 80)

            except Exception as e:
                print(f"⚠️  保存报告时出错: {e}")

        else:
            print(f"\n❌ 未找到分析结果: {task_id}")
            print(f"📌 请确认任务 ID 是否正确，或检查数据库连接")

            # 显示所有可用的分析结果（仅显示最近的 10 条）
            print(f"\n📋 查询所有可用的分析结果（最近 10 条）:")
            all_results = (
                db.analysis_results.find({"stock_code": stock_code})
                .sort("created_at", -1)
                .limit(10)
            )

            print("\n可用的分析任务:")
            for r in all_results:
                print(f"  - 任务 ID: {r.get('analysis_id')}")
                print(f"    分析日期: {r.get('analysis_date')}")
                print(f"    状态: {r.get('status', 'N/A')}")
                print()

    except Exception as e:
        print(f"❌ 数据库连接错误: {e}")
        print(f"💡 请确保 MongoDB 服务正在运行")


if __name__ == "__main__":
    check_analysis_results()
