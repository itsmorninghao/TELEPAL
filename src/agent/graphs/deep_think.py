import logging
import time
import uuid
from pathlib import Path

from aiogram.types import FSInputFile
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend
from langchain_openai import ChatOpenAI
from telegramify_markdown import markdownify

from src.agent.prompts import get_template
from src.agent.tools import get_tools
from src.bot import bot_instance
from src.utils.settings import setting

logger = logging.getLogger(__name__)

# 消息更新频率限制
UPDATE_INTERVAL = 2.0  # 秒
_last_update_times: dict[tuple[int, int], float] = {}


def get_deep_think_graph(topic: str, workspace_path: Path):
    """定义并返回 deepagents 编译后的图"""

    llm = ChatOpenAI(
        api_key=setting.OPENAI_API_KEY,
        base_url=setting.OPENAI_BASE_URL,
        model=setting.OPENAI_MODEL,
        temperature=0,
    )

    template = get_template("deep_think")
    rendered_system_prompt = template.render(topic=topic)

    return create_deep_agent(
        model=llm,
        tools=get_tools("deep_think"),
        backend=FilesystemBackend(root_dir=workspace_path, virtual_mode=True),
        system_prompt=rendered_system_prompt,
    )


async def _update_status_message(bot, chat_id: int, message_id: int, text: str) -> None:
    """更新消息显示当前调用的工具"""
    # 时间频率限制
    message_key = (chat_id, message_id)
    current_time = time.time()

    last_update_time = _last_update_times.get(message_key, 0)

    if current_time - last_update_time < UPDATE_INTERVAL:
        return

    try:
        await bot.edit_message_text(
            text=markdownify(text),
            chat_id=chat_id,
            message_id=message_id,
            parse_mode="MarkdownV2",
        )
        _last_update_times[message_key] = current_time
    except Exception as e:
        logger.debug(f"编辑消息失败: {e}")


def _extract_tool_name(message) -> str | None:
    """从消息中提取工具名称"""
    if not hasattr(message, "tool_calls") or not message.tool_calls:
        return None
    return message.tool_calls[0].get("name")


async def run_deep_think_task(msg_target_id: int, topic: str):
    """异步执行该图的工人函数"""
    bot = bot_instance.get()
    if not bot:
        return

    try:
        task_id = str(uuid.uuid4())
        workspace_path = (
            Path("./data/deep_think")
            / str(abs(msg_target_id))
            / f"{time.strftime('%Y%m%d%H%M%S')}-{task_id}"
        )
        workspace_path.mkdir(parents=True, exist_ok=True)

        graph = get_deep_think_graph(topic, workspace_path)

        status_msg = await bot.send_message(
            msg_target_id,
            markdownify(f"深度代理已创建，正在初始化研究方案: {topic}"),
            parse_mode="MarkdownV2",
        )

        last_msg = None
        last_tool_name = None

        async for event in graph.astream(
            {"messages": [{"role": "user", "content": topic}]},
            stream_mode="values",
        ):
            logger.debug(f"收到事件: {event}")

            if "messages" not in event:
                continue

            last_msg = event["messages"][-1]
            tool_name = _extract_tool_name(last_msg)

            if tool_name and tool_name != last_tool_name:
                last_tool_name = tool_name
                await _update_status_message(
                    bot,
                    msg_target_id,
                    status_msg.message_id,
                    f"正在调用工具:`{tool_name}`",
                )

        result_path = workspace_path / "result.md"
        if result_path.exists():
            doc = FSInputFile(str(result_path))
            await _update_status_message(
                bot, msg_target_id, status_msg.message_id, "深度研究完成，正在发送结果"
            )
            await bot.send_document(
                chat_id=msg_target_id, document=doc, caption="深度研究完成，请下载"
            )
        else:
            await bot.send_message(msg_target_id, "没有生成有效的 result.md")

    except Exception as e:
        logger.error(f"任务失败: {e}", exc_info=True)
        await bot.send_message(msg_target_id, "抱歉，研究过程中发生了意外错误。")
