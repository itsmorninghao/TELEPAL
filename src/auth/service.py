"""权限检查服务"""

import logging
from typing import Optional

from aiogram import Bot
from aiogram.types import ChatMember, Message

from src.auth.database import (
    is_group_authorized,
    is_super_admin,
    is_user_whitelisted,
)
from src.auth.models import UserRole

logger = logging.getLogger(__name__)


async def check_super_admin(user_id: int) -> bool:
    """检查用户是否为超管"""
    return await is_super_admin(user_id)


async def check_group_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    """检查用户是否为群组管理员（通过 Telegram API）"""
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        is_admin = member.status in ["administrator", "creator"]
        return is_admin
    except Exception as e:
        logger.warning(
            f"检查群管权限失败: user_id={user_id}, chat_id={chat_id}, error={e}"
        )
        return False


async def check_group_authorized(chat_id: int) -> bool:
    """检查群组是否已授权"""
    return await is_group_authorized(chat_id)


async def check_whitelist(
    user_id: int, chat_type: str, chat_id: Optional[int] = None
) -> bool:
    """检查用户是否在白名单中"""
    return await is_user_whitelisted(user_id, chat_type, chat_id)


async def check_permission(
    bot: Bot,
    user_id: int,
    chat_type: str,
    chat_id: Optional[int] = None,
    require_super_admin: bool = False,
    require_group_admin: bool = False,
) -> bool:
    """综合权限检查"""
    # 1. 检查超管权限
    if require_super_admin:
        if not await check_super_admin(user_id):
            return False

    # 2. 检查群组管理员权限
    if require_group_admin and chat_type == "group" and chat_id:
        if not await check_group_admin(bot, chat_id, user_id):
            return False

    return True


async def check_private_authorization(user_id: int) -> bool:
    """检查私聊授权（超管或私聊白名单）"""
    # 检查是否是超管
    if await check_super_admin(user_id):
        return True

    # 检查是否在私聊白名单中
    return await check_whitelist(user_id, "private", None)


async def check_user_role_in_group(bot: Bot, chat_id: int, user_id: int) -> str:
    """检查用户在群组中的身份，返回 super_admin/group_admin/authorized_user/unauthorized"""
    # 1. 检查是否是超管
    if await check_super_admin(user_id):
        return "super_admin"

    # 2. 检查是否是群组管理员
    if await check_group_admin(bot, chat_id, user_id):
        return "group_admin"

    # 3. 检查是否在群组白名单中
    if await check_whitelist(user_id, "group", chat_id):
        return "authorized_user"

    # 4. 都不符合
    return "unauthorized"


def is_command(text: Optional[str]) -> bool:
    """判断是否是命令（以 / 开头）"""
    if not text:
        return False
    return text.strip().startswith("/")


async def is_mention_bot(message: Message, bot: Bot) -> bool:
    """判断消息是否 @ 了机器人"""
    if message.chat.type not in ["group", "supergroup"]:
        return False

    # 检查消息实体中是否有 @ 提及
    if message.entities:
        bot_me = await bot.get_me()
        for entity in message.entities:
            if entity.type == "mention":
                # 提取 @ 提及的用户名
                if message.text:
                    mention = message.text[
                        entity.offset : entity.offset + entity.length
                    ]
                    if mention == f"@{bot_me.username}":
                        return True
            elif entity.type == "text_mention":
                # 检查是否提及了机器人
                if entity.user and entity.user.id == bot_me.id:
                    return True
            elif entity.type == "bot_command":
                # 这种情况没有被处理!就是/memory_list@bot_username这样的形式
                if message.text and "@" in message.text:
                    command_text = message.text[entity.offset : entity.offset + entity.length]
                    if f"@{bot_me.username}" in command_text:
                        return True

    return False


async def is_reply_to_bot(message: Message, bot: Bot) -> bool:
    """判断消息是否回复了机器人发送的消息"""
    if not message.reply_to_message:
        return False

    # 检查被回复的消息是否是机器人发送的
    bot_me = await bot.get_me()
    return (
        message.reply_to_message.from_user is not None
        and message.reply_to_message.from_user.id == bot_me.id
    )
