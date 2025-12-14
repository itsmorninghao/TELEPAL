"""LangGraph Graph 定义和编排"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple, cast
from zoneinfo import ZoneInfo

from deepagents import create_deep_agent
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    trim_messages,
)
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from src.agent.prompts import (
    system_prompt_template,
    time_info_template,
    time_info_utc_template,
)
from src.agent.state import AgentState
from src.agent.tools import get_available_tools
from src.agent.tools.memory import user_id_context
from src.database import get_checkpointer
from src.database.repositories import profiles
from src.utils.settings import setting

logger = logging.getLogger(__name__)


def limit_messages(messages: List[BaseMessage], max_count: int) -> List[BaseMessage]:
    """使用 trim_messages 策略限制消息数量"""
    if len(messages) <= max_count:
        return messages

    trimmed_messages = trim_messages(
        messages,
        max_tokens=max_count,
        token_counter=len,
        strategy="last",
        include_system=True,
        start_on="human",
        allow_partial=False,
    )

    logger.debug(
        f"消息条数超过限制 {max_count}，已从 {len(messages)} 条截断为 {len(trimmed_messages)} 条"
    )
    return cast(List[BaseMessage], trimmed_messages)


def create_deep_agent_node(deep_agent, user_id: int):
    """创建 deep_agent 节点包装函数"""

    async def deep_agent_node(state: AgentState) -> Dict[str, Any]:
        context_messages = list(state["messages"])
        replied_text = state.get("replied_message")

        # 只有当：有回复内容 AND 历史记录不为空 AND 最后一条是用户消息 时，才执行
        if (
            replied_text
            and context_messages
            and isinstance(context_messages[-1], HumanMessage)
        ):
            last_msg = context_messages[-1]
            replied_context = f"用户回复了以下内容：\n{replied_text}\n\n"

            # 替换最后一条消息
            context_messages[-1] = HumanMessage(
                content=replied_context + str(last_msg.content),
                id=last_msg.id,
                additional_kwargs=last_msg.additional_kwargs,
                response_metadata=last_msg.response_metadata,
            )

        context_messages = limit_messages(
            context_messages, setting.MAX_MESSAGES_IN_STATE
        )

        # 在调用前插入当前时间信息
        user_location = await profiles.get_user_location(state["user_id"])
        if user_location and user_location.get("timezone"):
            try:
                timezone_str = user_location["timezone"]
                tz = ZoneInfo(timezone_str)
                now = datetime.now(tz)
                time_info_content = time_info_template.format(
                    timezone=timezone_str,
                    time=now.strftime("%H:%M"),
                    period=["凌晨", "早上", "下午", "晚上"][now.hour // 6],
                    date=f"{now.strftime('%Y-%m-%d')} ({['周一', '周二', '周三', '周四', '周五', '周六', '周日'][now.weekday()]})",
                )
                current_time_msg = SystemMessage(content=time_info_content)
                context_messages.insert(0, current_time_msg)
            except Exception as e:
                logger.warning(f"插入当前时间信息时出错: {e}")
        else:
            # 未设置时区时，也插入 UTC 时间信息
            try:
                now_utc = datetime.now(ZoneInfo("UTC"))
                time_info_content = time_info_utc_template.format(
                    time=now_utc.strftime("%H:%M"), date=now_utc.strftime("%Y-%m-%d")
                )
                current_time_msg = SystemMessage(content=time_info_content)
                context_messages.insert(0, current_time_msg)
            except Exception as e:
                logger.warning(f"插入 UTC 时间信息时出错: {e}")

        try:
            # 设置用户 ID 上下文
            user_id_context.set(state["user_id"])

            # 记录插入时间消息后的上下文长度
            input_len = len(context_messages)

            result = await deep_agent.ainvoke({"messages": context_messages})

            result_messages = result.get("messages", [])

            if len(result_messages) > input_len:
                new_messages = result_messages[input_len:]
            else:
                new_messages = []

            logger.info(
                f"为用户 {user_id} 生成回复成功，新增 {len(new_messages)} 条消息"
            )

            return {"messages": new_messages}

        except Exception as e:
            logger.error(f"调用 deep_agent 时出错: {e}", exc_info=True)
            error_message = AIMessage(
                content="抱歉，处理您的消息时遇到了问题，请稍后重试。"
            )
            return {"messages": [error_message]}

    return deep_agent_node


def create_agent_graph(deep_agent, user_id: int) -> StateGraph:
    """创建 Agent Graph"""

    workflow = StateGraph(AgentState)

    # 创建 deep_agent 节点
    agent_node = create_deep_agent_node(deep_agent, user_id)
    workflow.add_node("agent", agent_node)

    workflow.set_entry_point("agent")
    workflow.add_edge("agent", END)

    return workflow


async def get_compiled_graph(
    user_id: int, chat_type: str, chat_id: int | None = None
) -> Tuple[Any, Dict[str, Any]]:
    """获取编译后的 Graph，返回 (graph, config) 元组"""
    checkpointer = await get_checkpointer()

    # 计算 thread_id
    if chat_type == "private":
        thread_id = str(user_id)
    else:
        thread_id = str(chat_id)

    # 格式化 system_prompt
    system_prompt = system_prompt_template.format(
        chat_type=chat_type,
        user_id=user_id,
    )

    llm = ChatOpenAI(
        api_key=setting.OPENAI_API_KEY,
        base_url=setting.OPENAI_BASE_URL,
        model=setting.OPENAI_MODEL,
        temperature=0.7,
    )

    # 根据配置获取可用工具列表
    tools = get_available_tools()

    # 创建 deep_agent
    deep_agent = create_deep_agent(
        tools=tools,
        system_prompt=system_prompt,
        model=llm,
    )

    workflow = create_agent_graph(deep_agent, user_id)

    compiled_graph = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=[],
    )

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
        },
    }

    return compiled_graph, config
