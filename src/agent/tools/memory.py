"""Agent 工具定义（长期记忆工具）"""

import logging
import uuid

from langchain_core.tools import tool

from src.bot import user_id_context
from src.database import get_store

logger = logging.getLogger(__name__)


async def _save_memory_impl(user_id: int, content: str) -> str:
    """存储用户信息到长期记忆"""
    try:
        store = await get_store()
        namespace = ("memories", str(user_id))
        key = str(uuid.uuid4())

        await store.aput(
            namespace=namespace,
            key=key,
            value={"value": content},  # 改为字典格式
        )

        return f"记忆已保存，key: {key}"
    except Exception as e:
        return f"保存记忆时发生错误: {str(e)}"


async def _search_memories_impl(user_id: int, query: str, limit: int = 5) -> str:
    """根据 query 检索相关记忆"""
    try:
        logger.info(f"用户:{user_id} 正在搜索记忆: {query}")
        store = await get_store()
        namespace = ("memories", str(user_id))

        # 使用语义搜索
        results = await store.asearch(
            namespace,
            query=query,
            limit=limit,
        )

        logger.info(f"搜索记忆结果: {results}")

        if not results:
            return f"未找到关于 '{query}' 的相关记忆"

        # 格式化结果
        memories = []
        for idx, result in enumerate(results, 1):
            key = result.key
            value_dict = result.value
            content = (
                value_dict.get("value", "")
                if isinstance(value_dict, dict)
                else str(value_dict)
            )
            memories.append(f"{idx}. [{key}]: {content}")

        return "\n".join(memories)
    except Exception as e:
        return f"检索记忆时发生错误: {str(e)}"


@tool
async def save_memory(content: str) -> str:
    """存储用户的重要信息到长期记忆

    Args:
        content: 要存储的内容（如用户偏好、关键事实等）
    """
    try:
        # 从上下文获取 user_id
        user_id = user_id_context.get()
        return await _save_memory_impl(user_id, content)
    except LookupError:
        return "错误：无法获取用户 ID，请确保在正确的上下文中调用此工具"


@tool
async def search_memories(query: str, limit: int = 5) -> str:
    """根据自然语言查询检索相关记忆

    Args:
        query: 自然语言查询（如"用户喜欢的颜色"）
        limit: 返回数量限制（默认 5）
    """
    try:
        # 从上下文获取 user_id
        user_id = user_id_context.get()
        return await _search_memories_impl(user_id, query, limit)
    except LookupError:
        return "错误：无法获取用户 ID，请确保在正确的上下文中调用此工具"


if __name__ == "__main__":
    import asyncio
    import sys

    # 导入 settings 以初始化环境变量和路径
    import src.utils.settings  # noqa: F401
    from src.database import close_pool, create_pool, health_check

    async def test():
        """测试记忆工具"""
        test_user_id = 12345

        try:
            # 1. 检查数据库连接
            await create_pool()
            if not await health_check():
                print("错误：数据库连接失败，请检查数据库配置和连接状态")

            # 2. 测试保存记忆
            result1 = await _save_memory_impl(test_user_id, "用户喜欢蓝色")
            print(result1)
            result2 = await _search_memories_impl(test_user_id, "蓝色", limit=5)
            print(result2)

        except Exception as e:
            print(f"\n测试过程中发生错误: {str(e)}")
        finally:
            # 关闭连接池
            await close_pool()

    asyncio.run(test())
