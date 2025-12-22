"""定时任务工具

提供定时任务相关工具：
- schedule_reminder: 创建定时提醒任务
- list_scheduled_tasks: 查看定时任务列表
- cancel_scheduled_task: 取消定时任务
"""

import logging
from datetime import datetime, timezone

from langchain_core.tools import tool

from src.bot import chat_id_context, chat_type_context, user_id_context
from src.bot.scheduler_service import get_scheduler_service

logger = logging.getLogger(__name__)


@tool
async def schedule_reminder(execute_time: str, content: str) -> str:
    """创建定时提醒任务

    使用流程：先调用 get_user_time 获取用户当前时间，计算目标执行时间后调用此工具。

    Args:
        execute_time: ISO 8601 格式时间字符串，必须包含时区，例如 "2024-01-15T14:30:00+08:00"
        content: 提醒内容（最大 500 字符）

    Returns:
        成功返回任务信息，失败返回错误提示
    """
    try:
        # 验证内容长度
        if len(content) > 500:
            return f"错误：提醒内容过长（最大 500 字符），当前长度：{len(content)}"

        if not content.strip():
            return "错误：提醒内容不能为空"

        # 解析 ISO 8601 时间字符串
        execute_at = datetime.fromisoformat(execute_time)

        # 确保时间带有时区信息
        if execute_at.tzinfo is None:
            logger.warning(f"时间缺少时区信息: {execute_time}")
            return (
                "错误：时间必须包含时区信息。请使用 ISO 8601 格式，"
                "例如：2024-01-15T14:30:00+08:00"
            )

        # 验证时间是否在未来
        now = datetime.now(timezone.utc)
        execute_at_utc = execute_at.astimezone(timezone.utc)

        if execute_at_utc <= now:
            return (
                f"错误：执行时间必须在未来。"
                f"当前时间（UTC）：{now.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        # 获取用户上下文信息
        user_id = user_id_context.get()
        chat_id = chat_id_context.get()
        chat_type = chat_type_context.get()

        # 调用 SchedulerService 添加任务
        scheduler = get_scheduler_service()
        task_id = await scheduler.add_task(
            user_id=user_id,
            chat_id=chat_id,
            chat_type=chat_type,
            content=content.strip(),
            execute_at=execute_at,
        )

        # 格式化返回消息
        time_str = execute_at.strftime("%Y-%m-%d %H:%M")
        logger.info(
            f"定时任务创建成功: task_id={task_id}, "
            f"user_id={user_id}, execute_at={execute_at}"
        )

        return (
            f"已创建提醒任务（ID: {task_id}）\n"
            f"执行时间：{time_str}\n"
            f"内容：{content.strip()}"
        )

    except ValueError as e:
        logger.warning(f"时间格式解析失败: {execute_time}, error={e}")
        return (
            "错误：时间格式不正确。请使用 ISO 8601 格式，"
            "例如：2024-01-15T14:30:00+08:00"
        )
    except Exception as e:
        logger.error(f"创建定时任务失败: {e}", exc_info=True)
        return f"抱歉，创建提醒任务时出现错误：{str(e)}"


def _format_task_list(tasks: list, title: str) -> str:
    """格式化任务列表为字符串

    Args:
        tasks: 任务列表
        title: 列表标题

    Returns:
        格式化后的字符串
    """
    if not tasks:
        return f"{title}\n\n暂无待执行的定时任务"

    lines = [f"{title}\n"]
    for task in tasks:
        time_str = task.execute_at.strftime("%Y-%m-%d %H:%M")
        chat_type_label = "私聊" if task.chat_type == "private" else "群聊"
        # 截断过长的内容
        content_preview = (
            task.content[:30] + "..." if len(task.content) > 30 else task.content
        )
        lines.append(
            f"• ID: {task.id} | {time_str} | {chat_type_label}\n"
            f"  内容: {content_preview}"
        )

    lines.append(f"\n共 {len(tasks)} 个任务")
    return "\n".join(lines)


@tool
async def list_scheduled_tasks() -> str:
    """查看当前上下文的定时任务列表

    Returns:
        任务列表或错误信息
    """
    try:
        chat_id = chat_id_context.get()
        chat_type = chat_type_context.get()

        scheduler = get_scheduler_service()
        tasks = await scheduler.get_tasks_by_chat(chat_id)
        title = "用户的定时任务：" if chat_type == "private" else "本群定时任务："
        return _format_task_list(tasks, title)

    except Exception as e:
        logger.error(f"查询定时任务失败: {e}", exc_info=True)
        return f"查询定时任务时出现错误：{str(e)}"


@tool
async def cancel_scheduled_task(task_id: int) -> str:
    """取消/删除定时任务

    只能取消当前上下文（chat_id）的任务。

    Args:
        task_id: 要取消的任务 ID

    Returns:
        操作结果
    """
    try:
        chat_id = chat_id_context.get()
        scheduler = get_scheduler_service()

        # 获取任务信息
        task = await scheduler.get_task_by_id(task_id)
        if not task:
            return f"错误：任务 ID {task_id} 不存在"

        if task.is_executed:
            return f"错误：任务 ID {task_id} 已执行，无法取消"

        # 简单鉴权
        if task.chat_id != chat_id:
            return "没有权限取消此任务（任务不属于当前上下文）"

        # 取消任务
        await scheduler.cancel_task(task_id)
        return f"已取消任务（ID: {task_id}）\n内容：{task.content}"

    except Exception as e:
        logger.error(f"取消定时任务失败: {e}", exc_info=True)
        return f"取消定时任务时出现错误：{str(e)}"
