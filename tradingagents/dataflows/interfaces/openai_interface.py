# -*- coding: utf-8 -*-
"""
OpenAI 集成接口模块

提供基于 OpenAI 的新闻和全球数据获取功能
"""

from datetime import datetime
from openai import OpenAI

from .base_interface import get_config


def get_stock_news_openai(ticker, curr_date):
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    response = client.responses.create(
        model=config["quick_think_llm"],
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Can you search Social Media for {ticker} from 7 days before {curr_date} to {curr_date}? Make sure you only get the data posted during that period.",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    # 提取响应文本，处理 Union 类型
    try:
        output_item = response.output[1]
        content = getattr(output_item, "content", None)
        if content and len(content) > 0:
            text = getattr(content[0], "text", None)
            if text:
                return text
    except (IndexError, AttributeError):
        pass
    return ""


def get_global_news_openai(curr_date):
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    response = client.responses.create(
        model=config["quick_think_llm"],
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Can you search global or macroeconomics news from 7 days before {curr_date} to {curr_date} that would be informative for trading purposes? Make sure you only get the data posted during that period.",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    # 提取响应文本，处理 Union 类型
    try:
        output_item = response.output[1]
        content = getattr(output_item, "content", None)
        if content and len(content) > 0:
            text = getattr(content[0], "text", None)
            if text:
                return text
    except (IndexError, AttributeError):
        pass
    return ""
