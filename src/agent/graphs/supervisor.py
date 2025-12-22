import logging
from typing import Any, Dict

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from src.agent.prompts import render_supervisor_prompt
from src.agent.state import SupervisorState
from src.agent.tools import get_tools
from src.utils.langchain_utils import limit_messages
from src.utils.settings import setting

logger = logging.getLogger(__name__)


def create_supervisor_node(model: ChatOpenAI):
    """创建 supervisor 工厂函数"""

    prompt_template = ChatPromptTemplate.from_messages(
        [
            ("system", "{system_content}"),
            MessagesPlaceholder(variable_name="messages"),
        ]
    )

    async def supervisor_node(state: SupervisorState) -> Dict[str, Any]:
        """主节点"""
        processed_messages = list(state["messages"])
        replied_text = state.get("replied_message")

        # 如果回复了消息，则将回复的内容添加到消息中
        if (
            replied_text
            and processed_messages
            and isinstance(processed_messages[-1], HumanMessage)
        ):
            last_msg = processed_messages[-1]
            processed_messages[-1] = HumanMessage(
                content=f"用户回复了以下内容：\n{replied_text}\n\n{last_msg.content}",
                id=last_msg.id,
            )

        processed_messages = limit_messages(
            processed_messages, setting.MAX_MESSAGES_IN_STATE
        )

        system_prompt = render_supervisor_prompt(
            chat_type=state.get("chat_type", "private"),
            user_id=state.get("user_id", 0),
        )

        # 调用模型
        chain = prompt_template | model
        response = await chain.ainvoke(
            {"system_content": system_prompt, "messages": processed_messages}
        )

        return {"messages": [response]}

    return supervisor_node


def get_supervisor_graph(checkpointer):
    """构建并编译主图"""

    tools = get_tools("supervisor")

    # 初始化模型
    llm = ChatOpenAI(
        api_key=setting.OPENAI_API_KEY,
        base_url=setting.OPENAI_BASE_URL,
        model=setting.OPENAI_MODEL,
        temperature=0.3,
    ).bind_tools(tools)

    workflow = StateGraph(SupervisorState)

    workflow.add_node("supervisor", create_supervisor_node(llm))

    workflow.set_entry_point("supervisor")

    workflow.add_node("tools", ToolNode(tools))

    workflow.add_conditional_edges(
        "supervisor",
        tools_condition,
    )

    workflow.add_edge("tools", "supervisor")

    return workflow.compile(checkpointer=checkpointer)
