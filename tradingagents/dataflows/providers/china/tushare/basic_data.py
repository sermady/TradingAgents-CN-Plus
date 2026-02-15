# -*- coding: utf-8 -*-
"""
股票基础信息模块

提供股票列表、基础信息等数据的获取功能。
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime
import asyncio
import pandas as pd

from .base_provider import BaseTushareProvider, ts, TUSHARE_AVAILABLE, logger
from ...base_provider import BaseStockDataProvider


class BasicDataMixin(BaseTushareProvider):
    """股票基础信息功能混入类"""

    def get_stock_list_sync(
        self, market: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """获取股票列表（同步版本）"""
        if not self.is_available():
            return None

        try:
            df = self.api.stock_basic(
                list_status="L",
                fields="ts_code,symbol,name,area,industry,market,exchange,list_date,is_hs",
            )
            if df is not None and not df.empty:
                self.logger.info(f"✅ 成功获取 {len(df)} 条股票数据")
                return df
            else:
                self.logger.warning("⚠️ Tushare API 返回空数据")
                return None
        except Exception as e:
            self.logger.error(f"❌ 获取股票列表失败: {e}")
            return None

    async def get_stock_list(
        self, market: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """获取股票列表（异步版本）"""
        if not self.is_available():
            return None

        try:
            # 构建查询参数
            params = {
                "list_status": "L",  # 只获取上市股票
                "fields": "ts_code,symbol,name,area,industry,market,exchange,list_date,is_hs",
            }

            if market:
                # 根据市场筛选
                if market == "CN":
                    params["exchange"] = "SSE,SZSE"  # 沪深交易所
                elif market == "HK":
                    return None  # Tushare港股需要单独处理
                elif market == "US":
                    return None  # Tushare不支持美股

            # 获取数据
            df = await asyncio.to_thread(self.api.stock_basic, **params)

            if df is None:
                return []

            if df.empty:
                return []

            # 转换为标准格式
            stock_list = []
            for _, row in df.iterrows():
                stock_info = self.standardize_basic_info(row.to_dict())
                stock_list.append(stock_info)

            self.logger.info(f"✅ 获取股票列表: {len(stock_list)}只")
            return stock_list

        except Exception as e:
            self.logger.error(f"❌ 获取股票列表失败: {e}")
            return []

    async def get_stock_basic_info(
        self, symbol: Optional[str] = None
    ) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """获取股票基础信息（包含 PE/PB 等财务指标）"""
        if not self.is_available():
            return None

        try:
            if symbol:
                ts_code = self._normalize_ts_code(symbol)
                df = await asyncio.to_thread(
                    self.api.stock_basic,
                    ts_code=ts_code,
                    fields="ts_code,symbol,name,area,industry,market,exchange,list_date,is_hs,act_name,act_ent_type",
                )

                if df is None or df.empty:
                    return None

                basic_data = df.iloc[0].to_dict()

                try:
                    daily_df = await asyncio.to_thread(
                        self.api.daily_basic,
                        ts_code=ts_code,
                        fields="ts_code,total_mv,circ_mv,pe,pb,ps,turnover_rate,volume_ratio,pe_ttm,pb_mrq,ps_ttm,"
                        "dv_ratio,dv_ttm,total_share,float_share",
                        limit=1,
                    )

                    if daily_df is not None and not daily_df.empty:
                        row = daily_df.iloc[0]
                        basic_data["pe"] = row["pe"]
                        basic_data["pb"] = row["pb"]
                        basic_data["ps"] = row["ps"]
                        basic_data["pe_ttm"] = row["pe_ttm"]
                        basic_data["ps_ttm"] = row.get("ps_ttm")
                        basic_data["total_mv"] = row["total_mv"]
                        basic_data["circ_mv"] = row["circ_mv"]
                        basic_data["turnover_rate"] = row["turnover_rate"]
                        basic_data["volume_ratio"] = row["volume_ratio"]
                        # 股息率指标（2026-02-12 新增）
                        basic_data["dv_ratio"] = row.get("dv_ratio")
                        basic_data["dv_ttm"] = row.get("dv_ttm")
                        # 股本数据（2026-02-12 新增）
                        basic_data["total_share"] = row.get("total_share")
                        basic_data["float_share"] = row.get("float_share")
                except Exception as daily_e:
                    self.logger.warning(f"获取 daily_basic 财务指标失败: {daily_e}")

                try:
                    # 获取财务指标数据（盈利能力、成长能力、偿债能力、每股指标）
                    # 2026-02-12: 增强字段获取，包含四大类核心指标
                    fina_df = await asyncio.to_thread(
                        self.api.fina_indicator,
                        ts_code=ts_code,
                        fields="ts_code,roe,roe_waa,roe_dt,roa,roa2,grossprofit_margin,netprofit_margin,"
                        "q_profit_yoy,or_yoy,eps_yoy,roe_yoy,profit_dedt_yoy,"
                        "debt_to_assets,current_ratio,quick_ratio,cash_ratio,"
                        "inv_turn,ar_turn,assets_turn,"
                        "diluted2_eps,bps,ocfps,capital_rese_ps,undist_profit_ps",
                        limit=1,
                    )
                    if fina_df is not None and not fina_df.empty:
                        row = fina_df.iloc[0]

                        # === 盈利能力指标 ===
                        basic_data["roe"] = row.get("roe")  # 净资产收益率
                        basic_data["roe_waa"] = row.get("roe_waa")  # 加权平均ROE
                        basic_data["roe_dt"] = row.get("roe_dt")  # 扣非ROE
                        basic_data["roa"] = row.get("roa")  # 总资产收益率
                        basic_data["roa2"] = row.get("roa2")  # 扣非ROA
                        basic_data["grossprofit_margin"] = row.get(
                            "grossprofit_margin"
                        )  # 毛利率
                        basic_data["netprofit_margin"] = row.get(
                            "netprofit_margin"
                        )  # 净利率

                        # === 成长能力指标 ===
                        basic_data["q_profit_yoy"] = row.get(
                            "q_profit_yoy"
                        )  # 净利润同比增长率
                        basic_data["or_yoy"] = row.get("or_yoy")  # 营业收入同比增长率
                        basic_data["eps_yoy"] = row.get("eps_yoy")  # 每股收益同比增长率
                        basic_data["roe_yoy"] = row.get("roe_yoy")  # ROE同比增长率
                        basic_data["profit_dedt_yoy"] = row.get(
                            "profit_dedt_yoy"
                        )  # 扣非净利润同比增长率

                        # === 偿债能力指标 ===
                        basic_data["debt_to_assets"] = row.get(
                            "debt_to_assets"
                        )  # 资产负债率
                        basic_data["current_ratio"] = row.get(
                            "current_ratio"
                        )  # 流动比率
                        basic_data["quick_ratio"] = row.get("quick_ratio")  # 速动比率
                        basic_data["cash_ratio"] = row.get("cash_ratio")  # 现金比率

                        # === 营运能力指标 ===
                        basic_data["inv_turn"] = row.get("inv_turn")  # 存货周转率
                        basic_data["ar_turn"] = row.get("ar_turn")  # 应收账款周转率
                        basic_data["assets_turn"] = row.get(
                            "assets_turn"
                        )  # 总资产周转率

                        # === 每股指标 ===
                        basic_data["eps"] = row.get("diluted2_eps")  # 稀释每股收益
                        basic_data["bps"] = row.get("bps")  # 每股净资产
                        basic_data["ocfps"] = row.get("ocfps")  # 每股经营现金流
                        basic_data["capital_rese_ps"] = row.get(
                            "capital_rese_ps"
                        )  # 每股公积金
                        basic_data["undist_profit_ps"] = row.get(
                            "undist_profit_ps"
                        )  # 每股未分配利润

                        self.logger.info(
                            f"🔍 [Tushare] 获取到 {ts_code} 财务指标: "
                            f"ROE={basic_data.get('roe')}%, 毛利率={basic_data.get('grossprofit_margin')}%, "
                            f"资产负债率={basic_data.get('debt_to_assets')}%, 营收同比={basic_data.get('or_yoy')}%"
                        )
                    else:
                        self.logger.warning(
                            f"⚠️ [Tushare] fina_indicator 返回空数据: {ts_code}"
                        )
                except Exception as fina_e:
                    self.logger.warning(f"获取 fina_indicator 财务指标失败: {fina_e}")

                # 获取股东增减持数据 (stk_holdertrade) - 5210积分可用
                try:
                    holder_trade_df = await asyncio.to_thread(
                        self.api.stk_holdertrade,
                        ts_code=ts_code,
                        limit=10,  # 获取最近10条增减持记录
                    )
                    if holder_trade_df is not None and not holder_trade_df.empty:
                        basic_data["holder_trade_records"] = holder_trade_df.to_dict(
                            "records"
                        )
                        # 统计增减持情况
                        net_buy = holder_trade_df["in_de"].sum()  # in_de: 增持或减持
                        basic_data["holder_net_buy"] = float(net_buy)
                        self.logger.debug(
                            f"✅ {ts_code} 股东增减持数据获取成功: {len(holder_trade_df)} 条记录, "
                            f"净增持: {net_buy}万股"
                        )
                    else:
                        self.logger.debug(f"⚠️ {ts_code} 股东增减持数据为空")
                except Exception as e:
                    self.logger.debug(
                        f"获取{ts_code}股东增减持数据失败: {e}"
                    )  # 股东增减持数据不是必需的，保持debug级别

                # 获取股东人数数据 (stk_holdernumber) - 5210积分可用
                try:
                    holder_num_df = await asyncio.to_thread(
                        self.api.stk_holdernumber,
                        ts_code=ts_code,
                        limit=4,  # 获取最近4个季度数据
                    )
                    if holder_num_df is not None and not holder_num_df.empty:
                        basic_data["holder_number_records"] = holder_num_df.to_dict(
                            "records"
                        )
                        latest_holders = holder_num_df.iloc[0]
                        holder_num = latest_holders.get("holder_num", 0)
                        basic_data["holder_num"] = int(holder_num)
                        self.logger.debug(
                            f"✅ {ts_code} 股东人数数据获取成功: {len(holder_num_df)} 条记录, "
                            f"最新股东人数: {holder_num}"
                        )
                    else:
                        self.logger.debug(f"⚠️ {ts_code} 股东人数数据为空")
                except Exception as e:
                    self.logger.debug(
                        f"获取{ts_code}股东人数数据失败: {e}"
                    )  # 股东人数数据不是必需的，保持debug级别

                return self.standardize_basic_info(basic_data)
            else:
                return await self.get_stock_list()

        except Exception as e:
            self.logger.error(f"❌ 获取股票基础信息失败 symbol={symbol}: {e}")
            return None

    def standardize_basic_info(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化股票基础信息"""
        ts_code = raw_data.get("ts_code", "")
        symbol = raw_data.get(
            "symbol", ts_code.split(".")[0] if "." in ts_code else ts_code
        )

        return {
            # 基础字段
            "code": symbol,
            "name": raw_data.get("name", ""),
            "symbol": symbol,
            "full_symbol": ts_code,
            # 市场信息
            "market_info": self._determine_market_info_from_ts_code(ts_code),
            # 业务信息
            "area": self._safe_str(raw_data.get("area")),
            "industry": self._safe_str(raw_data.get("industry")),
            "market": raw_data.get("market"),  # 主板/创业板/科创板
            "list_date": self._format_date_output(raw_data.get("list_date")),
            # 港股通信息
            "is_hs": raw_data.get("is_hs"),
            # 实控人信息
            "act_name": raw_data.get("act_name"),
            "act_ent_type": raw_data.get("act_ent_type"),
            # 财务指标
            "pe": self._convert_to_float(raw_data.get("pe")),
            "pe_ttm": self._convert_to_float(raw_data.get("pe_ttm")),
            "pb": self._convert_to_float(raw_data.get("pb")),
            "ps": self._convert_to_float(raw_data.get("ps")),
            "total_mv": self._convert_to_float(raw_data.get("total_mv")),
            "circ_mv": self._convert_to_float(raw_data.get("circ_mv")),
            "turnover_rate": self._convert_to_float(raw_data.get("turnover_rate")),
            "volume_ratio": self._convert_to_float(raw_data.get("volume_ratio")),
            # 盈利能力指标 (2026-02-12 新增: ROE、ROA、毛利率、净利率)
            "roe": self._convert_to_float(raw_data.get("roe")),  # 净资产收益率
            "roe_waa": self._convert_to_float(raw_data.get("roe_waa")),  # 加权平均ROE
            "roe_dt": self._convert_to_float(raw_data.get("roe_dt")),  # 扣非ROE
            "roa": self._convert_to_float(raw_data.get("roa")),  # 总资产收益率
            "roa2": self._convert_to_float(raw_data.get("roa2")),  # 扣非ROA
            "grossprofit_margin": self._convert_to_float(
                raw_data.get("grossprofit_margin")
            ),  # 毛利率
            "netprofit_margin": self._convert_to_float(
                raw_data.get("netprofit_margin")
            ),  # 净利率
            # 每股指标 (2026-02-02 新增: 基本每股收益、每股净资产、每股现金流等)
            "eps": self._convert_to_float(raw_data.get("eps")),  # 稀释每股收益
            "bps": self._convert_to_float(raw_data.get("bps")),  # 每股净资产
            "ocfps": self._convert_to_float(raw_data.get("ocfps")),  # 每股经营现金流
            # 同比增速 (2026-02-07 修复：添加营收/净利润同比增速字段)
            "or_yoy": self._convert_to_float(
                raw_data.get("or_yoy")
            ),  # 营业收入同比增长率（%）
            "q_profit_yoy": self._convert_to_float(
                raw_data.get("q_profit_yoy")
            ),  # 净利润同比增长率（%）
            "eps_yoy": self._convert_to_float(
                raw_data.get("eps_yoy")
            ),  # 每股收益同比增长率（%）
            "roe_yoy": self._convert_to_float(
                raw_data.get("roe_yoy")
            ),  # 净资产收益率同比增长率（%）
            "profit_dedt_yoy": self._convert_to_float(
                raw_data.get("profit_dedt_yoy")
            ),  # 扣非净利润同比增长率（%）
            # 偿债能力指标 (2026-02-12 新增)
            "debt_to_assets": self._convert_to_float(
                raw_data.get("debt_to_assets")
            ),  # 资产负债率
            "current_ratio": self._convert_to_float(
                raw_data.get("current_ratio")
            ),  # 流动比率
            "quick_ratio": self._convert_to_float(
                raw_data.get("quick_ratio")
            ),  # 速动比率
            "cash_ratio": self._convert_to_float(
                raw_data.get("cash_ratio")
            ),  # 现金比率
            # 营运能力指标 (2026-02-12 新增)
            "inv_turn": self._convert_to_float(raw_data.get("inv_turn")),  # 存货周转率
            "ar_turn": self._convert_to_float(
                raw_data.get("ar_turn")
            ),  # 应收账款周转率
            "assets_turn": self._convert_to_float(
                raw_data.get("assets_turn")
            ),  # 总资产周转率
            # 每股指标
            "capital_rese_ps": self._convert_to_float(
                raw_data.get("capital_rese_ps")
            ),  # 每股公积金
            "undist_profit_ps": self._convert_to_float(
                raw_data.get("undist_profit_ps")
            ),  # 每股未分配利润
            # 元数据
            "data_source": "tushare",
            "data_version": 1,
            "updated_at": datetime.utcnow(),
        }

    # 辅助方法
    def _normalize_ts_code(self, symbol: str) -> str:
        """标准化为Tushare的ts_code格式"""
        if "." in symbol:
            return symbol  # 已经是ts_code格式

        # 6位数字代码，需要添加后缀
        if symbol.isdigit() and len(symbol) == 6:
            if symbol.startswith(("60", "68", "90")):
                return f"{symbol}.SH"  # 上交所
            else:
                return f"{symbol}.SZ"  # 深交所

        return symbol

    def _determine_market_info_from_ts_code(self, ts_code: str) -> Dict[str, Any]:
        """根据ts_code确定市场信息（调用基类通用方法）"""
        return self._get_market_info(ts_code)

    def _format_date_output(self, date_value) -> Optional[str]:
        """格式化日期输出"""
        if date_value is None:
            return None
        if isinstance(date_value, str):
            # 已经是字符串，检查格式
            if len(date_value) == 8:
                return f"{date_value[:4]}-{date_value[4:6]}-{date_value[6:]}"
            return date_value
        return str(date_value)

    def _convert_to_float(self, value) -> Optional[float]:
        """安全转换为浮点数"""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                value = value.strip()
                if not value or value.lower() in ["nan", "null", "none", ""]:
                    return None
            return float(value)
        except (ValueError, TypeError):
            return None

    def _safe_str(self, value) -> Optional[str]:
        """安全转换为字符串，处理NaN值"""
        if value is None:
            return None
        if isinstance(value, float) and (value != value):  # 检查NaN
            return None
        return str(value) if value else None
