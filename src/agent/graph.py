"""LangGraph Graph 定义和编排"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

from deepagents import create_deep_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from src.agent.prompts import system_prompt_template
from src.agent.state import AgentState
from src.bot.location_service import get_user_location
from src.utils.db.checkpointer import get_checkpointer
from src.utils.settings import setting
from src.utils.tools import get_available_tools
from src.utils.tools.memory import user_id_context

logger = logging.getLogger(__name__)


def limit_messages(messages: List[BaseMessage], max_count: int) -> List[BaseMessage]:
    """保留最新的 max_count 条消息"""
    if len(messages) <= max_count:
        return messages

    # 只保留最新的 max_count 条消息
    limited_messages = messages[-max_count:]
    logger.debug(
        f"消息条数超过限制 {max_count}，已截断为最新 {len(limited_messages)} 条"
    )
    return limited_messages


def create_deep_agent_node(deep_agent, user_id: int):
    """创建 deep_agent 节点包装函数"""

    async def deep_agent_node(state: AgentState) -> AgentState:
        # 构建消息上下文
        messages = state["messages"].copy()

        # 如果有被回复的消息，添加到上下文
        if state.get("replied_message"):
            replied_context = f"用户回复了以下内容：\n{state['replied_message']}\n\n"
            # 在最后一条消息前插入被回复的内容
            if messages:
                last_msg = messages[-1]
                if isinstance(last_msg, HumanMessage):
                    # 更新最后一条消息的内容
                    messages[-1] = HumanMessage(
                        content=replied_context + str(last_msg.content)
                    )

        try:
            user_id_context.set(state["user_id"])

            result = await deep_agent.ainvoke({"messages": messages})

            # 更新状态中的消息
            updated_messages = result.get("messages", messages)

            # 限制消息条数
            updated_messages = limit_messages(
                updated_messages, setting.MAX_MESSAGES_IN_STATE
            )

            state["messages"] = updated_messages

            logger.info(f"为用户 {user_id} 生成回复成功")

        except Exception as e:
            logger.error(f"调用 deep_agent 时出错: {e}", exc_info=True)
            error_message = AIMessage(
                content="抱歉，处理您的消息时遇到了问题，请稍后重试。"
            )
            state["messages"].append(error_message)

            # 限制消息条数（包括错误消息）
            state["messages"] = limit_messages(
                state["messages"], setting.MAX_MESSAGES_IN_STATE
            )

        return state

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

    # 获取用户时间信息
    time_info = "未设置时区信息"
    user_location = await get_user_location(user_id)
    if user_location and user_location.get("timezone"):
        try:
            timezone_str = user_location["timezone"]
            tz = ZoneInfo(timezone_str)
            now = datetime.now(tz)
            # 格式化时间信息
            time_info = (
                f"【状态: 已校准】\n"
                f"- 时区: {timezone_str}\n"
                f"- 时间: {now.strftime('%H:%M')}\n"
                f"- 时段: {['凌晨', '早上', '下午', '晚上'][now.hour // 6]}\n"
                f"- 日期: {now.strftime('%Y-%m-%d')} ({['周一', '周二', '周三', '周四', '周五', '周六', '周日'][now.weekday()]})"
            )
            logger.debug(f"用户时间信息: {time_info}")
        except Exception as e:
            logger.warning(f"格式化用户时间信息时出错: {e}")
            time_info = f"时区: {user_location.get('timezone', '未知')}"
    else:
        now_utc = datetime.now(ZoneInfo("UTC"))
        time_info = (
            f"【状态: 未设置时区 (使用 UTC 标准时)】\n"
            f"当前时间: {now_utc.strftime('%H:%M')} (UTC)\n"
            f"当前日期: {now_utc.strftime('%Y-%m-%d')}\n"
            f"⚠️ 警告: 此时间可能与用户当地时间严重偏差。\n"
            f"👉 策略: 请忽略此时间进行问候，除非用户主动询问，否则引导使用 /set_location"
        )
    # 格式化 system_prompt
    system_prompt = system_prompt_template.format(
        chat_type=chat_type,
        user_id=user_id,
        time_info=time_info,
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
