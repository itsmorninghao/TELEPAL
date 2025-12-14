"""用户权限数据库操作"""

from typing import Optional

from sqlalchemy import delete, select, update

from src.auth.models import AuthorizedGroup, UserPermission, UserRole, WhitelistEntry
from src.database.engine import get_session
from src.database.models import (
    AuthorizedGroupModel,
    UserPermissionModel,
    WhitelistEntryModel,
)

# ==================== 用户权限操作 ====================


async def get_user_permission(user_id: int) -> Optional[UserPermission]:
    """获取用户权限"""
    async with get_session() as session:
        stmt = select(UserPermissionModel).where(UserPermissionModel.user_id == user_id)
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        return model.to_domain() if model else None


async def is_super_admin(user_id: int) -> bool:
    """检查用户是否为超管"""
    permission = await get_user_permission(user_id)
    return permission is not None and permission.role == UserRole.SUPER_ADMIN


async def set_user_permission(user_id: int, role: UserRole) -> UserPermission:
    """设置用户权限（存在则更新，不存在则创建）"""
    async with get_session() as session:
        # 先查询是否存在
        stmt = select(UserPermissionModel).where(UserPermissionModel.user_id == user_id)
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            # 更新现有记录
            model.role = role.value
        else:
            # 创建新记录
            model = UserPermissionModel(user_id=user_id, role=role.value)
            session.add(model)

        await session.flush()
        await session.refresh(model)
        return model.to_domain()


async def delete_user_permission(user_id: int) -> bool:
    """删除用户权限"""
    async with get_session() as session:
        stmt = delete(UserPermissionModel).where(UserPermissionModel.user_id == user_id)
        result = await session.execute(stmt)
        return result.rowcount == 1


# ==================== 群组授权操作 ====================


async def is_group_authorized(chat_id: int) -> bool:
    """检查群组是否已授权"""
    async with get_session() as session:
        stmt = select(AuthorizedGroupModel.id).where(
            AuthorizedGroupModel.chat_id == chat_id,
            AuthorizedGroupModel.is_active == True,  # noqa: E712
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None


async def get_authorized_group(chat_id: int) -> Optional[AuthorizedGroup]:
    """获取授权群组信息"""
    async with get_session() as session:
        stmt = select(AuthorizedGroupModel).where(
            AuthorizedGroupModel.chat_id == chat_id
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        return model.to_domain() if model else None


async def authorize_group(
    chat_id: int, chat_title: Optional[str], authorized_by: int
) -> AuthorizedGroup:
    """授权群组（存在则激活并更新，不存在则创建）"""
    async with get_session() as session:
        # 先查询是否存在
        stmt = select(AuthorizedGroupModel).where(
            AuthorizedGroupModel.chat_id == chat_id
        )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            # 更新现有记录
            model.is_active = True
            if chat_title:
                model.chat_title = chat_title
        else:
            # 创建新记录
            model = AuthorizedGroupModel(
                chat_id=chat_id,
                chat_title=chat_title,
                authorized_by=authorized_by,
            )
            session.add(model)

        await session.flush()
        await session.refresh(model)
        return model.to_domain()


async def revoke_group_authorization(chat_id: int) -> bool:
    """撤销群组授权"""
    async with get_session() as session:
        stmt = (
            update(AuthorizedGroupModel)
            .where(AuthorizedGroupModel.chat_id == chat_id)
            .values(is_active=False)
        )
        result = await session.execute(stmt)
        return result.rowcount == 1


async def list_authorized_groups() -> list[AuthorizedGroup]:
    """列出所有已授权的群组"""
    async with get_session() as session:
        stmt = (
            select(AuthorizedGroupModel)
            .where(AuthorizedGroupModel.is_active == True)  # noqa: E712
            .order_by(AuthorizedGroupModel.authorized_at.desc())
        )
        result = await session.execute(stmt)
        models = result.scalars().all()

        return [model.to_domain() for model in models]


# ==================== 白名单操作 ====================


async def is_user_whitelisted(
    user_id: int, chat_type: str, chat_id: Optional[int] = None
) -> bool:
    """检查用户是否在白名单中"""
    async with get_session() as session:
        # 使用 is_ 处理 NULL 比较
        if chat_id is None:
            stmt = select(WhitelistEntryModel.id).where(
                WhitelistEntryModel.user_id == user_id,
                WhitelistEntryModel.chat_type == chat_type,
                WhitelistEntryModel.chat_id.is_(None),
            )
        else:
            stmt = select(WhitelistEntryModel.id).where(
                WhitelistEntryModel.user_id == user_id,
                WhitelistEntryModel.chat_type == chat_type,
                WhitelistEntryModel.chat_id == chat_id,
            )
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None


async def add_to_whitelist(
    user_id: int,
    chat_type: str,
    chat_id: Optional[int],
    created_by: Optional[int] = None,
) -> WhitelistEntry:
    """添加用户到白名单（已存在则返回现有记录）"""
    async with get_session() as session:
        # 先检查是否已存在
        if chat_id is None:
            stmt = select(WhitelistEntryModel).where(
                WhitelistEntryModel.user_id == user_id,
                WhitelistEntryModel.chat_type == chat_type,
                WhitelistEntryModel.chat_id.is_(None),
            )
        else:
            stmt = select(WhitelistEntryModel).where(
                WhitelistEntryModel.user_id == user_id,
                WhitelistEntryModel.chat_type == chat_type,
                WhitelistEntryModel.chat_id == chat_id,
            )
        result = await session.execute(stmt)
        model = result.scalar_one_or_none()

        if model:
            return model.to_domain()

        # 创建新记录
        model = WhitelistEntryModel(
            user_id=user_id,
            chat_type=chat_type,
            chat_id=chat_id,
            created_by=created_by,
        )
        session.add(model)
        await session.flush()
        await session.refresh(model)
        return model.to_domain()


async def remove_from_whitelist(
    user_id: int, chat_type: str, chat_id: Optional[int] = None
) -> bool:
    """从白名单中移除用户"""
    async with get_session() as session:
        # 使用 is_ 处理 NULL 比较
        if chat_id is None:
            stmt = delete(WhitelistEntryModel).where(
                WhitelistEntryModel.user_id == user_id,
                WhitelistEntryModel.chat_type == chat_type,
                WhitelistEntryModel.chat_id.is_(None),
            )
        else:
            stmt = delete(WhitelistEntryModel).where(
                WhitelistEntryModel.user_id == user_id,
                WhitelistEntryModel.chat_type == chat_type,
                WhitelistEntryModel.chat_id == chat_id,
            )
        result = await session.execute(stmt)
        return result.rowcount == 1


async def list_whitelist(
    chat_type: Optional[str] = None, chat_id: Optional[int] = None
) -> list[WhitelistEntry]:
    """列出白名单，可按 chat_type 和 chat_id 过滤"""
    async with get_session() as session:
        stmt = select(WhitelistEntryModel)

        # 构建过滤条件
        if chat_type and chat_id is not None:
            stmt = stmt.where(
                WhitelistEntryModel.chat_type == chat_type,
                WhitelistEntryModel.chat_id == chat_id,
            )
        elif chat_type:
            stmt = stmt.where(WhitelistEntryModel.chat_type == chat_type)

        stmt = stmt.order_by(WhitelistEntryModel.created_at.desc())
        result = await session.execute(stmt)
        models = result.scalars().all()

        return [model.to_domain() for model in models]
