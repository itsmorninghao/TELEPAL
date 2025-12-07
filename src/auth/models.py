"""用户权限模型"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class UserRole(str, Enum):
    """用户角色枚举"""

    SUPER_ADMIN = "super_admin"
    USER = "user"
    # 注意：群组管理员通过 Telegram API 实时识别，不存储在数据库中


@dataclass
class UserPermission:
    """用户权限模型"""

    id: Optional[int] = None
    user_id: int = 0
    role: UserRole = UserRole.USER
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_db_row(cls, row) -> "UserPermission":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            role=UserRole(row["role"]),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )


@dataclass
class AuthorizedGroup:
    """授权群组模型"""

    id: Optional[int] = None
    chat_id: int = 0
    chat_title: Optional[str] = None
    authorized_by: int = 0
    authorized_at: Optional[datetime] = None
    is_active: bool = True

    @classmethod
    def from_db_row(cls, row) -> "AuthorizedGroup":
        return cls(
            id=row["id"],
            chat_id=row["chat_id"],
            chat_title=row.get("chat_title"),
            authorized_by=row["authorized_by"],
            authorized_at=row.get("authorized_at"),
            is_active=row.get("is_active", True),
        )


@dataclass
class WhitelistEntry:
    """白名单条目模型"""

    id: Optional[int] = None
    user_id: int = 0
    chat_type: str = ""  # 'private' 或 'group'
    chat_id: Optional[int] = None  # 群组 ID（私聊时为 None）
    created_at: Optional[datetime] = None
    created_by: Optional[int] = None

    @classmethod
    def from_db_row(cls, row) -> "WhitelistEntry":
        return cls(
            id=row["id"],
            user_id=row["user_id"],
            chat_type=row["chat_type"],
            chat_id=row.get("chat_id"),
            created_at=row.get("created_at"),
            created_by=row.get("created_by"),
        )
