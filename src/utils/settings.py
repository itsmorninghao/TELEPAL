"""项目配置和初始化模块"""

import sys
from pathlib import Path
from typing import Any

from langchain_openai import OpenAIEmbeddings
from pydantic import Field
from pydantic_settings import BaseSettings

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


class Settings(BaseSettings):
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    TELEGRAM_BOT_TOKEN: str = Field(..., description="Telegram Bot Token")

    POSTGRES_HOST: str = Field(..., description="PostgreSQL 主机地址")
    POSTGRES_PORT: int = Field(..., description="PostgreSQL 端口")
    POSTGRES_DB: str = Field(..., description="PostgreSQL 数据库名")
    POSTGRES_USER: str = Field(..., description="PostgreSQL 用户名")
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL 密码")

    OPENAI_API_KEY: str = Field(..., description="OpenAI 兼容 API Key")
    OPENAI_BASE_URL: str = Field(..., description="OpenAI 兼容 API Base URL")
    OPENAI_MODEL: str = Field(..., description="OpenAI 兼容模型名称")

    TAVILY_API_KEY: str | None = Field(
        default=None, description="Tavily Search API Key"
    )

    LOG_LEVEL: str = Field(
        default="INFO", description="日志级别: DEBUG, INFO, WARNING, ERROR"
    )
    ENABLE_TYPING_ACTION: bool = Field(default=True, description="是否启用正在输入提示")
    MAX_MESSAGE_LENGTH: int = Field(
        default=4000, le=4096, description="最大消息长度 (Telegram 限制为 4096)"
    )
    MAX_MESSAGES_IN_STATE: int = Field(
        ..., description="State 中最大对话条数,不限制可能会超过大模型的上下文"
    )

    INITIAL_SUPER_ADMINS: str | None = Field(
        default=None, description="初始超管用户 ID (Telegram User ID，多个用逗号分隔)"
    )

    EMBEDDING_API_KEY: str = Field(..., description="嵌入模型 API Key")
    EMBEDDING_BASE_URL: str = Field(..., description="嵌入模型 API Base URL")
    EMBEDDING_MODEL: str = Field(..., description="嵌入模型名称")
    EMBEDDING_DIMS: int = Field(..., description="嵌入向量维度")


setting = Settings()


def get_embeddings() -> OpenAIEmbeddings:
    """获取嵌入模型实例"""
    return OpenAIEmbeddings(
        api_key=setting.EMBEDDING_API_KEY,
        base_url=setting.EMBEDDING_BASE_URL,
        model=setting.EMBEDDING_MODEL,
        check_embedding_ctx_length=False,
    )


def get_index_config(embeddings: OpenAIEmbeddings) -> dict:
    """获取向量索引配置"""
    return {"dims": setting.EMBEDDING_DIMS, "embed": embeddings, "fields": ["value"]}


def get_db_config() -> dict[str, Any]:
    """获取数据库配置"""
    return {
        "host": setting.POSTGRES_HOST,
        "port": setting.POSTGRES_PORT,
        "database": setting.POSTGRES_DB,
        "user": setting.POSTGRES_USER,
        "password": setting.POSTGRES_PASSWORD,
    }
