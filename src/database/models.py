"""SQLAlchemy ORM 模型定义

本模块定义业务表的 ORM 模型，与 src/auth/models.py 中的领域模型对应。
每个 ORM 模型提供 to_domain() 方法转换为领域模型。
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Double, Index, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

if TYPE_CHECKING:
    from src.auth.models import AuthorizedGroup, UserPermission, WhitelistEntry


class Base(DeclarativeBase):
    """SQLAlchemy 声明式基类"""

    pass


class UserPermissionModel(Base):
    """用户权限表 ORM 模型"""

    __tablename__ = "user_permissions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
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

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    chat_title: Mapped[Optional[str]] = mapped_column(String(255))
    authorized_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    authorized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (Index("idx_authorized_groups_chat_id", "chat_id"),)

    def to_domain(self) -> "AuthorizedGroup":
        """转换为领域模型"""
        from src.auth.models import AuthorizedGroup

        return AuthorizedGroup(
            id=self.id,
            chat_id=self.chat_id,
            chat_title=self.chat_title,
            authorized_by=self.authorized_by,
            authorized_at=self.authorized_at,
            is_active=self.is_active,
        )


class WhitelistEntryModel(Base):
    """白名单条目表 ORM 模型"""

    __tablename__ = "whitelist"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chat_type: Mapped[str] = mapped_column(String(20), nullable=False)
    chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )
    created_by: Mapped[Optional[int]] = mapped_column(BigInteger)

    __table_args__ = (
        UniqueConstraint("user_id", "chat_type", "chat_id", name="uq_whitelist_user_chat"),
        Index("idx_whitelist_user_id", "user_id"),
        Index("idx_whitelist_chat", "chat_type", "chat_id"),
    )

    def to_domain(self) -> "WhitelistEntry":
        """转换为领域模型"""
        from src.auth.models import WhitelistEntry

        return WhitelistEntry(
            id=self.id,
            user_id=self.user_id,
            chat_type=self.chat_type,
            chat_id=self.chat_id,
            created_at=self.created_at,
            created_by=self.created_by,
        )


class UserProfileModel(Base):
    """用户资料表 ORM 模型"""

    __tablename__ = "user_profiles"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    latitude: Mapped[float] = mapped_column(Double, nullable=False)
    longitude: Mapped[float] = mapped_column(Double, nullable=False)
    timezone: Mapped[Optional[str]] = mapped_column(String(100))
    location_updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, server_default=func.now()
    )

    __table_args__ = (Index("idx_user_profiles_user_id", "user_id"),)

