# -*- coding: utf-8 -*-
"""
TushareProvider 基类模块

提供 Token 管理、连接管理等基础功能。
"""

from typing import Optional
import os
import logging

from ...base_provider import BaseStockDataProvider
from tradingagents.config.providers_config import get_provider_config

try:
    import tushare as ts

    TUSHARE_AVAILABLE = True
except ImportError:
    TUSHARE_AVAILABLE = False
    ts = None

logger = logging.getLogger(__name__)


class BaseTushareProvider(BaseStockDataProvider):
    """
    Tushare数据提供器基类
    提供Token管理和连接功能
    """

    def __init__(self):
        super().__init__("Tushare")
        self.api = None
        self.config = get_provider_config("tushare")
        self.token_source = None  # 记录 Token 来源: 'database' 或 'env'

        if not TUSHARE_AVAILABLE:
            self.logger.error("❌ Tushare库未安装，请运行: pip install tushare")

        # 初始化时尝试连接，解决 connected=False 问题
        self.connect_sync()

    def _get_token_from_database(self) -> Optional[str]:
        """
        从数据库读取 Tushare Token

        优先级：数据库配置 > 环境变量
        这样用户在 Web 后台修改配置后可以立即生效

        优化：检查 TUSHARE_ENABLED 开关，禁用时跳过数据库查询
        优化：检查 CONFIG_SOURCE，当设置为 env 时跳过数据库查询
        """
        # 优化：检查 TUSHARE_ENABLED 开关，禁用时跳过数据库查询
        tushare_enabled_str = os.getenv("TUSHARE_ENABLED", "true").lower()
        tushare_enabled = tushare_enabled_str in ("true", "1", "yes", "on")

        if not tushare_enabled:
            # 静默跳过，不打印日志（减少噪音）
            return None

        # 新增：检查 CONFIG_SOURCE 参数，跳过数据库配置查询
        try:
            from app.core.config import settings

            if settings.CONFIG_SOURCE == "env" or settings.SKIP_DATABASE_CONFIG:
                # 静默跳过，不打印数据库查询日志
                return None
        except ImportError:
            # 配置模块不可用时继续正常流程
            pass

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

        # 检查TUSHARE_ENABLED开关
        tushare_enabled_str = os.getenv("TUSHARE_ENABLED", "true").lower()
        tushare_enabled = tushare_enabled_str in ("true", "1", "yes", "on")

        if not tushare_enabled:
            self.logger.info("⏸️ [Tushare] TUSHARE_ENABLED=false，跳过Tushare数据源")
            self.connected = False
            return False

        # 测试连接超时时间（秒）- 只是测试连通性，不需要很长时间
        test_timeout = 10

        try:
            # 修改优先级：优先从.env读取Token，只有.env没有时才从数据库读取
            self.logger.info("🔍 [步骤1] 开始从 .env 读取 Tushare Token...")
            env_token = self.config.get("token")
            if env_token:
                self.logger.info(
                    f"✅ [步骤1] .env 中找到 Token (长度: {len(env_token)})"
                )
            else:
                self.logger.info("⚠️ [步骤1] .env 中未找到 Token")

            self.logger.info("🔍 [步骤2] 从数据库读取 Token（备用）...")
            db_token = self._get_token_from_database()
            if db_token:
                self.logger.info(
                    f"✅ [步骤2] 数据库中找到 Token (长度: {len(db_token)})"
                )
            else:
                self.logger.info("⚠️ [步骤2] 数据库中未找到 Token")

            # 优先尝试 .env Token（用户配置优先）
            if env_token:
                try:
                    self.logger.info(
                        f"🔄 [步骤3] 尝试使用 .env 中的 Tushare Token (超时: {test_timeout}秒)..."
                    )
                    ts.set_token(env_token)
                    self.api = ts.pro_api()
                    self.logger.info("✅ [步骤3.1] Tushare API 初始化完成")

                    # 测试连接 - 直接调用同步方法（不使用 asyncio.run）
                    try:
                        self.logger.info(
                            "🔄 [步骤3.2] 调用 stock_basic API 测试连接..."
                        )
                        test_data = self.api.stock_basic(list_status="L", limit=1)
                        self.logger.info(
                            f"✅ [步骤3.2] API 调用成功，返回数据: {len(test_data) if test_data is not None else 0} 条"
                        )
                    except Exception as e:
                        self.logger.warning(f"⚠️ [步骤3.2] .env Token 测试异常: {e}")
                        test_data = None

                    if test_data is not None and not test_data.empty:
                        self.connected = True
                        self.token_source = "env"
                        self.logger.info(
                            f"✅ [步骤3.3] Tushare连接成功 (Token来源: .env 环境变量)"
                        )
                        return True
                    else:
                        self.logger.warning(
                            f"⚠️ [步骤3.3] .env Token 测试失败: API返回空数据。将尝试数据库配置..."
                        )
                except Exception as e:
                    self.logger.warning(
                        f"⚠️ [步骤3] .env Token 连接失败: {e}，尝试数据库配置..."
                    )

            # 降级到数据库 Token（.env没有或失败时使用）
            if db_token:
                try:
                    self.logger.info(
                        f"🔄 [步骤4] 尝试使用数据库中的 Tushare Token (超时: {test_timeout}秒)..."
                    )
                    ts.set_token(db_token)
                    self.api = ts.pro_api()
                    self.logger.info("✅ [步骤3] Tushare API 初始化完成")
                    ts.set_token(db_token)
                    self.api = ts.pro_api()

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
                        self.logger.error(f"❌ [步骤4.1] 数据库 Token 测试失败: {e}")
                        return False

                    if test_data is not None and not test_data.empty:
                        self.connected = True
                        self.token_source = "database"
                        self.logger.info(
                            f"✅ [步骤4.2] Tushare连接成功 (Token来源: 数据库)"
                        )
                        return True
                    else:
                        self.logger.error(
                            "❌ [步骤4.2] 数据库 Token 测试失败: API返回空数据"
                        )
                        return False
                except Exception as e:
                    self.logger.error(f"❌ [步骤4] 数据库 Token 连接失败: {e}")
                    return False

            # 两个都没有
            self.logger.error(
                "❌ [步骤5] Tushare token未配置，请在 .env 文件中配置 TUSHARE_TOKEN 或在 Web 后台配置"
            )
            return False

        except Exception as e:
            self.logger.error(f"❌ Tushare连接失败: {e}")
            return False

    async def connect(self) -> bool:
        """异步连接到Tushare"""
        import asyncio

        if not TUSHARE_AVAILABLE:
            self.logger.error("❌ Tushare库不可用")
            return False

        # 如果已经连接，直接返回成功（防止重复连接触发限流）
        if self.connected and self.api is not None:
            self.logger.info("✅ Tushare已连接，跳过重复连接")
            return True

        # 测试连接超时时间（秒）- 只是测试连通性，不需要很长时间
        test_timeout = 10

        try:
            # 优先从数据库读取 Token
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
                    self.logger.info("✅ [步骤3] Tushare API 初始化完成")

                    # 测试连接 - 直接调用同步方法（不使用 asyncio.run）
                    try:
                        self.logger.info(
                            "🔄 [步骤3.1] 调用 stock_basic API 测试连接..."
                        )
                        # 移除 limit=1，防止偶然空数据
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
                    self.logger.info("✅ [步骤4] Tushare API 初始化完成")

                    # 测试连接（异步）- 使用超时和重试机制
                    retry_count = 0
                    max_retries = 3
                    while retry_count < max_retries:
                        try:
                            self.logger.info(
                                f"🔄 [步骤4.1] 调用 stock_basic API 测试连接... (尝试 {retry_count + 1}/{max_retries})"
                            )
                            # 移除 limit=1，使用 limit=5 防止偶然空数据
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
