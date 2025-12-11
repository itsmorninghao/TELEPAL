"""AsyncPostgresStore 初始化（长期记忆）"""

from langgraph.store.postgres.aio import AsyncPostgresStore

from src.database.langgraph_pool import get_pool
from src.utils.settings import get_embeddings, get_index_config

# 单例 store 实例
_store_instance: AsyncPostgresStore | None = None


async def get_store() -> AsyncPostgresStore:
    """获取 AsyncPostgresStore 单例实例"""
    global _store_instance

    # 如果已存在实例，直接返回
    if _store_instance is not None:
        return _store_instance

    # 创建新实例
    pool = await get_pool()
    embeddings = get_embeddings()
    index_config = get_index_config(embeddings)
    _store_instance = AsyncPostgresStore(pool, index=index_config)

    return _store_instance
