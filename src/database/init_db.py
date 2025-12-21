"""数据库初始化脚本"""

import sys

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore
from sqlalchemy import select

# 导入 settings 以初始化环境变量和路径
import src.utils.settings  # noqa: F401
from src.database.engine import get_engine, get_session
from src.database.langgraph_pool import create_pool
from src.database.models import Base, UserPermissionModel, WhitelistEntryModel
from src.utils.logger import setup_logger
from src.utils.settings import get_embeddings, get_index_config, setting

logger = setup_logger()


async def _init_langgraph_tables(pool) -> None:
    """初始化 LangGraph 相关表结构

    包括：
    - AsyncPostgresSaver (对话记忆/checkpointer) 所需的表
    - AsyncPostgresStore (长期记忆/向量存储) 所需的表

    Args:
        pool: psycopg 数据库连接池
    """
    # 初始化 checkpointer 表
    logger.info("初始化 LangGraph Checkpointer 表...")
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()

    # 初始化 store 表
    logger.info("初始化 LangGraph Store 表...")
    embeddings = get_embeddings()
    index_config = get_index_config(embeddings)
    store = AsyncPostgresStore(pool, index=index_config)
    await store.setup()


async def _init_super_admins() -> None:
    """初始化超管权限和白名单"""
    initial_admins = (setting.INITIAL_SUPER_ADMINS or "").strip()
    if not initial_admins:
        logger.warning("INITIAL_SUPER_ADMINS 环境变量未设置，跳过超管初始化")
        return

    admin_ids = [
        int(uid.strip())
        for uid in initial_admins.split(",")
        if uid.strip() and uid.strip().isdigit()
    ]

    if not admin_ids:
        logger.warning("INITIAL_SUPER_ADMINS 环境变量为空或格式错误，跳过超管初始化")
        return

    logger.info(f"初始化 {len(admin_ids)} 个超管用户...")

    async with get_session() as session:
        for user_id in admin_ids:
            # 检查并插入超管权限
            stmt = select(UserPermissionModel).where(
                UserPermissionModel.user_id == user_id
            )
            result = await session.execute(stmt)
            if result.scalar_one_or_none() is None:
                permission = UserPermissionModel(user_id=user_id, role="super_admin")
                session.add(permission)

            # 检查并插入私聊白名单
            stmt = select(WhitelistEntryModel).where(
                WhitelistEntryModel.user_id == user_id,
                WhitelistEntryModel.chat_type == "private",
                WhitelistEntryModel.group_id.is_(None),
            )
            result = await session.execute(stmt)
            if result.scalar_one_or_none() is None:
                whitelist_entry = WhitelistEntryModel(
                    user_id=user_id,
                    chat_type="private",
                    group_id=None,
                    created_by=user_id,
                )
                session.add(whitelist_entry)

            logger.info(f"超管用户 {user_id} 初始化完成")


async def init_database() -> None:
    """初始化数据库：创建业务表、初始化超管权限和白名单、初始化 LangGraph 表"""
    try:
        engine = get_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        await _init_super_admins()

        pool = await create_pool()
        await _init_langgraph_tables(pool)

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}", exc_info=True)
        sys.exit(1)
