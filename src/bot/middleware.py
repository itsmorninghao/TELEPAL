"""Bot 中间件"""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """日志中间件"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message):
            chat_type = event.chat.type
            user_id = event.from_user.id if event.from_user else None
            chat_id = event.chat.id

            logger.info(
                f"收到消息 - 用户: {user_id}, 聊天类型: {chat_type}, "
                f"聊天ID: {chat_id}, 消息ID: {event.message_id}"
            )

        return await handler(event, data)


class ErrorHandlingMiddleware(BaseMiddleware):
    """错误处理中间件"""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        try:
            return await handler(event, data)
        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}", exc_info=True)

            # 如果是消息事件，尝试发送错误提示
            if isinstance(event, Message):
                try:
                    error_messages = {
                        "数据库": "服务暂时不可用，请稍后重试",
                        "API": "AI 服务暂时不可用，请稍后重试",
                        "网络": "网络连接出现问题，请稍后重试",
                    }

                    # 根据错误类型返回不同的提示
                    error_msg = "发生未知错误，请联系管理员"
                    error_str = str(e).lower()

                    if "database" in error_str or "connection" in error_str:
                        error_msg = error_messages["数据库"]
                    elif "api" in error_str or "openai" in error_str:
                        error_msg = error_messages["API"]
                    elif "network" in error_str or "timeout" in error_str:
                        error_msg = error_messages["网络"]

                    await event.answer(error_msg)
                except Exception:
                    # 如果发送错误提示也失败，记录日志
                    logger.error("发送错误提示失败", exc_info=True)

            # 不继续传播异常，避免影响其他消息处理
            return None
