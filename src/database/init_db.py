"""数据库初始化脚本"""

import asyncio
import sys

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.store.postgres.aio import AsyncPostgresStore

# 导入 settings 以初始化环境变量和路径
import src.utils.settings  # noqa: F401
from src.database.connection import close_pool, create_pool
from src.utils.logger import setup_logger
from src.utils.settings import get_embeddings, get_index_config, setting

logger = setup_logger()


async def _init_langgraph_tables(pool) -> None:
    """初始化 LangGraph 相关表结构

    包括：
    - AsyncPostgresSaver (对话记忆/checkpointer) 所需的表
    - AsyncPostgresStore (长期记忆/向量存储) 所需的表

    Args:
        pool: 数据库连接池
    """
    # 初始化checkpointer表
    logger.info("初始化 LangGraph Checkpointer 表...")
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()

    # 2. 初始化store表
    logger.info("初始化 LangGraph Store 表...")
    embeddings = get_embeddings()
    index_config = get_index_config(embeddings)
    store = AsyncPostgresStore(pool, index=index_config)
    await store.setup()


async def init_database():
    """初始化数据库：创建业务表，初始化超管权限和白名单，初始化 LangGraph 表"""
    try:
        logger.info("开始数据库初始化...")

        pool = await create_pool()

        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                # 1. 创建用户权限表
                logger.info("创建 user_permissions 表...")
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_permissions (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL UNIQUE,
                        role VARCHAR(20) NOT NULL DEFAULT 'user',
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                """)

                # 2. 创建授权群组表
                logger.info("创建 authorized_groups 表...")
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS authorized_groups (
                        id SERIAL PRIMARY KEY,
                        chat_id BIGINT NOT NULL UNIQUE,
                        chat_title VARCHAR(255),
                        authorized_by BIGINT NOT NULL,
                        authorized_at TIMESTAMP DEFAULT NOW(),
                        is_active BOOLEAN DEFAULT TRUE
                    );
                """)

                # 创建索引
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_authorized_groups_chat_id 
                    ON authorized_groups(chat_id);
                """)

                # 3. 创建白名单表
                logger.info("创建 whitelist 表...")
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS whitelist (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        chat_type VARCHAR(20) NOT NULL,
                        chat_id BIGINT,
                        created_at TIMESTAMP DEFAULT NOW(),
                        created_by BIGINT,
                        UNIQUE(user_id, chat_type, chat_id)
                    );
                """)

                # 创建索引
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_whitelist_user_id 
                    ON whitelist(user_id);
                """)

                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_whitelist_chat 
                    ON whitelist(chat_type, chat_id);
                """)

                # 4. 创建用户资料表
                logger.info("创建 user_profiles 表...")
                await cur.execute("""
                    CREATE TABLE IF NOT EXISTS user_profiles (
                        user_id BIGINT PRIMARY KEY,
                        latitude DOUBLE PRECISION NOT NULL,
                        longitude DOUBLE PRECISION NOT NULL,
                        timezone VARCHAR(100),
                        location_updated_at TIMESTAMP DEFAULT NOW(),
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """)

                # 创建索引
                await cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id 
                    ON user_profiles(user_id);
                """)

                # 5. 初始化超管权限和白名单
                initial_admins = (setting.INITIAL_SUPER_ADMINS or "").strip()
                if initial_admins:
                    admin_ids = [
                        int(uid.strip())
                        for uid in initial_admins.split(",")
                        if uid.strip() and uid.strip().isdigit()
                    ]

                    if admin_ids:
                        logger.info(f"初始化 {len(admin_ids)} 个超管用户...")

                        for user_id in admin_ids:
                            # 插入超管权限（如果不存在）
                            await cur.execute(
                                """
                                INSERT INTO user_permissions (user_id, role)
                                VALUES (%s, 'super_admin')
                                ON CONFLICT (user_id) DO NOTHING;
                            """,
                                (user_id,),
                            )

                            # 插入私聊白名单（如果不存在）
                            await cur.execute(
                                """
                                INSERT INTO whitelist (user_id, chat_type, chat_id, created_by)
                                SELECT %s, 'private', NULL, %s
                                WHERE NOT EXISTS (
                                    SELECT 1 FROM whitelist 
                                    WHERE user_id = %s AND chat_type = 'private' AND chat_id IS NULL
                                );
                            """,
                                (user_id, user_id, user_id),
                            )

                            logger.info(f"超管用户 {user_id} 初始化完成")
                    else:
                        logger.warning(
                            "INITIAL_SUPER_ADMINS 环境变量为空或格式错误，跳过超管初始化"
                        )
                else:
                    logger.warning(
                        "INITIAL_SUPER_ADMINS 环境变量未设置，跳过超管初始化"
                    )

        # 6. 初始化 LangGraph 相关表（在业务表之后）
        await _init_langgraph_tables(pool)

        await close_pool()
        logger.info("数据库初始化成功")

    except Exception as e:
        logger.error(f"数据库初始化失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(init_database())
