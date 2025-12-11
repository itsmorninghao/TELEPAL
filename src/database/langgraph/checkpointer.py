"""AsyncPostgresSaver 初始化（对话记忆）"""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.database.langgraph_pool import get_pool

# 单例 checkpointer 实例
_checkpointer_instance: AsyncPostgresSaver | None = None


async def get_checkpointer() -> AsyncPostgresSaver:
    """获取 AsyncPostgresSaver 单例实例（对话记忆）"""
    global _checkpointer_instance

    # 如果已存在实例，直接返回
    if _checkpointer_instance is not None:
        return _checkpointer_instance

    # 创建新实例
    pool = await get_pool()
    _checkpointer_instance = AsyncPostgresSaver(pool)

    return _checkpointer_instance
