# -*- coding: utf-8 -*-
"""P2-3: 技术指标信号预计算摘要

从结构化数据中确定性地计算技术信号 (不依赖 LLM 推理):
- 趋势信号: MA 排列、价格相对 MA 位置
- 动量信号: RSI 超买超卖、KDJ 金叉死叉、MACD 状态
- 波动信号: 布林带位置、ATR 水平
- 量价信号: OBV 方向、成交量状态

输出简洁的文本摘要, 注入分析师 prompt 前部, 减少 LLM 解读负担。
"""

from typing import Any, Dict, List, Optional


def compute_technical_signals(data: Dict[str, Any]) -> Dict[str, Any]:
    """从结构化市场数据计算确定性技术信号

    Args:
        data: _parse_market_data() 返回的 Dict, 包含
              current_price, MA5/10/20/60, RSI, RSI14, MACD_DIF/DEA/MACD,
              KDJ_K/D/J, ATR14, WR14, CCI14, OBV, BOLL_UPPER/MID/LOWER 等

    Returns:
        Dict 包含各类信号及文本摘要
    """
    if not data:
        return {"signals": [], "summary": "", "trend": "unknown"}

    signals: List[str] = []
    trend_score = 0  # 正=看多, 负=看空, 用于综合趋势判断

    price = _get_float(data, "current_price")

    # ==================== 趋势信号 ====================

    ma5 = _get_float(data, "MA5")
    ma10 = _get_float(data, "MA10")
    ma20 = _get_float(data, "MA20")
    ma60 = _get_float(data, "MA60")

    # MA 排列: 按固定顺序取实际存在的 MA, 检查值是否单调递减(多头)或递增(空头)
    _ma_order = ["MA5", "MA10", "MA20", "MA60"]
    ma_values = {k: v for k, v in {"MA5": ma5, "MA10": ma10, "MA20": ma20, "MA60": ma60}.items() if v is not None}
    if len(ma_values) >= 3:
        available_keys = [k for k in _ma_order if k in ma_values]
        values_in_order = [ma_values[k] for k in available_keys]
        if values_in_order == sorted(values_in_order, reverse=True):
            signals.append("MA多头排列 (短期均线在上)")
            trend_score += 2
        elif values_in_order == sorted(values_in_order):
            signals.append("MA空头排列 (短期均线在下)")
            trend_score -= 2

    # 价格相对 MA 位置
    if price is not None and ma20 is not None:
        pct_above_ma20 = (price - ma20) / ma20 * 100
        if pct_above_ma20 > 5:
            signals.append(f"价格高于MA20 {pct_above_ma20:.1f}%, 短期偏强")
            trend_score += 1
        elif pct_above_ma20 < -5:
            signals.append(f"价格低于MA20 {pct_above_ma20:.1f}%, 短期偏弱")
            trend_score -= 1

    if price is not None and ma60 is not None:
        if price > ma60:
            trend_score += 1
        else:
            trend_score -= 1

    # ==================== 动量信号 ====================

    # RSI
    rsi14 = _get_float(data, "RSI14")
    if rsi14 is None:
        rsi14 = _get_float(data, "RSI")
    if rsi14 is not None:
        if rsi14 > 80:
            signals.append(f"RSI={rsi14:.1f}, 严重超买")
            trend_score -= 1
        elif rsi14 > 70:
            signals.append(f"RSI={rsi14:.1f}, 超买区间")
            trend_score -= 0.5
        elif rsi14 < 20:
            signals.append(f"RSI={rsi14:.1f}, 严重超卖")
            trend_score += 1
        elif rsi14 < 30:
            signals.append(f"RSI={rsi14:.1f}, 超卖区间")
            trend_score += 0.5

    # MACD
    macd_dif = _get_float(data, "MACD_DIF")
    macd_dea = _get_float(data, "MACD_DEA")
    macd_val = _get_float(data, "MACD")
    if macd_dif is not None and macd_dea is not None:
        if macd_dif > macd_dea and macd_dif > 0:
            signals.append("MACD: DIF > DEA 且在零轴上方, 多头强势")
            trend_score += 1.5
        elif macd_dif > macd_dea and macd_dif <= 0:
            signals.append("MACD: DIF > DEA, 零轴下方偏多")
            trend_score += 0.5
        elif macd_dif < macd_dea and macd_dif < 0:
            signals.append("MACD: DIF < DEA 且在零轴下方, 空头强势")
            trend_score -= 1.5
        elif macd_dif < macd_dea and macd_dif >= 0:
            signals.append("MACD: DIF < DEA, 零轴上方偏空")
            trend_score -= 0.5

    # KDJ
    kdj_k = _get_float(data, "KDJ_K")
    kdj_d = _get_float(data, "KDJ_D")
    kdj_j = _get_float(data, "KDJ_J")
    if kdj_k is not None and kdj_d is not None:
        if kdj_k > kdj_d and kdj_k > 80:
            signals.append(f"KDJ: K({kdj_k:.0f})>D({kdj_d:.0f}), 高位偏多, 注意超买回落风险")
        elif kdj_k > kdj_d and kdj_k < 20:
            signals.append(f"KDJ: K({kdj_k:.0f})>D({kdj_d:.0f}), 低位偏多, 看涨信号")
            trend_score += 1
        elif kdj_k < kdj_d and kdj_k > 80:
            signals.append(f"KDJ: K({kdj_k:.0f})<D({kdj_d:.0f}), 高位偏空, 看跌信号")
            trend_score -= 1
        elif kdj_k < kdj_d and kdj_k < 20:
            signals.append(f"KDJ: K({kdj_k:.0f})<D({kdj_d:.0f}), 低位偏空, 注意超卖反弹")

    if kdj_j is not None:
        if kdj_j > 100:
            signals.append(f"KDJ-J={kdj_j:.0f}, 严重超买")
        elif kdj_j < 0:
            signals.append(f"KDJ-J={kdj_j:.0f}, 严重超卖")

    # Williams %R
    wr14 = _get_float(data, "WR14")
    if wr14 is not None:
        if wr14 > -20:
            signals.append(f"Williams %R={wr14:.1f}, 超买区间")
        elif wr14 < -80:
            signals.append(f"Williams %R={wr14:.1f}, 超卖区间")

    # CCI
    cci14 = _get_float(data, "CCI14")
    if cci14 is not None:
        if cci14 > 200:
            signals.append(f"CCI={cci14:.0f}, 极度超买")
            trend_score -= 0.5
        elif cci14 > 100:
            signals.append(f"CCI={cci14:.0f}, 超买区间")
        elif cci14 < -200:
            signals.append(f"CCI={cci14:.0f}, 极度超卖")
            trend_score += 0.5
        elif cci14 < -100:
            signals.append(f"CCI={cci14:.0f}, 超卖区间")

    # ==================== 波动信号 ====================

    boll_upper = _get_float(data, "BOLL_UPPER")
    boll_mid = _get_float(data, "BOLL_MID")
    boll_lower = _get_float(data, "BOLL_LOWER")
    if all(v is not None for v in [price, boll_upper, boll_lower, boll_mid]):
        boll_width = (boll_upper - boll_lower) / boll_mid * 100 if boll_mid > 0 else 0
        if price >= boll_upper:
            signals.append(f"价格触及布林带上轨, 短期偏强/超买")
        elif price <= boll_lower:
            signals.append(f"价格触及布林带下轨, 短期偏弱/超卖")

        if boll_width < 5:
            signals.append(f"布林带收口 (宽度{boll_width:.1f}%), 可能蓄势突破")

    atr14 = _get_float(data, "ATR14")
    if atr14 is not None and price is not None and price > 0:
        atr_pct = atr14 / price * 100
        if atr_pct > 5:
            signals.append(f"ATR/价格={atr_pct:.1f}%, 高波动状态")
        elif atr_pct < 1:
            signals.append(f"ATR/价格={atr_pct:.1f}%, 低波动状态")

    # ==================== 综合趋势判断 ====================

    if trend_score >= 3:
        trend = "strong_bullish"
        trend_text = "强势看多"
    elif trend_score >= 1:
        trend = "bullish"
        trend_text = "偏多"
    elif trend_score <= -3:
        trend = "strong_bearish"
        trend_text = "强势看空"
    elif trend_score <= -1:
        trend = "bearish"
        trend_text = "偏空"
    else:
        trend = "neutral"
        trend_text = "中性震荡"

    # ==================== 多指标交叉验证 ====================

    cross_signals = _cross_validate(signals, trend_score, rsi14, kdj_k, macd_dif, macd_dea)
    if cross_signals:
        signals.extend(cross_signals)

    # 构建摘要文本
    summary = _build_summary(signals, trend_text, trend_score)

    return {
        "signals": signals,
        "summary": summary,
        "trend": trend,
        "trend_text": trend_text,
        "trend_score": trend_score,
    }


def format_signals_for_prompt(signal_result: Dict[str, Any]) -> str:
    """将信号结果格式化为可注入 prompt 前部的文本块"""
    summary = signal_result.get("summary", "")
    if not summary:
        return ""

    return f"""
=== 技术信号预计算摘要 (代码确定性计算, 非LLM推理) ===
{summary}
=== 请基于以上信号和原始数据进行深入分析 ===
""".strip()


# ==================== 私有辅助 ====================


def _get_float(data: Dict[str, Any], key: str) -> Optional[float]:
    """安全获取浮点值, 过滤 NaN 和 Inf"""
    val = data.get(key)
    if val is None:
        return None
    try:
        f = float(val)
        if f != f or f == float("inf") or f == float("-inf"):
            return None
        return f
    except (ValueError, TypeError):
        return None


def _cross_validate(
    existing_signals: List[str],
    trend_score: float,
    rsi: Optional[float],
    kdj_k: Optional[float],
    macd_dif: Optional[float],
    macd_dea: Optional[float],
) -> List[str]:
    """多指标交叉验证, 识别高置信度信号"""
    cross = []

    # RSI超买 + KDJ高位 = 强卖出共振
    if rsi is not None and rsi > 70 and kdj_k is not None and kdj_k > 80:
        cross.append("[共振] RSI超买 + KDJ高位 → 短期回调概率高")

    # RSI超卖 + KDJ低位 = 强买入共振
    if rsi is not None and rsi < 30 and kdj_k is not None and kdj_k < 20:
        cross.append("[共振] RSI超卖 + KDJ低位 → 超卖反弹概率高")

    # MACD偏多 + 多头排列 = 确认多头
    has_macd_bullish = (
        macd_dif is not None
        and macd_dea is not None
        and macd_dif > macd_dea
    )
    if has_macd_bullish and trend_score >= 3:
        cross.append("[共振] MACD偏多 + MA多头排列 → 趋势确认看多")

    # MACD偏空 + 空头排列 = 确认空头
    has_macd_bearish = (
        macd_dif is not None
        and macd_dea is not None
        and macd_dif < macd_dea
    )
    if has_macd_bearish and trend_score <= -3:
        cross.append("[共振] MACD偏空 + MA空头排列 → 趋势确认看空")

    return cross


def _build_summary(signals: List[str], trend_text: str, trend_score: float) -> str:
    """构建简洁的摘要文本"""
    if not signals:
        return "当前数据不足, 无法生成技术信号摘要。"

    lines = [f"综合研判: {trend_text} (信号强度: {abs(trend_score):.1f}/8)"]

    # 按类型分组
    cross = [s for s in signals if s.startswith("[共振]")]
    normal = [s for s in signals if not s.startswith("[共振]")]

    if cross:
        lines.append("")
        lines.append("关键共振信号:")
        for s in cross:
            lines.append(f"  {s}")

    if normal:
        lines.append("")
        lines.append("单项信号:")
        for s in normal:
            lines.append(f"  - {s}")

    return "\n".join(lines)
