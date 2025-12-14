"""SQLAlchemy 异步引擎配置

本模块为业务表提供 SQLAlchemy 异步数据库连接。
LangGraph 相关操作仍使用 langgraph_pool.py 中的 psycopg 连接池。
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.utils.settings import get_db_config

# 全局引擎实例
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _build_async_connection_string() -> str:
    """构建 SQLAlchemy 异步连接字符串"""
    config = get_db_config()
    return (
        f"postgresql+asyncpg://{config['user']}:{config['password']}"
        f"@{config['host']}:{config['port']}/{config['database']}"
    )


def get_engine() -> AsyncEngine:
    """获取 SQLAlchemy 异步引擎（单例）"""
    global _engine

    if _engine is None:
        connection_string = _build_async_connection_string()
        _engine = create_async_engine(
            connection_string,
            echo=False,  # 生产环境关闭 SQL 日志
            pool_size=10,
            max_overflow=20,
        )

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """获取会话工厂（单例）"""
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取异步会话（上下文管理器）

    使用示例：
        async with get_session() as session:
            result = await session.execute(select(Model))
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def close_engine() -> None:
    """关闭 SQLAlchemy 引擎"""
    global _engine, _session_factory

    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None
