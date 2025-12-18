"""LangGraph Graph 定义和编排"""

import logging
from typing import Any, Dict, Tuple

from langchain.agents import create_agent
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
)
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from src.agent.prompts import system_prompt_template
from src.agent.state import AgentState
from src.agent.tools import (
    chat_id_context,
    chat_type_context,
    get_available_tools,
    user_id_context,
)
from src.database import get_checkpointer
from src.utils.langchain_utils import limit_messages
from src.utils.settings import setting

logger = logging.getLogger(__name__)


def create_agent_node(agent, user_id: int):
    """创建 agent 节点包装函数"""

    async def agent_node(state: AgentState) -> Dict[str, Any]:
        context_messages = list(state["messages"])
        replied_text = state.get("replied_message")

        # 只有当：有回复内容 AND 历史记录不为空 AND 最后一条是用户消息 时，才执行
        # 即处理tg上回复某条消息的情况
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

        try:
            # 设置上下文变量
            user_id_context.set(state["user_id"])
            chat_type_context.set(state["chat_type"])
            # chat_id: 私聊时为 user_id，群聊时为 chat_id
            effective_chat_id = (
                state["chat_id"] if state["chat_id"] else state["user_id"]
            )
            chat_id_context.set(effective_chat_id)

            # 记录上下文长度
            input_len = len(context_messages)

            result = await agent.ainvoke({"messages": context_messages})

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
            logger.error(f"调用 agent 时出错: {e}", exc_info=True)
            error_message = AIMessage(
                content="抱歉，处理您的消息时遇到了问题，请稍后重试。"
            )
            return {"messages": [error_message]}

    return agent_node


def create_agent_graph(agent, user_id: int) -> StateGraph:
    """创建 Agent Graph"""

    workflow = StateGraph(AgentState)

    # 创建 agent 节点
    agent_node = create_agent_node(agent, user_id)
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

    # 生成 system prompt
    system_prompt = system_prompt_template.format(
        chat_type=chat_type,
        user_id=user_id,
    )

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=system_prompt,
    )

    workflow = create_agent_graph(agent, user_id)

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
