"""LangGraph 专用 psycopg 连接池管理

本模块为 LangGraph 组件 `AsyncPostgresSaver` 和 `AsyncPostgresStore` 提供连接池。
LangGraph 要求使用 `psycopg_pool.AsyncConnectionPool` 不兼容 SQLAlchemy。

"""

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from src.utils.settings import get_db_config

# 全局连接池以支持 LangGraph 
_pool: AsyncConnectionPool | None = None


def _build_connection_string() -> str:
    """构建 psycopg 数据库连接字符串"""
    config = get_db_config()
    return (
        f"postgresql://{config['user']}:{config['password']}"
        f"@{config['host']}:{config['port']}/{config['database']}"
    )


async def _configure_connection(conn: AsyncConnection) -> None:
    """配置连接回调，设置 autocommit"""
    await conn.set_autocommit(True)


async def create_pool() -> AsyncConnectionPool:
    """创建 LangGraph 专用连接池"""
    global _pool

    if _pool is None:
        connection_string = _build_connection_string()
        _pool = AsyncConnectionPool(
            conninfo=connection_string,
            min_size=2,
            max_size=20,
            configure=_configure_connection,
            open=False,
        )
        await _pool.open()

    return _pool


async def get_pool() -> AsyncConnectionPool:
    """获取 LangGraph 连接池（如果不存在则创建）"""
    if _pool is None:
        return await create_pool()
    return _pool


async def close_pool() -> None:
    """关闭 LangGraph 连接池"""
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None


async def health_check() -> bool:
    """检查数据库连接健康状态"""
    try:
        pool = await get_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                await cur.fetchone()
        return True
    except Exception:
        return False

