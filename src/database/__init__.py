"""数据库模块 - 统一数据库操作入口

本模块整合了所有数据库相关操作，包括：
- 连接池管理
- 数据库初始化
- LangGraph 存储（对话记忆、长期记忆）
- 业务数据访问层（认证、用户资料）
"""

# 连接管理
from src.database.connection import (
    close_pool,
    create_pool,
    get_db_config,
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
    # 连接管理
    "create_pool",
    "get_pool",
    "close_pool",
    "get_db_config",
    "health_check",
    # LangGraph
    "get_checkpointer",
    "get_store",
    # 业务 repositories
    "auth",
    "profiles",
]
