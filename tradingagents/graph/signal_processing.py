# -*- coding: utf-8 -*-
# TradingAgents/graph/signal_processing.py
"""
信号处理器 (P0-2 重构)

优先使用 LLM 结构化输出 (with_structured_output)，
回退到 JSON regex 提取，最终回退到文本 regex。
"""

import json
import re

from langchain_openai import ChatOpenAI

from tradingagents.graph.trading_decision_schema import TradingDecision, TradeAction
from tradingagents.utils.logging_init import get_logger
from tradingagents.utils.tool_logging import log_graph_module

logger = get_logger("graph.signal_processing")


class SignalProcessor:
    """Processes trading signals to extract actionable decisions."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Initialize with an LLM for processing."""
        self.quick_thinking_llm = quick_thinking_llm

    @log_graph_module("signal_processing")
    def process_signal(
        self,
        full_signal: str,
        stock_symbol: str = None,
        structured_data: dict = None,
    ) -> dict:
        """
        Process a full trading signal to extract structured decision information.

        Args:
            full_signal: Complete trading signal text
            stock_symbol: Stock symbol to determine currency type
            structured_data: P0-1 结构化数据 (market_data_structured 等)，
                             用于提供精确的当前价格

        Returns:
            Dictionary containing extracted decision information
        """
        # 验证输入
        if not full_signal or not isinstance(full_signal, str) or len(full_signal.strip()) == 0:
            logger.error(f"❌ [SignalProcessor] 输入信号为空或无效")
            return self._get_default_decision()

        full_signal = full_signal.strip()

        # 检测股票类型和货币
        from tradingagents.utils.stock_utils import StockUtils
        market_info = StockUtils.get_market_info(stock_symbol)
        is_china = market_info['is_china']
        currency = market_info['currency_name']
        currency_symbol = market_info['currency_symbol']

        logger.info(
            f"🔍 [SignalProcessor] 处理信号: 股票={stock_symbol}, "
            f"市场={market_info['market_name']}, 货币={currency}",
            extra={'stock_symbol': stock_symbol, 'market': market_info['market_name']},
        )

        # P0-1: 从结构化数据获取精确当前价格
        current_price = self._get_current_price_from_structured(structured_data)
        if current_price:
            logger.info(f"📊 [SignalProcessor] 使用结构化数据当前价: {currency_symbol}{current_price}")

        # 策略 1: 尝试 LLM 结构化输出
        result = self._try_structured_output(full_signal, stock_symbol, currency, currency_symbol)
        if result:
            # 用结构化数据验证和增强结果
            result = self._enhance_with_structured_data(result, current_price, is_china)
            logger.info(
                f"✅ [SignalProcessor] 结构化输出成功: {result}",
                extra={'action': result['action'], 'target_price': result['target_price']},
            )
            return result

        # 策略 2: 回退到 JSON regex 提取
        result = self._try_json_extraction(full_signal, currency, currency_symbol)
        if result:
            result = self._enhance_with_structured_data(result, current_price, is_china)
            logger.info(f"✅ [SignalProcessor] JSON提取成功: {result}")
            return result

        # 策略 3: 回退到简单文本 regex
        result = self._extract_simple_decision(full_signal)
        result = self._enhance_with_structured_data(result, current_price, is_china)
        logger.warning(f"⚠️ [SignalProcessor] 回退到简单提取: {result}")
        return result

    def _get_current_price_from_structured(self, structured_data: dict) -> float | None:
        """从 P0-1 结构化数据中提取当前价格"""
        if not structured_data:
            return None

        # 优先从 market_data_structured 获取
        market = structured_data.get("market_data_structured", {})
        if market and market.get("current_price"):
            return float(market["current_price"])

        # 回退到 china_market_data_structured
        china = structured_data.get("china_market_data_structured", {})
        if china and china.get("current_price"):
            return float(china["current_price"])

        return None

    def _try_structured_output(
        self, full_signal: str, stock_symbol: str, currency: str, currency_symbol: str
    ) -> dict | None:
        """尝试使用 LLM with_structured_output"""
        try:
            structured_llm = self.quick_thinking_llm.with_structured_output(TradingDecision)

            messages = [
                (
                    "system",
                    f"""您是一位专业的金融分析助手。请从交易分析报告中提取结构化的投资决策。

要求：
- action: 必须是 "买入"、"持有" 或 "卖出"
- target_price: 具体的{currency}价格数字
- confidence: 0-1之间的置信度
- risk_score: 0-1之间的风险评分
- reasoning: 简洁的中文决策理由

股票 {stock_symbol or '未知'} 使用 {currency}({currency_symbol}) 计价。""",
                ),
                ("human", full_signal),
            ]

            decision = structured_llm.invoke(messages)
            return decision.to_signal_dict()

        except Exception as e:
            logger.debug(f"结构化输出失败，回退到JSON提取: {e}")
            return None

    def _try_json_extraction(
        self, full_signal: str, currency: str, currency_symbol: str
    ) -> dict | None:
        """回退策略: 让 LLM 返回 JSON，用 regex 提取"""
        try:
            messages = [
                (
                    "system",
                    f"""请从分析报告中提取投资决策，以JSON格式返回：
{{
    "action": "买入/持有/卖出",
    "target_price": 数字({currency}价格),
    "confidence": 0-1之间,
    "risk_score": 0-1之间,
    "reasoning": "决策理由"
}}
action 必须是"买入"、"持有"或"卖出"之一。""",
                ),
                ("human", full_signal),
            ]

            response = self.quick_thinking_llm.invoke(messages).content

            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if not json_match:
                return None

            data = json.loads(json_match.group())

            # 标准化 action
            action = data.get('action', '持有')
            action_map = {
                'buy': '买入', 'hold': '持有', 'sell': '卖出',
                'BUY': '买入', 'HOLD': '持有', 'SELL': '卖出',
                '购买': '买入', '保持': '持有', '出售': '卖出',
            }
            action = action_map.get(action, action)
            if action not in ('买入', '持有', '卖出'):
                action = '持有'

            # 标准化 target_price
            target_price = data.get('target_price')
            if isinstance(target_price, str):
                clean = target_price.replace('$', '').replace('¥', '').replace('￥', '').replace('元', '').strip()
                try:
                    target_price = float(clean) if clean and clean.lower() not in ('none', 'null', '') else None
                except ValueError:
                    target_price = None
            elif isinstance(target_price, (int, float)):
                target_price = float(target_price)
            else:
                target_price = None

            # 标准化 confidence/risk_score
            confidence = float(data.get('confidence', 0.7))
            if confidence > 1:
                confidence = confidence / 100.0
            risk_score = float(data.get('risk_score', 0.5))
            if risk_score > 1:
                risk_score = risk_score / 100.0

            return {
                'action': action,
                'target_price': target_price,
                'confidence': confidence,
                'risk_score': risk_score,
                'reasoning': data.get('reasoning', '基于综合分析的投资建议'),
            }

        except Exception as e:
            logger.debug(f"JSON提取失败: {e}")
            return None

    def _enhance_with_structured_data(
        self, result: dict, current_price: float | None, is_china: bool
    ) -> dict:
        """
        使用结构化数据增强决策结果。

        P0-2 关键改进: 当 target_price 缺失时，基于结构化当前价格给出
        明确标记为估算的目标价，而非 _smart_price_estimation 的隐式编造。
        """
        if result.get('target_price') is not None:
            return result

        if current_price is None:
            return result

        action = result.get('action', '持有')
        if action == '买入':
            result['target_price'] = round(current_price * 1.15, 2)
            result['_target_price_estimated'] = True
            logger.info(
                f"📈 目标价估算(买入): 当前价{current_price} × 1.15 = {result['target_price']}"
            )
        elif action == '卖出':
            result['target_price'] = round(current_price * 0.90, 2)
            result['_target_price_estimated'] = True
            logger.info(
                f"📉 目标价估算(卖出): 当前价{current_price} × 0.90 = {result['target_price']}"
            )
        # 持有不估算目标价

        return result

    def _extract_simple_decision(self, text: str) -> dict:
        """简单的决策提取方法作为最终备用"""
        action = '持有'
        if re.search(r'买入|BUY', text, re.IGNORECASE):
            action = '买入'
        elif re.search(r'卖出|SELL', text, re.IGNORECASE):
            action = '卖出'

        target_price = None
        price_patterns = [
            r'目标价[位格]?[：:]?\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'\*\*目标价[位格]?\*\*[：:]?\s*[¥\$]?(\d+(?:\.\d+)?)',
            r'[¥\$](\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)元',
        ]
        for pattern in price_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    target_price = float(match.group(1))
                    break
                except ValueError:
                    continue

        return {
            'action': action,
            'target_price': target_price,
            'confidence': 0.7,
            'risk_score': 0.5,
            'reasoning': '基于综合分析的投资建议',
        }

    def _get_default_decision(self) -> dict:
        """返回默认的投资决策"""
        return {
            'action': '持有',
            'target_price': None,
            'confidence': 0.5,
            'risk_score': 0.5,
            'reasoning': '输入数据无效，默认持有建议',
        }
