import asyncio

from langchain_core.tools import tool

from src.agent.graphs.deep_think import run_deep_think_task
from src.bot import chat_id_context, chat_type_context, user_id_context


@tool
async def trigger_deep_think(topic: str) -> str:
    """当需要深度思考或详尽研究时调用。系统将异步处理。"""
    # chat_id 是消息目标ID
    chat_id = chat_id_context.get()

    asyncio.create_task(run_deep_think_task(chat_id, topic))

    return (
        f"已经在后台启动深度代理研究“{topic}”，大概需要3~10分钟，完成后会自动通知用户"
    )
