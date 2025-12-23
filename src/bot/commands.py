"""命令元数据定义

此模块定义命令的元数据，用于生成帮助信息等用途。
实际的命令路由由 Aiogram 装饰器处理（command_handlers.py）。
"""

import logging
from dataclasses import dataclass
from typing import List

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
)

from src.database.repositories.auth import list_super_admins

logger = logging.getLogger(__name__)


@dataclass
class CommandMetadata:
    """命令元数据定义"""

    name: str  # 命令名称（如 "group_authorize"）
    description: str  # 命令描述
    usage: str  # 使用说明
    required_role: str  # 所需权限：'super_admin' | 'group_admin' | 'user'
    allowed_chat_types: List[str]  # 允许使用的场景


# 命令元数据列表用于生成帮助信息
COMMANDS_METADATA: List[CommandMetadata] = [
    # 超管独占指令（仅私聊）
    CommandMetadata(
        name="group_authorize",
        description="授权群组",
        usage="/group_authorize <group_id> - 授权群组",
        required_role="super_admin",
        allowed_chat_types=["private"],
    ),
    CommandMetadata(
        name="group_revoke",
        description="撤销群组授权",
        usage="/group_revoke <group_id> - 撤销群组授权",
        required_role="super_admin",
        allowed_chat_types=["private"],
    ),
    CommandMetadata(
        name="group_list",
        description="查看所有已授权群组",
        usage="/group_list - 查看所有已授权群组",
        required_role="super_admin",
        allowed_chat_types=["private"],
    ),
    CommandMetadata(
        name="permission_set",
        description="设置用户权限",
        usage="/permission_set <user_id> <role> - 设置用户权限\n角色: super_admin, user",
        required_role="super_admin",
        allowed_chat_types=["private"],
    ),
    # 管理指令（群组和私聊）
    CommandMetadata(
        name="whitelist_add",
        description="添加白名单用户",
        usage="/whitelist_add <user_id> [private|group] [group_id] - 添加白名单用户",
        required_role="group_admin",
        allowed_chat_types=["private", "group"],
    ),
    CommandMetadata(
        name="whitelist_remove",
        description="移除白名单用户",
        usage="/whitelist_remove <user_id> [private|group] [group_id] - 移除白名单用户",
        required_role="group_admin",
        allowed_chat_types=["private", "group"],
    ),
    CommandMetadata(
        name="whitelist_list",
        description="查看白名单列表",
        usage="/whitelist_list [private|group] [group_id] - 查看白名单列表",
        required_role="group_admin",
        allowed_chat_types=["private", "group"],
    ),
    # 普通指令（群组和私聊）
    CommandMetadata(
        name="memory_list",
        description="查看长期记忆",
        usage="/memory_list [user_id] [query] - 查看长期记忆",
        required_role="user",
        allowed_chat_types=["private", "group"],
    ),
    CommandMetadata(
        name="memory_delete",
        description="删除长期记忆",
        usage="/memory_delete [user_id] <memory_key> - 删除长期记忆",
        required_role="user",
        allowed_chat_types=["private", "group"],
    ),
    # 位置信息命令由于tg限制原因仅私聊可用
    # 为了让群聊用户也能使用相关功能，为决定加入自行选择
    CommandMetadata(
        name="set_location",
        description="设置位置信息",
        usage="/set_location - 设置位置信息",
        required_role="user",
        allowed_chat_types=["private", "group"],
    ),
    CommandMetadata(
        name="help",
        description="显示帮助信息",
        usage="/help - 显示可用命令列表",
        required_role="user",
        allowed_chat_types=["private", "group"],
    ),
]


def get_commands_by_role(role: str) -> List[CommandMetadata]:
    """根据角色获取可用命令列表"""
    if role == "super_admin":
        return COMMANDS_METADATA
    elif role == "group_admin":
        return [
            cmd
            for cmd in COMMANDS_METADATA
            if cmd.required_role in ["group_admin", "user"]
        ]
    else:
        return [cmd for cmd in COMMANDS_METADATA if cmd.required_role == "user"]


def get_commands_by_chat_type(chat_type: str) -> List[CommandMetadata]:
    """根据聊天类型获取可用命令列表"""
    return [cmd for cmd in COMMANDS_METADATA if chat_type in cmd.allowed_chat_types]


# 角色显示配置
ROLE_DISPLAY = {
    "super_admin": ("🔴 超管命令", "super_admin"),
    "group_admin": ("🟡 管理命令", "group_admin"),
    "user": ("🟢 普通命令", "user"),
}


def generate_help_text(
    user_role: str,
    chat_type: str,
    is_group_admin: bool = False,
) -> str:
    """
    根据用户角色和聊天类型动态生成帮助文本

    Args:
        user_role: 用户角色 ("super_admin", "group_admin", "user")
        chat_type: 聊天类型 ("private", "group")
        is_group_admin: 是否为群组管理员（用于群组场景）

    Returns:
        格式化的帮助文本
    """
    help_text = "📋 可用命令列表\n\n"

    # 按角色分组命令
    role_commands: dict[str, List[CommandMetadata]] = {
        "super_admin": [],
        "group_admin": [],
        "user": [],
    }

    # 先过滤聊天类型
    for cmd in COMMANDS_METADATA:
        if chat_type not in cmd.allowed_chat_types:
            continue
        role_commands[cmd.required_role].append(cmd)

    # 再过滤身份
    if user_role == "super_admin" and chat_type == "private":
        if role_commands["super_admin"]:
            title, _ = ROLE_DISPLAY["super_admin"]
            help_text += f"{title}：\n"
            for cmd in role_commands["super_admin"]:
                help_text += f"• {cmd.usage}\n"
            help_text += "\n"

    if user_role == "super_admin" or is_group_admin:
        if role_commands["group_admin"]:
            title, _ = ROLE_DISPLAY["group_admin"]
            help_text += f"{title}：\n"
            for cmd in role_commands["group_admin"]:
                help_text += f"• {cmd.usage}\n"
            help_text += "\n"

    if role_commands["user"]:
        title, _ = ROLE_DISPLAY["user"]
        help_text += f"{title}：\n"
        for cmd in role_commands["user"]:
            help_text += f"• {cmd.usage}\n"

    return help_text


async def setup_bot_commands(bot: Bot) -> None:
    """
    设置 Bot 命令菜单
    """
    # 为普通用户设置私聊命令 (AllPrivateChats)
    # 包含：user 角色 且 支持 private 的命令
    private_user_commands = [
        BotCommand(command=cmd.name, description=cmd.description)
        for cmd in COMMANDS_METADATA
        if cmd.required_role
        in ["user", "group_admin"]  # 包含管理工具，因为私聊无法区分是否是群管
        and "private" in cmd.allowed_chat_types
    ]
    if private_user_commands:
        await bot.set_my_commands(
            commands=private_user_commands, scope=BotCommandScopeAllPrivateChats()
        )

    # 为超管设置私聊全量命令 (ScopeChat)
    # [超管命令 + 普通私聊命令] 的合集
    all_private_commands_for_admin = [
        BotCommand(command=cmd.name, description=cmd.description)
        for cmd in COMMANDS_METADATA
        if "private" in cmd.allowed_chat_types
    ]
    if all_private_commands_for_admin:
        super_admin_ids = await list_super_admins()
        for user_id in super_admin_ids:
            try:
                await bot.set_my_commands(
                    commands=all_private_commands_for_admin,
                    scope=BotCommandScopeChat(chat_id=user_id),
                )
            except Exception as e:
                logger.warning(
                    f"超管用户 {user_id} 设置指令失败（可能未与机器人对话过）: {e}"
                )

    # 为群组普通用户设置命令 (AllGroupChats)
    group_user_commands = [
        BotCommand(command=cmd.name, description=cmd.description)
        for cmd in COMMANDS_METADATA
        if cmd.required_role == "user" and "group" in cmd.allowed_chat_types
    ]
    if group_user_commands:
        await bot.set_my_commands(
            commands=group_user_commands, scope=BotCommandScopeAllGroupChats()
        )

    # 为群组管理员设置命令 (AllChatAdministrators)
    # 包含：group_admin + user 的群组命令
    group_admin_commands = [
        BotCommand(command=cmd.name, description=cmd.description)
        for cmd in COMMANDS_METADATA
        if cmd.required_role in ["group_admin", "user"]
        and "group" in cmd.allowed_chat_types
    ]
    if group_admin_commands:
        await bot.set_my_commands(
            commands=group_admin_commands,
            scope=BotCommandScopeAllChatAdministrators(),
        )
