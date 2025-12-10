"""PostgreSQL 数据库连接池管理"""

from typing import Any, Dict

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from src.utils.settings import setting

# 全局连接池
_pool: AsyncConnectionPool | None = None


def get_db_config() -> Dict[str, Any]:
    """获取数据库配置"""
    return {
        "host": setting.POSTGRES_HOST,
        "port": setting.POSTGRES_PORT,
        "database": setting.POSTGRES_DB,
        "user": setting.POSTGRES_USER,
        "password": setting.POSTGRES_PASSWORD,
    }


def _build_connection_string() -> str:
    """构建数据库连接字符串"""
    config = get_db_config()
    return (
        f"postgresql://{config['user']}:{config['password']}"
        f"@{config['host']}:{config['port']}/{config['database']}"
    )


async def _configure_connection(conn: AsyncConnection):
    """配置连接回调，设置 autocommit"""
    await conn.set_autocommit(True)


async def create_pool() -> AsyncConnectionPool:
    """创建数据库连接池"""
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
    """获取数据库连接池（如果不存在则创建）"""
    if _pool is None:
        return await create_pool()
    return _pool


async def close_pool() -> None:
    """关闭数据库连接池"""
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

