"""LangGraph Graph 定义和编排"""

import logging
from typing import Any, Dict, List, Tuple

from deepagents import create_deep_agent
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from src.agent.prompts import system_prompt
from src.agent.state import AgentState
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
