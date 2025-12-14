"""Agent 工具模块"""

import logging

from src.agent.tools.memory import save_memory, search_memories
from src.agent.tools.scraper import scrape_webpage
from src.agent.tools.search import tavily_search
from src.utils.settings import setting

logger = logging.getLogger(__name__)

__all__ = [
    "save_memory",
    "search_memories",
    "tavily_search",
    "scrape_webpage",
    "get_available_tools",
]


def get_available_tools():
    """根据配置获取可用的工具列表"""
    tools = [
        scrape_webpage,
        save_memory,
        search_memories,
    ]

    # 如果配置了 TAVILY_API_KEY，才添加 tavily_search 工具
    if setting.TAVILY_API_KEY:
        tools.append(tavily_search)

    return tools
