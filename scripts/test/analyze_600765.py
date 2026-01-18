# -*- coding: utf-8 -*-
"""
自动分析股票 600765 (中航重机)
"""

import os
import sys
import asyncio
import io

# Windows 控制台编码设置
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 禁用 emoji 日志
os.environ["DISABLE_EMOJI"] = "1"

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.utils.logging_manager import get_logger

logger = get_logger("analyze_600765")


async def analyze_stock():
    """分析股票 600765"""

    print("=" * 80)
    print("股票分析 - 600765 (中航重机)")
    print("=" * 80)

    # 配置参数
    symbol = "600765"
    config = DEFAULT_CONFIG.copy()

    # 根据环境变量配置 LLM
    config["llm_provider"] = os.getenv("DEFAULT_LLM_PROVIDER", "deepseek")
    config["model_name"] = os.getenv("DEFAULT_MODEL", "deepseek-chat")
    config["deep_think_model"] = os.getenv("DEFAULT_DEEP_MODEL", "deepseek-chat")

    print(f"\n[配置] 分析配置:")
    print(f"  股票代码: {symbol}")
    print(f"  LLM 提供商: {config['llm_provider']}")
    print(f"  通用模型: {config['model_name']}")
    print(f"  深度模型: {config['deep_think_model']}")
    print(f"  研究深度: {config.get('research_depth', 1)}")

    # 创建分析图
    print("\n[初始化] 正在初始化分析系统...")
    try:
        graph = TradingAgentsGraph(config=config)
        print("[成功] 分析系统初始化成功")
    except Exception as e:
        print(f"[错误] 分析系统初始化失败: {e}")
        import traceback

        traceback.print_exc()
        return

    # 执行分析
    print(f"\n[开始] 开始分析股票 {symbol}...")
    print("[提示] 这可能需要几分钟时间，请耐心等待...")
    print("-" * 80)

    try:
        # 运行分析（使用 propagate 方法）
        from datetime import datetime

        trade_date = datetime.now().strftime("%Y-%m-%d")

        result = graph.propagate(
            company_name=symbol,
            trade_date=trade_date,
            progress_callback=None,  # 简化，不使用进度回调
        )

        print("-" * 80)
        print("\n[成功] 分析完成！\n")

        # 显示分析结果摘要
        if result:
            print("=" * 80)
            print("分析结果摘要")
            print("=" * 80)
            # 打印 result 的键
            print(f"结果包含的键: {list(result.keys())}")
            print("=" * 80)

        # 保存分析结果
        if result:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "results",
                "analysis_600765",
            )
            os.makedirs(output_dir, exist_ok=True)

            output_file = os.path.join(
                output_dir, f"report_{symbol}_{os.environ.get('USERNAME', 'user')}.md"
            )

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# 股票分析报告 - {symbol} (中航重机)\n\n")
                f.write(f"分析时间: {os.path.basename(__file__)}\n\n")
                f.write("---\n\n")

                if "market_report" in result:
                    f.write("## 市场分析\n\n")
                    f.write(result["market_report"])
                    f.write("\n\n")

                if "fundamentals_report" in result:
                    f.write("## 基本面分析\n\n")
                    f.write(result["fundamentals_report"])
                    f.write("\n\n")

                if "social_report" in result:
                    f.write("## 社交媒体分析\n\n")
                    f.write(result["social_report"])
                    f.write("\n\n")

                if "news_report" in result:
                    f.write("## 新闻分析\n\n")
                    f.write(result["news_report"])
                    f.write("\n\n")

                if "final_report" in result:
                    f.write("## 综合报告\n\n")
                    f.write(result["final_report"])
                    f.write("\n\n")

            print(f"\n[保存] 分析报告已保存到: {output_file}")

        return result

    except Exception as e:
        print(f"\n[错误] 分析过程中出错: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    # 运行分析
    result = asyncio.run(analyze_stock())

    if result:
        print("\n[成功] 分析成功完成！")
        sys.exit(0)
    else:
        print("\n[警告] 分析未完成，请检查错误信息")
        sys.exit(1)
