"""应用入口"""

import asyncio
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.bot.admin_handlers import register_all_commands
from src.bot.handlers import router as handlers_router
from src.bot.middleware import (
    ErrorHandlingMiddleware,
    LoggingMiddleware,
)
from src.utils.db.checkpointer import init_checkpointer
from src.utils.db.connection import close_pool, create_pool, health_check
from src.utils.db.init_db import init_database
from src.utils.db.store import init_store
from src.utils.logger import setup_logger
from src.utils.settings import setting

logger = setup_logger()


async def main():
    """主函数"""
    try:
        await create_pool()
        if not await health_check():
            raise Exception("数据库连接失败")

        # 2. 执行数据库初始化
        await init_database()

        await init_checkpointer()
        await init_store()

        bot = Bot(
            token=setting.TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN_V2),
        )
        dp = Dispatcher()

        # 注册所有命令
        register_all_commands()

        # 按顺序注册中间件
        # 注意：中间件的执行顺序与注册顺序相反，后进先出
        # 所以先注册的中间件最后执行

        # 错误处理中间件
        dp.message.middleware(ErrorHandlingMiddleware())

        # 日志中间件
        dp.message.middleware(LoggingMiddleware())

        # 注册消息处理器（统一处理所有消息，包括命令）
        dp.include_router(handlers_router)

        logger.info("telepal已启动")

        await dp.start_polling(bot)

    except KeyboardInterrupt:
        logger.info("收到停止信号，正在关闭...")
    except Exception as e:
        logger.error(f"Bot 运行出错: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # 清理资源：关闭统一的数据库连接池
        await close_pool()
        logger.info("Bot 已关闭")


if __name__ == "__main__":
    asyncio.run(main())
