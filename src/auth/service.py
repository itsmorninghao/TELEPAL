"""权限检查服务"""

import logging
from typing import Optional

from aiogram import Bot

from src.auth.models import UserRole
from src.database.repositories.auth import (
    is_group_authorized,
    is_super_admin,
    is_user_whitelisted,
)

logger = logging.getLogger(__name__)


async def check_super_admin(user_id: int) -> bool:
    """检查用户是否为超管"""
    return await is_super_admin(user_id)


async def check_group_admin(bot: Bot, group_id: int, user_id: int) -> bool:
    """检查用户是否为群组管理员（通过 Telegram API）"""
    try:
        member = await bot.get_chat_member(chat_id=group_id, user_id=user_id)
        is_admin = member.status in ["administrator", "creator"]
        return is_admin
    except Exception as e:
        logger.warning(
            f"检查群管权限失败: user_id={user_id}, group_id={group_id}, error={e}"
        )
        return False


async def check_group_authorized(group_id: int) -> bool:
    """检查群组是否已授权"""
    return await is_group_authorized(group_id)


async def check_whitelist(
    user_id: int, chat_type: str, group_id: Optional[int] = None
) -> bool:
    """检查用户是否在白名单中"""
    return await is_user_whitelisted(user_id, chat_type, group_id)


async def check_private_authorization(user_id: int) -> bool:
    """检查私聊授权（超管或私聊白名单）"""
    # 检查是否是超管
    if await check_super_admin(user_id):
        return True

    # 检查是否在私聊白名单中
    return await check_whitelist(user_id, "private", None)


async def check_user_role_in_group(bot: Bot, group_id: int, user_id: int) -> str:
    """检查用户在群组中的身份，返回 super_admin/group_admin/authorized_user/unauthorized"""
    # 1. 检查是否是超管
    if await check_super_admin(user_id):
        return "super_admin"

    # 2. 检查是否是群组管理员
    if await check_group_admin(bot, group_id, user_id):
        return "group_admin"

    # 3. 检查是否在群组白名单中
    if await check_whitelist(user_id, "group", group_id):
        return "authorized_user"

    # 4. 都不符合
    return "unauthorized"
