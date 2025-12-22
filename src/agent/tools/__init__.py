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
    "list_scheduled_tasks",
    "cancel_scheduled_task",
    "get_tools",
    "trigger_deep_think",
    # 上下文变量
    "user_id_context",
    "group_id_context",
    "chat_id_context",
    "chat_type_context",
]

def get_tools(agent_name: str):
    """根据 agent 名称获取对应的工具集

    Args:
        agent_name: agent 名称

    Returns:
        工具列表

    Raises:
        ValueError: 当 agent_name 无效时
    """
    from src.agent.tools.memory import save_memory, search_memories
    from src.agent.tools.scheduler import (
        cancel_scheduled_task,
        list_scheduled_tasks,
        schedule_reminder,
    )
    from src.agent.tools.search import scrape_webpage, tavily_search
    from src.agent.tools.time import get_user_time
    from src.agent.tools.think import trigger_deep_think

    if agent_name == "supervisor":
        tools = [
            # 基础工具
            search_memories,
            scrape_webpage,
            get_user_time,
            # 定时任务工具
            cancel_scheduled_task,
            list_scheduled_tasks,
            schedule_reminder,
            # Supervisor 专用工具
            trigger_deep_think,
            save_memory,
        ]
        # 条件工具
        if setting.TAVILY_API_KEY:
            tools.append(tavily_search)
        return tools

    elif agent_name == "deep_think":
        tools = [
            scrape_webpage,
            get_user_time,
            search_memories,
        ]
        # 条件工具
        if setting.TAVILY_API_KEY:
            tools.append(tavily_search)
        return tools

    else:
        raise ValueError(f"Invalid agent name: {agent_name}")