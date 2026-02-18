# -*- coding: utf-8 -*-
"""
新闻数据模块

提供股票新闻、新闻处理等功能。
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import asyncio
import pandas as pd

from .base_provider import BaseTushareProvider


class NewsDataMixin(BaseTushareProvider):
    """新闻数据功能混入类"""

    async def get_stock_news(
        self,
        symbol: Optional[str] = None,
        limit: int = 10,
        hours_back: int = 24,
        src: Optional[str] = None,
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
        self,
        news_df: pd.DataFrame,
        source: str,
        symbol: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """处理Tushare新闻数据"""
        news_list = []

        # 限制处理数量
        df_limited = news_df.head(limit * 2)  # 多获取一些，用于过滤

        for _, row in df_limited.iterrows():
            content_val = str(row.get("content", "") or "")
            title_val = str(row.get("title", "") or "")
            channels_val = str(row.get("channels", "") or "")
            datetime_val = str(row.get("datetime", "") or "")

            news_item = {
                "title": str(
                    title_val
                    or (
                        content_val[:50] + "..."
                        if len(content_val) > 50
                        else content_val
                    )
                ),
                "content": content_val,
                "summary": self._generate_summary(content_val),
                "url": "",  # Tushare新闻接口不提供URL
                "source": self._get_source_name(source),
                "author": "",
                "publish_time": self._parse_tushare_news_time(datetime_val),
                "category": self._classify_tushare_news(channels_val, content_val),
                "sentiment": self._analyze_news_sentiment(content_val, title_val),
                "importance": self._assess_news_importance(content_val, title_val),
                "keywords": self._extract_keywords(content_val, title_val),
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
