"""Agent 状态定义"""

from typing import Annotated, Optional, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Agent 状态结构"""

    # 用户消息内容
    messages: Annotated[list, add_messages]

    # 被回复的消息内容（可选）
    replied_message: Optional[str]

    # 用户 ID（用于长期记忆检索）
    user_id: int

    # 聊天类型（'private' 或 'group'）
    chat_type: str

    # 群组 ID（群组时为群组 ID，私聊时为 None）
    chat_id: Optional[int]

    # Thread ID（用于对话记忆隔离）
    thread_id: str
