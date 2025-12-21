"""LangGraph 架构入口"""

import logging
from typing import Any, Dict, Tuple

from src.agent.graphs.supervisor import get_supervisor_graph
from src.database.langgraph.checkpointer import get_checkpointer

logger = logging.getLogger(__name__)


async def get_compiled_graph(
    user_id: int, chat_type: str, group_id: int | None = None
) -> Tuple[Any, Dict[str, Any]]:
    """获取编译后的 Graph,返回 (graph, config) 元组"""
    checkpointer = await get_checkpointer()

    compiled_graph = get_supervisor_graph(checkpointer)

    # 计算 thread_id 和 chat_id
    if chat_type == "private":
        thread_id = str(user_id)
        chat_id = user_id
    else:
        thread_id = str(group_id)
        chat_id = group_id

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
            "chat_type": chat_type,
            "chat_id": chat_id,
        },
    }

    return compiled_graph, config
