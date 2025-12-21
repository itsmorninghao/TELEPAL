from contextvars import ContextVar
from typing import Optional

from aiogram import Bot

# 用于在全局范围内访问 Bot 实例
bot_instance: ContextVar[Optional[Bot]] = ContextVar("bot_instance", default=None)
user_id_context: ContextVar[int] = ContextVar("user_id")
group_id_context: ContextVar[Optional[int]] = ContextVar("group_id", default=None)
chat_id_context: ContextVar[int] = ContextVar("chat_id")
chat_type_context: ContextVar[str] = ContextVar("chat_type")
