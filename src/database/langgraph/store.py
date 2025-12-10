"""AsyncPostgresStore 初始化（长期记忆）"""

from langchain_openai import OpenAIEmbeddings
from langgraph.store.postgres.aio import AsyncPostgresStore

from src.database.connection import get_pool
from src.utils.settings import setting

# 初始化标志，确保 setup() 只执行一次
_setup_done: bool = False
# 单例 store 实例
_store_instance: AsyncPostgresStore | None = None


def _get_embeddings() -> OpenAIEmbeddings | None:
    """获取嵌入模型实例"""
    return OpenAIEmbeddings(
        api_key=setting.EMBEDDING_API_KEY,
        base_url=setting.EMBEDDING_BASE_URL,
        model=setting.EMBEDDING_MODEL,
        check_embedding_ctx_length=False,
    )


def _get_index_config(embeddings: OpenAIEmbeddings) -> dict:
    """获取向量索引配置"""
    return {"dims": setting.EMBEDDING_DIMS, "embed": embeddings, "fields": ["value"]}


async def _create_store_instance() -> AsyncPostgresStore:
    """创建 AsyncPostgresStore 实例"""
    pool = await get_pool()
    embeddings = _get_embeddings()

    if embeddings is None:
        raise ValueError("必须要配置嵌入模型")

    index_config = _get_index_config(embeddings)
    return AsyncPostgresStore(pool, index=index_config)


async def init_store() -> None:
    """初始化 store 表结构，应用启动时调用"""
    global _setup_done

    if _setup_done:
        return

    # 创建临时实例用于初始化表结构
    store = await _create_store_instance()
    await store.setup()
    _setup_done = True


async def get_store() -> AsyncPostgresStore:
    """获取 AsyncPostgresStore 单例实例"""
    global _setup_done, _store_instance

    # 如果已存在实例，直接返回
    if _store_instance is not None:
        return _store_instance

    # 创建新实例
    _store_instance = await _create_store_instance()

    # 如果尚未初始化表结构，执行初始化
    if not _setup_done:
        await _store_instance.setup()
        _setup_done = True

    return _store_instance

