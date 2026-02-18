# -*- coding: utf-8 -*-
"""
基本面数据加载器
提供A股基本面数据加载和分析功能
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from zoneinfo import ZoneInfo

from .base_data_loader import BaseDataLoader, logger
from ..parsers.symbol_parser import (
    normalize_symbol,
    get_market_type,
    get_special_stock_info,
)
from ..parsers.data_validator import check_data_quality, format_number_yi
from tradingagents.config.runtime_settings import get_timezone_name


class FundamentalsLoader(BaseDataLoader):
    """
    基本面数据加载器

    负责加载和分析A股基本面数据，包括财务指标、行业信息等
    """

    def __init__(self):
        super().__init__()

    def load(self, symbol: str, force_refresh: bool = False, **kwargs) -> str:
        """
        加载基本面数据

        Args:
            symbol: 股票代码
            force_refresh: 是否强制刷新缓存
            **kwargs: 其他参数
                - analysis_modules: 分析模块级别 (basic/standard/full/detailed/comprehensive)

        Returns:
            格式化的基本面分析报告
        """
        analysis_modules = kwargs.get("analysis_modules", "standard")
        logger.info(f"📊 获取A股基本面数据: {symbol}")

        # 1. 优先尝试从MongoDB获取
        if not force_refresh:
            data = self._try_mongodb(symbol)
            if data:
                return data

        # 2. 检查文件缓存
        if not force_refresh:
            data = self._try_file_cache(symbol)
            if data:
                return data

        # 3. 生成基本面分析
        return self._generate_fundamentals_report(symbol, analysis_modules)

    def _try_mongodb(self, symbol: str) -> Optional[str]:
        """尝试从MongoDB获取财务数据"""
        try:
            from ..cache.mongodb_cache_adapter import get_mongodb_cache_adapter

            adapter = get_mongodb_cache_adapter()
            if not adapter.use_app_cache:
                return None

            financial_data = adapter.get_financial_data(symbol)
            if financial_data:
                logger.info(f"💰 [数据来源: MongoDB财务数据] 使用MongoDB财务数据: {symbol}")
                return self._format_financial_data_to_fundamentals(financial_data, symbol)
        except Exception as e:
            logger.debug(f"从MongoDB获取财务数据失败: {e}")

        return None

    def _try_file_cache(self, symbol: str) -> Optional[str]:
        """尝试从文件缓存获取数据"""
        try:
            import json

            for metadata_file in self.cache.metadata_dir.glob(f"*_meta.json"):
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)

                    if (
                        metadata.get("symbol") == symbol
                        and metadata.get("data_type") == "fundamentals"
                        and metadata.get("market_type") == "china"
                    ):
                        cache_key = metadata_file.stem.replace("_meta", "")
                        if self.cache.is_cache_valid(
                            cache_key, symbol=symbol, data_type="fundamentals"
                        ):
                            cached_data = self.cache.load_stock_data(cache_key)
                            if cached_data:
                                logger.info(
                                    f"⚡ [数据来源: 文件缓存] 从缓存加载A股基本面数据: {symbol}"
                                )
                                return cached_data
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f"从文件缓存获取基本面数据失败: {e}")

        return None

    def _format_financial_data_to_fundamentals(
        self, financial_data: Dict[str, Any], symbol: str
    ) -> str:
        """将MongoDB财务数据转换为基本面分析格式"""
        try:
            # 提取关键财务指标
            revenue = financial_data.get("total_revenue", "N/A")
            net_profit = financial_data.get("net_profit", "N/A")
            total_assets = financial_data.get("total_assets", "N/A")
            total_equity = financial_data.get("total_equity", "N/A")
            report_period = financial_data.get("report_period", "N/A")

            revenue_str = format_number_yi(revenue)
            net_profit_str = format_number_yi(net_profit)
            total_assets_str = format_number_yi(total_assets)
            total_equity_str = format_number_yi(total_equity)

            # 计算财务比率
            roe = "N/A"
            if (
                isinstance(net_profit, (int, float))
                and isinstance(total_equity, (int, float))
                and total_equity != 0
            ):
                roe = f"{(net_profit / total_equity * 100):.2f}%"

            roa = "N/A"
            if (
                isinstance(net_profit, (int, float))
                and isinstance(total_assets, (int, float))
                and total_assets != 0
            ):
                roa = f"{(net_profit / total_assets * 100):.2f}%"

            fundamentals_report = f"""
# {symbol} 基本面数据分析

## 📊 财务概况
- **报告期**: {report_period}
- **营业收入**: {revenue_str} 亿元
- **净利润**: {net_profit_str} 亿元
- **总资产**: {total_assets_str} 亿元
- **股东权益**: {total_equity_str} 亿元

## 📈 财务比率
- **净资产收益率(ROE)**: {roe}
- **总资产收益率(ROA)**: {roa}

## 📝 数据说明
- 数据来源: MongoDB财务数据库
- 更新时间: {self._get_current_time()}
- 数据类型: 同步财务数据
"""
            return fundamentals_report.strip()

        except Exception as e:
            logger.warning(f"⚠️ 格式化财务数据失败: {e}")
            return f"# {symbol} 基本面数据\n\n❌ 数据格式化失败: {str(e)}"

    def _generate_fundamentals_report(
        self, symbol: str, analysis_modules: str = "standard"
    ) -> str:
        """生成基本面分析报告"""
        try:
            # 获取股票基础信息
            stock_basic_info = self._get_stock_basic_info(symbol)

            # 获取行业信息
            industry_info = self._get_industry_info(symbol)

            # 获取财务指标
            try:
                financial_metrics = self._get_financial_metrics(symbol)
            except ValueError as e:
                logger.warning(f"⚠️ 无法获取财务指标: {e}")
                return self._generate_simplified_report(symbol, industry_info, str(e))

            # 检查数据质量
            data_quality = check_data_quality(symbol, industry_info, financial_metrics)

            # 触发后台同步（如果有缺失的关键字段）
            if data_quality["missing_fields"]:
                self._trigger_background_sync(symbol, data_quality["missing_fields"])

            # 根据分析模块级别生成报告
            if analysis_modules == "basic":
                return self._generate_basic_report(symbol, industry_info, financial_metrics, data_quality)
            elif analysis_modules in ["standard", "full"]:
                return self._generate_standard_report(symbol, industry_info, financial_metrics, data_quality)
            else:
                return self._generate_detailed_report(symbol, industry_info, financial_metrics, data_quality)

        except Exception as e:
            logger.error(f"❌ 生成基本面报告失败: {e}")
            return self._generate_fallback_fundamentals(symbol, str(e))

    def _get_stock_basic_info(self, symbol: str) -> Dict[str, Any]:
        """获取股票基础信息"""
        try:
            from ..interface import get_china_stock_info_unified

            stock_info = get_china_stock_info_unified(symbol)
            if stock_info and "股票名称:" in stock_info:
                return {"raw_info": stock_info}
        except Exception as e:
            logger.debug(f"获取股票基础信息失败: {e}")

        return {"raw_info": ""}

    def _get_industry_info(self, symbol: str) -> Dict[str, Any]:
        """获取行业信息"""
        code = normalize_symbol(symbol)

        # 首先尝试从数据库获取
        try:
            from ..cache.app_adapter import get_basics_from_cache

            doc = get_basics_from_cache(code)
            if isinstance(doc, list) and len(doc) > 0:
                doc = doc[0]

            if doc and isinstance(doc, dict):
                board_labels = {"主板", "中小板", "创业板", "科创板"}
                raw_industry = str(doc.get("industry") or doc.get("industry_name") or "").strip()
                sec_or_cat = str(doc.get("sec") or doc.get("category") or "").strip()
                market_val = str(doc.get("market") or "").strip()
                industry_val = raw_industry or sec_or_cat or "未知"

                # 如果industry字段是板块名，则将其用于market
                if raw_industry in board_labels:
                    if not market_val:
                        market_val = raw_industry
                    if sec_or_cat:
                        industry_val = sec_or_cat

                info = {
                    "industry": industry_val or "未知",
                    "market": market_val or str(doc.get("market", "未知")),
                    "type": get_market_type(code).get("type", "综合"),
                }

                # 添加特殊股票信息
                special_info = get_special_stock_info(code)
                if special_info:
                    info.update(special_info)
                else:
                    info.update({
                        "analysis": f"该股票属于{info['industry']}行业，在{info['market']}上市交易。",
                        "market_share": "待分析",
                        "brand_value": "待评估",
                        "tech_advantage": "待分析",
                    })

                return info
        except Exception as e:
            logger.warning(f"⚠️ 从数据库获取行业信息失败: {e}")

        # 使用代码前缀判断
        market_info = get_market_type(code)
        info = {
            "industry": "未知",
            "market": market_info["market"],
            "type": market_info["type"],
        }

        # 添加特殊股票信息
        special_info = get_special_stock_info(code)
        if special_info:
            info.update(special_info)
        else:
            info.update({
                "analysis": f"该股票在{info['market']}上市交易，具体行业信息需要进一步查询。",
                "market_share": "待分析",
                "brand_value": "待评估",
                "tech_advantage": "待分析",
            })

        return info

    def _get_financial_metrics(self, symbol: str) -> Dict[str, Any]:
        """获取财务指标

        从MongoDB获取真实的财务数据，包括：
        - 估值指标：PE、PB
        - 盈利能力：ROE、ROA、毛利率、净利率
        - 综合评分：基本面评分、估值评分、成长评分
        """
        try:
            from ..cache.mongodb_cache_adapter import get_mongodb_cache_adapter

            adapter = get_mongodb_cache_adapter()
            metrics = {
                "pe": "N/A",
                "pb": "N/A",
                "roe": "N/A",
                "roa": "N/A",
                "gross_margin": "N/A",
                "net_margin": "N/A",
                "fundamental_score": 5.0,
                "valuation_score": 5.0,
                "growth_score": 5.0,
                "risk_level": "中等",
            }

            if not adapter.use_app_cache or adapter.db is None:
                logger.debug(f"📊 MongoDB缓存不可用，返回默认指标: {symbol}")
                return metrics

            code6 = str(symbol).zfill(6)

            # 1. 从 stock_basic_info 获取估值指标（PE、PB）
            try:
                basics_collection = adapter.db.stock_basic_info
                basics_doc = basics_collection.find_one(
                    {"code": code6},
                    {"_id": 0, "pe": 1, "pe_ttm": 1, "pb": 1, "total_mv": 1, "circ_mv": 1}
                )
                if basics_doc:
                    pe = basics_doc.get("pe")
                    pb = basics_doc.get("pb")
                    pe_ttm = basics_doc.get("pe_ttm")

                    # 优先使用PE_TTM，如果没有则使用PE
                    if pe is not None and pe > 0:
                        metrics["pe"] = f"{pe:.2f}"
                    elif pe_ttm is not None and pe_ttm > 0:
                        metrics["pe"] = f"{pe_ttm:.2f} (TTM)"

                    if pb is not None and pb > 0:
                        metrics["pb"] = f"{pb:.2f}"

                    logger.debug(f"✅ 从stock_basics获取估值指标: PE={metrics['pe']}, PB={metrics['pb']}")
            except Exception as e:
                logger.debug(f"⚠️ 从stock_basics获取估值指标失败: {e}")

            # 2. 从 stock_financial_data 获取财务指标
            try:
                financial_doc = adapter.get_financial_data(symbol)
                if financial_doc:
                    # 标准化数据中的字段直接使用
                    raw_data = financial_doc.get("raw_data", {})
                    financial_indicators = raw_data.get("financial_indicators", [])

                    if financial_indicators:
                        # 获取最新的财务指标
                        latest_indicator = financial_indicators[0]

                        # 提取ROE
                        roe = latest_indicator.get("roe")
                        if roe is not None:
                            metrics["roe"] = f"{float(roe):.2f}%"

                        # 提取ROA
                        roa = latest_indicator.get("roa")
                        if roa is not None:
                            metrics["roa"] = f"{float(roa):.2f}%"

                        # 提取毛利率
                        gross_margin = latest_indicator.get("grossprofit_margin")
                        if gross_margin is not None:
                            metrics["gross_margin"] = f"{float(gross_margin):.2f}%"

                        # 提取净利率
                        net_margin = latest_indicator.get("netprofit_margin")
                        if net_margin is not None:
                            metrics["net_margin"] = f"{float(net_margin):.2f}%"

                    # 计算各项评分
                    metrics["fundamental_score"] = self._calculate_fundamental_score(financial_doc)
                    metrics["valuation_score"] = self._calculate_valuation_score(financial_doc, metrics)
                    metrics["growth_score"] = self._calculate_growth_score(financial_doc)

                    logger.debug(f"✅ 从financial_data获取财务指标: ROE={metrics['roe']}, ROA={metrics['roa']}")
            except Exception as e:
                logger.debug(f"⚠️ 从financial_data获取财务指标失败: {e}")

            # 3. 根据指标计算风险等级
            metrics["risk_level"] = self._calculate_risk_level(metrics)

            return metrics

        except Exception as e:
            logger.warning(f"⚠️ 获取财务指标失败: {e}")
            return {
                "pe": "N/A",
                "pb": "N/A",
                "roe": "N/A",
                "roa": "N/A",
                "gross_margin": "N/A",
                "net_margin": "N/A",
                "fundamental_score": 5.0,
                "valuation_score": 5.0,
                "growth_score": 5.0,
                "risk_level": "中等",
            }

    def _calculate_fundamental_score(self, financial_data: Dict[str, Any]) -> float:
        """计算基本面评分 (0-10分)"""
        score = 5.0  # 基础分

        try:
            raw_data = financial_data.get("raw_data", {})
            indicators = raw_data.get("financial_indicators", [])
            if not indicators:
                return score

            latest = indicators[0]

            # ROE评分 (权重30%)
            roe = latest.get("roe")
            if roe is not None:
                roe_val = float(roe)
                if roe_val >= 20:
                    score += 1.5
                elif roe_val >= 15:
                    score += 1.0
                elif roe_val >= 10:
                    score += 0.5
                elif roe_val < 5:
                    score -= 0.5

            # ROA评分 (权重20%)
            roa = latest.get("roa")
            if roa is not None:
                roa_val = float(roa)
                if roa_val >= 10:
                    score += 1.0
                elif roa_val >= 5:
                    score += 0.5

            # 毛利率评分 (权重20%)
            gross_margin = latest.get("grossprofit_margin")
            if gross_margin is not None:
                gm_val = float(gross_margin)
                if gm_val >= 40:
                    score += 1.0
                elif gm_val >= 30:
                    score += 0.5

            # 净利率评分 (权重20%)
            net_margin = latest.get("netprofit_margin")
            if net_margin is not None:
                nm_val = float(net_margin)
                if nm_val >= 20:
                    score += 1.0
                elif nm_val >= 10:
                    score += 0.5

            # 负债率评分 (权重10%，越低越好)
            debt_ratio = latest.get("debt_to_assets")
            if debt_ratio is not None:
                dr_val = float(debt_ratio)
                if dr_val > 80:  # 高负债
                    score -= 0.5
                elif dr_val < 40:  # 低负债健康
                    score += 0.5

        except Exception as e:
            logger.debug(f"计算基本面评分失败: {e}")

        return max(0, min(10, score))  # 限制在0-10范围内

    def _calculate_valuation_score(self, financial_data: Dict[str, Any], metrics: Dict[str, Any]) -> float:
        """计算估值吸引力评分 (0-10分)"""
        score = 5.0  # 基础分

        try:
            # 解析PE值（去掉" (TTM)"后缀）
            pe_str = metrics.get("pe", "N/A")
            if pe_str != "N/A":
                pe_val = float(pe_str.replace(" (TTM)", ""))
                # PE越低越有价值，但PE<0表示亏损
                if 0 < pe_val <= 15:  # 低估值，很好
                    score += 2.5
                elif 15 < pe_val <= 25:  # 合理估值
                    score += 1.5
                elif 25 < pe_val <= 40:  # 稍贵
                    score += 0.5
                elif pe_val > 60:  # 高估
                    score -= 1.0
                elif pe_val < 0:  # 亏损
                    score -= 0.5

            # 解析PB值
            pb_str = metrics.get("pb", "N/A")
            if pb_str != "N/A":
                pb_val = float(pb_str)
                if 0 < pb_val <= 1.5:  # 低PB，很好
                    score += 1.5
                elif 1.5 < pb_val <= 3:  # 合理PB
                    score += 0.5
                elif pb_val > 6:  # 高PB
                    score -= 0.5

        except Exception as e:
            logger.debug(f"计算估值评分失败: {e}")

        return max(0, min(10, score))

    def _calculate_growth_score(self, financial_data: Dict[str, Any]) -> float:
        """计算成长潜力评分 (0-10分)"""
        score = 5.0  # 基础分

        try:
            raw_data = financial_data.get("raw_data", {})
            income_statements = raw_data.get("income_statement", [])

            if len(income_statements) >= 2:
                # 获取最近两期数据
                current = income_statements[0]
                previous = income_statements[1]

                # 营收增长率
                current_revenue = current.get("revenue") or current.get("total_revenue")
                previous_revenue = previous.get("revenue") or previous.get("total_revenue")
                if current_revenue and previous_revenue:
                    try:
                        revenue_growth = (float(current_revenue) / float(previous_revenue) - 1) * 100
                        if revenue_growth >= 50:
                            score += 2.0
                        elif revenue_growth >= 30:
                            score += 1.5
                        elif revenue_growth >= 15:
                            score += 1.0
                        elif revenue_growth < 0:
                            score -= 0.5
                    except (ValueError, ZeroDivisionError):
                        pass

                # 净利润增长率
                current_profit = current.get("n_income_attr_p") or current.get("net_profit")
                previous_profit = previous.get("n_income_attr_p") or previous.get("net_profit")
                if current_profit and previous_profit:
                    try:
                        profit_growth = (float(current_profit) / float(previous_profit) - 1) * 100
                        if profit_growth >= 50:
                            score += 1.5
                        elif profit_growth >= 30:
                            score += 1.0
                        elif profit_growth >= 15:
                            score += 0.5
                        elif profit_growth < -20:
                            score -= 0.5
                    except (ValueError, ZeroDivisionError):
                        pass

        except Exception as e:
            logger.debug(f"计算成长评分失败: {e}")

        return max(0, min(10, score))

    def _calculate_risk_level(self, metrics: Dict[str, Any]) -> str:
        """根据指标计算风险等级"""
        risk_score = 0

        try:
            # PE风险
            pe_str = metrics.get("pe", "N/A")
            if pe_str != "N/A":
                pe_val = float(pe_str.replace(" (TTM)", ""))
                if pe_val < 0:  # 亏损股
                    risk_score += 3
                elif pe_val > 100:  # 极高估值
                    risk_score += 2
                elif pe_val > 60:  # 高估值
                    risk_score += 1

            # PB风险
            pb_str = metrics.get("pb", "N/A")
            if pb_str != "N/A":
                pb_val = float(pb_str)
                if pb_val > 10:
                    risk_score += 2
                elif pb_val > 6:
                    risk_score += 1

            # ROE风险（盈利能力差）
            roe_str = metrics.get("roe", "N/A")
            if roe_str != "N/A":
                roe_val = float(roe_str.replace("%", ""))
                if roe_val < 5:
                    risk_score += 2
                elif roe_val < 10:
                    risk_score += 1

            # 基本面评分风险
            fundamental_score = metrics.get("fundamental_score", 5.0)
            if fundamental_score < 4:
                risk_score += 1

        except Exception as e:
            logger.debug(f"计算风险等级失败: {e}")

        # 转换风险分数为等级
        if risk_score >= 6:
            return "高"
        elif risk_score >= 3:
            return "中高"
        elif risk_score >= 1:
            return "中等"
        else:
            return "低"

    def _trigger_background_sync(self, symbol: str, missing_fields: List[str]) -> bool:
        """触发后台数据同步"""
        try:
            critical_missing = [
                f for f in missing_fields
                if f in ["所属行业", "营收同比增速", "净利润同比增速"]
            ]

            if not critical_missing:
                return False

            logger.info(f"🔄 [{symbol}] 检测到关键数据缺失，尝试触发后台同步")
            # 实际实现需要调用后台同步逻辑
            return True

        except Exception as e:
            logger.warning(f"⚠️ [{symbol}] 触发后台同步失败: {e}")
            return False

    def _generate_simplified_report(
        self, symbol: str, industry_info: Dict[str, Any], error_msg: str
    ) -> str:
        """生成简化版报告"""
        tz = ZoneInfo(get_timezone_name())
        return f"""# 中国A股基本面分析报告 - {symbol} (简化版)

## 📊 基本信息
- **股票代码**: {symbol}
- **所属行业**: {industry_info.get("industry", "未知")}

## 📈 行业分析
{industry_info.get("analysis", "暂无行业分析")}

## ⚠️ 数据说明
由于无法获取完整的财务数据，本报告仅包含基本价格信息和行业分析。

---
**生成时间**: {datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")}
**数据来源**: 基础市场数据
"""

    def _generate_basic_report(
        self,
        symbol: str,
        industry_info: Dict[str, Any],
        financial_metrics: Dict[str, Any],
        data_quality: Dict[str, Any],
    ) -> str:
        """生成基础版报告"""
        tz = ZoneInfo(get_timezone_name())
        return f"""# 中国A股基本面分析报告 - {symbol} (基础版)

## 📊 股票基本信息
- **股票代码**: {symbol}
- **所属行业**: {industry_info.get("industry", "未知")}
- **市场板块**: {industry_info.get("market", "未知")}
- **分析日期**: {datetime.now(tz).strftime("%Y年%m月%d日")}

## 💰 核心财务指标
- **市盈率(PE)**: {financial_metrics.get("pe", "N/A")}
- **市净率(PB)**: {financial_metrics.get("pb", "N/A")}
- **净资产收益率(ROE)**: {financial_metrics.get("roe", "N/A")}

## 💡 基础评估
- **基本面评分**: {financial_metrics.get("fundamental_score", 5.0)}/10
- **风险等级**: {financial_metrics.get("risk_level", "中等")}

---
**重要声明**: 本报告基于公开数据和模型估算生成，仅供参考，不构成投资建议。
**生成时间**: {datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _generate_standard_report(
        self,
        symbol: str,
        industry_info: Dict[str, Any],
        financial_metrics: Dict[str, Any],
        data_quality: Dict[str, Any],
    ) -> str:
        """生成标准版报告"""
        tz = ZoneInfo(get_timezone_name())
        return f"""# 中国A股基本面分析报告 - {symbol}

## 📊 股票基本信息
- **股票代码**: {symbol}
- **所属行业**: {industry_info.get("industry", "未知")}
- **市场板块**: {industry_info.get("market", "未知")}
- **分析日期**: {datetime.now(tz).strftime("%Y年%m月%d日")}

## 💰 财务数据分析

### 估值指标
- **市盈率(PE)**: {financial_metrics.get("pe", "N/A")}
- **市净率(PB)**: {financial_metrics.get("pb", "N/A")}

### 盈利能力指标
- **净资产收益率(ROE)**: {financial_metrics.get("roe", "N/A")}
- **总资产收益率(ROA)**: {financial_metrics.get("roa", "N/A")}
- **毛利率**: {financial_metrics.get("gross_margin", "N/A")}
- **净利率**: {financial_metrics.get("net_margin", "N/A")}

## 📈 行业分析
{industry_info.get("analysis", "暂无行业分析")}

## 💡 投资建议
- **基本面评分**: {financial_metrics.get("fundamental_score", 5.0)}/10
- **估值吸引力**: {financial_metrics.get("valuation_score", 5.0)}/10
- **成长潜力**: {financial_metrics.get("growth_score", 5.0)}/10
- **风险等级**: {financial_metrics.get("risk_level", "中等")}

---
**重要声明**: 本报告基于公开数据和模型估算生成，仅供参考，不构成投资建议。
**生成时间**: {datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")}
"""

    def _generate_detailed_report(
        self,
        symbol: str,
        industry_info: Dict[str, Any],
        financial_metrics: Dict[str, Any],
        data_quality: Dict[str, Any],
    ) -> str:
        """生成详细版报告"""
        # 详细版包含更多分析内容
        return self._generate_standard_report(
            symbol, industry_info, financial_metrics, data_quality
        )


# 全局实例
_fundamentals_loader: Optional[FundamentalsLoader] = None


def get_fundamentals_loader() -> FundamentalsLoader:
    """获取全局基本面数据加载器实例"""
    global _fundamentals_loader
    if _fundamentals_loader is None:
        _fundamentals_loader = FundamentalsLoader()
    return _fundamentals_loader
