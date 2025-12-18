"""定时任务数据访问层"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.engine import get_session
from src.database.models import ScheduledTaskModel


async def create_task(
    user_id: int,
    chat_id: int,
    chat_type: str,
    content: str,
    execute_at: datetime,
) -> ScheduledTaskModel:
    """创建定时任务

    Args:
        user_id: 用户 ID
        chat_id: 聊天 ID
        chat_type: 聊天类型 ('private' 或 'group')
        content: 任务内容
        execute_at: 执行时间（带时区）

    Returns:
        创建的任务模型
    """
    async with get_session() as session:
        task = ScheduledTaskModel(
            user_id=user_id,
            chat_id=chat_id,
            chat_type=chat_type,
            content=content,
            execute_at=execute_at,
        )
        session.add(task)
        await session.flush()
        await session.refresh(task)
        return task


async def get_pending_tasks(limit: int = 1000) -> list[ScheduledTaskModel]:
    """用于系统启动时恢复所有待执行的任务

    Args:
        limit: 返回数量限制

    Returns:
        待执行任务列表
    """
    async with get_session() as session:
        now = datetime.now(timezone.utc)
        stmt = (
            select(ScheduledTaskModel)
            .where(
                ScheduledTaskModel.is_executed == False,  # noqa: E712
                ScheduledTaskModel.execute_at > now,
            )
            .order_by(ScheduledTaskModel.execute_at)
            .limit(limit)
        )

        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_task_by_id(task_id: int) -> Optional[ScheduledTaskModel]:
    """根据 ID 获取任务"""
    async with get_session() as session:
        stmt = select(ScheduledTaskModel).where(ScheduledTaskModel.id == task_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def mark_task_as_executed(task_id: int) -> bool:
    """标记任务为已执行"""
    async with get_session() as session:
        stmt = select(ScheduledTaskModel).where(ScheduledTaskModel.id == task_id)
        result = await session.execute(stmt)
        task = result.scalar_one_or_none()

        if not task:
            return False

        task.is_executed = True
        task.executed_at = datetime.now(timezone.utc)
        await session.flush()
        return True
