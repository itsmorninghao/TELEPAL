"""消息过滤器"""

from aiogram.filters import Filter, or_f
from aiogram.types import Message


class PrivateChatFilter(Filter):
    """私聊消息过滤器"""

    async def __call__(self, message: Message) -> bool:
        """检查是否为私聊消息"""
        return message.chat.type == "private"


class GroupMentionFilter(Filter):
    """群组 @ 提及过滤器"""

    async def __call__(self, message: Message, bot) -> bool:
        """检查是否为群组 @ 提及消息"""
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
