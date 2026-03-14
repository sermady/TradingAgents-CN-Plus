# -*- coding: utf-8 -*-
"""
市场资金流向数据模块

获取A股市场的机构行为和资金流向数据，作为社交情绪分析的替代数据源：
- 龙虎榜 (Top Trader Activity / LHB)
- 北向资金 (Northbound Capital Flow / HSGT)
- 融资融券 (Margin Trading)
- 大宗交易 (Block Trades)

所有数据通过 AKShare 获取，每个数据源独立容错。
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from tradingagents.utils.logging_init import get_logger

logger = get_logger("dataflows.market_flow")


def fetch_market_flow_data(
    symbol: str,
    trade_date: str,
    lookback_days: int = 10,
) -> str:
    """
    获取指定股票的市场资金流向综合数据

    Args:
        symbol: 股票代码 (如 "000001", "600519")
        trade_date: 交易日期 (YYYY-MM-DD)
        lookback_days: 回看天数 (用于龙虎榜、大宗交易等低频数据)

    Returns:
        格式化的资金流向数据文本
    """
    # 解析日期
    try:
        end_dt = datetime.strptime(trade_date, "%Y-%m-%d")
    except ValueError:
        end_dt = datetime.strptime(trade_date, "%Y%m%d")
    start_dt = end_dt - timedelta(days=lookback_days)

    end_str = end_dt.strftime("%Y%m%d")
    start_str = start_dt.strftime("%Y%m%d")

    # 提取纯数字代码
    pure_code = symbol.replace(".", "").replace("SH", "").replace("SZ", "")
    # 去掉可能的交易所后缀
    if len(pure_code) > 6:
        pure_code = pure_code[:6]

    sections: List[str] = []
    sections.append(f"=== {pure_code} 市场资金流向数据 ===")
    sections.append(f"数据日期: {trade_date}")
    sections.append(f"回看区间: {start_dt.strftime('%Y-%m-%d')} ~ {trade_date}")
    sections.append("")

    # 独立获取每类数据，互不影响
    lhb = _fetch_lhb_data(pure_code, start_str, end_str)
    sections.append(lhb)

    north = _fetch_northbound_flow(trade_date, end_dt)
    sections.append(north)

    margin = _fetch_margin_data(pure_code, trade_date, end_dt)
    sections.append(margin)

    block = _fetch_block_trade_data(pure_code, start_str, end_str)
    sections.append(block)

    # 评估数据可用性
    available_count = sum(
        1 for s in [lhb, north, margin, block] if "暂无数据" not in s and "获取失败" not in s
    )
    sections.append(f"\n--- 数据可用性: {available_count}/4 类数据成功获取 ---")

    return "\n".join(sections)


def _fetch_lhb_data(pure_code: str, start_str: str, end_str: str) -> str:
    """获取龙虎榜数据 (机构买卖明细)"""
    try:
        import akshare as ak

        # 尝试东方财富龙虎榜详情
        df = ak.stock_lhb_detail_em(
            start_date=start_str,
            end_date=end_str,
        )

        if df is None or df.empty:
            return "📊 龙虎榜: 近期暂无龙虎榜数据 (该股未触发龙虎榜条件)\n"

        # 筛选目标股票
        code_cols = [c for c in df.columns if "代码" in c or "code" in c.lower()]
        if code_cols:
            mask = df[code_cols[0]].astype(str).str.contains(pure_code)
            stock_df = df[mask]
        else:
            stock_df = df[df.apply(lambda r: pure_code in str(r.values), axis=1)]

        if stock_df.empty:
            return "📊 龙虎榜: 近期暂无龙虎榜数据 (该股未触发龙虎榜条件)\n"

        result = "📊 龙虎榜 (近期机构/游资活动):\n"

        # 提取关键信息
        for _, row in stock_df.head(5).iterrows():
            date_val = ""
            for col in ["上榜日期", "日期", "date"]:
                if col in row.index:
                    date_val = str(row[col])[:10]
                    break

            reason = ""
            for col in ["解读", "上榜原因", "reason"]:
                if col in row.index:
                    reason = str(row[col])
                    break

            buy_amt = ""
            for col in ["买入额", "买入金额"]:
                if col in row.index:
                    try:
                        amt = float(row[col])
                        buy_amt = f"买入: {amt / 10000:.2f}万"
                    except (ValueError, TypeError):
                        pass
                    break

            sell_amt = ""
            for col in ["卖出额", "卖出金额"]:
                if col in row.index:
                    try:
                        amt = float(row[col])
                        sell_amt = f"卖出: {amt / 10000:.2f}万"
                    except (ValueError, TypeError):
                        pass
                    break

            net = ""
            for col in ["净额", "净买入额"]:
                if col in row.index:
                    try:
                        amt = float(row[col])
                        direction = "净买入" if amt > 0 else "净卖出"
                        net = f"{direction}: {abs(amt) / 10000:.2f}万"
                    except (ValueError, TypeError):
                        pass
                    break

            parts = [p for p in [date_val, reason, buy_amt, sell_amt, net] if p]
            result += f"   - {' | '.join(parts)}\n"

        result += "\n"
        return result

    except ImportError:
        return "📊 龙虎榜: AKShare未安装，无法获取\n"
    except Exception as e:
        logger.warning(f"龙虎榜数据获取失败: {e}")
        return f"📊 龙虎榜: 获取失败 ({type(e).__name__})\n"


def _fetch_northbound_flow(trade_date: str, end_dt: datetime) -> str:
    """获取北向资金流向数据 (沪深港通)"""
    try:
        import akshare as ak

        # 获取北向资金净流入数据 (市场层面)
        df = ak.stock_hsgt_north_net_flow_in_em(symbol="北上")

        if df is None or df.empty:
            return "📊 北向资金: 暂无数据\n"

        # 按日期筛选最近数据
        date_cols = [c for c in df.columns if "日期" in c or "date" in c.lower()]
        if date_cols:
            date_col = date_cols[0]
            df[date_col] = df[date_col].astype(str)
            # 取最近5个交易日
            df_sorted = df.sort_values(date_col, ascending=False).head(5)
        else:
            df_sorted = df.tail(5)

        result = "📊 北向资金 (沪深港通, 近5个交易日):\n"

        value_cols = [c for c in df_sorted.columns if "净流入" in c or "金额" in c]

        for _, row in df_sorted.iterrows():
            date_val = str(row.iloc[0])[:10] if len(row) > 0 else ""
            if value_cols:
                try:
                    flow = float(row[value_cols[0]])
                    direction = "流入" if flow > 0 else "流出"
                    result += f"   {date_val}: 北向资金净{direction} {abs(flow):.2f}亿元\n"
                except (ValueError, TypeError):
                    result += f"   {date_val}: {row[value_cols[0]]}\n"
            else:
                result += f"   {date_val}: {' | '.join(str(v) for v in row.values[:3])}\n"

        result += "\n"
        return result

    except ImportError:
        return "📊 北向资金: AKShare未安装，无法获取\n"
    except Exception as e:
        logger.warning(f"北向资金数据获取失败: {e}")
        return f"📊 北向资金: 获取失败 ({type(e).__name__})\n"


def _fetch_margin_data(pure_code: str, trade_date: str, end_dt: datetime) -> str:
    """获取融资融券数据"""
    try:
        import akshare as ak

        # 判断交易所 (6开头 = 上交所, 0/3开头 = 深交所)
        date_str = end_dt.strftime("%Y%m%d")

        result = "📊 融资融券:\n"
        found = False

        # 尝试获取个股融资融券明细
        try:
            df = ak.stock_margin_detail_sse(date=date_str)
            if df is not None and not df.empty:
                code_cols = [c for c in df.columns if "代码" in c or "code" in c.lower()]
                if code_cols:
                    mask = df[code_cols[0]].astype(str).str.contains(pure_code)
                    stock_df = df[mask]
                    if not stock_df.empty:
                        row = stock_df.iloc[0]
                        found = True
                        for col in stock_df.columns:
                            if any(kw in col for kw in ["融资余额", "融券余额", "融资买入", "融券卖出"]):
                                try:
                                    val = float(row[col])
                                    if val > 100000000:
                                        result += f"   {col}: {val / 100000000:.2f}亿元\n"
                                    elif val > 10000:
                                        result += f"   {col}: {val / 10000:.2f}万元\n"
                                    else:
                                        result += f"   {col}: {val:.2f}\n"
                                except (ValueError, TypeError):
                                    result += f"   {col}: {row[col]}\n"
        except Exception:
            pass

        if not found:
            # 尝试深交所
            try:
                df = ak.stock_margin_detail_szse(date=date_str)
                if df is not None and not df.empty:
                    code_cols = [c for c in df.columns if "代码" in c or "code" in c.lower()]
                    if code_cols:
                        mask = df[code_cols[0]].astype(str).str.contains(pure_code)
                        stock_df = df[mask]
                        if not stock_df.empty:
                            row = stock_df.iloc[0]
                            found = True
                            for col in stock_df.columns:
                                if any(kw in col for kw in ["融资余额", "融券余额", "融资买入", "融券卖出"]):
                                    try:
                                        val = float(row[col])
                                        if val > 100000000:
                                            result += f"   {col}: {val / 100000000:.2f}亿元\n"
                                        elif val > 10000:
                                            result += f"   {col}: {val / 10000:.2f}万元\n"
                                        else:
                                            result += f"   {col}: {val:.2f}\n"
                                    except (ValueError, TypeError):
                                        result += f"   {col}: {row[col]}\n"
            except Exception:
                pass

        if not found:
            result += "   暂无数据 (该股可能非融资融券标的或当日无数据)\n"

        result += "\n"
        return result

    except ImportError:
        return "📊 融资融券: AKShare未安装，无法获取\n"
    except Exception as e:
        logger.warning(f"融资融券数据获取失败: {e}")
        return f"📊 融资融券: 获取失败 ({type(e).__name__})\n"


def _fetch_block_trade_data(pure_code: str, start_str: str, end_str: str) -> str:
    """获取大宗交易数据"""
    try:
        import akshare as ak

        df = ak.stock_dzjy_mdetail(symbol=pure_code, start_date=start_str, end_date=end_str)

        if df is None or df.empty:
            return "📊 大宗交易: 近期暂无大宗交易记录\n"

        result = "📊 大宗交易 (近期记录):\n"

        for _, row in df.head(5).iterrows():
            date_val = ""
            for col in ["交易日期", "日期", "date"]:
                if col in row.index:
                    date_val = str(row[col])[:10]
                    break

            price = ""
            for col in ["成交价", "成交价格"]:
                if col in row.index:
                    try:
                        price = f"¥{float(row[col]):.2f}"
                    except (ValueError, TypeError):
                        pass
                    break

            volume = ""
            for col in ["成交量", "成交数量"]:
                if col in row.index:
                    try:
                        vol = float(row[col])
                        volume = f"{vol / 10000:.2f}万股" if vol > 10000 else f"{vol:.0f}股"
                    except (ValueError, TypeError):
                        pass
                    break

            amount = ""
            for col in ["成交额", "成交金额"]:
                if col in row.index:
                    try:
                        amt = float(row[col])
                        if amt > 100000000:
                            amount = f"{amt / 100000000:.2f}亿元"
                        elif amt > 10000:
                            amount = f"{amt / 10000:.2f}万元"
                        else:
                            amount = f"{amt:.2f}元"
                    except (ValueError, TypeError):
                        pass
                    break

            discount = ""
            for col in ["折溢率", "折价率", "溢价率"]:
                if col in row.index:
                    try:
                        disc = float(row[col])
                        discount = f"折溢率: {disc:+.2f}%"
                    except (ValueError, TypeError):
                        pass
                    break

            buyer = ""
            for col in ["买方营业部", "买入营业部"]:
                if col in row.index:
                    buyer_name = str(row[col])
                    if buyer_name and buyer_name != "nan":
                        # 截短营业部名称
                        if len(buyer_name) > 15:
                            buyer_name = buyer_name[:15] + "..."
                        buyer = f"买方: {buyer_name}"
                    break

            parts = [p for p in [date_val, price, volume, amount, discount, buyer] if p]
            result += f"   - {' | '.join(parts)}\n"

        result += "\n"
        return result

    except ImportError:
        return "📊 大宗交易: AKShare未安装，无法获取\n"
    except Exception as e:
        logger.warning(f"大宗交易数据获取失败: {e}")
        return f"📊 大宗交易: 获取失败 ({type(e).__name__})\n"
