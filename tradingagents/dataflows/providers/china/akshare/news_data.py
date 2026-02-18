# -*- coding: utf-8 -*-
"""
AKShare新闻数据模块

包含新闻数据获取和情感分析功能
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class NewsDataMixin:
    """新闻数据功能混入类"""

    def _get_stock_news_direct(
        self, symbol: str, limit: int = 10
    ) -> Optional[pd.DataFrame]:
        """
        直接调用东方财富网新闻 API（绕过 AKShare）
        使用 curl_cffi 模拟真实浏览器，适用于 Docker 环境

        Args:
            symbol: 股票代码
            limit: 返回数量限制

        Returns:
            新闻 DataFrame 或 None
        """
        try:
            from curl_cffi import requests as curl_requests
            import json
            import time

            # 标准化股票代码
            symbol_6 = symbol.zfill(6)

            # 构建请求参数
            url = "https://search-api-web.eastmoney.com/search/jsonp"
            param = {
                "uid": "",
                "keyword": symbol_6,
                "type": ["cmsArticleWebOld"],
                "client": "web",
                "clientType": "web",
                "clientVersion": "curr",
                "param": {
                    "cmsArticleWebOld": {
                        "searchScope": "default",
                        "sort": "default",
                        "pageIndex": 1,
                        "pageSize": limit,
                        "preTag": "<em>",
                        "postTag": "</em>",
                    }
                },
            }

            params = {
                "cb": f"jQuery{int(time.time() * 1000)}",
                "param": json.dumps(param),
                "_": str(int(time.time() * 1000)),
            }

            # 使用 curl_cffi 发送请求
            response = curl_requests.get(
                url, params=params, timeout=10, impersonate="chrome120"
            )

            if response.status_code != 200:
                self.logger.error(
                    f"❌ {symbol} 东方财富网 API 返回错误: {response.status_code}"
                )
                return None

            # 解析 JSONP 响应
            text = response.text
            if text.startswith("jQuery"):
                text = text[text.find("(") + 1 : text.rfind(")")]

            data = json.loads(text)

            # 检查返回数据
            if "result" not in data or "cmsArticleWebOld" not in data["result"]:
                self.logger.error(f"❌ {symbol} 东方财富网 API 返回数据结构异常")
                return None

            articles = data["result"]["cmsArticleWebOld"]

            if not articles:
                self.logger.warning(f"⚠️ {symbol} 未获取到新闻")
                return None

            # 转换为 DataFrame（与 AKShare 格式兼容）
            news_data = []
            for article in articles:
                news_data.append(
                    {
                        "新闻标题": article.get("title", ""),
                        "新闻内容": article.get("content", ""),
                        "发布时间": article.get("date", ""),
                        "新闻链接": article.get("url", ""),
                        "关键词": article.get("keywords", ""),
                        "新闻来源": article.get("source", "东方财富网"),
                        "新闻类型": article.get("type", ""),
                    }
                )

            df = pd.DataFrame(news_data)
            self.logger.info(f"✅ {symbol} 直接调用 API 获取新闻成功: {len(df)} 条")
            return df

        except Exception as e:
            self.logger.error(f"❌ {symbol} 直接调用 API 失败: {e}")
            return None

    def get_stock_news_sync(
        self, symbol: Optional[str] = None, limit: int = 10
    ) -> Optional[pd.DataFrame]:
        """
        获取股票新闻（同步版本，返回原始 DataFrame）

        Args:
            symbol: 股票代码，为None时获取市场新闻
            limit: 返回数量限制

        Returns:
            新闻 DataFrame 或 None
        """
        if not self.is_available():
            return None

        try:
            import akshare as ak
            import json
            import time

            if symbol:
                # 获取个股新闻
                self.logger.debug(f"📰 获取AKShare个股新闻: {symbol}")

                # 标准化股票代码
                symbol_6 = symbol.zfill(6)

                # 获取东方财富个股新闻，添加重试机制
                max_retries = 3
                retry_delay = 1  # 秒
                news_df = None

                for attempt in range(max_retries):
                    try:
                        news_df = ak.stock_news_em(symbol=symbol_6)
                        break  # 成功则跳出重试循环
                    except json.JSONDecodeError as e:
                        if attempt < max_retries - 1:
                            self.logger.warning(
                                f"⚠️ {symbol} 第{attempt + 1}次获取新闻失败(JSON解析错误)，{retry_delay}秒后重试..."
                            )
                            time.sleep(retry_delay)
                            retry_delay *= 2  # 指数退避
                        else:
                            self.logger.error(
                                f"❌ {symbol} 获取新闻失败(JSON解析错误): {e}"
                            )
                            return None
                    except Exception as e:
                        if attempt < max_retries - 1:
                            self.logger.warning(
                                f"⚠️ {symbol} 第{attempt + 1}次获取新闻失败: {e}，{retry_delay}秒后重试..."
                            )
                            time.sleep(retry_delay)
                            retry_delay *= 2
                        else:
                            raise

                if news_df is not None and not news_df.empty:
                    self.logger.info(
                        f"✅ {symbol} AKShare新闻获取成功: {len(news_df)} 条"
                    )
                    return news_df.head(limit) if limit else news_df
                else:
                    self.logger.warning(f"⚠️ {symbol} 未获取到AKShare新闻数据")
                    return None
            else:
                # 获取市场新闻
                self.logger.debug("📰 获取AKShare市场新闻")
                news_df = ak.news_cctv()

                if news_df is not None and not news_df.empty:
                    self.logger.info(f"✅ AKShare市场新闻获取成功: {len(news_df)} 条")
                    return news_df.head(limit) if limit else news_df
                else:
                    self.logger.warning("⚠️ 未获取到AKShare市场新闻数据")
                    return None

        except Exception as e:
            self.logger.error(f"❌ AKShare新闻获取失败: {e}")
            return None

    async def get_stock_news(
        self, symbol: Optional[str] = None, limit: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        获取股票新闻（异步版本，返回结构化列表）

        Args:
            symbol: 股票代码，为None时获取市场新闻
            limit: 返回数量限制

        Returns:
            新闻列表
        """
        if not self.is_available():
            return None

        try:
            import akshare as ak
            import json
            import os

            if symbol:
                # 获取个股新闻
                self.logger.debug(f"📰 获取AKShare个股新闻: {symbol}")

                # 标准化股票代码
                symbol_6 = symbol.zfill(6)

                # 检测是否在 Docker 环境中
                is_docker = (
                    os.path.exists("/.dockerenv")
                    or os.environ.get("DOCKER_CONTAINER") == "true"
                )

                # 获取东方财富个股新闻，添加重试机制
                max_retries = 3
                retry_delay = 1  # 秒
                news_df = None

                # 如果在 Docker 环境中，尝试使用 curl_cffi 直接调用 API
                if is_docker:
                    try:
                        from curl_cffi import requests as curl_requests

                        self.logger.debug(
                            f"🐳 检测到 Docker 环境，使用 curl_cffi 直接调用 API"
                        )
                        news_df = await asyncio.to_thread(
                            self._get_stock_news_direct, symbol=symbol_6, limit=limit
                        )
                        if news_df is not None and not news_df.empty:
                            self.logger.info(
                                f"✅ {symbol} Docker 环境直接调用 API 成功"
                            )
                        else:
                            self.logger.warning(
                                f"⚠️ {symbol} Docker 环境直接调用 API 失败，回退到 AKShare"
                            )
                            news_df = None  # 回退到 AKShare
                    except ImportError:
                        self.logger.warning(f"⚠️ curl_cffi 未安装，回退到 AKShare")
                        news_df = None
                    except Exception as e:
                        self.logger.warning(
                            f"⚠️ {symbol} Docker 环境直接调用 API 异常: {e}，回退到 AKShare"
                        )
                        news_df = None

                # 如果直接调用失败或不在 Docker 环境，使用 AKShare
                if news_df is None:
                    for attempt in range(max_retries):
                        try:
                            news_df = await asyncio.to_thread(
                                ak.stock_news_em, symbol=symbol_6
                            )
                            break  # 成功则跳出重试循环
                        except json.JSONDecodeError as e:
                            if attempt < max_retries - 1:
                                self.logger.warning(
                                    f"⚠️ {symbol} 第{attempt + 1}次获取新闻失败(JSON解析错误)，{retry_delay}秒后重试..."
                                )
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2  # 指数退避
                            else:
                                self.logger.error(
                                    f"❌ {symbol} 获取新闻失败(JSON解析错误): {e}"
                                )
                                return []
                        except KeyError as e:
                            # 东方财富网接口变更或反爬虫拦截，返回的字段结构改变
                            if str(e) == "'cmsArticleWebOld'":
                                self.logger.error(
                                    f"❌ {symbol} AKShare新闻接口返回数据结构异常: 缺少 'cmsArticleWebOld' 字段"
                                )
                                self.logger.error(
                                    f"   这通常是因为：1) 反爬虫拦截 2) 接口变更 3) 网络问题"
                                )
                                self.logger.error(
                                    f"   建议：检查 AKShare 版本是否为最新 (当前要求 >=1.17.86)"
                                )
                                # 返回空列表，避免程序崩溃
                                return []
                            else:
                                if attempt < max_retries - 1:
                                    self.logger.warning(
                                        f"⚠️ {symbol} 第{attempt + 1}次获取新闻失败(字段错误): {e}，{retry_delay}秒后重试..."
                                    )
                                    await asyncio.sleep(retry_delay)
                                    retry_delay *= 2
                                else:
                                    self.logger.error(
                                        f"❌ {symbol} 获取新闻失败(字段错误): {e}"
                                    )
                                    return []
                        except Exception as e:
                            if attempt < max_retries - 1:
                                self.logger.warning(
                                    f"⚠️ {symbol} 第{attempt + 1}次获取新闻失败: {e}，{retry_delay}秒后重试..."
                                )
                                await asyncio.sleep(retry_delay)
                                retry_delay *= 2
                            else:
                                raise

                if news_df is not None and not news_df.empty:
                    news_list = []

                    for _, row in news_df.head(limit).iterrows():
                        title = str(row.get("新闻标题", "") or row.get("标题", ""))
                        content = str(row.get("新闻内容", "") or row.get("内容", ""))
                        summary = str(row.get("新闻摘要", "") or row.get("摘要", ""))

                        news_item = {
                            "symbol": symbol,
                            "title": title,
                            "content": content,
                            "summary": summary,
                            "url": str(row.get("新闻链接", "") or row.get("链接", "")),
                            "source": str(
                                row.get("文章来源", "")
                                or row.get("来源", "")
                                or "东方财富"
                            ),
                            "author": str(row.get("作者", "") or ""),
                            "publish_time": self._parse_news_time(
                                str(
                                    row.get("发布时间", "") or row.get("时间", "") or ""
                                )
                            ),
                            "category": self._classify_news(content, title),
                            "sentiment": self._analyze_news_sentiment(content, title),
                            "sentiment_score": self._calculate_sentiment_score(
                                content, title
                            ),
                            "keywords": self._extract_keywords(content, title),
                            "importance": self._assess_news_importance(content, title),
                            "data_source": "akshare",
                        }

                        # 过滤空标题的新闻
                        if news_item["title"]:
                            news_list.append(news_item)

                    self.logger.info(
                        f"✅ {symbol} AKShare新闻获取成功: {len(news_list)} 条"
                    )
                    return news_list
                else:
                    self.logger.warning(f"⚠️ {symbol} 未获取到AKShare新闻数据")
                    return []
            else:
                # 获取市场新闻
                self.logger.debug("📰 获取AKShare市场新闻")

                try:
                    # 获取财经新闻
                    news_df = await asyncio.to_thread(ak.news_cctv, limit=limit)  # type: ignore

                    if news_df is not None and not news_df.empty:
                        news_list = []

                        for _, row in news_df.iterrows():
                            title = str(row.get("title", "") or row.get("标题", ""))
                            content = str(row.get("content", "") or row.get("内容", ""))
                            summary = str(row.get("brief", "") or row.get("摘要", ""))

                            news_item = {
                                "title": title,
                                "content": content,
                                "summary": summary,
                                "url": str(row.get("url", "") or row.get("链接", "")),
                                "source": str(
                                    row.get("source", "")
                                    or row.get("来源", "")
                                    or "CCTV财经"
                                ),
                                "author": str(row.get("author", "") or ""),
                                "publish_time": self._parse_news_time(
                                    str(
                                        row.get("time", "") or row.get("时间", "") or ""
                                    )
                                ),
                                "category": self._classify_news(content, title),
                                "sentiment": self._analyze_news_sentiment(
                                    content, title
                                ),
                                "sentiment_score": self._calculate_sentiment_score(
                                    content, title
                                ),
                                "keywords": self._extract_keywords(content, title),
                                "importance": self._assess_news_importance(
                                    content, title
                                ),
                                "data_source": "akshare",
                            }

                            if news_item["title"]:
                                news_list.append(news_item)

                        self.logger.info(
                            f"✅ AKShare市场新闻获取成功: {len(news_list)} 条"
                        )
                        return news_list

                except Exception as e:
                    self.logger.debug(f"CCTV新闻获取失败: {e}")

                return []

        except Exception as e:
            self.logger.error(f"❌ 获取AKShare新闻失败 symbol={symbol}: {e}")
            return None

    def _parse_news_time(self, time_str: str) -> Optional[datetime]:
        """解析新闻时间"""
        if not time_str:
            return datetime.utcnow()

        try:
            # 尝试多种时间格式
            formats = [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d",
                "%Y/%m/%d %H:%M:%S",
                "%Y/%m/%d %H:%M",
                "%Y/%m/%d",
                "%m-%d %H:%M",
                "%m/%d %H:%M",
            ]

            for fmt in formats:
                try:
                    parsed_time = datetime.strptime(str(time_str), fmt)

                    # 如果只有月日，补充年份
                    if fmt in ["%m-%d %H:%M", "%m/%d %H:%M"]:
                        current_year = datetime.now().year
                        parsed_time = parsed_time.replace(year=current_year)

                    return parsed_time
                except ValueError:
                    continue

            # 如果都失败了，返回当前时间
            self.logger.debug(f"⚠️ 无法解析新闻时间: {time_str}")
            return datetime.utcnow()

        except Exception as e:
            self.logger.debug(f"解析新闻时间异常: {e}")
            return datetime.utcnow()

    def _analyze_news_sentiment(self, content: str, title: str) -> str:
        """
        分析新闻情绪

        Args:
            content: 新闻内容
            title: 新闻标题

        Returns:
            情绪类型: positive/negative/neutral
        """
        text = f"{title} {content}".lower()

        # 积极关键词
        positive_keywords = [
            "利好",
            "上涨",
            "增长",
            "盈利",
            "突破",
            "创新高",
            "买入",
            "推荐",
            "看好",
            "乐观",
            "强势",
            "大涨",
            "飙升",
            "暴涨",
            "涨停",
            "涨幅",
            "业绩增长",
            "营收增长",
            "净利润增长",
            "扭亏为盈",
            "超预期",
            "获批",
            "中标",
            "签约",
            "合作",
            "并购",
            "重组",
            "分红",
            "回购",
        ]

        # 消极关键词
        negative_keywords = [
            "利空",
            "下跌",
            "亏损",
            "风险",
            "暴跌",
            "卖出",
            "警告",
            "下调",
            "看空",
            "悲观",
            "弱势",
            "大跌",
            "跳水",
            "暴跌",
            "跌停",
            "跌幅",
            "业绩下滑",
            "营收下降",
            "净利润下降",
            "亏损",
            "低于预期",
            "被查",
            "违规",
            "处罚",
            "诉讼",
            "退市",
            "停牌",
            "商誉减值",
        ]

        positive_count = sum(1 for keyword in positive_keywords if keyword in text)
        negative_count = sum(1 for keyword in negative_keywords if keyword in text)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _calculate_sentiment_score(self, content: str, title: str) -> float:
        """
        计算情绪分数

        Args:
            content: 新闻内容
            title: 新闻标题

        Returns:
            情绪分数: -1.0 到 1.0
        """
        text = f"{title} {content}".lower()

        # 积极关键词权重
        positive_keywords = {
            "涨停": 1.0,
            "暴涨": 0.9,
            "大涨": 0.8,
            "飙升": 0.8,
            "创新高": 0.7,
            "突破": 0.6,
            "上涨": 0.5,
            "增长": 0.4,
            "利好": 0.6,
            "看好": 0.5,
            "推荐": 0.5,
            "买入": 0.6,
        }

        # 消极关键词权重
        negative_keywords = {
            "跌停": -1.0,
            "暴跌": -0.9,
            "大跌": -0.8,
            "跳水": -0.8,
            "创新低": -0.7,
            "破位": -0.6,
            "下跌": -0.5,
            "下滑": -0.4,
            "利空": -0.6,
            "看空": -0.5,
            "卖出": -0.6,
            "警告": -0.5,
        }

        score = 0.0

        # 计算积极分数
        for keyword, weight in positive_keywords.items():
            if keyword in text:
                score += weight

        # 计算消极分数
        for keyword, weight in negative_keywords.items():
            if keyword in text:
                score += weight

        # 归一化到 [-1.0, 1.0]
        return max(-1.0, min(1.0, score / 3.0))

    def _extract_keywords(self, content: str, title: str) -> List[str]:
        """
        提取关键词

        Args:
            content: 新闻内容
            title: 新闻标题

        Returns:
            关键词列表
        """
        text = f"{title} {content}"

        # 常见财经关键词
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
            "涨停",
            "跌停",
            "上涨",
            "下跌",
            "盈利",
            "亏损",
            "并购",
            "重组",
            "分红",
            "回购",
            "增持",
            "减持",
            "融资",
            "IPO",
            "监管",
            "央行",
            "利率",
            "汇率",
            "GDP",
            "通胀",
            "经济",
            "贸易",
            "科技",
            "互联网",
            "新能源",
            "医药",
            "房地产",
            "金融",
            "制造业",
        ]

        keywords = []
        for keyword in common_keywords:
            if keyword in text:
                keywords.append(keyword)

        return keywords[:10]  # 最多返回10个关键词

    def _assess_news_importance(self, content: str, title: str) -> str:
        """
        评估新闻重要性

        Args:
            content: 新闻内容
            title: 新闻标题

        Returns:
            重要性级别: high/medium/low
        """
        text = f"{title} {content}".lower()

        # 高重要性关键词
        high_importance_keywords = [
            "业绩",
            "财报",
            "年报",
            "季报",
            "重大",
            "公告",
            "监管",
            "政策",
            "并购",
            "重组",
            "退市",
            "停牌",
            "涨停",
            "跌停",
            "暴涨",
            "暴跌",
            "央行",
            "证监会",
            "交易所",
            "违规",
            "处罚",
            "立案",
            "调查",
        ]

        # 中等重要性关键词
        medium_importance_keywords = [
            "分析",
            "预测",
            "观点",
            "建议",
            "行业",
            "市场",
            "趋势",
            "机会",
            "研报",
            "评级",
            "目标价",
            "增持",
            "减持",
            "买入",
            "卖出",
            "合作",
            "签约",
            "中标",
            "获批",
            "分红",
            "回购",
        ]

        # 检查高重要性
        if any(keyword in text for keyword in high_importance_keywords):
            return "high"

        # 检查中等重要性
        if any(keyword in text for keyword in medium_importance_keywords):
            return "medium"

        return "low"

    def _classify_news(self, content: str, title: str) -> str:
        """
        分类新闻

        Args:
            content: 新闻内容
            title: 新闻标题

        Returns:
            新闻类别
        """
        text = f"{title} {content}".lower()

        # 公司公告
        if any(keyword in text for keyword in ["公告", "业绩", "财报", "年报", "季报"]):
            return "company_announcement"

        # 政策新闻
        if any(
            keyword in text for keyword in ["政策", "监管", "央行", "证监会", "国务院"]
        ):
            return "policy_news"

        # 行业新闻
        if any(keyword in text for keyword in ["行业", "板块", "产业", "领域"]):
            return "industry_news"

        # 市场新闻
        if any(
            keyword in text for keyword in ["市场", "指数", "大盘", "沪指", "深成指"]
        ):
            return "market_news"

        # 研究报告
        if any(
            keyword in text for keyword in ["研报", "分析", "评级", "目标价", "机构"]
        ):
            return "research_report"

        return "general"
