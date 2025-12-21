"""Agent 工具模块"""

import logging

from src.utils.settings import setting

logger = logging.getLogger(__name__)

__all__ = [
    "save_memory",
    "search_memories",
    "tavily_search",
    "scrape_webpage",
    "get_user_time",
    "schedule_reminder",
    "get_base_tools",
    "get_supervisor_tools",
    "trigger_deep_think",
    # 上下文变量
    "user_id_context",
    "group_id_context",
    "chat_id_context",
    "chat_type_context",
]


def get_base_tools():
    """获取不包含深度思考触发器的基础工具集"""
    from src.agent.tools.memory import save_memory, search_memories
    from src.agent.tools.scheduler import schedule_reminder
    from src.agent.tools.search import scrape_webpage, tavily_search
    from src.agent.tools.time import get_user_time

    tools = [
        scrape_webpage,
        get_user_time,
        schedule_reminder,
        save_memory,
        search_memories,
    ]
    if setting.TAVILY_API_KEY:
        tools.append(tavily_search)
    return tools


def get_supervisor_tools():
    """获取给 Supervisor 使用的全量工具集"""
    from src.agent.tools.think import trigger_deep_think

    tools = get_base_tools()
    tools.append(trigger_deep_think)
    return tools
