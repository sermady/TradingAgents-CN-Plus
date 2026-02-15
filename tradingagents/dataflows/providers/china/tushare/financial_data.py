# -*- coding: utf-8 -*-
"""
财务数据模块

提供财务报表、财务指标、TTM计算等功能。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio

from .base_provider import BaseTushareProvider, logger
from ...base_provider import BaseStockDataProvider


class FinancialDataMixin(BaseTushareProvider):
    """财务数据功能混入类"""

    async def get_financial_data(
        self,
        symbol: str,
        report_type: str = "quarterly",
        period: Optional[str] = None,
        limit: int = 8,
    ) -> Optional[Dict[str, Any]]:
        """
        获取财务数据

        Args:
            symbol: 股票代码
            report_type: 报告类型 (quarterly/annual)
            period: 指定报告期 (YYYYMMDD格式)，为空则获取最新数据
            limit: 获取记录数量，默认8条（最近8个季度，2年数据，用于TTM计算）

        Returns:
            财务数据字典，包含利润表、资产负债表、现金流量表和财务指标
        """
        if not self.is_available():
            return None

        try:
            ts_code = self._normalize_ts_code(symbol)
            self.logger.debug(f"📊 获取Tushare财务数据: {ts_code}, 类型: {report_type}")

            # 构建查询参数
            query_params = {"ts_code": ts_code, "limit": limit}

            # 如果指定了报告期，添加期间参数
            if period:
                query_params["period"] = period

            financial_data = {}

            # 1. 获取利润表数据 (income statement)
            try:
                income_df = await asyncio.to_thread(self.api.income, **query_params)
                if income_df is not None and not income_df.empty:
                    financial_data["income_statement"] = income_df.to_dict("records")
                    self.logger.debug(
                        f"✅ {ts_code} 利润表数据获取成功: {len(income_df)} 条记录"
                    )
                else:
                    self.logger.debug(f"⚠️ {ts_code} 利润表数据为空")
            except Exception as e:
                self.logger.warning(f"❌ 获取{ts_code}利润表数据失败: {e}")

            # 2. 获取资产负债表数据 (balance sheet)
            try:
                balance_df = await asyncio.to_thread(
                    self.api.balancesheet, **query_params
                )
                if balance_df is not None and not balance_df.empty:
                    financial_data["balance_sheet"] = balance_df.to_dict("records")
                    self.logger.debug(
                        f"✅ {ts_code} 资产负债表数据获取成功: {len(balance_df)} 条记录"
                    )
                else:
                    self.logger.debug(f"⚠️ {ts_code} 资产负债表数据为空")
            except Exception as e:
                self.logger.warning(f"❌ 获取{ts_code}资产负债表数据失败: {e}")

            # 3. 获取现金流量表数据 (cash flow statement)
            try:
                cashflow_df = await asyncio.to_thread(self.api.cashflow, **query_params)
                if cashflow_df is not None and not cashflow_df.empty:
                    financial_data["cashflow_statement"] = cashflow_df.to_dict(
                        "records"
                    )
                    self.logger.debug(
                        f"✅ {ts_code} 现金流量表数据获取成功: {len(cashflow_df)} 条记录"
                    )
                else:
                    self.logger.debug(f"⚠️ {ts_code} 现金流量表数据为空")
            except Exception as e:
                self.logger.warning(f"❌ 获取{ts_code}现金流量表数据失败: {e}")

            # 4. 获取财务指标数据 (financial indicators)
            try:
                indicator_df = await asyncio.to_thread(
                    self.api.fina_indicator, **query_params
                )
                if indicator_df is not None and not indicator_df.empty:
                    financial_data["financial_indicators"] = indicator_df.to_dict(
                        "records"
                    )
                    self.logger.debug(
                        f"✅ {ts_code} 财务指标数据获取成功: {len(indicator_df)} 条记录"
                    )
                else:
                    self.logger.debug(f"⚠️ {ts_code} 财务指标数据为空")
            except Exception as e:
                self.logger.warning(f"❌ 获取{ts_code}财务指标数据失败: {e}")

            # 5. 获取主营业务构成数据 (可选)
            try:
                mainbz_df = await asyncio.to_thread(
                    self.api.fina_mainbz, **query_params
                )
                if mainbz_df is not None and not mainbz_df.empty:
                    financial_data["main_business"] = mainbz_df.to_dict("records")
                    self.logger.debug(
                        f"✅ {ts_code} 主营业务构成数据获取成功: {len(mainbz_df)} 条记录"
                    )
                else:
                    self.logger.debug(f"⚠️ {ts_code} 主营业务构成数据为空")
            except Exception as e:
                self.logger.debug(
                    f"获取{ts_code}主营业务构成数据失败: {e}"
                )  # 主营业务数据不是必需的，保持debug级别

            # 6. 获取分红送股数据 (dividend) - 5210积分可用
            try:
                # dividend接口不需要period参数，使用end_date和limit
                dividend_params = {"ts_code": ts_code, "limit": limit}
                dividend_df = await asyncio.to_thread(
                    self.api.dividend, **dividend_params
                )
                if dividend_df is not None and not dividend_df.empty:
                    financial_data["dividend"] = dividend_df.to_dict("records")
                    # 计算股息率
                    latest_dividend = dividend_df.iloc[0]
                    dividend_yield = latest_dividend.get("dividend_yield", 0)
                    cash_div = latest_dividend.get("cash_div", 0)
                    financial_data["latest_dividend_yield"] = dividend_yield
                    financial_data["latest_cash_div"] = cash_div
                    self.logger.debug(
                        f"✅ {ts_code} 分红送股数据获取成功: {len(dividend_df)} 条记录, "
                        f"最新股息率: {dividend_yield}%, 现金分红: {cash_div}元"
                    )
                else:
                    self.logger.debug(f"⚠️ {ts_code} 分红送股数据为空")
            except Exception as e:
                self.logger.debug(
                    f"获取{ts_code}分红送股数据失败: {e}"
                )  # 分红数据不是必需的，保持debug级别

            if financial_data:
                # 标准化财务数据
                standardized_data = self._standardize_tushare_financial_data(
                    financial_data, ts_code
                )
                self.logger.info(
                    f"✅ {ts_code} Tushare财务数据获取完成: {len(financial_data)} 个数据集"
                )
                return standardized_data
            else:
                self.logger.warning(f"⚠️ {ts_code} 未获取到任何Tushare财务数据")
                return None

        except Exception as e:
            self.logger.error(f"❌ 获取Tushare财务数据失败 symbol={symbol}: {e}")
            return None

    async def get_financial_data_by_period(
        self,
        symbol: str,
        start_period: Optional[str] = None,
        end_period: Optional[str] = None,
        report_type: str = "quarterly",
    ) -> Optional[List[Dict[str, Any]]]:
        """
        按时间范围获取财务数据

        Args:
            symbol: 股票代码
            start_period: 开始报告期 (YYYYMMDD)
            end_period: 结束报告期 (YYYYMMDD)
            report_type: 报告类型 (quarterly/annual)

        Returns:
            财务数据列表，按报告期倒序排列
        """
        if not self.is_available():
            return None

        try:
            ts_code = self._normalize_ts_code(symbol)
            self.logger.debug(
                f"📊 按期间获取Tushare财务数据: {ts_code}, {start_period} - {end_period}"
            )

            # 构建查询参数
            query_params = {"ts_code": ts_code}

            if start_period:
                query_params["start_date"] = start_period
            if end_period:
                query_params["end_date"] = end_period

            # 获取利润表数据作为主要数据源
            income_df = await asyncio.to_thread(self.api.income, **query_params)

            if income_df is None or income_df.empty:
                self.logger.warning(f"⚠️ {ts_code} 指定期间无财务数据")
                return None

            # 按报告期分组获取完整财务数据
            financial_data_list = []

            for _, income_row in income_df.iterrows():
                period = (
                    str(income_row["end_date"])
                    if income_row["end_date"] is not None
                    else None
                )

                # 获取该期间的完整财务数据
                if period is None:
                    continue
                period_data = await self.get_financial_data(
                    symbol=symbol, period=period, limit=1
                )

                if period_data:
                    financial_data_list.append(period_data)

            self.logger.info(
                f"✅ {ts_code} 按期间获取财务数据完成: {len(financial_data_list)} 个报告期"
            )
            return financial_data_list

        except Exception as e:
            self.logger.error(f"❌ 按期间获取Tushare财务数据失败 symbol={symbol}: {e}")
            return None

    async def get_financial_indicators_only(
        self, symbol: str, limit: int = 4
    ) -> Optional[Dict[str, Any]]:
        """
        仅获取财务指标数据（轻量级接口）

        Args:
            symbol: 股票代码
            limit: 获取记录数量

        Returns:
            财务指标数据
        """
        if not self.is_available():
            return None

        try:
            ts_code = self._normalize_ts_code(symbol)

            # 仅获取财务指标
            indicator_df = await asyncio.to_thread(
                self.api.fina_indicator, ts_code=ts_code, limit=limit
            )

            if indicator_df is not None and not indicator_df.empty:
                indicators = indicator_df.to_dict("records")

                return {
                    "symbol": symbol,
                    "ts_code": ts_code,
                    "financial_indicators": indicators,
                    "data_source": "tushare",
                    "updated_at": datetime.utcnow(),
                }

            return None

        except Exception as e:
            self.logger.error(f"❌ 获取Tushare财务指标失败 symbol={symbol}: {e}")
            return None

    def _standardize_tushare_financial_data(
        self, financial_data: Dict[str, Any], ts_code: str
    ) -> Dict[str, Any]:
        """
        标准化Tushare财务数据

        Args:
            financial_data: 原始财务数据字典
            ts_code: Tushare股票代码

        Returns:
            标准化后的财务数据
        """
        try:
            # 获取最新的数据记录（第一条记录通常是最新的）
            latest_income = (
                financial_data.get("income_statement", [{}])[0]
                if financial_data.get("income_statement")
                else {}
            )
            latest_balance = (
                financial_data.get("balance_sheet", [{}])[0]
                if financial_data.get("balance_sheet")
                else {}
            )
            latest_cashflow = (
                financial_data.get("cashflow_statement", [{}])[0]
                if financial_data.get("cashflow_statement")
                else {}
            )
            latest_indicator = (
                financial_data.get("financial_indicators", [{}])[0]
                if financial_data.get("financial_indicators")
                else {}
            )

            # 提取基础信息
            symbol = ts_code.split(".")[0] if "." in ts_code else ts_code
            report_period = (
                latest_income.get("end_date")
                or latest_balance.get("end_date")
                or latest_cashflow.get("end_date")
            )
            ann_date = (
                latest_income.get("ann_date")
                or latest_balance.get("ann_date")
                or latest_cashflow.get("ann_date")
            )

            # 计算 TTM 数据
            income_statements = financial_data.get("income_statement", [])
            revenue_ttm = self._calculate_ttm_from_tushare(income_statements, "revenue")
            net_profit_ttm = self._calculate_ttm_from_tushare(
                income_statements, "n_income_attr_p"
            )

            standardized_data = {
                # 基础信息
                "symbol": symbol,
                "ts_code": ts_code,
                "report_period": report_period,
                "ann_date": ann_date,
                "report_type": self._determine_report_type(report_period or ""),
                # 利润表核心指标
                "revenue": self._safe_float(
                    latest_income.get("revenue")
                ),  # 营业收入（单期）
                "revenue_ttm": revenue_ttm,  # 营业收入（TTM）
                "oper_rev": self._safe_float(latest_income.get("oper_rev")),  # 营业收入
                "net_income": self._safe_float(
                    latest_income.get("n_income")
                ),  # 净利润（单期）
                "net_profit": self._safe_float(
                    latest_income.get("n_income_attr_p")
                ),  # 归属母公司净利润（单期）
                "net_profit_ttm": net_profit_ttm,  # 归属母公司净利润（TTM）
                "oper_profit": self._safe_float(
                    latest_income.get("oper_profit")
                ),  # 营业利润
                "total_profit": self._safe_float(
                    latest_income.get("total_profit")
                ),  # 利润总额
                "oper_cost": self._safe_float(
                    latest_income.get("oper_cost")
                ),  # 营业成本
                "oper_exp": self._safe_float(latest_income.get("oper_exp")),  # 营业费用
                "admin_exp": self._safe_float(
                    latest_income.get("admin_exp")
                ),  # 管理费用
                "fin_exp": self._safe_float(latest_income.get("fin_exp")),  # 财务费用
                "rd_exp": self._safe_float(latest_income.get("rd_exp")),  # 研发费用
                # 资产负债表核心指标
                "total_assets": self._safe_float(
                    latest_balance.get("total_assets")
                ),  # 总资产
                "total_liab": self._safe_float(
                    latest_balance.get("total_liab")
                ),  # 总负债
                "total_equity": self._safe_float(
                    latest_balance.get("total_hldr_eqy_exc_min_int")
                ),  # 股东权益
                "total_cur_assets": self._safe_float(
                    latest_balance.get("total_cur_assets")
                ),  # 流动资产
                "total_nca": self._safe_float(
                    latest_balance.get("total_nca")
                ),  # 非流动资产
                "total_cur_liab": self._safe_float(
                    latest_balance.get("total_cur_liab")
                ),  # 流动负债
                "total_ncl": self._safe_float(
                    latest_balance.get("total_ncl")
                ),  # 非流动负债
                "money_cap": self._safe_float(
                    latest_balance.get("money_cap")
                ),  # 货币资金
                "accounts_receiv": self._safe_float(
                    latest_balance.get("accounts_receiv")
                ),  # 应收账款
                "inventories": self._safe_float(
                    latest_balance.get("inventories")
                ),  # 存货
                "fix_assets": self._safe_float(
                    latest_balance.get("fix_assets")
                ),  # 固定资产
                # 现金流量表核心指标
                "n_cashflow_act": self._safe_float(
                    latest_cashflow.get("n_cashflow_act")
                ),  # 经营活动现金流
                "n_cashflow_inv_act": self._safe_float(
                    latest_cashflow.get("n_cashflow_inv_act")
                ),  # 投资活动现金流
                "n_cashflow_fin_act": self._safe_float(
                    latest_cashflow.get("n_cashflow_fin_act")
                ),  # 筹资活动现金流
                "c_cash_equ_end_period": self._safe_float(
                    latest_cashflow.get("c_cash_equ_end_period")
                ),  # 期末现金
                "c_cash_equ_beg_period": self._safe_float(
                    latest_cashflow.get("c_cash_equ_beg_period")
                ),  # 期初现金
                # 财务指标
                "roe": self._safe_float(latest_indicator.get("roe")),  # 净资产收益率
                "roa": self._safe_float(latest_indicator.get("roa")),  # 总资产收益率
                "roe_waa": self._safe_float(
                    latest_indicator.get("roe_waa")
                ),  # 加权平均净资产收益率
                "roe_dt": self._safe_float(
                    latest_indicator.get("roe_dt")
                ),  # 净资产收益率(扣除非经常损益)
                "roa2": self._safe_float(
                    latest_indicator.get("roa2")
                ),  # 总资产收益率(扣除非经常损益)
                "gross_margin": self._safe_float(
                    latest_indicator.get("grossprofit_margin")
                ),  # 销售毛利率
                "netprofit_margin": self._safe_float(
                    latest_indicator.get("netprofit_margin")
                ),  # 销售净利率
                "cogs_of_sales": self._safe_float(
                    latest_indicator.get("cogs_of_sales")
                ),  # 销售成本率
                "expense_of_sales": self._safe_float(
                    latest_indicator.get("expense_of_sales")
                ),  # 销售期间费用率
                "profit_to_gr": self._safe_float(
                    latest_indicator.get("profit_to_gr")
                ),  # 净利润/营业总收入
                "saleexp_to_gr": self._safe_float(
                    latest_indicator.get("saleexp_to_gr")
                ),  # 销售费用/营业总收入
                "adminexp_of_gr": self._safe_float(
                    latest_indicator.get("adminexp_of_gr")
                ),  # 管理费用/营业总收入
                "finaexp_of_gr": self._safe_float(
                    latest_indicator.get("finaexp_of_gr")
                ),  # 财务费用/营业总收入
                "debt_to_assets": self._safe_float(
                    latest_indicator.get("debt_to_assets")
                ),  # 资产负债率
                "assets_to_eqt": self._safe_float(
                    latest_indicator.get("assets_to_eqt")
                ),  # 权益乘数
                "dp_assets_to_eqt": self._safe_float(
                    latest_indicator.get("dp_assets_to_eqt")
                ),  # 权益乘数(杜邦分析)
                "ca_to_assets": self._safe_float(
                    latest_indicator.get("ca_to_assets")
                ),  # 流动资产/总资产
                "nca_to_assets": self._safe_float(
                    latest_indicator.get("nca_to_assets")
                ),  # 非流动资产/总资产
                "current_ratio": self._safe_float(
                    latest_indicator.get("current_ratio")
                ),  # 流动比率
                "quick_ratio": self._safe_float(
                    latest_indicator.get("quick_ratio")
                ),  # 速动比率
                "cash_ratio": self._safe_float(
                    latest_indicator.get("cash_ratio")
                ),  # 现金比率
                # 原始数据保留（用于详细分析）
                "raw_data": {
                    "income_statement": financial_data.get("income_statement", []),
                    "balance_sheet": financial_data.get("balance_sheet", []),
                    "cashflow_statement": financial_data.get("cashflow_statement", []),
                    "financial_indicators": financial_data.get(
                        "financial_indicators", []
                    ),
                    "main_business": financial_data.get("main_business", []),
                },
                # 元数据
                "data_source": "tushare",
                "updated_at": datetime.utcnow(),
            }

            return standardized_data

        except Exception as e:
            self.logger.error(f"❌ 标准化Tushare财务数据失败: {e}")
            return {
                "symbol": ts_code.split(".")[0] if "." in ts_code else ts_code,
                "data_source": "tushare",
                "updated_at": datetime.utcnow(),
                "error": str(e),
            }

    def _calculate_ttm_from_tushare(
        self, income_statements: list, field: str
    ) -> Optional[float]:
        """
        从 Tushare 利润表数据计算 TTM（最近12个月）

        支持多种回退策略以提高计算成功率：
        1. 标准TTM计算：基准年报 + (本期累计 - 去年同期累计)
        2. 回退策略A：累计最近4个季度单季数据
        3. 回退策略B：使用最近可用年报数据
        4. 回退策略C：年化当前季度数据（仅限Q1）

        Tushare 利润表数据是累计值（从年初到报告期的累计）：
        - 2025Q1 (20250331): 2025年1-3月累计
        - 2025Q2 (20250630): 2025年1-6月累计
        - 2025Q3 (20250930): 2025年1-9月累计
        - 2025Q4 (20251231): 2025年1-12月累计（年报）

        Args:
            income_statements: 利润表数据列表（按报告期倒序）
            field: 字段名（'revenue' 或 'n_income_attr_p'）

        Returns:
            TTM 值，如果无法计算则返回 None
        """
        if not income_statements or len(income_statements) < 1:
            return None

        try:
            latest = income_statements[0]
            latest_period = latest.get("end_date")
            latest_value = self._safe_float(latest.get(field))

            if not latest_period or latest_value is None:
                return None

            month_day = latest_period[4:8]

            # 如果最新期是年报（1231），直接使用
            if month_day == "1231":
                self.logger.debug(
                    f"✅ TTM计算: 使用年报数据 {latest_period} = {latest_value:.2f}"
                )
                return latest_value

            # 尝试标准TTM计算
            ttm_result = self._try_standard_ttm(
                income_statements, field, latest, latest_period, latest_value
            )
            if ttm_result is not None:
                return ttm_result

            # 回退策略A：累计最近4个季度
            ttm_result = self._try_quarterly_sum_ttm(
                income_statements, field, latest_period
            )
            if ttm_result is not None:
                return ttm_result

            # 回退策略B：使用最近可用年报
            ttm_result = self._try_latest_annual_ttm(
                income_statements, field, latest_period
            )
            if ttm_result is not None:
                return ttm_result

            # 回退策略C：年化当前季度（仅限Q1，准确性最低）
            if month_day == "0331":
                ttm_result = self._try_annualized_ttm(latest_value, latest_period)
                if ttm_result is not None:
                    return ttm_result

            self.logger.warning(
                f"⚠️ TTM计算: 所有策略均失败，字段={field}，最新期={latest_period}"
            )
            return None

        except Exception as e:
            self.logger.warning(f"❌ TTM计算异常: {e}")
            return None

    def _try_standard_ttm(
        self,
        income_statements: list,
        field: str,
        latest: dict,
        latest_period: str,
        latest_value: float,
    ) -> Optional[float]:
        """标准TTM计算：基准年报 + (本期累计 - 去年同期累计)"""
        try:
            latest_year = latest_period[:4]
            last_year = str(int(latest_year) - 1)
            last_year_same_period = last_year + latest_period[4:]

            # 查找去年同期
            last_year_same = None
            for stmt in income_statements:
                if stmt.get("end_date") == last_year_same_period:
                    last_year_same = stmt
                    break

            if not last_year_same:
                self.logger.debug(f"标准TTM: 缺少去年同期数据 {last_year_same_period}")
                return None

            last_year_value = self._safe_float(last_year_same.get(field))
            if last_year_value is None:
                self.logger.debug(
                    f"标准TTM: 去年同期数据值为空 {last_year_same_period}"
                )
                return None

            # 查找基准年报
            base_period = None
            for stmt in income_statements:
                period = stmt.get("end_date")
                if period and period > last_year_same_period and period[4:8] == "1231":
                    base_period = stmt
                    break

            if not base_period:
                self.logger.debug(
                    f"标准TTM: 缺少基准年报（需要在 {last_year_same_period} 之后的年报）"
                )
                return None

            base_value = self._safe_float(base_period.get(field))
            if base_value is None:
                self.logger.debug(
                    f"标准TTM: 基准年报数据值为空 {base_period.get('end_date')}"
                )
                return None

            ttm_value = base_value + (latest_value - last_year_value)
            self.logger.debug(
                f"✅ 标准TTM: {base_period.get('end_date')}({base_value:.2f}) + "
                f"({latest_period}({latest_value:.2f}) - {last_year_same_period}({last_year_value:.2f})) = {ttm_value:.2f}"
            )
            return ttm_value

        except Exception as e:
            self.logger.debug(f"标准TTM计算异常: {e}")
            return None

    def _try_quarterly_sum_ttm(
        self, income_statements: list, field: str, latest_period: str
    ) -> Optional[float]:
        """
        回退策略A：累计最近4个季度的单季数据
        通过 本季累计 - 上季累计 计算每个季度的单季值，然后累加
        """
        try:
            quarterly_values = []
            periods_found = []

            # 按报告期排序（倒序）
            sorted_stmts = sorted(
                income_statements, key=lambda x: x.get("end_date", ""), reverse=True
            )

            for i, stmt in enumerate(sorted_stmts):
                if len(quarterly_values) >= 4:
                    break

                period = stmt.get("end_date")
                if not period:
                    continue

                cumulative_value = self._safe_float(stmt.get(field))
                if cumulative_value is None:
                    continue

                month_day = period[4:8]

                if month_day == "1231":
                    # Q4: 年报累计 - Q3累计
                    q3_period = period[:4] + "0930"
                    q3_value = self._find_period_value(sorted_stmts, q3_period, field)
                    if q3_value is not None:
                        quarterly_value = cumulative_value - q3_value
                        quarterly_values.append(quarterly_value)
                        periods_found.append(f"Q4({period})")
                    else:
                        # 如果没有Q3数据，尝试使用年报数据除以4（粗略估计）
                        continue

                elif month_day == "0930":
                    # Q3: Q3累计 - Q2累计
                    q2_period = period[:4] + "0630"
                    q2_value = self._find_period_value(sorted_stmts, q2_period, field)
                    if q2_value is not None:
                        quarterly_value = cumulative_value - q2_value
                        quarterly_values.append(quarterly_value)
                        periods_found.append(f"Q3({period})")

                elif month_day == "0630":
                    # Q2: Q2累计 - Q1累计
                    q1_period = period[:4] + "0331"
                    q1_value = self._find_period_value(sorted_stmts, q1_period, field)
                    if q1_value is not None:
                        quarterly_value = cumulative_value - q1_value
                        quarterly_values.append(quarterly_value)
                        periods_found.append(f"Q2({period})")

                elif month_day == "0331":
                    # Q1: 直接使用Q1累计值
                    quarterly_values.append(cumulative_value)
                    periods_found.append(f"Q1({period})")

            if len(quarterly_values) >= 4:
                ttm_value = sum(quarterly_values[:4])
                self.logger.debug(
                    f"✅ 季度累加TTM: {' + '.join(periods_found[:4])} = {ttm_value:.2f}"
                )
                return ttm_value
            elif len(quarterly_values) >= 2:
                # 如果只有2-3个季度数据，进行年化估算
                avg_quarterly = sum(quarterly_values) / len(quarterly_values)
                ttm_value = avg_quarterly * 4
                self.logger.debug(
                    f"✅ 季度年化TTM（{len(quarterly_values)}季度平均×4）: {ttm_value:.2f}"
                )
                return ttm_value

            return None

        except Exception as e:
            self.logger.debug(f"季度累加TTM计算异常: {e}")
            return None

    def _find_period_value(
        self, statements: list, period: str, field: str
    ) -> Optional[float]:
        """在报表列表中查找指定期间的字段值"""
        for stmt in statements:
            if stmt.get("end_date") == period:
                return self._safe_float(stmt.get(field))
        return None

    def _try_latest_annual_ttm(
        self, income_statements: list, field: str, latest_period: str
    ) -> Optional[float]:
        """
        回退策略B：使用最近可用的年报数据
        当无法计算精确TTM时，使用最近年报作为参考值
        """
        try:
            for stmt in income_statements:
                period = stmt.get("end_date")
                if period and period[4:8] == "1231":
                    value = self._safe_float(stmt.get(field))
                    if value is not None:
                        self.logger.debug(
                            f"✅ 年报回退TTM: 使用 {period} 年报数据 = {value:.2f}（非精确TTM）"
                        )
                        return value
            return None
        except Exception as e:
            self.logger.debug(f"年报回退TTM计算异常: {e}")
            return None

    def _try_annualized_ttm(
        self, q1_value: float, latest_period: str
    ) -> Optional[float]:
        """
        回退策略C：年化Q1数据（准确性最低）
        仅当最新期是Q1且无其他数据可用时使用
        """
        try:
            ttm_value = q1_value * 4
            self.logger.debug(
                f"✅ Q1年化TTM: {latest_period}({q1_value:.2f}) × 4 = {ttm_value:.2f}（粗略估计）"
            )
            return ttm_value
        except Exception as e:
            self.logger.debug(f"Q1年化TTM计算异常: {e}")
            return None

    def _determine_report_type(self, report_period: str) -> str:
        """根据报告期确定报告类型"""
        if not report_period:
            return "quarterly"

        try:
            # 报告期格式: YYYYMMDD
            month_day = report_period[4:8]
            if month_day == "1231":
                return "annual"  # 年报
            else:
                return "quarterly"  # 季报
        except:
            return "quarterly"

    def _safe_float(self, value) -> Optional[float]:
        """安全转换为浮点数，处理各种异常情况"""
        if value is None:
            return None

        try:
            # 处理字符串类型
            if isinstance(value, str):
                value = value.strip()
                if not value or value.lower() in ["nan", "null", "none", "--", ""]:
                    return None
                # 移除可能的单位符号
                value = value.replace(",", "").replace("万", "").replace("亿", "")

            # 处理数值类型
            if isinstance(value, (int, float)):
                # 检查是否为NaN
                if isinstance(value, float) and (value != value):  # NaN检查
                    return None
                return float(value)

            # 尝试转换
            return float(value)

        except (ValueError, TypeError, AttributeError):
            return None

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
