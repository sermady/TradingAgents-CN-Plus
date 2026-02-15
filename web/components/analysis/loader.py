# -*- coding: utf-8 -*-
"""
分析结果组件 - 数据加载
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

import streamlit as st

from .base import safe_timestamp_to_datetime, get_analysis_results_dir
from .favorites import load_favorites
from .tags import load_tags

# MongoDB相关导入
try:
    from web.utils.mongodb_report_manager import MongoDBReportManager
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

logger = logging.getLogger(__name__)


def load_analysis_results(
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    stock_symbol: Optional[str] = None,
    analyst_type: Optional[str] = None,
    limit: int = 100,
    search_text: Optional[str] = None,
    tags_filter: Optional[List[str]] = None,
    favorites_only: bool = False,
) -> List[Dict[str, Any]]:
    """加载分析结果 - 优先从MongoDB加载"""
    all_results = []
    favorites = load_favorites() if favorites_only else []
    tags_data = load_tags()
    mongodb_loaded = False

    # 优先从MongoDB加载数据
    if MONGODB_AVAILABLE:
        try:
            print("🔍 [数据加载] 从MongoDB加载分析结果")
            mongodb_manager = MongoDBReportManager()
            mongodb_results = mongodb_manager.get_all_reports()
            print(f"🔍 [数据加载] MongoDB返回 {len(mongodb_results)} 个结果")

            for mongo_result in mongodb_results:
                # 转换MongoDB结果格式
                result = {
                    "analysis_id": mongo_result.get("analysis_id", ""),
                    "timestamp": mongo_result.get("timestamp", 0),
                    "stock_symbol": mongo_result.get("stock_symbol", ""),
                    "analysts": mongo_result.get("analysts", []),
                    "research_depth": mongo_result.get("research_depth", 1),
                    "status": mongo_result.get("status", "completed"),
                    "summary": mongo_result.get("summary", ""),
                    "performance": mongo_result.get("performance", {}),
                    "tags": tags_data.get(mongo_result.get("analysis_id", ""), []),
                    "is_favorite": mongo_result.get("analysis_id", "") in favorites,
                    "reports": mongo_result.get("reports", {}),
                    "source": "mongodb",  # 标记数据来源
                }
                all_results.append(result)

            mongodb_loaded = True
            print(f"✅ 从MongoDB加载了 {len(mongodb_results)} 个分析结果")

        except Exception as e:
            print(f"❌ MongoDB加载失败: {e}")
            logger.error(f"MongoDB加载失败: {e}")
            mongodb_loaded = False
    else:
        print("⚠️ MongoDB不可用，将使用文件系统数据")

    # 只有在MongoDB加载失败或不可用时才从文件系统加载
    if not mongodb_loaded:
        _load_from_filesystem(all_results, tags_data, favorites)

    # 过滤结果
    filtered_results = _filter_results(
        all_results,
        start_date=start_date,
        end_date=end_date,
        stock_symbol=stock_symbol,
        analyst_type=analyst_type,
        search_text=search_text,
        tags_filter=tags_filter,
        favorites_only=favorites_only,
    )

    # 按时间倒序排列 - 使用安全的时间戳转换函数确保类型一致
    filtered_results.sort(
        key=lambda x: safe_timestamp_to_datetime(x.get("timestamp", 0)), reverse=True
    )

    # 限制数量
    return filtered_results[:limit]


def _load_from_filesystem(
    all_results: List[Dict[str, Any]],
    tags_data: Dict[str, List[str]],
    favorites: List[str],
) -> None:
    """从文件系统加载分析结果"""
    print("🔄 [备用数据源] 从文件系统加载分析结果")

    # 首先尝试从Web界面的保存位置读取
    web_results_dir = get_analysis_results_dir()
    for result_file in web_results_dir.glob("*.json"):
        if result_file.name in ["favorites.json", "tags.json"]:
            continue

        try:
            with open(result_file, "r", encoding="utf-8") as f:
                result = json.load(f)

                # 添加标签信息
                result["tags"] = tags_data.get(result.get("analysis_id", ""), [])
                result["is_favorite"] = result.get("analysis_id", "") in favorites
                result["source"] = "file_system"  # 标记数据来源

                all_results.append(result)
        except Exception as e:
            st.warning(f"读取分析结果文件 {result_file.name} 失败: {e}")

    # 然后从实际的分析结果保存位置读取
    project_results_dir = (
        Path(__file__).parent.parent.parent
        / "data"
        / "analysis_results"
        / "detailed"
    )

    if project_results_dir.exists():
        _load_from_detailed_directory(project_results_dir, all_results, tags_data, favorites)

    print(f"🔄 [备用数据源] 从文件系统加载了 {len(all_results)} 个分析结果")


def _load_from_detailed_directory(
    project_results_dir: Path,
    all_results: List[Dict[str, Any]],
    tags_data: Dict[str, List[str]],
    favorites: List[str],
) -> None:
    """从详细结果目录加载"""
    # 遍历股票代码目录
    for stock_dir in project_results_dir.iterdir():
        if not stock_dir.is_dir():
            continue

        stock_code = stock_dir.name

        # 遍历日期目录
        for date_dir in stock_dir.iterdir():
            if not date_dir.is_dir():
                continue

            date_str = date_dir.name
            reports_dir = date_dir / "reports"

            if not reports_dir.exists():
                continue

            # 读取所有报告文件
            reports, summary_content = _read_reports(reports_dir)

            if reports:
                # 解析日期
                try:
                    analysis_date = datetime.strptime(date_str, "%Y-%m-%d")
                    timestamp = analysis_date.timestamp()
                except:
                    timestamp = datetime.now().timestamp()

                # 创建分析结果条目
                analysis_id = f"{stock_code}_{date_str}_{int(timestamp)}"

                # 尝试从元数据文件中读取真实的研究深度和分析师信息
                research_depth, analysts = _read_metadata(date_dir, len(reports))

                result = {
                    "analysis_id": analysis_id,
                    "timestamp": timestamp,
                    "stock_symbol": stock_code,
                    "analysts": analysts,
                    "research_depth": research_depth,
                    "status": "completed",
                    "summary": summary_content,
                    "performance": {},
                    "tags": tags_data.get(analysis_id, []),
                    "is_favorite": analysis_id in favorites,
                    "reports": reports,  # 保存所有报告内容
                    "source": "file_system",  # 标记数据来源
                }

                all_results.append(result)


def _read_reports(reports_dir: Path) -> tuple[Dict[str, str], str]:
    """读取报告文件"""
    reports = {}
    summary_content = ""

    for report_file in reports_dir.glob("*.md"):
        try:
            with open(report_file, "r", encoding="utf-8") as f:
                content = f.read()
                report_name = report_file.stem
                reports[report_name] = content

                # 如果是最终决策报告，提取摘要
                if report_name == "final_trade_decision":
                    # 提取前200个字符作为摘要
                    summary_content = (
                        content[:200]
                        .replace("#", "")
                        .replace("*", "")
                        .strip()
                    )
                    if len(content) > 200:
                        summary_content += "..."
        except Exception:
            continue

    return reports, summary_content


def _read_metadata(date_dir: Path, reports_count: int) -> tuple[int, List[str]]:
    """读取元数据"""
    research_depth = 1
    analysts = ["market", "fundamentals", "trader"]  # 默认值

    metadata_file = date_dir / "analysis_metadata.json"
    if metadata_file.exists():
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
                research_depth = metadata.get("research_depth", 1)
                analysts = metadata.get("analysts", analysts)
        except Exception:
            # 如果读取元数据失败，使用推断逻辑
            if reports_count >= 5:
                research_depth = 3
            elif reports_count >= 3:
                research_depth = 2
    else:
        # 如果没有元数据文件，使用推断逻辑
        if reports_count >= 5:
            research_depth = 3
        elif reports_count >= 3:
            research_depth = 2

    return research_depth, analysts


def _filter_results(
    all_results: List[Dict[str, Any]],
    start_date: Optional[datetime.date] = None,
    end_date: Optional[datetime.date] = None,
    stock_symbol: Optional[str] = None,
    analyst_type: Optional[str] = None,
    search_text: Optional[str] = None,
    tags_filter: Optional[List[str]] = None,
    favorites_only: bool = False,
) -> List[Dict[str, Any]]:
    """过滤分析结果"""
    filtered_results = []

    for result in all_results:
        # 收藏过滤
        if favorites_only and not result.get("is_favorite", False):
            continue

        # 时间过滤
        if start_date or end_date:
            result_time = safe_timestamp_to_datetime(result.get("timestamp", 0))
            if start_date and result_time.date() < start_date:
                continue
            if end_date and result_time.date() > end_date:
                continue

        # 股票代码过滤
        if (
            stock_symbol
            and stock_symbol.upper() not in result.get("stock_symbol", "").upper()
        ):
            continue

        # 分析师类型过滤
        if analyst_type and analyst_type not in result.get("analysts", []):
            continue

        # 文本搜索过滤
        if search_text:
            search_text_lower = search_text.lower()
            searchable_text = f"{result.get('stock_symbol', '')} {result.get('summary', '')} {' '.join(result.get('analysts', []))}".lower()
            if search_text_lower not in searchable_text:
                continue

        # 标签过滤
        if tags_filter:
            result_tags = result.get("tags", [])
            if not any(tag in result_tags for tag in tags_filter):
                continue

        filtered_results.append(result)

    return filtered_results
