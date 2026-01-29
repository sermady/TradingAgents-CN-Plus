# -*- coding: utf-8 -*-
"""
统一的Tushare数据提供器
合并app层和tradingagents层的所有优势功能
"""

from typing import Optional, Dict, Any, List, Union
from datetime import datetime, date, timedelta
import pandas as pd
import asyncio
import logging
import os
import threading
import json

from ..base_provider import BaseStockDataProvider
from tradingagents.config.providers_config import get_provider_config

try:
    import tushare as ts

    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    ts = None

logger = logging.getLogger(__name__)


BATCH_QUOTES_CACHE = {"data": None, "timestamp": None, "lock": threading.Lock()}
BATCH_CACHE_TTL_SECONDS = 30


def _is_batch_cache_valid() -> bool:
    """检查批量缓存是否有效"""
    if BATCH_QUOTES_CACHE["data"] is None or BATCH_QUOTES_CACHE["timestamp"] is None:
        return False
    age = (datetime.now() - BATCH_QUOTES_CACHE["timestamp"]).total_seconds()
    return age < BATCH_CACHE_TTL_SECONDS


def _get_cached_batch_quotes() -> Optional[Dict[str, Dict[str, Any]]]:
    """获取缓存的批量行情"""
    if _is_batch_cache_valid():
        return BATCH_QUOTES_CACHE["data"]
    return None


def _set_cached_batch_quotes(data: Dict[str, Dict[str, Any]]) -> None:
    """设置批量行情缓存"""
    with BATCH_QUOTES_CACHE["lock"]:
        BATCH_QUOTES_CACHE["data"] = data
        BATCH_QUOTES_CACHE["timestamp"] = datetime.now()


def _invalidate_batch_cache() -> None:
    """使批量缓存失效"""
    with BATCH_QUOTES_CACHE["lock"]:
        BATCH_QUOTES_CACHE["data"] = None
        BATCH_QUOTES_CACHE["timestamp"] = None


class TushareProvider(BaseStockDataProvider):
    """
    统一的Tushare数据提供器
    合并app层和tradingagents层的所有优势功能
    """

    def __init__(self):
        super().__init__("Tushare")
        self.api = None
        self.config = get_provider_config("tushare")
        self.token_source = None  # 记录 Token 来源: 'database' 或 'env'

        if not TUSHARE_AVAILABLE:
            self.logger.error("❌ Tushare库未安装，请运行: pip install tushare")

        # 🔥 初始化时尝试连接，解决 connected=False 问题
        self.connect_sync()

    def _get_token_from_database(self) -> Optional[str]:
        """
        从数据库读取 Tushare Token

        优先级：数据库配置 > 环境变量
        这样用户在 Web 后台修改配置后可以立即生效
        """
        try:
            self.logger.info("🔍 [DB查询] 开始从数据库读取 Token...")
            from app.core.database import get_mongo_db_sync

            db = get_mongo_db_sync()
            config_collection = db.system_configs

            # 获取最新的激活配置
            self.logger.info("🔍 [DB查询] 查询 is_active=True 的配置...")
            config_data = config_collection.find_one(
                {"is_active": True}, sort=[("version", -1)]
            )

            if config_data:
                self.logger.info(
                    f"✅ [DB查询] 找到激活配置，版本: {config_data.get('version')}"
                )
                if config_data.get("data_source_configs"):
                    self.logger.info(
                        f"✅ [DB查询] 配置中有 {len(config_data['data_source_configs'])} 个数据源"
                    )
                    for ds_config in config_data["data_source_configs"]:
                        ds_type = ds_config.get("type")
                        self.logger.info(f"🔍 [DB查询] 检查数据源: {ds_type}")
                        if ds_type == "tushare":
                            api_key = ds_config.get("api_key")
                            self.logger.info(
                                f"✅ [DB查询] 找到 Tushare 配置，api_key 长度: {len(api_key) if api_key else 0}"
                            )
                            if api_key and not api_key.startswith("your_"):
                                self.logger.info(
                                    f"✅ [DB查询] Token 有效 (长度: {len(api_key)})"
                                )
                                return api_key
                            else:
                                self.logger.warning(f"⚠️ [DB查询] Token 无效或为占位符")
                else:
                    self.logger.warning("⚠️ [DB查询] 配置中没有 data_source_configs")
            else:
                self.logger.warning("⚠️ [DB查询] 未找到激活的配置")

            self.logger.info("⚠️ [DB查询] 数据库中未找到有效的 Tushare Token")
        except Exception as e:
            self.logger.error(f"❌ [DB查询] 从数据库读取 Token 失败: {e}")
            import traceback

            self.logger.error(f"❌ [DB查询] 堆栈跟踪:\n{traceback.format_exc()}")

        return None

    def connect_sync(self) -> bool:
        """同步连接到Tushare"""
        if not TUSHARE_AVAILABLE:
            self.logger.error("❌ Tushare库不可用")
            return False

        # 🔥 检查TUSHARE_ENABLED开关
        tushare_enabled_str = os.getenv("TUSHARE_ENABLED", "true").lower()
        tushare_enabled = tushare_enabled_str in ("true", "1", "yes", "on")

        if not tushare_enabled:
            self.logger.info("⏸️ [Tushare] TUSHARE_ENABLED=false，跳过Tushare数据源")
            self.connected = False
            return False

        # 测试连接超时时间（秒）- 只是测试连通性，不需要很长时间
        test_timeout = 10

        try:
            # 🔥 优先从数据库读取 Token
            self.logger.info("🔍 [步骤1] 开始从数据库读取 Tushare Token...")
            db_token = self._get_token_from_database()
            if db_token:
                self.logger.info(
                    f"✅ [步骤1] 数据库中找到 Token (长度: {len(db_token)})"
                )
            else:
                self.logger.info("⚠️ [步骤1] 数据库中未找到 Token")

            self.logger.info("🔍 [步骤2] 读取 .env 中的 Token...")
            env_token = self.config.get("token")
            if env_token:
                self.logger.info(
                    f"✅ [步骤2] .env 中找到 Token (长度: {len(env_token)})"
                )
            else:
                self.logger.info("⚠️ [步骤2] .env 中未找到 Token")

            # 尝试数据库 Token
            if db_token:
                try:
                    self.logger.info(
                        f"🔄 [步骤3] 尝试使用数据库中的 Tushare Token (超时: {test_timeout}秒)..."
                    )
                    ts.set_token(db_token)
                    self.api = ts.pro_api()

                    # 测试连接 - 直接调用同步方法（不使用 asyncio.run）
                    try:
                        self.logger.info(
                            "🔄 [步骤3.1] 调用 stock_basic API 测试连接..."
                        )
                        test_data = self.api.stock_basic(list_status="L", limit=1)
                        self.logger.info(
                            f"✅ [步骤3.1] API 调用成功，返回数据: {len(test_data) if test_data is not None else 0} 条"
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"⚠️ [步骤3.1] 数据库 Token 测试失败: {e}，尝试降级到 .env 配置..."
                        )
                        test_data = None

                    if test_data is not None and not test_data.empty:
                        self.connected = True
                        self.token_source = "database"
                        self.logger.info(
                            f"✅ [步骤3.2] Tushare连接成功 (Token来源: 数据库)"
                        )
                        return True
                    else:
                        self.logger.warning(
                            "⚠️ [步骤3.2] 数据库 Token 测试失败，尝试降级到 .env 配置..."
                        )
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ [步骤3] 数据库 Token 连接失败: {e}，尝试降级到 .env 配置..."
                    )

            # 降级到环境变量 Token
            if env_token:
                try:
                    self.logger.info(
                        f"🔄 [步骤4] 尝试使用 .env 中的 Tushare Token (超时: {test_timeout}秒)..."
                    )
                    ts.set_token(env_token)
                    self.api = ts.pro_api()

                    # 🔥 使用官方 API 地址 (强制 HTTPS)
                    self.api._DataApi__token = env_token
                    self.api._DataApi__http_url = "https://api.tushare.pro"
                    self.logger.info(
                        "✅ [步骤4] 已设置 _DataApi__token 和 _DataApi__http_url (HTTPS) 属性"
                    )

                    # 测试连接 - 直接调用同步方法（不使用 asyncio.run）
                    try:
                        self.logger.info(
                            "🔄 [步骤4.1] 调用 stock_basic API 测试连接..."
                        )
                        test_data = self.api.stock_basic(list_status="L", limit=1)
                        self.logger.info(
                            f"✅ [步骤4.1] API 调用成功，返回数据: {len(test_data) if test_data is not None else 0} 条"
                        )
                    except Exception as e:
                        self.logger.error(f"❌ [步骤4.1] .env Token 测试异常: {e}")
                        return False

                    if test_data is not None and not test_data.empty:
                        self.connected = True
                        self.token_source = "env"
                        self.logger.info(
                            f"✅ [步骤4.2] Tushare连接成功 (Token来源: .env 环境变量)"
                        )
                        return True
                    else:
                        self.logger.error(
                            f"❌ [步骤4.2] .env Token 测试失败: API返回空数据。请检查Token是否正确: {env_token[:10]}***"
                        )
                        return False

                    if test_data is not None and not test_data.empty:
                        self.connected = True
                        self.token_source = "env"
                        self.logger.info(
                            f"✅ [步骤4.2] Tushare连接成功 (Token来源: .env 环境变量)"
                        )
                        return True
                    else:
                        self.logger.error("❌ [步骤4.2] .env Token 测试失败")
                        return False
                except Exception as e:
                    self.logger.error(f"❌ [步骤4] .env Token 连接失败: {e}")
                    return False

            # 两个都没有
            self.logger.error(
                "❌ [步骤5] Tushare token未配置，请在 Web 后台或 .env 文件中配置 TUSHARE_TOKEN"
            )
            return False

        except Exception as e:
            self.logger.error(f"❌ Tushare连接失败: {e}")
            return False

    async def connect(self) -> bool:
        """异步连接到Tushare"""
        if not TUSHARE_AVAILABLE:
            self.logger.error("❌ Tushare库不可用")
            return False

        # 测试连接超时时间（秒）- 只是测试连通性，不需要很长时间
        test_timeout = 10

        try:
            # 🔥 优先从数据库读取 Token
            db_token = self._get_token_from_database()
            env_token = self.config.get("token")

            # 尝试数据库 Token
            if db_token:
                try:
                    self.logger.info(
                        f"🔄 [步骤3] 尝试使用数据库中的 Tushare Token (超时: {test_timeout}秒)..."
                    )
                    ts.set_token(db_token)
                    self.api = ts.pro_api()

                    # 🔥 使用官方 API 地址
                    self.api._DataApi__token = db_token
                    self.api._DataApi__http_url = "https://api.tushare.pro"
                    self.logger.info(
                        "✅ [步骤3] 已设置 _DataApi__token 和 _DataApi__http_url (HTTPS) 属性"
                    )

                    # 测试连接 - 直接调用同步方法（不使用 asyncio.run）
                    try:
                        self.logger.info(
                            "🔄 [步骤3.1] 调用 stock_basic API 测试连接..."
                        )
                        # 🔥 移除 limit=1，防止偶然空数据
                        test_data = self.api.stock_basic(list_status="L", limit=5)
                        self.logger.info(
                            f"✅ [步骤3.1] API 调用成功，返回数据: {len(test_data) if test_data is not None else 0} 条"
                        )
                    except Exception as e:
                        self.logger.warning(
                            f"⚠️ [步骤3.1] 数据库 Token 测试失败: {e}，尝试降级到 .env 配置..."
                        )
                        test_data = None

                    if test_data is not None and not test_data.empty:
                        self.connected = True
                        self.logger.info(f"✅ Tushare连接成功 (Token来源: 数据库)")
                        return True
                    else:
                        self.logger.warning(
                            "⚠️ [步骤3.2] 数据库 Token 测试失败 (返回空数据)，尝试降级到 .env 配置..."
                        )
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ [步骤3] 数据库 Token 连接失败: {e}，尝试降级到 .env 配置..."
                    )

            # 降级到环境变量 Token
            if env_token:
                try:
                    self.logger.info(
                        f"🔄 [步骤4] 尝试使用 .env 中的 Tushare Token (超时: {test_timeout}秒)..."
                    )
                    ts.set_token(env_token)
                    self.api = ts.pro_api()

                    # 🔥 使用官方 API 地址
                    self.api._DataApi__token = env_token
                    self.api._DataApi__http_url = "https://api.tushare.pro"
                    self.logger.info(
                        "✅ [步骤4] 已设置 _DataApi__token 和 _DataApi__http_url (HTTPS) 属性"
                    )

                    # 测试连接（异步）- 使用超时和重试机制
                    retry_count = 0
                    max_retries = 3
                    while retry_count < max_retries:
                        try:
                            self.logger.info(
                                f"🔄 [步骤4.1] 调用 stock_basic API 测试连接... (尝试 {retry_count + 1}/{max_retries})"
                            )
                            # 🔥 移除 limit=1，使用 limit=5 防止偶然空数据
                            test_data = await asyncio.wait_for(
                                asyncio.to_thread(
                                    self.api.stock_basic, list_status="L", limit=5
                                ),
                                timeout=test_timeout,
                            )
                            self.logger.info(
                                f"✅ [步骤4.1] API 调用成功，返回数据: {len(test_data) if test_data is not None else 0} 条"
                            )
                            # 成功，退出重试循环
                            break
                        except asyncio.TimeoutError:
                            retry_count += 1
                            self.logger.warning(
                                f"⚠️ [步骤4.1] .env Token 测试超时 ({test_timeout}秒)，重试 {retry_count}/{max_retries}..."
                            )
                            if retry_count >= max_retries:
                                self.logger.error(
                                    f"❌ [步骤4.1] .env Token 测试超时 ({test_timeout}秒)，已达最大重试次数"
                                )
                                return False
                        except Exception as e:
                            retry_count += 1
                            self.logger.warning(
                                f"⚠️ [步骤4.1] .env Token 测试异常 (尝试 {retry_count}/{max_retries}): {e}"
                            )
                            if retry_count >= max_retries:
                                self.logger.error(
                                    f"❌ [步骤4.1] .env Token 测试异常: {e}"
                                )
                                return False

                    if test_data is not None and not test_data.empty:
                        self.connected = True
                        self.logger.info(
                            f"✅ [步骤4.2] Tushare连接成功 (Token来源: .env 环境变量)"
                        )
                        return True
                    else:
                        self.logger.error(
                            f"❌ [步骤4.2] .env Token 测试失败: API返回空数据"
                        )
                        return False

                    if test_data is not None and not test_data.empty:
                        self.connected = True
                        self.logger.info(
                            f"✅ Tushare连接成功 (Token来源: .env 环境变量)"
                        )
                        return True
                    else:
                        self.logger.error("❌ .env Token 测试失败")
                        return False
                except Exception as e:
                    self.logger.error(f"❌ .env Token 连接失败: {e}")
                    return False

            # 两个都没有
            self.logger.error(
                "❌ Tushare token未配置，请在 Web 后台或 .env 文件中配置 TUSHARE_TOKEN"
            )
            return False

        except Exception as e:
            self.logger.error(f"❌ Tushare连接失败: {e}")
            return False

    def is_available(self) -> bool:
        """检查Tushare是否可用"""
        return TUSHARE_AVAILABLE and self.connected and self.api is not None

    # ==================== 基础数据接口 ====================

    def get_stock_list_sync(self, market: str = None) -> Optional[pd.DataFrame]:
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
        self, market: str = None
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

            if df is None or df.empty:
                return None

            # 转换为标准格式
            stock_list = []
            for _, row in df.iterrows():
                stock_info = self.standardize_basic_info(row.to_dict())
                stock_list.append(stock_info)

            self.logger.info(f"✅ 获取股票列表: {len(stock_list)}只")
            return stock_list

        except Exception as e:
            self.logger.error(f"❌ 获取股票列表失败: {e}")
            return None

    async def get_stock_basic_info(
        self, symbol: str = None
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
                        fields="ts_code,total_mv,circ_mv,pe,pb,ps,turnover_rate,volume_ratio,pe_ttm,pb_mrq",
                        limit=1,
                    )

                    if daily_df is not None and not daily_df.empty:
                        row = daily_df.iloc[0]
                        basic_data["pe"] = row["pe"]
                        basic_data["pb"] = row["pb"]
                        basic_data["ps"] = row["ps"]
                        basic_data["pe_ttm"] = row["pe_ttm"]
                        basic_data["total_mv"] = row["total_mv"]
                        basic_data["circ_mv"] = row["circ_mv"]
                        basic_data["turnover_rate"] = row["turnover_rate"]
                        basic_data["volume_ratio"] = row["volume_ratio"]
                except Exception as daily_e:
                    self.logger.warning(f"获取 daily_basic 财务指标失败: {daily_e}")

                try:
                    fina_df = await asyncio.to_thread(
                        self.api.fina_indicator,
                        ts_code=ts_code,
                        fields="ts_code,q_profit_yoy",
                        limit=1,
                    )
                    if fina_df is not None and not fina_df.empty:
                        basic_data["q_profit_yoy"] = fina_df.iloc[0]["q_profit_yoy"]
                        self.logger.info(
                            f"🔍 [Tushare] 获取到 {ts_code} q_profit_yoy: {basic_data['q_profit_yoy']}, pe_ttm: {basic_data.get('pe_ttm')}"
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

    async def get_stock_quotes(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取单只股票实时行情

        策略：
        1. 优先尝试 ts.get_realtime_quotes (Sina/Web API) 获取秒级实时数据
        2. 失败则回退到 daily 接口 (T-1或收盘数据)
        """
        if not self.is_available():
            return None

        # 1. 尝试使用 ts.get_realtime_quotes (实时接口)
        try:
            # ts.get_realtime_quotes 是同步的，需放入线程池
            # 注意：ts.get_realtime_quotes 接受的是股票代码字符串 (如 '000001')
            # 不需要带后缀，或者它能处理
            # 这里的 symbol 可能是 '000001' 或 '000001.SZ'
            # ts.get_realtime_quotes 需要 6位代码
            code_6 = symbol.split(".")[0]

            df = await asyncio.to_thread(ts.get_realtime_quotes, code_6)

            if df is not None and not df.empty:
                row = df.iloc[0]

                # Sina 返回的数据
                # price: 当前价
                # volume: 成交量(股)
                # amount: 成交额(元)
                # date: 日期 (YYYY-MM-DD)
                # time: 时间 (HH:MM:SS)

                # 检查数据有效性 (有时返回空壳数据)
                if float(row["price"]) > 0:
                    trade_date = row["date"]

                    # 🔥 成交量单位转换：Sina实时接口返回的是"股"，转换为"手"（1手=100股）
                    volume_in_shares = float(row["volume"])
                    volume_in_lots = volume_in_shares / 100 if volume_in_shares else 0

                    return {
                        "ts_code": self._normalize_ts_code(symbol),
                        "symbol": symbol,
                        "trade_date": trade_date.replace("-", ""),  # YYYYMMDD
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["price"]),  # 当前价
                        "current_price": float(row["price"]),
                        "price": float(row["price"]),  # 兼容性字段
                        "pre_close": float(row["pre_close"]),
                        "change": float(row["price"]) - float(row["pre_close"]),
                        "pct_chg": (float(row["price"]) - float(row["pre_close"]))
                        / float(row["pre_close"])
                        * 100
                        if float(row["pre_close"]) > 0
                        else 0,
                        "volume": volume_in_lots,  # 单位：手（已转换）
                        "volume_unit": "lots",  # 明确标注单位为手
                        "amount": float(row["amount"]),  # 已经是元
                        "source": "sina_realtime",
                    }

        except Exception as e:
            self.logger.warning(f"⚠️ Tushare实时接口(Sina)获取失败，降级到daily: {e}")

        # 2. 回退到 daily 接口 (原有逻辑)
        try:
            ts_code = self._normalize_ts_code(symbol)

            # 🔥 使用 daily 接口获取最新一天的数据（更节省配额）
            from datetime import datetime, timedelta

            # 获取最近3天的数据（考虑周末和节假日）
            end_date = datetime.now().strftime("%Y%m%d")
            start_date = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")

            df = await asyncio.to_thread(
                self.api.daily,
                ts_code=ts_code,
                start_date=start_date,
                end_date=end_date,
            )

            if df is not None and not df.empty:
                # 取最新一天的数据
                row = df.iloc[0]

                # 标准化字段
                quote_data = {
                    "ts_code": row.get("ts_code"),
                    "symbol": symbol,
                    "trade_date": row.get("trade_date"),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": row.get("close"),  # 收盘价
                    "pre_close": row.get("pre_close"),
                    "change": row.get("change"),  # 涨跌额
                    "pct_chg": row.get("pct_chg"),  # 涨跌幅
                    "volume": row.get("vol"),  # 成交量（手）
                    "amount": row.get("amount"),  # 成交额（千元）
                }

                # 补充 price 字段
                standardized = self.standardize_quotes(quote_data)
                standardized["price"] = standardized.get("close", 0)
                return standardized

            return None

        except Exception as e:
            # 检查是否为限流错误
            if self._is_rate_limit_error(str(e)):
                self.logger.error(f"❌ 获取实时行情失败（限流） symbol={symbol}: {e}")
                raise  # 抛出限流错误，让上层处理

            self.logger.error(f"❌ 获取实时行情失败 symbol={symbol}: {e}")
            return None

        except Exception as e:
            # 检查是否为限流错误
            if self._is_rate_limit_error(str(e)):
                self.logger.error(f"❌ 获取实时行情失败（限流） symbol={symbol}: {e}")
                raise  # 抛出限流错误，让上层处理

            self.logger.error(f"❌ 获取实时行情失败 symbol={symbol}: {e}")
            return None

    async def get_realtime_quotes_batch(
        self, force_refresh: bool = False
    ) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        批量获取全市场实时行情
        使用 rt_k 接口的通配符功能，一次性获取所有A股实时行情

        Args:
            force_refresh: 是否强制刷新缓存

        Returns:
            Dict[str, Dict]: {symbol: quote_data}
            例如: {'000001': {'close': 10.5, 'pct_chg': 1.2, ...}, ...}
        """
        if not self.is_available():
            return None

        if not force_refresh:
            cached = _get_cached_batch_quotes()
            if cached is not None:
                self.logger.debug(f"[Cache] 使用缓存的批量行情: {len(cached)} 只股票")
                return cached

        try:
            df = await asyncio.to_thread(
                self.api.rt_k, ts_code="3*.SZ,6*.SH,0*.SZ,9*.BJ"
            )

            if df is None or df.empty:
                self.logger.warning("rt_k 接口返回空数据")
                return None

            cn_tz = __import__("datetime").timezone(
                __import__("datetime").timedelta(hours=8)
            )
            now_cn = datetime.now(cn_tz)
            trade_date = now_cn.strftime("%Y%m%d")

            result = {}
            for _, row in df.iterrows():
                ts_code = row.get("ts_code")
                if not ts_code or "." not in ts_code:
                    continue

                symbol = ts_code.split(".")[0]

                close = row.get("close")
                pre_close = row.get("pre_close")

                pct_chg = None
                change_val = None
                if close and pre_close:
                    try:
                        close_f = float(close)
                        pre_close_f = float(pre_close)
                        if pre_close_f > 0:
                            pct_chg = round(
                                ((close_f - pre_close_f) / pre_close_f) * 100, 2
                            )
                            change_val = round(close_f - pre_close_f, 2)
                    except (ValueError, TypeError):
                        pass

                quote_data = {
                    "ts_code": ts_code,
                    "symbol": symbol,
                    "name": row.get("name"),
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": close,
                    "pre_close": pre_close,
                    "volume": row.get("vol"),
                    "amount": row.get("amount"),
                    "num": row.get("num"),
                    "trade_date": trade_date,
                    "pct_chg": pct_chg,
                    "change": change_val,
                }

                result[symbol] = quote_data

            _set_cached_batch_quotes(result)
            self.logger.info(f"[RT-K] 获取到 {len(result)} 只股票的实时行情")

            return result

        except Exception as e:
            if self._is_rate_limit_error(str(e)):
                self.logger.error(f"批量获取实时行情失败（限流）: {e}")
                raise

            self.logger.error(f"批量获取实时行情失败: {e}")
            return None

    async def get_realtime_price_from_batch(self, symbol: str) -> Optional[float]:
        """
        从批量实时行情中获取单只股票价格
        使用缓存机制，避免重复调用 rt_k 接口

        Args:
            symbol: 股票代码（如 '000001.SZ' 或 '000001'）

        Returns:
            实时价格，失败返回 None
        """
        if not self.is_available():
            return None

        try:
            ts_code = self._normalize_ts_code(symbol)
            code6 = ts_code.split(".")[0]

            cached = _get_cached_batch_quotes()
            if cached is not None:
                if code6 in cached:
                    close = cached[code6].get("close")
                    return float(close) if close else None
                return None

            batch_quotes = await self.get_realtime_quotes_batch()
            if not batch_quotes:
                return None

            if code6 in batch_quotes:
                close = batch_quotes[code6].get("close")
                return float(close) if close else None

            return None

        except Exception as e:
            self.logger.warning(f"从批量行情获取 {symbol} 价格失败: {e}")
            return None

    def get_batch_cache_status(self) -> Dict[str, Any]:
        """获取批量行情缓存状态"""
        if (
            BATCH_QUOTES_CACHE["data"] is None
            or BATCH_QUOTES_CACHE["timestamp"] is None
        ):
            return {
                "cached": False,
                "count": 0,
                "age_seconds": None,
                "ttl_seconds": BATCH_CACHE_TTL_SECONDS,
            }

        age = (datetime.now() - BATCH_QUOTES_CACHE["timestamp"]).total_seconds()
        return {
            "cached": True,
            "count": len(BATCH_QUOTES_CACHE["data"]),
            "age_seconds": round(age, 1),
            "ttl_seconds": BATCH_CACHE_TTL_SECONDS,
            "is_valid": age < BATCH_CACHE_TTL_SECONDS,
        }

    def invalidate_batch_cache(self) -> None:
        """使批量缓存失效"""
        _invalidate_batch_cache()

    def _is_rate_limit_error(self, error_msg: str) -> bool:
        """检测是否为 API 限流错误"""
        rate_limit_keywords = [
            "每分钟最多访问",
            "每分钟最多",
            "rate limit",
            "too many requests",
            "访问频率",
            "请求过于频繁",
        ]
        error_msg_lower = error_msg.lower()
        return any(keyword in error_msg_lower for keyword in rate_limit_keywords)

    async def get_historical_data(
        self,
        symbol: str,
        start_date: Union[str, date],
        end_date: Union[str, date] = None,
        period: str = "daily",
    ) -> Optional[pd.DataFrame]:
        """
        获取历史数据

        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            period: 数据周期 (daily/weekly/monthly)
        """
        if not self.is_available():
            return None

        try:
            ts_code = self._normalize_ts_code(symbol)

            # 格式化日期
            start_str = self._format_date(start_date)
            end_str = (
                self._format_date(end_date)
                if end_date
                else datetime.now().strftime("%Y%m%d")
            )

            # 🔧 使用 pro_bar 接口获取前复权数据（与同花顺一致）
            # 注意：Tushare 的 daily/weekly/monthly 接口不支持复权
            # 必须使用 ts.pro_bar() 函数并指定 adj='qfq' 参数

            # 周期映射
            freq_map = {"daily": "D", "weekly": "W", "monthly": "M"}
            freq = freq_map.get(period, "D")

            # 使用 ts.pro_bar() 函数获取前复权数据
            # 注意：pro_bar 是 tushare 模块的函数，不是 api 对象的方法
            # 🔥 FIX: 添加异常处理，如果 pro_bar 失败也尝试备用方案
            df = None
            try:
                df = await asyncio.to_thread(
                    ts.pro_bar,
                    ts_code=ts_code,
                    api=self.api,  # 传入 api 对象
                    start_date=start_str,
                    end_date=end_str,
                    freq=freq,
                    adj="qfq",  # 前复权（与同花顺一致）
                )
            except Exception as pro_bar_e:
                self.logger.warning(
                    f"⚠️ Tushare pro_bar 调用异常: {pro_bar_e} "
                    f"symbol={symbol}, ts_code={ts_code}"
                )

            if df is None or df.empty:
                if df is None:
                    self.logger.warning(
                        f"⚠️ Tushare pro_bar 调用失败或返回 None: "
                        f"symbol={symbol}, ts_code={ts_code}, "
                        f"period={period}, start={start_str}, end={end_str}"
                    )
                else:
                    self.logger.warning(
                        f"⚠️ Tushare pro_bar 返回空数据: symbol={symbol}, ts_code={ts_code}, "
                        f"period={period}, start={start_str}, end={end_str}"
                    )

                # 🔥 FIX: 尝试使用 api.daily 作为备用方案（5210积分可用）
                try:
                    self.logger.info(
                        f"🔄 [备用方案] 尝试使用 api.daily 获取数据: {ts_code}"
                    )
                    df = await asyncio.to_thread(
                        self.api.daily,
                        ts_code=ts_code,
                        start_date=start_str,
                        end_date=end_str,
                    )

                    if df is not None and not df.empty:
                        self.logger.info(
                            f"✅ [备用方案成功] api.daily 返回 {len(df)} 条记录"
                        )
                        # 注意：api.daily 返回的是非复权数据
                    else:
                        self.logger.warning(f"⚠️ [备用方案失败] api.daily 也返回空数据")
                        self.logger.warning(
                            f"💡 可能原因: "
                            f"1) 该股票在此期间无交易数据 "
                            f"2) 日期范围不正确 (当前: {start_str} 至 {end_str}) "
                            f"3) 股票代码格式错误 (当前: {ts_code}) "
                            f"4) Tushare API 限制或积分不足"
                        )
                        return None
                except Exception as daily_e:
                    self.logger.warning(
                        f"⚠️ [备用方案异常] api.daily 调用失败: {daily_e}"
                    )
                    return None

            # 数据标准化
            df = self._standardize_historical_data(df)

            self.logger.info(
                f"✅ 获取{period}历史数据: {symbol} {len(df)}条记录 (前复权 qfq)"
            )
            return df

        except Exception as e:
            import traceback

            error_details = traceback.format_exc()
            self.logger.error(
                f"❌ 获取历史数据失败 symbol={symbol}, period={period}\n"
                f"   参数: ts_code={ts_code if 'ts_code' in locals() else 'N/A'}, "
                f"start={start_str if 'start_str' in locals() else 'N/A'}, "
                f"end={end_str if 'end_str' in locals() else 'N/A'}\n"
                f"   错误类型: {type(e).__name__}\n"
                f"   错误信息: {str(e)}\n"
                f"   堆栈跟踪:\n{error_details}"
            )
            return None

    # ==================== 扩展接口 ====================

    async def get_daily_basic(self, trade_date: str) -> Optional[pd.DataFrame]:
        """获取每日基础财务数据"""
        if not self.is_available():
            return None

        try:
            date_str = trade_date.replace("-", "")
            df = await asyncio.to_thread(
                self.api.daily_basic,
                trade_date=date_str,
                fields="ts_code,total_mv,circ_mv,pe,pb,turnover_rate,volume_ratio,pe_ttm,pb_mrq",
            )

            if df is not None and not df.empty:
                self.logger.info(f"✅ 获取每日基础数据: {trade_date} {len(df)}条记录")
                return df

            return None

        except Exception as e:
            self.logger.error(f"❌ 获取每日基础数据失败 trade_date={trade_date}: {e}")
            return None

    async def find_latest_trade_date(self) -> Optional[str]:
        """查找最新交易日期"""
        if not self.is_available():
            return None

        try:
            today = datetime.now()
            for delta in range(0, 10):  # 最多回溯10天
                check_date = (today - timedelta(days=delta)).strftime("%Y%m%d")

                try:
                    df = await asyncio.to_thread(
                        self.api.daily_basic,
                        trade_date=check_date,
                        fields="ts_code",
                        limit=1,
                    )

                    if df is not None and not df.empty:
                        formatted_date = (
                            f"{check_date[:4]}-{check_date[4:6]}-{check_date[6:8]}"
                        )
                        self.logger.info(f"✅ 找到最新交易日期: {formatted_date}")
                        return formatted_date

                except Exception:
                    continue

            return None

        except Exception as e:
            self.logger.error(f"❌ 查找最新交易日期失败: {e}")
            return None

    async def get_financial_data(
        self,
        symbol: str,
        report_type: str = "quarterly",
        period: str = None,
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

    async def get_stock_news(
        self, symbol: str = None, limit: int = 10, hours_back: int = 24, src: str = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取股票新闻（需要Tushare新闻权限）

        Args:
            symbol: 股票代码，为None时获取市场新闻
            limit: 返回数量限制
            hours_back: 回溯小时数，默认24小时
            src: 新闻源，默认自动选择

        Returns:
            新闻列表
        """
        if not self.is_available():
            return None

        try:
            from datetime import datetime, timedelta

            # 计算时间范围
            end_time = datetime.now()
            start_time = end_time - timedelta(hours=hours_back)

            start_date = start_time.strftime("%Y-%m-%d %H:%M:%S")
            end_date = end_time.strftime("%Y-%m-%d %H:%M:%S")

            self.logger.debug(
                f"📰 获取Tushare新闻: symbol={symbol}, 时间范围={start_date} 到 {end_date}"
            )

            # 支持的新闻源列表（按优先级排序）
            news_sources = [
                "sina",  # 新浪财经
                "eastmoney",  # 东方财富
                "10jqka",  # 同花顺
                "wallstreetcn",  # 华尔街见闻
                "cls",  # 财联社
                "yicai",  # 第一财经
                "jinrongjie",  # 金融界
                "yuncaijing",  # 云财经
                "fenghuang",  # 凤凰新闻
            ]

            # 如果指定了数据源，优先使用
            if src and src in news_sources:
                sources_to_try = [src]
            else:
                sources_to_try = news_sources[:3]  # 默认尝试前3个源

            all_news = []

            for source in sources_to_try:
                try:
                    self.logger.debug(f"📰 尝试从 {source} 获取新闻...")

                    # 获取新闻数据
                    news_df = await asyncio.to_thread(
                        self.api.news,
                        src=source,
                        start_date=start_date,
                        end_date=end_date,
                    )

                    if news_df is not None and not news_df.empty:
                        source_news = self._process_tushare_news(
                            news_df, source, symbol, limit
                        )
                        all_news.extend(source_news)

                        self.logger.info(
                            f"✅ 从 {source} 获取到 {len(source_news)} 条新闻"
                        )

                        # 如果已经获取足够的新闻，停止尝试其他源
                        if len(all_news) >= limit:
                            break
                    else:
                        self.logger.debug(f"⚠️ {source} 未返回新闻数据")

                except Exception as e:
                    self.logger.debug(f"从 {source} 获取新闻失败: {e}")
                    continue

                # API限流 (已由上层调用者控制)
                # await asyncio.sleep(0.2)

            # 去重和排序
            if all_news:
                # 按时间排序并去重
                unique_news = self._deduplicate_news(all_news)
                sorted_news = sorted(
                    unique_news,
                    key=lambda x: x.get("publish_time", datetime.min),
                    reverse=True,
                )

                # 限制返回数量
                final_news = sorted_news[:limit]

                self.logger.info(
                    f"✅ Tushare新闻获取成功: {len(final_news)} 条（去重后）"
                )
                return final_news
            else:
                self.logger.warning("⚠️ 未获取到任何Tushare新闻数据")
                return []

        except Exception as e:
            # 如果是权限问题，给出明确提示
            if any(
                keyword in str(e).lower()
                for keyword in ["权限", "permission", "unauthorized", "access denied"]
            ):
                self.logger.warning(
                    f"⚠️ Tushare新闻接口需要单独开通权限（付费功能）: {e}"
                )
            elif "积分" in str(e) or "point" in str(e).lower():
                self.logger.warning(f"⚠️ Tushare积分不足，无法获取新闻数据: {e}")
            else:
                self.logger.error(f"❌ 获取Tushare新闻失败: {e}")
            return None

    def _process_tushare_news(
        self, news_df: pd.DataFrame, source: str, symbol: str = None, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """处理Tushare新闻数据"""
        news_list = []

        # 限制处理数量
        df_limited = news_df.head(limit * 2)  # 多获取一些，用于过滤

        for _, row in df_limited.iterrows():
            news_item = {
                "title": str(
                    row.get("title", "") or row.get("content", "")[:50] + "..."
                ),
                "content": str(row.get("content", "")),
                "summary": self._generate_summary(row.get("content", "")),
                "url": "",  # Tushare新闻接口不提供URL
                "source": self._get_source_name(source),
                "author": "",
                "publish_time": self._parse_tushare_news_time(row.get("datetime", "")),
                "category": self._classify_tushare_news(
                    row.get("channels", ""), row.get("content", "")
                ),
                "sentiment": self._analyze_news_sentiment(
                    row.get("content", ""), row.get("title", "")
                ),
                "importance": self._assess_news_importance(
                    row.get("content", ""), row.get("title", "")
                ),
                "keywords": self._extract_keywords(
                    row.get("content", ""), row.get("title", "")
                ),
                "data_source": "tushare",
                "original_source": source,
            }

            # 如果指定了股票代码，过滤相关新闻
            if symbol:
                if self._is_news_relevant_to_symbol(news_item, symbol):
                    news_list.append(news_item)
            else:
                news_list.append(news_item)

        return news_list

    def _get_source_name(self, source_code: str) -> str:
        """获取新闻源中文名称"""
        source_names = {
            "sina": "新浪财经",
            "eastmoney": "东方财富",
            "10jqka": "同花顺",
            "wallstreetcn": "华尔街见闻",
            "cls": "财联社",
            "yicai": "第一财经",
            "jinrongjie": "金融界",
            "yuncaijing": "云财经",
            "fenghuang": "凤凰新闻",
        }
        return source_names.get(source_code, source_code)

    def _generate_summary(self, content: str) -> str:
        """生成新闻摘要"""
        if not content:
            return ""

        content_str = str(content)
        if len(content_str) <= 200:
            return content_str

        # 简单的摘要生成：取前200个字符
        return content_str[:200] + "..."

    def _is_news_relevant_to_symbol(
        self, news_item: Dict[str, Any], symbol: str
    ) -> bool:
        """判断新闻是否与股票相关"""
        content = news_item.get("content", "").lower()
        title = news_item.get("title", "").lower()

        # 标准化股票代码
        symbol_clean = symbol.replace(".SH", "").replace(".SZ", "").zfill(6)

        # 关键词匹配
        return any(
            [
                symbol_clean in content,
                symbol_clean in title,
                symbol in content,
                symbol in title,
            ]
        )

    def _deduplicate_news(
        self, news_list: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """新闻去重"""
        seen_titles = set()
        unique_news = []

        for news in news_list:
            title = news.get("title", "")
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_news.append(news)

        return unique_news

    def _analyze_news_sentiment(self, content: str, title: str) -> str:
        """分析新闻情绪"""
        text = f"{title} {content}".lower()

        positive_keywords = [
            "利好",
            "上涨",
            "增长",
            "盈利",
            "突破",
            "创新高",
            "买入",
            "推荐",
        ]
        negative_keywords = [
            "利空",
            "下跌",
            "亏损",
            "风险",
            "暴跌",
            "卖出",
            "警告",
            "下调",
        ]

        positive_count = sum(1 for keyword in positive_keywords if keyword in text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _assess_news_importance(self, content: str, title: str) -> str:
        """评估新闻重要性"""
        text = f"{title} {content}".lower()

        high_importance_keywords = [
            "业绩",
            "财报",
            "重大",
            "公告",
            "监管",
            "政策",
            "并购",
            "重组",
        ]
        medium_importance_keywords = ["分析", "预测", "观点", "建议", "行业", "市场"]

        if any(keyword in text for keyword in high_importance_keywords):
            return "high"
        elif any(keyword in text for keyword in medium_importance_keywords):
            return "medium"
        else:
            return "low"

    def _extract_keywords(self, content: str, title: str) -> List[str]:
        """提取关键词"""
        text = f"{title} {content}"

        # 简单的关键词提取
        keywords = []
        common_keywords = [
            "股票",
            "公司",
            "市场",
            "投资",
            "业绩",
            "财报",
            "政策",
            "行业",
            "分析",
            "预测",
        ]

        for keyword in common_keywords:
            if keyword in text:
                keywords.append(keyword)

        return keywords[:5]  # 最多返回5个关键词

    def _parse_tushare_news_time(self, time_str: str) -> Optional[datetime]:
        """解析Tushare新闻时间"""
        if not time_str:
            return datetime.utcnow()

        try:
            # Tushare时间格式: 2018-11-21 09:30:00
            return datetime.strptime(str(time_str), "%Y-%m-%d %H:%M:%S")
        except Exception as e:
            self.logger.debug(f"解析Tushare新闻时间失败: {e}")
            return datetime.utcnow()

    def _classify_tushare_news(self, channels: str, content: str) -> str:
        """分类Tushare新闻"""
        channels = str(channels).lower()
        content = str(content).lower()

        # 根据频道和内容关键词分类
        if any(
            keyword in channels or keyword in content
            for keyword in ["公告", "业绩", "财报"]
        ):
            return "company_announcement"
        elif any(
            keyword in channels or keyword in content
            for keyword in ["政策", "监管", "央行"]
        ):
            return "policy_news"
        elif any(
            keyword in channels or keyword in content for keyword in ["行业", "板块"]
        ):
            return "industry_news"
        elif any(
            keyword in channels or keyword in content
            for keyword in ["市场", "指数", "大盘"]
        ):
            return "market_news"
        else:
            return "other"

    async def get_financial_data_by_period(
        self,
        symbol: str,
        start_period: str = None,
        end_period: str = None,
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
                period = income_row["end_date"]

                # 获取该期间的完整财务数据
                period_data = await self.get_financial_data(
                    symbol=symbol, period=period, limit=1
                )

                if period_data:
                    financial_data_list.append(period_data)

                # API限流 (已由上层调用者控制)
                # await asyncio.sleep(0.1)

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

    # ==================== 数据标准化方法 ====================

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
            # 元数据
            "data_source": "tushare",
            "data_version": 1,
            "updated_at": datetime.utcnow(),
        }

    def standardize_quotes(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """标准化实时行情数据"""
        ts_code = raw_data.get("ts_code", "")
        symbol = ts_code.split(".")[0] if "." in ts_code else ts_code

        # 🔧 统一处理 volume/vol 字段，支持多种数据源格式
        raw_volume = raw_data.get("volume") or raw_data.get("vol")

        return {
            # 基础字段
            "code": symbol,
            "symbol": symbol,
            "full_symbol": ts_code,
            "market": self._determine_market(ts_code),
            # 价格数据
            "close": self._convert_to_float(raw_data.get("close")),
            "current_price": self._convert_to_float(raw_data.get("close")),
            "open": self._convert_to_float(raw_data.get("open")),
            "high": self._convert_to_float(raw_data.get("high")),
            "low": self._convert_to_float(raw_data.get("low")),
            "pre_close": self._convert_to_float(raw_data.get("pre_close")),
            # 变动数据
            "change": self._convert_to_float(raw_data.get("change")),
            "pct_chg": self._convert_to_float(raw_data.get("pct_chg")),
            # 成交数据
            # 🔥 成交量单位：直接使用原始单位"手"（Tushare返回的是手）
            # 🔧 统一处理 volume/vol 字段，保持原始单位
            "volume": self._convert_to_float(raw_volume) if raw_volume else None,
            "volume_unit": "lots",  # 明确标注单位为手
            # 🔥 成交额单位转换：Tushare daily 接口返回的是千元，需要转换为元
            "amount": self._convert_to_float(raw_data.get("amount")) * 1000
            if raw_data.get("amount")
            else None,
            # 财务指标
            "total_mv": self._convert_to_float(raw_data.get("total_mv")),
            "circ_mv": self._convert_to_float(raw_data.get("circ_mv")),
            "pe": self._convert_to_float(raw_data.get("pe")),
            "pb": self._convert_to_float(raw_data.get("pb")),
            "turnover_rate": self._convert_to_float(raw_data.get("turnover_rate")),
            # 时间数据
            "trade_date": self._format_date_output(raw_data.get("trade_date")),
            "timestamp": datetime.utcnow(),
            # 元数据
            "data_source": "tushare",
            "data_version": 1,
            "updated_at": datetime.utcnow(),
        }

    # ==================== 辅助方法 ====================

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

    def _determine_market(self, ts_code: str) -> str:
        """确定市场代码（调用基类通用方法）"""
        return self._get_market_info(ts_code).get("market", "CN")

    def _format_date(self, date_value: Union[str, date]) -> str:
        """格式化日期为Tushare格式 (YYYYMMDD)"""
        if isinstance(date_value, str):
            return date_value.replace("-", "")
        elif isinstance(date_value, date):
            return date_value.strftime("%Y%m%d")
        else:
            return str(date_value).replace("-", "")

    def _standardize_historical_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化历史数据"""
        # 🔧 统一列名映射，与 AKShare 保持一致
        column_mapping = {
            "trade_date": "date",
            "vol": "volume",
            "open": "open",
            "close": "close",
            "high": "high",
            "low": "low",
            "amount": "amount",
            "pre_close": "pre_close",
            "change": "change",
            "pct_chg": "pct_chg",
            "turnover_rate": "turnover_rate",
        }
        df = df.rename(columns=column_mapping)

        # 格式化日期
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
            df.set_index("date", inplace=True)

        # 按日期排序
        df = df.sort_index()

        return df

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
                "report_type": self._determine_report_type(report_period),
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
                ),  # 🔥 修复：使用 grossprofit_margin（销售毛利率%）而不是 gross_margin（毛利绝对值）
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

    def _calculate_gross_profit(self, revenue, oper_cost) -> Optional[float]:
        """安全计算毛利润"""
        revenue_float = self._safe_float(revenue)
        oper_cost_float = self._safe_float(oper_cost)

        if revenue_float is not None and oper_cost_float is not None:
            return revenue_float - oper_cost_float
        return None

    def _safe_str(self, value) -> Optional[str]:
        """安全转换为字符串，处理NaN值"""
        if value is None:
            return None
        if isinstance(value, float) and (value != value):  # 检查NaN
            return None
        return str(value) if value else None


# 全局提供器实例
_tushare_provider = None
_tushare_provider_initialized = False


def get_tushare_provider() -> TushareProvider:
    """获取全局Tushare提供器实例"""
    global _tushare_provider, _tushare_provider_initialized
    if _tushare_provider is None:
        _tushare_provider = TushareProvider()
        # 使用同步连接方法，避免异步上下文问题
        if not _tushare_provider_initialized:
            try:
                # 直接使用同步连接方法
                _tushare_provider.connect_sync()
                _tushare_provider_initialized = True
            except Exception as e:
                logger.warning(f"⚠️ Tushare自动连接失败: {e}")
    return _tushare_provider


def get_realtime_quote(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取单只股票的实时行情（同步版本，供 data_source_manager 调用）

    使用 Tushare 的 daily 接口获取最新日线数据，
    因为 rt_k 接口是批量接口，单只股票调用浪费配额。

    Args:
        symbol: 股票代码（6位数字，如 '000001'）

    Returns:
        dict: 标准化的实时行情数据，包含以下字段：
            - symbol: 股票代码
            - name: 股票名称（如果可获取）
            - price: 当前/收盘价
            - change: 涨跌额
            - change_pct: 涨跌幅
            - open: 开盘价
            - high: 最高价
            - low: 最低价
            - pre_close: 昨收价
            - volume: 成交量（股）
            - amount: 成交额（元）
            - timestamp: 数据时间戳
            - source: 数据源标识
        None: 获取失败时返回
    """
    try:
        provider = get_tushare_provider()
        if not provider.is_available():
            logger.warning("⚠️ Tushare 提供器不可用，无法获取实时行情")
            return None

        # 标准化股票代码为 Tushare 格式
        ts_code = provider._normalize_ts_code(symbol)

        # 获取最近3天的日线数据（考虑周末和节假日）
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")

        df = provider.api.daily(
            ts_code=ts_code, start_date=start_date, end_date=end_date
        )

        if df is None or df.empty:
            logger.warning(f"⚠️ Tushare daily 接口返回空数据: {symbol}")
            return None

        # 取最新一天的数据
        row = df.iloc[0]

        # 安全获取数值
        def safe_float(val, default=0.0):
            try:
                if val is None or (isinstance(val, float) and val != val):  # NaN check
                    return default
                return float(val)
            except (ValueError, TypeError):
                return default

        # 标准化输出格式
        result = {
            "symbol": symbol,
            "name": "",  # daily 接口不包含名称
            "price": safe_float(row.get("close")),
            "change": safe_float(row.get("change")),
            "change_pct": safe_float(row.get("pct_chg")),
            "open": safe_float(row.get("open")),
            "high": safe_float(row.get("high")),
            "low": safe_float(row.get("low")),
            "pre_close": safe_float(row.get("pre_close")),
            # Tushare daily 返回的成交量单位是手，直接使用原始单位
            "volume": safe_float(row.get("vol")),
            "volume_unit": "lots",  # 明确标注单位为手
            # Tushare daily 返回的成交额单位是千元，转换为元
            "amount": safe_float(row.get("amount")) * 1000,
            "trade_date": str(row.get("trade_date", "")),
            "timestamp": datetime.now().isoformat(),
            "source": "tushare_daily",
        }

        logger.debug(f"✅ Tushare 获取实时行情成功: {symbol} 价格={result['price']}")
        return result

    except Exception as e:
        logger.error(f"❌ Tushare 获取实时行情失败 {symbol}: {e}")
        return None
