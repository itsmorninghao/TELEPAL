"""应用入口"""

import asyncio
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.bot.admin_handlers import admin_router
from src.bot.handlers import router as handlers_router
from src.bot.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
)
from src.bot.scheduler_service import get_scheduler_service
from src.database import (
    close_engine,
    close_pool,
    create_pool,
    health_check,
)
from src.database.init_db import init_database
from src.utils.logger import setup_logger
from src.utils.settings import setting

logger = setup_logger()


async def main():
    """主函数"""
    try:
        await create_pool()
        if not await health_check():
            raise Exception("数据库连接失败")

        # 执行数据库初始化
        await init_database()

        bot = Bot(
            token=setting.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
        )
        dp = Dispatcher()

        # 初始化定时任务调度器
        scheduler_service = get_scheduler_service()
        await scheduler_service.initialize(bot)

        # 按顺序注册中间件
        # 注意：中间件的执行顺序与注册顺序相反，后进先出
        # 所以先注册的中间件最后执行

        # 错误处理中间件
        dp.message.middleware(ErrorHandlingMiddleware())

        # 日志中间件
        dp.message.middleware(LoggingMiddleware())

        # 注册路由器
        # 注意：顺序很重要，命令处理器（admin_router）应该先注册然后才是消息处理器（handlers_router）
        dp.include_router(admin_router)
        dp.include_router(handlers_router)

        logger.info("telepal已启动")

        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭...")
    except Exception as e:
        logger.error(f"Bot 运行出错: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # 关闭定时任务调度器
        scheduler_service = get_scheduler_service()
        await scheduler_service.shutdown()

        # 关闭数据库连接
        await close_pool()  # LangGraph 连接池
        await close_engine()  # SQLAlchemy 引擎
        logger.info("Bot 已关闭")


if __name__ == "__main__":
    asyncio.run(main())
