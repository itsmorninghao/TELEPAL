"""消息过滤器"""

from typing import List

from aiogram.filters import Filter, or_f
from aiogram.types import Message

from src.auth.service import check_super_admin, check_user_role_in_group


class RoleFilter(Filter):
    """权限过滤器，检查用户是否具有指定角色"""

    def __init__(self, roles: List[str]):
        """
        初始化权限过滤器

        Args:
            roles: 允许的角色列表，如 ["super_admin", "group_admin"]
        """
        self.roles = roles

    async def __call__(self, message: Message) -> bool:
        """检查用户权限"""
        if not message.from_user:
            return False

        user_id = message.from_user.id
        is_private = message.chat.type == "private"

        # 先检查超管权限（适用于所有角色）
        is_super = await check_super_admin(user_id)
        if "super_admin" in self.roles and is_super:
            return True

        # 检查群组管理员权限
        if "group_admin" not in self.roles:
            return False

        # 私聊中，群组管理员权限等同于超管权限
        if is_private:
            return is_super

        # 群组中，检查是否为群管或超管
        user_role = await check_user_role_in_group(
            message.bot, message.chat.id, user_id
        )
        return user_role in ["super_admin", "group_admin"]


class PrivateChatFilter(Filter):
    """私聊消息过滤器"""

    async def __call__(self, message: Message) -> bool:
        """检查是否为私聊消息"""
        return message.chat.type == "private"


class GroupChatFilter(Filter):
    """群组消息过滤器"""

    async def __call__(self, message: Message) -> bool:
        """检查是否为群组消息"""
        return message.chat.type in ["group", "supergroup"]


class NotCommandFilter(Filter):
    """非命令消息过滤器"""

    async def __call__(self, message: Message) -> bool:
        """检查是否为非命令消息（不以 / 开头）"""
        text = message.text or message.caption or ""
        return not text.strip().startswith("/")


class GroupMentionFilter(Filter):
    """群组 @ 提及过滤器"""

    async def __call__(self, message: Message, bot) -> bool:
        """检查是否为群组 @ 提及消息"""
        if message.chat.type not in ["group", "supergroup"] or not message.entities:
            return False

        bot_me = await bot.get_me()
        bot_username = bot_me.username
        bot_id = bot_me.id

        for entity in message.entities:
            # mention 类型：@username
            if entity.type == "mention" and message.text:
                mention = message.text[entity.offset : entity.offset + entity.length]
                if mention == f"@{bot_username}":
                    return True

            # text_mention 类型：直接提及用户
            elif entity.type == "text_mention":
                if entity.user and entity.user.id == bot_id:
                    return True

            # bot_command 类型：/command@bot_username
            elif entity.type == "bot_command" and message.text and "@" in message.text:
                command_text = message.text[entity.offset : entity.offset + entity.length]
                if f"@{bot_username}" in command_text:
                    return True

        return False


class ReplyMessageFilter(Filter):
    """回复消息过滤器"""

    async def __call__(self, message: Message) -> bool:
        """检查是否为回复消息"""
        return message.reply_to_message is not None


class ReplyToBotFilter(Filter):
    """回复机器人消息过滤器"""

    async def __call__(self, message: Message, bot) -> bool:
        """检查是否为回复机器人发送的消息"""
        if not message.reply_to_message:
            return False

        # 检查被回复的消息是否是机器人发送的
        bot_me = await bot.get_me()
        return (
            message.reply_to_message.from_user is not None
            and message.reply_to_message.from_user.id == bot_me.id
        )


# 组合过滤器：私聊或群组 @ 提及
PrivateOrMentionFilter = or_f(PrivateChatFilter(), GroupMentionFilter())

# 组合过滤器：回复消息（私聊或群组）
ReplyFilter = ReplyMessageFilter()

# 单例过滤器实例
not_command_filter = NotCommandFilter()
group_mention_filter = GroupMentionFilter()
reply_to_bot_filter = ReplyToBotFilter()
