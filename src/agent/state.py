"""状态定义"""

from typing import Annotated, List, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class SupervisorState(TypedDict):
    """Supervisor 状态结构"""

    # 用户消息内容
    messages: Annotated[list[AnyMessage], add_messages]

    # 被回复的消息内容（可选）
    replied_message: Optional[str]

    # 用户 ID（用于长期记忆检索）
    user_id: int

    # 聊天类型（'private' 或 'group'）
    chat_type: str

    # 群组 ID（群组时为群组 ID，私聊时为 None）
    group_id: Optional[int]

    # 消息目标 ID（私聊时为 user_id，群聊时为 group_id）
    chat_id: int

    # Thread ID（用于对话记忆隔离）
    thread_id: str


class SearchSubState(TypedDict):
    """搜索子图状态"""

    query: str

    results: List[str]

    # 子图内部的对话流，包含爬虫返回的原始数据等
    messages: Annotated[List[AnyMessage], add_messages]

    # 最终生成的摘要结果
    answer: Optional[str]
