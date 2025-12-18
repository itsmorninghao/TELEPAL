"""定时任务调度服务

使用 APScheduler 管理定时任务的调度和执行。
"""

import logging
from datetime import datetime, timezone

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegramify_markdown import markdownify

from src.database.repositories import scheduled_tasks as task_repo

logger = logging.getLogger(__name__)


class SchedulerService:
    """定时任务调度服务（单例）

    职责：
    - 管理所有定时任务的调度和执行
    - 系统启动时从数据库恢复未执行的任务
    - 任务到期时触发回调函数发送提醒消息
    """

    _instance: "SchedulerService | None" = None
    _scheduler: AsyncIOScheduler | None = None
    _bot: Bot | None = None
    _initialized: bool = False

    def __new__(cls) -> "SchedulerService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def initialize(self, bot: Bot) -> None:
        """初始化

        Args:
            bot: Telegram Bot 实例，用于发送提醒消息
        """
        if self._initialized:
            logger.warning("SchedulerService 已经初始化，跳过重复初始化")
            return

        self._bot = bot
        self._scheduler = AsyncIOScheduler()
        self._scheduler.start()
        self._initialized = True

        logger.info("APScheduler 调度器已启动")

        # 从数据库加载待执行任务
        await self._load_pending_tasks()

    async def add_task(
        self,
        user_id: int,
        chat_id: int,
        chat_type: str,
        content: str,
        execute_at: datetime,
    ) -> int:
        """添加定时任务

        流程：
        1. 先保存到数据库，获取任务 ID
        2. 如果执行时间在未来，添加到内存调度器
        3. 返回任务 ID

        Args:
            user_id: 用户 ID
            chat_id: 聊天 ID
            chat_type: 聊天类型 ('private' 或 'group')
            content: 任务内容
            execute_at: 执行时间（带时区）

        Returns:
            任务 ID
        """
        # 1. 保存到数据库
        task = await task_repo.create_task(
            user_id=user_id,
            chat_id=chat_id,
            chat_type=chat_type,
            content=content,
            execute_at=execute_at,
        )
        task_id = task.id

        logger.info(
            f"任务已保存到数据库: task_id={task_id}, "
            f"user_id={user_id}, execute_at={execute_at}"
        )

        # 2. 如果时间在未来，添加到调度器
        now = datetime.now(timezone.utc)
        # 确保 execute_at 是 UTC 时区用于比较
        execute_at_utc = (
            execute_at.astimezone(timezone.utc)
            if execute_at.tzinfo
            else execute_at.replace(tzinfo=timezone.utc)
        )

        if execute_at_utc > now and self._scheduler:
            self._scheduler.add_job(
                self._execute_task,
                "date",
                run_date=execute_at,
                args=[task_id],
                id=f"task_{task_id}",
                replace_existing=True,
            )
            logger.info(f"任务已添加到调度器: task_id={task_id}")

        return task_id

    async def _load_pending_tasks(self) -> None:
        """系统启动时，从数据库加载未执行且时间在未来的任务"""
        try:
            tasks = await task_repo.get_pending_tasks()
            loaded_count = 0

            for task in tasks:
                if self._scheduler:
                    self._scheduler.add_job(
                        self._execute_task,
                        "date",
                        run_date=task.execute_at,
                        args=[task.id],
                        id=f"task_{task.id}",
                        replace_existing=True,
                    )
                    loaded_count += 1

            logger.info(f"从数据库恢复了 {loaded_count} 个待执行任务")
        except Exception as e:
            logger.error(f"加载待执行任务失败: {e}", exc_info=True)

    async def _execute_task(self, task_id: int) -> None:
        """任务执行回调

        当任务到期时，APScheduler 会调用此方法

        Args:
            task_id: 任务 ID
        """
        try:
            # 从数据库获取任务详情
            task = await task_repo.get_task_by_id(task_id)
            if not task:
                logger.warning(f"任务不存在: task_id={task_id}")
                return

            if task.is_executed:
                logger.warning(f"任务已执行，跳过: task_id={task_id}")
                return

            # 发送提醒消息
            if self._bot:
                formatted_text = markdownify(task.content)

                await self._bot.send_message(
                    chat_id=task.chat_id,
                    text=formatted_text,
                )
                # TODO:即使发送失败，也标记为已执行，避免重复发送，考虑后续添加重试机制

            # 更新任务状态
            await task_repo.mark_task_as_executed(task_id)
            logger.info(f"提醒消息已发送: task_id={task_id}, chat_id={task.chat_id}")

        except Exception as e:
            logger.error(f"执行任务失败: task_id={task_id}, error={e}", exc_info=True)

    async def shutdown(self) -> None:
        """关闭调度器"""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._scheduler = None
            logger.info("APScheduler 调度器已关闭")

        self._initialized = False
        self._bot = None


# 获取单例实例
def get_scheduler_service() -> SchedulerService:
    """获取 SchedulerService 单例实例"""
    return SchedulerService()
