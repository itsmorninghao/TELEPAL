"""数据库模块 - 统一数据库操作入口

本模块整合了所有数据库相关操作，包括：
- SQLAlchemy 引擎
- LangGraph 连接池
- LangGraph 存储（对话记忆、长期记忆）
- 业务数据访问层（认证、用户资料）
"""

# SQLAlchemy 引擎
from src.database.engine import (
    close_engine,
    get_engine,
    get_session,
)

# LangGraph 专用连接池
from src.database.langgraph_pool import (
    close_pool,
    create_pool,
    get_pool,
    health_check,
)

# LangGraph 存储
from src.database.langgraph import (
    get_checkpointer,
    get_store,
)

# 业务数据访问层
from src.database.repositories import auth, profiles

__all__ = [
    # SQLAlchemy 引擎
    "get_engine",
    "get_session",
    "close_engine",
    # LangGraph 连接池
    "create_pool",
    "get_pool",
    "close_pool",
    "health_check",
    # LangGraph 存储
    "get_checkpointer",
    "get_store",
    # 业务 repositories
    "auth",
    "profiles",
]
