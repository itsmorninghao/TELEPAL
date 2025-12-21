"""SQLAlchemy ORM 模型定义

本模块定义业务表的 ORM 模型，与 src/auth/models.py 中的领域模型对应。
每个 ORM 模型提供 to_domain() 方法转换为领域模型。
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Double,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

if TYPE_CHECKING:
    from src.auth.models import AuthorizedGroup, UserPermission, WhitelistEntry


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""

    pass


class UserPermissionModel(Base):
    """用户权限表 ORM 模型"""

    __tablename__ = "user_permissions"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="主键ID"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, comment="用户ID（Telegram用户ID）"
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="user", comment="用户角色（user/admin等）"
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间",
    )

    def to_domain(self) -> "UserPermission":
        """转换为领域模型"""
        from src.auth.models import UserPermission, UserRole

        return UserPermission(
            id=self.id,
            user_id=self.user_id,
            role=UserRole(self.role),
            created_at=self.created_at,
            updated_at=self.updated_at,
        )


class AuthorizedGroupModel(Base):
    """授权群组表 ORM 模型"""

    __tablename__ = "authorized_groups"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="主键ID"
    )
    group_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False, comment="群组ID"
    )
    chat_title: Mapped[Optional[str]] = mapped_column(String(255))
    authorized_by: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="授权人用户ID"
    )
    authorized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now(), comment="授权时间"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="是否启用"
    )

    __table_args__ = (Index("idx_authorized_groups_group_id", "group_id"),)

    def to_domain(self) -> "AuthorizedGroup":
        """转换为领域模型"""
        from src.auth.models import AuthorizedGroup

        return AuthorizedGroup(
            id=self.id,
            group_id=self.group_id,
            chat_title=self.chat_title,
            authorized_by=self.authorized_by,
            authorized_at=self.authorized_at,
            is_active=self.is_active,
        )


class WhitelistEntryModel(Base):
    """白名单条目表 ORM 模型"""

    __tablename__ = "whitelist"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="主键ID"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, comment="用户ID（Telegram用户ID）"
    )
    chat_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="聊天类型（private/group等）"
    )
    group_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="群组ID（Telegram群组ID，私聊时为空）"
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        BigInteger, comment="创建人用户ID"
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "chat_type", "group_id", name="uq_whitelist_user_chat"
        ),
        Index("idx_whitelist_user_id", "user_id"),
        Index("idx_whitelist_chat", "chat_type", "group_id"),
    )

    def to_domain(self) -> "WhitelistEntry":
        """转换为领域模型"""
        from src.auth.models import WhitelistEntry

        return WhitelistEntry(
            id=self.id,
            user_id=self.user_id,
            chat_type=self.chat_type,
            group_id=self.group_id,
            created_at=self.created_at,
            created_by=self.created_by,
        )


class UserProfileModel(Base):
    """用户资料表 ORM 模型"""

    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, comment="用户ID（Telegram用户ID，主键）"
    )
    latitude: Mapped[float] = mapped_column(Double, nullable=False, comment="纬度")
    longitude: Mapped[float] = mapped_column(Double, nullable=False, comment="经度")
    timezone: Mapped[Optional[str]] = mapped_column(
        String(100), comment="时区（如：Asia/Shanghai）"
    )
    location_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now(), comment="位置更新时间"
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now(), comment="创建时间"
    )

    __table_args__ = (Index("idx_user_profiles_user_id", "user_id"),)


class ScheduledTaskModel(Base):
    """定时任务表 ORM 模型

    用于存储用户通过自然语言创建的定时提醒任务。
    支持私聊和群聊场景，任务到期后通过 APScheduler 触发回调发送提醒消息。
    
    注意：chat_id 是消息目标ID，私聊时为 user_id，群聊时为 group_id。
    """

    __tablename__ = "scheduled_tasks"

    id: Mapped[int] = mapped_column(
        primary_key=True, autoincrement=True, comment="主键ID"
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="用户ID（Telegram用户ID）"
    )
    chat_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True, comment="消息目标ID（私聊时为user_id，群聊时为group_id）"
    )
    chat_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="聊天类型（'private' 或 'group'）"
    )
    content: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="任务内容（提醒消息内容）"
    )
    execute_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="执行时间（任务到期时间，带时区）",
    )
    is_executed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="是否已执行",
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="创建时间（带时区）",
    )
    executed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), comment="实际执行时间（带时区）"
    )

    __table_args__ = (
        Index("idx_scheduled_tasks_user_execute", "user_id", "execute_at"),
        Index("idx_scheduled_tasks_pending", "is_executed", "execute_at"),
    )
