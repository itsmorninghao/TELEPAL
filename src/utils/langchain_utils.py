"""LangChain 相关工具函数"""

import logging
from typing import List, cast

from langchain_core.messages import BaseMessage, trim_messages

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

