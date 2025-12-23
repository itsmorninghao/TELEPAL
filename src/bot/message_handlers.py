"""消息处理器"""

import logging
from typing import Optional

from aiogram import F, Router, types
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
from langchain_core.messages import AIMessage, HumanMessage
from telegramify_markdown import markdownify

from src.agent.graph import get_compiled_graph
from src.agent.state import SupervisorState
from src.auth.service import (
    check_group_authorized,
    check_private_authorization,
    check_user_role_in_group,
)
from src.bot import (
    bot_instance,
    chat_id_context,
    chat_type_context,
    group_id_context,
    user_id_context,
)
from src.bot.filters import (
    group_mention_filter,
    not_command_filter,
    reply_to_bot_filter,
)
from src.bot.location_service import get_timezone_from_location, save_user_location
from src.bot.states import LocationStates
from src.utils.langchain_utils import limit_messages
from src.utils.settings import project_root, setting

logger = logging.getLogger(__name__)

router = Router()

FEATURED_COUNTRIES = [
    {
        "label": "🇨🇳 中国 (CST)",
        "zone": "Asia/Shanghai",
        "name": "China",
        "desc": "中国标准时间 (GMT+8)。",
        "latitude": 31.2304,
        "longitude": 121.4737,
    },
    {
        "label": "🇯🇵 日本 (JST)",
        "zone": "Asia/Tokyo",
        "name": "Japan",
        "desc": "日本标准时间 (GMT+9)。",
        "latitude": 35.6762,
        "longitude": 139.6503,
    },
    {
        "label": "🇷🇺 俄罗斯 (MSK)",
        "zone": "Europe/Moscow",
        "name": "Russia",
        "desc": "莫斯科标准时间 (GMT+3)。",
        "latitude": 55.7558,
        "longitude": 37.6173,
    },
    {
        "label": "🇺🇸 美国 (EST)",
        "zone": "America/New_York",
        "name": "USA",
        "desc": "美国东部时间 (GMT-5)。",
        "latitude": 40.7128,
        "longitude": -74.0060,
    },
    {
        "label": "🇬🇧 英国 (GMT)",
        "zone": "Europe/London",
        "name": "UK",
        "desc": "格林威治标准时间 (GMT+0)。",
        "latitude": 51.5074,
        "longitude": -0.1278,
    },
    {
        "label": "🇫🇷 法国 (CET)",
        "zone": "Europe/Paris",
        "name": "France",
        "desc": "中部欧洲时间 (GMT+1)。",
        "latitude": 48.8566,
        "longitude": 2.3522,
    },
]


class TimezoneSelect(CallbackData, prefix="tz_sel"):
    zone: str


async def handle_chat(message: Message) -> None:
    """处理聊天消息，调用 AI 生成回复"""
    try:
        if not message.from_user:
            return

        user_id = message.from_user.id
        chat_type = "private" if message.chat.type == "private" else "group"

        # 群组ID：群聊时为群组ID，私聊时为None
        group_id = message.chat.id if chat_type == "group" else None

        # 消息目标ID：私聊时为user_id，群聊时为group_id
        chat_id = user_id if chat_type == "private" else group_id

        # 设置上下文变量（必须在确定正确的值后设置）
        user_id_context.set(user_id)
        chat_type_context.set(chat_type)
        group_id_context.set(group_id)
        chat_id_context.set(chat_id)
        bot_instance.set(message.bot)

        user_message = message.text or message.caption or ""

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
        graph, config = await get_compiled_graph(user_id, chat_type, group_id)

        # 构建初始状态
        thread_id = config["configurable"]["thread_id"]
        initial_state: SupervisorState = {
            "messages": [HumanMessage(content=user_message)],
            "replied_message": replied_message,
            "user_id": user_id,
            "chat_type": chat_type,
            "group_id": group_id,
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
        reply_content = markdownify(str(reply_content))

        # 检查消息长度
        if len(reply_content) > setting.MAX_MESSAGE_LENGTH:
            reply_content = reply_content[: setting.MAX_MESSAGE_LENGTH - 3] + "..."

        # 发送回复（使用 MarkdownV2 格式）
        await message.answer(reply_content, parse_mode="MarkdownV2")

        logger.info(f"为用户 {user_id} 生成并发送回复成功")

    except Exception as e:
        logger.error(f"处理消息时发生错误: {e}", exc_info=True)
        await message.answer("处理您的消息时遇到了问题，请稍后重试。")


async def finalize_location_setup(
    event: types.Message | types.CallbackQuery,
    user_id: int,
    lat: float,
    lon: float,
    tz: str,
):
    """保存位置信息并通知用户"""
    try:
        await save_user_location(user_id, lat, lon, tz)

        text = (
            f"✅ 位置信息已保存！\n\n"
            f"📍 位置：纬度 {lat:.6f}, 经度 {lon:.6f}\n"
            f"🕐 时区：{tz}"
        )

        if isinstance(event, types.Message):
            await event.answer(
                text, reply_markup=ReplyKeyboardRemove(), parse_mode=None
            )
        else:
            await event.message.answer(
                text, reply_markup=ReplyKeyboardRemove(), parse_mode=None
            )
            await event.answer()

    except Exception as e:
        logger.error(f"保存位置时出错: {e}", exc_info=True)
        error_msg = "处理位置信息时遇到了问题，请稍后重试。"
        if isinstance(event, types.Message):
            await event.answer(
                error_msg, reply_markup=ReplyKeyboardRemove(), parse_mode=None
            )
        else:
            await event.message.answer(error_msg, parse_mode=None)


@router.callback_query(TimezoneSelect.filter())
async def handle_timezone_selection(
    callback: types.CallbackQuery, callback_data: TimezoneSelect, state: FSMContext
):
    """处理手动点击国家按钮的逻辑"""
    await state.clear()

    # 从 FEATURED_COUNTRIES 中匹配经纬度
    selected = next(
        (c for c in FEATURED_COUNTRIES if c["zone"] == callback_data.zone), None
    )

    if selected:
        await finalize_location_setup(
            callback,
            callback.from_user.id,
            selected["latitude"],
            selected["longitude"],
            selected["zone"],
        )
    else:
        await callback.answer()  # 处理回调
        await callback.message.answer(
            "抱歉，所选地区无效。请使用 /set_location 重新设置。",
            reply_markup=ReplyKeyboardRemove(),
        )


@router.message(LocationStates.waiting_for_location)
async def handle_location_message(message: Message, state: FSMContext):
    """处理位置消息或拒绝位置请求"""

    # 处理拒绝
    if message.text == "🚫 我拒绝!":
        await state.clear()
        await message.answer(
            "好的，您可以随时使用 /set_location 重新设置。",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # 处理手动选择
    if message.text == "🌍 手动选择":
        # 注意：这里不需要 clear state，因为用户还没选完
        builder = InlineKeyboardBuilder()
        for country in FEATURED_COUNTRIES:
            builder.button(
                text=country["label"],
                callback_data=TimezoneSelect(zone=country["zone"]),
            )
        builder.adjust(2)

        await message.answer(
            "🌏 *跨越山海，只为精准陪伴*",
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardRemove(),
        )

        # 使用本地文件路径发送图片和内联键盘
        image_path = project_root / "resources" / "images" / "location-select.jpg"
        photo = FSInputFile(str(image_path))

        await message.answer_photo(
            photo=photo,
            caption="在下方选择您所在的区域：",
            parse_mode="Markdown",
            reply_markup=builder.as_markup(),
        )
        return

    # 处理自动发送的位置
    if message.location:
        await state.clear()
        lat, lon = message.location.latitude, message.location.longitude
        timezone = await get_timezone_from_location(lat, lon)

        if timezone == "Unknown":
            await message.answer(
                "无法解析该经纬度的时区，请尝试手动选择。",
                reply_markup=ReplyKeyboardRemove(),
            )
            return

        await finalize_location_setup(message, message.from_user.id, lat, lon, timezone)
    else:
        await state.clear()
        await message.answer(
            "请发送位置信息，或者点击下方的按钮。\n\n"
            "如果您想取消设置，可以点击「🚫 我拒绝!」按钮，或使用 /set_location 重新开始。",
            reply_markup=ReplyKeyboardRemove(),
        )


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
        group_id = message.chat.id
        is_group_authorized = await check_group_authorized(group_id)
        if not is_group_authorized:
            try:
                await message.answer(
                    f"本群 {group_id} 未获授权，机器人将退出。", parse_mode=None
                )
                await message.bot.leave_chat(group_id)
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
        user_role = await check_user_role_in_group(message.bot, group_id, user_id)
        if user_role == "unauthorized":
            await message.answer("您未获本群授权")
            return

        await handle_chat(message)
