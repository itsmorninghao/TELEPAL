"""消息处理器"""

import logging
from typing import Optional

import telegramify_markdown
from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import Message, ReplyKeyboardRemove
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.graph import get_compiled_graph, limit_messages
from src.agent.state import AgentState
from src.auth.service import (
    check_group_authorized,
    check_private_authorization,
    check_user_role_in_group,
)
from src.bot.filters import (
    group_mention_filter,
    not_command_filter,
    reply_to_bot_filter,
)
from src.bot.location_service import get_timezone_from_location, save_user_location
from src.utils.settings import setting

logger = logging.getLogger(__name__)

router = Router()


def convert_to_telegram_markdown(text: str) -> str:
    """使用 telegramify-markdown 库进行转换"""
    try:
        return telegramify_markdown.markdownify(text)
    except Exception as e:
        logger.warning(f"Markdown 转换失败: {e}")
        return text


async def handle_chat(message: Message) -> None:
    """处理聊天消息，调用 AI 生成回复"""
    try:
        user_message = message.text or message.caption or ""

        # 获取用户和聊天信息
        if not message.from_user:
            logger.warning("收到没有 from_user 的消息")
            return
        user_id = message.from_user.id
        chat_type = "private" if message.chat.type == "private" else "group"
        chat_id = message.chat.id if chat_type == "group" else None

        # 检查是否回复消息，提取被回复的内容
        replied_message: Optional[str] = None
        if message.reply_to_message:
            replied_message = (
                message.reply_to_message.text
                or message.reply_to_message.caption
                or None
            )

        # 显示"正在输入"状态
        if setting.ENABLE_TYPING_ACTION:
            await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        # 获取或创建 Agent Graph
        graph, config = await get_compiled_graph(user_id, chat_type, chat_id)

        # 构建初始状态
        thread_id = config["configurable"]["thread_id"]
        initial_state: AgentState = {
            "messages": [HumanMessage(content=user_message)],
            "replied_message": replied_message,
            "user_id": user_id,
            "chat_type": chat_type,
            "chat_id": chat_id,
            "thread_id": thread_id,
        }

        # 调用 Agent 生成回复
        result = await graph.ainvoke(initial_state, config=config)

        # 确保返回的状态中的消息不超过限制（防止从 checkpointer 恢复的旧状态超过限制）
        if len(result["messages"]) > setting.MAX_MESSAGES_IN_STATE:
            result["messages"] = limit_messages(
                result["messages"], setting.MAX_MESSAGES_IN_STATE
            )

        # 获取最后一条 AI 消息
        ai_messages = [msg for msg in result["messages"] if isinstance(msg, AIMessage)]
        if not ai_messages:
            await message.answer("抱歉，无法生成回复。")
            return

        # 获取回复内容
        reply_content = ai_messages[-1].content

        # 将标准 Markdown 转换为 Telegram MarkdownV2 格式
        reply_content = convert_to_telegram_markdown(str(reply_content))

        # 检查消息长度
        if len(reply_content) > setting.MAX_MESSAGE_LENGTH:
            reply_content = reply_content[: setting.MAX_MESSAGE_LENGTH - 3] + "..."

        # 发送回复（使用 MarkdownV2 格式）
        await message.answer(reply_content, parse_mode="MarkdownV2")

        logger.info(f"为用户 {user_id} 生成并发送回复成功")

    except Exception as e:
        logger.error(f"处理消息时发生错误: {e}", exc_info=True)
        await message.answer("处理您的消息时遇到了问题，请稍后重试。")


async def handle_location(message: Message) -> None:
    """处理用户位置信息，保存到数据库"""
    try:
        user_id = message.from_user.id
        latitude = message.location.latitude
        longitude = message.location.longitude

        timezone = await get_timezone_from_location(latitude, longitude)

        if timezone == "Unknown":
            await message.answer("无法获取时区,请联系管理员或者重试", parse_mode=None)
            return

        await save_user_location(user_id, latitude, longitude, timezone)

        await message.answer(
            f"✅ 位置信息已保存！\n\n"
            f"📍 位置：纬度 {latitude:.6f}, 经度 {longitude:.6f}\n"
            f"🕐 时区：{timezone}",
            parse_mode=None,
        )

    except Exception as e:
        logger.error(f"处理位置信息时发生错误: {e}", exc_info=True)
        await message.answer(
            "处理位置信息时遇到了问题，请稍后重试。",
            parse_mode=None,
        )


@router.message(F.location)
async def handle_location_message(message: Message):
    """处理位置消息"""
    latitude = message.location.latitude
    longitude = message.location.longitude

    await message.answer(
        f"收到！你的位置是：\n纬度: {latitude}\n经度: {longitude}\n\n正在设置时区...",
        parse_mode=None,
        reply_markup=ReplyKeyboardRemove(),
    )

    await handle_location(message)


@router.message(not_command_filter)
async def handle_message(message: Message):
    """处理非命令消息（AI 对话）"""
    chat_type = "private" if message.chat.type == "private" else "group"
    user_id = message.from_user.id if message.from_user else None

    if not user_id:
        return

    # 私聊处理流程
    if chat_type == "private":
        is_authorized = await check_private_authorization(user_id)
        if not is_authorized:
            await message.answer("未获授权")
            return

        await handle_chat(message)

    # 群组处理流程
    else:
        is_group_authorized = await check_group_authorized(message.chat.id)
        if not is_group_authorized:
            try:
                await message.answer(
                    f"本群 {message.chat.id} 未获授权，机器人将退出。", parse_mode=None
                )
                await message.bot.leave_chat(message.chat.id)
            except TelegramForbiddenError:
                logger.debug("机器人已不在群组中")
            except Exception as e:
                logger.error(f"退群失败: {e}", exc_info=True)
            return

        # 检查是否 @ 机器人或回复机器人
        is_mention = await group_mention_filter(message, bot=message.bot)
        is_reply = await reply_to_bot_filter(message, bot=message.bot)

        if not (is_mention or is_reply):
            return

        # 用户身份判定
        user_role = await check_user_role_in_group(
            message.bot, message.chat.id, user_id
        )
        if user_role == "unauthorized":
            await message.answer("您未获本群授权")
            return

        await handle_chat(message)
