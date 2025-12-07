"""AsyncPostgresSaver 初始化（对话记忆）"""

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from src.utils.db.connection import get_pool

# 初始化标志，确保 setup() 只执行一次
_setup_done: bool = False


async def get_checkpointer() -> AsyncPostgresSaver:
    """获取 AsyncPostgresSaver 实例（对话记忆）

    使用共享连接池以优化性能和资源管理。

    Returns:
        AsyncPostgresSaver 实例
    """
    global _setup_done

    pool = await get_pool()

    checkpointer = AsyncPostgresSaver(pool)

    if not _setup_done:
        await checkpointer.setup()
        _setup_done = True

    return checkpointer


async def init_checkpointer() -> None:
    """初始化 checkpointer 表结构

    在应用启动时调用，确保表结构已创建。
    这个方法会处理 CREATE INDEX CONCURRENTLY 等不能在事务中执行的命令。
    """
    global _setup_done

    if _setup_done:
        return

    # 获取共享连接池
    pool = await get_pool()

    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    _setup_done = True
