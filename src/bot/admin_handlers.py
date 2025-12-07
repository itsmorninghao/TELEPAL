"""管理员命令处理器"""

import logging

from aiogram.types import Message

from src.auth.database import (
    add_to_whitelist,
    authorize_group,
    list_authorized_groups,
    list_whitelist,
    remove_from_whitelist,
    revoke_group_authorization,
    set_user_permission,
)
from src.auth.models import UserRole
from src.auth.service import check_super_admin
from src.bot.commands import Command, command_registry
from src.utils.db.store import get_store

logger = logging.getLogger(__name__)


# ==================== 群组授权命令 ====================


async def cmd_group_authorize(message: Message):
    """授权群组（仅超管）"""
    # 解析参数
    args = message.text.split()[1:] if message.text else []
    if not args:
        await message.answer(
            "命令参数错误，请检查格式\n\n/group_authorize <chat_id> - 授权群组",
            parse_mode=None,
        )
        return

    try:
        chat_id = int(args[0])
        user_id = message.from_user.id
        chat_title = message.chat.title if message.chat.title else None

        # 授权群组
        await authorize_group(chat_id, chat_title, user_id)
        await message.answer(f"群组 {chat_id} 已授权。", parse_mode=None)

    except ValueError:
        await message.answer(
            "命令参数错误，请检查格式\n\n/group_authorize <chat_id> - 授权群组\n\n错误：chat_id 必须是数字。",
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"授权群组时出错: {e}", exc_info=True)
        await message.answer("操作失败，请稍后重试。", parse_mode=None)


async def cmd_group_revoke(message: Message):
    """撤销群组授权（仅超管）"""
    # 解析参数
    args = message.text.split()[1:] if message.text else []
    if not args:
        await message.answer(
            "命令参数错误，请检查格式\n\n/group_revoke <chat_id> - 撤销群组授权",
            parse_mode=None,
        )
        return

    try:
        chat_id = int(args[0])

        # 撤销授权
        success = await revoke_group_authorization(chat_id)
        if success:
            await message.answer(f"群组 {chat_id} 的授权已撤销。", parse_mode=None)
        else:
            await message.answer(f"群组 {chat_id} 未找到或未授权。", parse_mode=None)

    except ValueError:
        await message.answer(
            "命令参数错误，请检查格式\n\n/group_revoke <chat_id> - 撤销群组授权\n\n错误：chat_id 必须是数字。",
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"撤销群组授权时出错: {e}", exc_info=True)
        await message.answer("操作失败，请稍后重试。", parse_mode=None)


async def cmd_group_list(message: Message):
    """查看所有已授权群组（仅超管）"""
    try:
        groups = await list_authorized_groups()
        if not groups:
            await message.answer("没有已授权的群组。", parse_mode=None)
            return

        # 格式化列表
        lines = []
        for group in groups:
            title = group.chat_title or "未知"
            lines.append(f"• {group.chat_id} - {title}")

        result = "已授权群组：\n" + "\n".join(lines)
        await message.answer(result, parse_mode=None)

    except Exception as e:
        logger.error(f"列出授权群组时出错: {e}", exc_info=True)
        await message.answer("操作失败，请稍后重试。", parse_mode=None)


# ==================== 白名单管理命令 ====================


async def cmd_whitelist_add(message: Message):
    """添加白名单用户"""
    user_id = message.from_user.id
    args = message.text.split()[1:] if message.text else []

    if not args:
        await message.answer(
            "命令参数错误，请检查格式\n\n/whitelist_add <user_id> [private|group] [chat_id] - 添加白名单用户",
            parse_mode=None,
        )
        return

    try:
        target_user_id = int(args[0])

        # 判断是超管还是群组管理员
        is_super = await check_super_admin(user_id)
        chat_id = None
        chat_type = "private"

        if message.chat.type in ["group", "supergroup"]:
            chat_id = message.chat.id
            # 群组管理员执行时，自动使用当前群组 ID
            if not is_super:
                chat_type = "group"
                await add_to_whitelist(target_user_id, "group", chat_id, user_id)
                await message.answer(
                    f"用户 {target_user_id} 已添加到当前群组白名单。", parse_mode=None
                )
                return

        # 超管可以添加任意白名单
        if is_super:
            chat_type = args[1] if len(args) > 1 else "private"
            if chat_type == "group":
                if len(args) > 2:
                    chat_id = int(args[2])
                elif chat_id is None:
                    # 在私聊中，如果指定了 group 但没有提供 chat_id，需要提示
                    await message.answer(
                        "命令参数错误，请检查格式\n\n/whitelist_add <user_id> [private|group] [chat_id] - 添加白名单用户\n\n错误：添加群组白名单时需要提供 chat_id。",
                        parse_mode=None,
                    )
                    return
            else:
                chat_id = None

            await add_to_whitelist(target_user_id, chat_type, chat_id, user_id)
            await message.answer(
                f"用户 {target_user_id} 已添加到白名单（{chat_type}, {chat_id}）。",
                parse_mode=None,
            )

    except ValueError:
        await message.answer(
            "命令参数错误，请检查格式\n\n/whitelist_add <user_id> [private|group] [chat_id] - 添加白名单用户\n\n错误：user_id 或 chat_id 必须是数字。",
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"添加白名单时出错: {e}", exc_info=True)
        await message.answer("操作失败，请稍后重试。", parse_mode=None)


async def cmd_whitelist_remove(message: Message):
    """移除白名单用户"""
    user_id = message.from_user.id
    args = message.text.split()[1:] if message.text else []

    if not args:
        await message.answer(
            "命令参数错误，请检查格式\n\n/whitelist_remove <user_id> [private|group] [chat_id] - 移除白名单用户",
            parse_mode=None,
        )
        return

    try:
        target_user_id = int(args[0])

        # 判断是超管还是群组管理员
        is_super = await check_super_admin(user_id)
        chat_id = None

        if message.chat.type in ["group", "supergroup"]:
            chat_id = message.chat.id
            # 群组管理员执行时，自动使用当前群组 ID
            if not is_super:
                success = await remove_from_whitelist(target_user_id, "group", chat_id)
                if success:
                    await message.answer(
                        f"用户 {target_user_id} 已从当前群组白名单移除。",
                        parse_mode=None,
                    )
                else:
                    await message.answer("用户不在当前群组白名单中。", parse_mode=None)
                return

        # 超管可以移除任意白名单
        if is_super:
            chat_type = args[1] if len(args) > 1 else "private"
            if chat_type == "group":
                if len(args) > 2:
                    chat_id = int(args[2])
                elif chat_id is None:
                    # 在私聊中，如果指定了 group 但没有提供 chat_id，需要提示
                    await message.answer(
                        "命令参数错误，请检查格式\n\n/whitelist_remove <user_id> [private|group] [chat_id] - 移除白名单用户\n\n错误：移除群组白名单时需要提供 chat_id。",
                        parse_mode=None,
                    )
                    return
            else:
                chat_id = None

            success = await remove_from_whitelist(target_user_id, chat_type, chat_id)
            if success:
                await message.answer(
                    f"用户 {target_user_id} 已从白名单移除（{chat_type}, {chat_id}）。",
                    parse_mode=None,
                )
            else:
                await message.answer("用户不在白名单中。", parse_mode=None)

    except ValueError:
        await message.answer(
            "命令参数错误，请检查格式\n\n/whitelist_remove <user_id> [private|group] [chat_id] - 移除白名单用户\n\n错误：user_id 或 chat_id 必须是数字。",
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"移除白名单时出错: {e}", exc_info=True)
        await message.answer("操作失败，请稍后重试。", parse_mode=None)


async def cmd_whitelist_list(message: Message):
    """查看白名单列表"""
    user_id = message.from_user.id
    args = message.text.split()[1:] if message.text else []

    try:
        # 判断是超管还是群组管理员
        is_super = await check_super_admin(user_id)
        chat_id = None

        if message.chat.type in ["group", "supergroup"]:
            chat_id = message.chat.id
            # 群组管理员执行时，自动使用当前群组 ID
            if not is_super:
                entries = await list_whitelist("group", chat_id)
                if not entries:
                    await message.answer("白名单为空。", parse_mode=None)
                    return

                # 格式化列表
                lines = []
                for entry in entries[:20]:  # 限制显示数量
                    lines.append(f"• 用户 {entry.user_id}")

                result = "当前群组白名单列表：\n" + "\n".join(lines)
                if len(entries) > 20:
                    result += f"\n... 还有 {len(entries) - 20} 条记录"

                await message.answer(result, parse_mode=None)
                return

        # 超管可以查看任意白名单
        if is_super:
            chat_type = args[0] if args else None
            if chat_type == "group":
                if len(args) > 1:
                    chat_id = int(args[1])
                else:
                    chat_id = None  # 查看所有群组白名单
            else:
                chat_id = None

            entries = await list_whitelist(chat_type, chat_id)

            if not entries:
                await message.answer("白名单为空。", parse_mode=None)
                return

            # 格式化列表
            lines = []
            for entry in entries[:20]:  # 限制显示数量
                chat_info = f"群组 {entry.chat_id}" if entry.chat_id else "私聊"
                lines.append(
                    f"• 用户 {entry.user_id} - {entry.chat_type} - {chat_info}"
                )

            result = "白名单列表：\n" + "\n".join(lines)
            if len(entries) > 20:
                result += f"\n... 还有 {len(entries) - 20} 条记录"

            await message.answer(result, parse_mode=None)

    except ValueError:
        await message.answer(
            "命令参数错误，请检查格式\n\n/whitelist_list [private|group] [chat_id] - 查看白名单列表\n\n错误：参数格式不正确。",
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"列出白名单时出错: {e}", exc_info=True)
        await message.answer("操作失败，请稍后重试。", parse_mode=None)


# ==================== 权限管理命令 ====================


async def cmd_permission_set(message: Message):
    """设置用户权限（仅超管）"""
    args = message.text.split()[1:] if message.text else []
    if len(args) < 2:
        await message.answer(
            "命令参数错误，请检查格式\n\n/permission_set <user_id> <role> - 设置用户权限\n角色: super_admin, user",
            parse_mode=None,
        )
        return

    try:
        target_user_id = int(args[0])
        role_str = args[1].lower()

        # 验证角色
        if role_str == "super_admin":
            role = UserRole.SUPER_ADMIN
        elif role_str == "user":
            role = UserRole.USER
        else:
            await message.answer(
                "命令参数错误，请检查格式\n\n/permission_set <user_id> <role> - 设置用户权限\n角色: super_admin, user\n\n错误：无效的角色。支持的角色: super_admin, user",
                parse_mode=None,
            )
            return

        # 设置权限
        await set_user_permission(target_user_id, role)
        await message.answer(
            f"用户 {target_user_id} 的权限已设置为 {role_str}。", parse_mode=None
        )

    except ValueError:
        await message.answer(
            "命令参数错误，请检查格式\n\n/permission_set <user_id> <role> - 设置用户权限\n角色: super_admin, user\n\n错误：user_id 必须是数字。",
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"设置用户权限时出错: {e}", exc_info=True)
        await message.answer("操作失败，请稍后重试。", parse_mode=None)


# ==================== 记忆管理命令 ====================


async def cmd_memory_list(message: Message):
    """查看长期记忆"""
    user_id = message.from_user.id
    args = message.text.split()[1:] if message.text else []

    try:
        # 判断是超管还是普通用户
        is_super = await check_super_admin(user_id)

        # 确定要查看的用户 ID
        if is_super and args and args[0].isdigit():
            target_user_id = int(args[0])
            query = args[1] if len(args) > 1 else None
        else:
            target_user_id = user_id
            query = args[0] if args else None

        # 获取记忆
        store = await get_store()
        namespace = ("memories", str(target_user_id))

        if query:
            # 语义搜索
            results = await store.asearch(namespace, query=query, limit=10)
        else:
            # 获取所有记忆（通过空查询）
            results = await store.asearch(namespace, query="", limit=20)

        if not results:
            await message.answer("未找到相关记忆。", parse_mode=None)
            return

        # 格式化结果
        lines = []
        for idx, result in enumerate(results, 1):
            key = result.key  # 使用属性访问
            value_dict = result.value  # 这是一个字典 {"value": "..."}
            # 从字典中提取实际内容
            content = (
                value_dict.get("value", "")
                if isinstance(value_dict, dict)
                else str(value_dict)
            )
            content = content[:100]  # 限制长度
            lines.append(f"{idx}. [{key}]: {content}")

        result_text = f"用户 {target_user_id} 的记忆：\n" + "\n".join(lines)
        await message.answer(result_text, parse_mode=None)

    except ValueError:
        await message.answer(
            "命令参数错误，请检查格式\n\n/memory_list [user_id] [query] - 查看长期记忆\n\n错误：参数格式不正确。",
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"列出记忆时出错: {e}", exc_info=True)
        await message.answer("操作失败，请稍后重试。", parse_mode=None)


async def cmd_memory_delete(message: Message):
    """删除长期记忆"""
    user_id = message.from_user.id
    args = message.text.split()[1:] if message.text else []

    if not args:
        await message.answer(
            "命令参数错误，请检查格式\n\n/memory_delete [user_id] <memory_key> - 删除长期记忆",
            parse_mode=None,
        )
        return

    try:
        # 判断是超管还是普通用户
        is_super = await check_super_admin(user_id)

        # 确定要删除的用户 ID 和 key
        if is_super and args[0].isdigit() and len(args) > 1:
            target_user_id = int(args[0])
            memory_key = args[1]
        else:
            target_user_id = user_id
            memory_key = args[0]

        # 删除记忆
        store = await get_store()
        namespace = ("memories", str(target_user_id))

        await store.adelete(namespace=namespace, key=memory_key)
        await message.answer(f"记忆 {memory_key} 已删除。", parse_mode=None)

    except ValueError:
        await message.answer(
            "命令参数错误，请检查格式\n\n/memory_delete [user_id] <memory_key> - 删除长期记忆\n\n错误：参数格式不正确。",
            parse_mode=None,
        )
    except Exception as e:
        logger.error(f"删除记忆时出错: {e}", exc_info=True)
        await message.answer("操作失败，请稍后重试。", parse_mode=None)


# ==================== 注册所有命令 ====================


def register_all_commands():
    """注册所有命令到命令注册表"""

    # 超管独占指令（仅私聊）
    command_registry.register(
        Command(
            name="group_authorize",
            description="授权群组",
            usage="/group_authorize <chat_id> - 授权群组",
            required_role="super_admin",
            allowed_chat_types=["private"],
            handler=cmd_group_authorize,
        )
    )

    command_registry.register(
        Command(
            name="group_revoke",
            description="撤销群组授权",
            usage="/group_revoke <chat_id> - 撤销群组授权",
            required_role="super_admin",
            allowed_chat_types=["private"],
            handler=cmd_group_revoke,
        )
    )

    command_registry.register(
        Command(
            name="group_list",
            description="查看所有已授权群组",
            usage="/group_list - 查看所有已授权群组",
            required_role="super_admin",
            allowed_chat_types=["private"],
            handler=cmd_group_list,
        )
    )

    command_registry.register(
        Command(
            name="permission_set",
            description="设置用户权限",
            usage="/permission_set <user_id> <role> - 设置用户权限\n角色: super_admin, user",
            required_role="super_admin",
            allowed_chat_types=["private"],
            handler=cmd_permission_set,
        )
    )

    # 管理指令（群组和私聊）
    command_registry.register(
        Command(
            name="whitelist_add",
            description="添加白名单用户",
            usage="/whitelist_add <user_id> [private|group] [chat_id] - 添加白名单用户",
            required_role="group_admin",
            allowed_chat_types=["private", "group"],
            handler=cmd_whitelist_add,
        )
    )

    command_registry.register(
        Command(
            name="whitelist_remove",
            description="移除白名单用户",
            usage="/whitelist_remove <user_id> [private|group] [chat_id] - 移除白名单用户",
            required_role="group_admin",
            allowed_chat_types=["private", "group"],
            handler=cmd_whitelist_remove,
        )
    )

    command_registry.register(
        Command(
            name="whitelist_list",
            description="查看白名单列表",
            usage="/whitelist_list [private|group] [chat_id] - 查看白名单列表",
            required_role="group_admin",
            allowed_chat_types=["private", "group"],
            handler=cmd_whitelist_list,
        )
    )

    # 普通指令（群组和私聊）
    command_registry.register(
        Command(
            name="memory_list",
            description="查看长期记忆",
            usage="/memory_list [user_id] [query] - 查看长期记忆",
            required_role="user",
            allowed_chat_types=["private", "group"],
            handler=cmd_memory_list,
        )
    )

    command_registry.register(
        Command(
            name="memory_delete",
            description="删除长期记忆",
            usage="/memory_delete [user_id] <memory_key> - 删除长期记忆",
            required_role="user",
            allowed_chat_types=["private", "group"],
            handler=cmd_memory_delete,
        )
    )
